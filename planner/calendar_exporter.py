"""
iCalendar (.ics) Exporter for Scholarship Deadlines and Milestones.
Generates RFC 5545 compliant calendar files for Google Calendar, Apple Calendar, and Outlook,
with built-in reminder alarms (60 days, 30 days, 7 days, and 48 hours before deadlines)
plus "start by" events for every paper that still has to be obtained.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from .models import CandidateProfile, MatchResult
from .roadmap import select_shortlist, build_action_plan


MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4, "may": 5,
    "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def parse_deadline_date(deadline_text: str, default_year: int) -> Optional[date]:
    """Best-effort parse of free-text deadlines (used for scraped pages without a deadline pattern)."""
    text = deadline_text.strip().lower()
    for pattern, order in ((r"([0-9]{1,2})\s+([a-z]+)", "dm"), (r"([a-z]+)\s+([0-9]{1,2})", "md")):
        m = re.search(pattern, text)
        if m:
            day_s, month_s = (m.group(1), m.group(2)) if order == "dm" else (m.group(2), m.group(1))
            if month_s in MONTH_MAP:
                month = MONTH_MAP[month_s]
                year = default_year - 1 if month >= 8 else default_year
                return date(year, month, min(int(day_s), 28))
    for name, month in MONTH_MAP.items():
        if name in text:
            year = default_year - 1 if month >= 8 else default_year
            return date(year, month, 15 if "mid" in text else (5 if "early" in text else 28))
    return None


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> List[str]:
    """RFC 5545 line folding: at most 75 octets per line, continuation lines start with a space."""
    out, raw, limit = [], line.encode("utf-8"), 75
    while len(raw) > limit:
        cut = limit
        while (raw[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(("" if not out else " ") + raw[:cut].decode("utf-8"))
        raw, limit = raw[cut:], 74
    out.append(("" if not out else " ") + raw.decode("utf-8"))
    return out


def _alarm(trigger: str, text: str) -> List[str]:
    return ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(text)}", f"TRIGGER:{trigger}", "END:VALARM"]


def _event(uid: str, day: date, summary: str, description: str, url: Optional[str], alarms: List[List[str]], stamp: str) -> List[str]:
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
             f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}", f"SUMMARY:{_escape(summary)}",
             f"DESCRIPTION:{_escape(description)}"]
    if url:
        lines.append(f"URL:{url}")
    lines += ["STATUS:CONFIRMED", "TRANSP:TRANSPARENT"]
    for a in alarms:
        lines += a
    lines.append("END:VEVENT")
    return lines


def generate_ics_content(profile: CandidateProfile, matches: List[MatchResult],
                         shortlist: Optional[List[MatchResult]] = None,
                         actions: Optional[List[Dict[str, Any]]] = None,
                         today: Optional[date] = None) -> str:
    today = today or date.today()
    shortlist = shortlist if shortlist is not None else select_shortlist(matches)
    actions = actions if actions is not None else build_action_plan(profile, shortlist, today)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Global Scholarship Navigator//Application Planner//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{_escape('Scholarship Deadlines - ' + profile.full_name)}",
             "X-WR-TIMEZONE:UTC"]

    tracked = {m.scholarship.id for m in shortlist}
    for m in [m for m in matches if m.is_eligible]:
        s, r = m.scholarship, m.readiness
        if not r or not r.deadline or r.deadline < today:
            continue
        if s.id not in tracked and m.match_status not in ("High Match", "Moderate Match"):
            continue
        est = " (estimated - verify)" if r.deadline_is_estimate else ""
        description = (
            f"{s.name} ({s.country})\nDeadline: {r.deadline.isoformat()}{est} - {r.deadline_label}\n"
            f"Fit {m.fit_score:.0f}/100 · readiness {r.percent:.0f}% · {r.timeline_status}\n"
            f"Missing: {', '.join(q.name for q in r.missing) or 'nothing'}\nPortal: {s.official_portal}"
        )
        lines += _event(
            f"{s.id}-{profile.target_intake_year}-deadline@scholarship-navigator.local", r.deadline,
            f"🚨 Deadline: {s.name}{est}", description, s.official_portal,
            [_alarm("-P60D", f"60 days until the {s.name} deadline"),
             _alarm("-P30D", f"Reminder: 30 days until {s.name} application deadline!"),
             _alarm("-P7D", f"Final week: 7 days remaining for {s.name} submission!"),
             _alarm("-PT48H", f"Urgent: 48 hours left to submit {s.name} application!")],
            stamp,
        )

    for i, a in enumerate(actions):
        if a["kind"] != "paper" or not a["start_by"]:
            continue
        day = max(a["start_by"], today)
        lines += _event(
            f"task-{i}-{a['doc']}-{profile.target_intake_year}@scholarship-navigator.local", day,
            f"📄 Start: {a['title']}", f"Needed for: {', '.join(a['needed_for'])}\n{a['details']}", None,
            [_alarm("-P1D", f"Tomorrow: start '{a['title']}'")], stamp,
        )

    lines.append("END:VCALENDAR")
    folded: List[str] = []
    for line in lines:
        folded += _fold(line)
    return "\r\n".join(folded) + "\r\n"


def export_calendar_ics(profile: CandidateProfile, matches: List[MatchResult], output_path: str,
                        shortlist: Optional[List[MatchResult]] = None, actions: Optional[List[Dict[str, Any]]] = None,
                        today: Optional[date] = None) -> str:
    content = generate_ics_content(profile, matches, shortlist=shortlist, actions=actions, today=today)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")
    return str(out_file.resolve())
