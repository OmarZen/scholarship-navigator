"""
Personalized, dated action plan.

Tasks are scheduled backwards from each shortlisted scholarship's deadline using the lead time of every
missing paper (data/document_catalog.json). Shared papers (passport, transcripts, references...) become one
task covering every scholarship that needs them, due before the earliest of those deadlines.
"""

from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional

from .models import CandidateProfile, MatchResult, RequirementStatus
from .documents import catalog_doc, DEADLINE_BUFFER_DAYS

INACTIVE_TIMELINES = {"Deadline passed", "Not feasible this cycle"}
PHASES = [
    ("Start now", "Overdue or due to start this week"),
    ("Next 30 days", "Start within the next month"),
    ("1-3 months", "Start in 1 to 3 months"),
    ("3+ months", "Later in the cycle"),
    ("After submitting", "Interviews, offers and post-selection papers"),
]


def select_shortlist(matches: List[MatchResult], size: int = 8, include_ids: Iterable[str] = (),
                     exclude_ids: Iterable[str] = ()) -> List[MatchResult]:
    """Best-priority scholarships that are still open, plus any the user already tracks (minus skipped ones)."""
    exclude = set(exclude_ids)
    include = set(include_ids) - exclude
    active = [
        m for m in matches
        if m.is_eligible and m.readiness and m.readiness.timeline_status not in INACTIVE_TIMELINES
        and m.scholarship.id not in exclude
    ]
    active.sort(key=lambda m: -m.priority_score)
    chosen = active[:size]
    chosen_ids = {m.scholarship.id for m in chosen}
    for m in matches:
        if m.scholarship.id in include and m.scholarship.id not in chosen_ids and m.is_eligible:
            chosen.append(m)
            chosen_ids.add(m.scholarship.id)
    return chosen


def _bucket(start_by: Optional[date], today: date) -> str:
    if start_by is None:
        return "After submitting"
    if start_by <= today + timedelta(days=7):
        return "Start now"
    if start_by <= today + timedelta(days=30):
        return "Next 30 days"
    if start_by <= today + timedelta(days=90):
        return "1-3 months"
    return "3+ months"


def _task(title: str, kind: str, start_by: Optional[date], due_by: Optional[date], today: date,
          needed_for: List[str], scholarship_ids: List[str], details: str, doc: Optional[str] = None) -> Dict[str, Any]:
    overdue = bool(start_by and start_by < today)
    return {
        "title": title,
        "kind": kind,
        "doc": doc,
        "start_by": start_by,
        "due_by": due_by,
        "overdue": overdue,
        "bucket": _bucket(start_by, today),
        "needed_for": needed_for,
        "scholarship_ids": scholarship_ids,
        "details": details,
    }


def _shared_paper_tasks(shortlist: List[MatchResult], today: date) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for m in shortlist:
        r = m.readiness
        if not r or not r.deadline:
            continue
        for req in r.requirements:
            if req.scope != "shared" or req.units >= 1.0 or req.stage != "application" or req.optional:
                continue
            key = "references" if req.category == "references" else req.doc
            g = grouped.setdefault(key, {"reqs": [], "matches": []})
            g["reqs"].append(req)
            g["matches"].append(m)

    tasks = []
    for key, g in grouped.items():
        reqs: List[RequirementStatus] = g["reqs"]
        matches: List[MatchResult] = g["matches"]
        names = sorted({m.scholarship.name for m in matches})
        ids = sorted({m.scholarship.id for m in matches})
        start_by = min((q.start_by for q in reqs if q.start_by), default=None)
        due_by = min(m.readiness.deadline for m in matches) - timedelta(days=DEADLINE_BUFFER_DAYS)
        if key == "references":
            need: Dict[str, int] = {}
            for q in reqs:
                need[q.name] = max(need.get(q.name, 0), q.count)
            summary = "; ".join(f"{n}: {c}" for n, c in need.items())
            title = "Secure recommendation letters"
            details = (f"Most demanding requirement per type - {summary}. Approach referees with a brag sheet; "
                       f"some programs need their own template or online upload.")
            doc = "references"
        else:
            q = reqs[0]
            issues = sorted({i for x in reqs for i in x.issues})
            title = f"Get {q.name}" if q.state == "missing" else f"Finish {q.name} ({q.state.replace('_', ' ')})"
            details = q.how_to_obtain + (" Issues: " + "; ".join(issues) + "." if issues else "")
            doc = q.doc
        tasks.append(_task(title, "paper", start_by, due_by, today, names, ids, details, doc))
    return tasks


def _scholarship_tasks(m: MatchResult, today: date) -> List[Dict[str, Any]]:
    s, r = m.scholarship, m.readiness
    tasks: List[Dict[str, Any]] = []
    if not r:
        return tasks
    deadline = r.deadline
    if deadline and r.deadline_is_estimate:
        tasks.append(_task(
            f"Confirm the {s.name} deadline", "verify", today, min(today + timedelta(days=7), deadline), today,
            [s.name], [s.id],
            f"Current date {deadline.isoformat()} is an estimate ({r.deadline_label}). Check {s.official_portal} and record it "
            f"with `cli.py deadline --scholarship {s.id} --date YYYY-MM-DD --source URL`.",
        ))
    for req in r.requirements:
        if req.scope != "per_scholarship" or req.units >= 1.0:
            continue
        if req.stage == "later":
            tasks.append(_task(f"{s.name}: {req.name} (after submission)", "after", None, None, today,
                               [s.name], [s.id], req.label + (f" — {req.notes}" if req.notes else ""), req.doc))
            continue
        if req.optional:
            continue
        count = f" ({req.count})" if req.count > 1 else ""
        words = f", {req.words} words" if req.words else ""
        due = deadline - timedelta(days=DEADLINE_BUFFER_DAYS) if deadline else None
        tasks.append(_task(f"{s.name}: {req.name}{count}{words}", "write" if req.category in ("essays", "letters") else "form",
                           req.start_by, due, today, [s.name], [s.id], req.label, req.doc))
    if deadline:
        tasks.append(_task(f"Submit {s.name}", "submit", deadline - timedelta(days=7), deadline - timedelta(days=2), today,
                           [s.name], [s.id],
                           f"Submit at least 48 hours early on {s.application_portal_system}. Save the confirmation in submitted/."))
    for req in r.requirements:
        if req.scope == "shared" and req.stage == "later" and req.units < 1.0:
            tasks.append(_task(f"{s.name}: {req.name} (after submission)", "after", None, None, today,
                               [s.name], [s.id], req.label, req.doc))
    if s.timeline.interview_period and "no interview" not in s.timeline.interview_period.lower():
        tasks.append(_task(f"Prepare for the {s.name} interview", "after", None, None, today, [s.name], [s.id],
                           f"Interview period: {s.timeline.interview_period}. Practice with `cli.py interview`."))
    return tasks


def _profile_fix_tasks(shortlist: List[MatchResult], today: date) -> List[Dict[str, Any]]:
    fixes: Dict[str, List[MatchResult]] = {}
    for m in shortlist:
        for g in m.gate_checks:
            if g.result == "unknown" and g.fix:
                fixes.setdefault(g.fix, []).append(m)
    return [
        _task(f"Fill a profile gap: {fix}", "profile", today, today + timedelta(days=3), today,
              sorted({m.scholarship.name for m in ms}), sorted({m.scholarship.id for m in ms}),
              "Missing information makes the eligibility check inconclusive.")
        for fix, ms in fixes.items()
    ]


def build_action_plan(profile: CandidateProfile, shortlist: List[MatchResult], today: Optional[date] = None) -> List[Dict[str, Any]]:
    today = today or date.today()
    tasks = _profile_fix_tasks(shortlist, today) + _shared_paper_tasks(shortlist, today)
    for m in shortlist:
        tasks.extend(_scholarship_tasks(m, today))
    order = {name: i for i, (name, _) in enumerate(PHASES)}
    tasks.sort(key=lambda t: (order[t["bucket"]], t["start_by"] or date.max, t["due_by"] or date.max, t["title"]))
    return tasks


def generate_roadmap(profile: CandidateProfile, matches: List[MatchResult], today: Optional[date] = None,
                     shortlist_size: int = 8) -> Dict[str, Any]:
    today = today or date.today()
    shortlist = select_shortlist(matches, size=shortlist_size)
    actions = build_action_plan(profile, shortlist, today)
    phases = []
    for name, objective in PHASES:
        bucket_tasks = [t for t in actions if t["bucket"] == name]
        phases.append({
            "phase": name,
            "timeframe": objective,
            "objective": objective,
            "tasks": [
                {
                    "task": t["title"],
                    "urgency": "Overdue" if t["overdue"] else name,
                    "details": t["details"],
                    "start_by": t["start_by"].isoformat() if t["start_by"] else None,
                    "due_by": t["due_by"].isoformat() if t["due_by"] else None,
                    "needed_for": t["needed_for"],
                }
                for t in bucket_tasks
            ],
        })
    return {
        "candidate": profile.full_name,
        "target_intake": profile.target_intake_year,
        "target_degree": profile.target_degree,
        "generated_on": today.isoformat(),
        "top_targets": [m.scholarship.name for m in shortlist],
        "actions": actions,
        "phases": phases,
    }
