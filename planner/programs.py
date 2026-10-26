"""
Program finder: individual programs inside a scholarship scheme (each Erasmus Mundus Joint Master,
each Intra-Africa mobility project). Programs live in data/programs/*.json.

A program score (0-100) combines:
  field relevance 50 · host country vs your target countries 20 · language 15 · funding status 15
Discontinued programs, programs for other degree levels, and programs whose nationality rule excludes
the candidate are marked ineligible.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import ApplicationState, CandidateProfile, Program, ProgramMatch
from .deadlines import DeadlineInfo, pattern_date
from .fields import FIELD_GROUPS, groups_for
from .regions import in_group, in_list, normalize_country, same_country
from .language import to_ielts

PROGRAMS_DIR = Path(__file__).parent.parent / "data" / "programs"
STATUS_POINTS = {"open": 15.0, "upcoming": 12.0, "unknown": 8.0, "self_funded_only": 3.0, "discontinued": 0.0}
STOP_WORDS = {"and", "for", "of", "the", "in", "with", "master", "masters", "msc", "international", "european",
              "erasmus", "mundus", "joint", "programme", "program", "engineering", "systems", "science", "sciences",
              "technologies", "technology", "sustainable", "sustainability", "advanced", "bachelor", "bsc", "studies",
              "applied", "intelligent", "smart", "digital", "innovation", "integrated", "modern", "new"}
# Too broad to signal a field match on their own (they still count inside a multi-word phrase).
GENERIC_TERMS = {"intelligence", "security", "power", "control", "learning", "machine", "design", "management",
                 "data", "information", "materials", "energy", "art", "arts", "computing", "computer", "analysis",
                 "modelling", "modeling", "development", "environment", "environmental", "health", "food", "business",
                 "production", "process", "processes", "industry", "industrial", "communication", "communications",
                 "society", "societies", "low", "high", "systems", "network", "networks"}


def load_programs(directory: Path = PROGRAMS_DIR) -> List[Program]:
    programs: List[Program] = []
    if not directory.exists():
        return programs
    for path in sorted(directory.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                programs.append(Program(**item))
    return programs


def programs_for(scholarship_id: str, programs: Optional[List[Program]] = None) -> List[Program]:
    return [p for p in (programs if programs is not None else load_programs()) if p.parent_scholarship == scholarship_id]


def _phrases(texts: Iterable[str]) -> List[str]:
    out: List[str] = []
    for t in texts:
        for part in re.split(r",|;|/|&|\band\b|\(|\)", (t or "").lower()):
            part = part.strip(" .-")
            if len(part) >= 3 and part not in out:
                out.append(part)
    return out


def _terms(phrase: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", phrase.lower()) if len(w) > 2 and w not in STOP_WORDS]


def _contains(haystack: str, needle: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None


def _specific(terms: Iterable[str]) -> set:
    return {t for t in terms if t not in GENERIC_TERMS}


def field_relevance(profile: CandidateProfile, program: Program) -> tuple:
    """Returns (label, points out of 50, matched terms).

    strong  = a shared multi-word phrase ("machine learning", "power electronics") or 2+ shared specific terms
    partial = related field group (25-35), or one specific shared term (15; 35 together with a group match)
    """
    cand_texts = [profile.field_of_study, profile.current_degree, profile.thesis_title or ""] + profile.field_keywords
    cand_phrases = _phrases(cand_texts)
    prog_phrases = _phrases(program.fields + [program.name])

    phrase_hits: List[str] = []
    for cp in cand_phrases:
        for pp in prog_phrases:
            shorter, longer = (cp, pp) if len(cp) <= len(pp) else (pp, cp)
            if len(_terms(shorter)) >= 2 and _contains(longer, shorter):
                phrase_hits.append(shorter)
    term_hits = sorted(_specific(t for p in cand_phrases for t in _terms(p))
                       & _specific(t for p in prog_phrases for t in _terms(p)))

    cand_groups = groups_for(cand_texts)
    prog_groups = set(program.field_groups) or groups_for(program.fields + [program.name])
    overlap = cand_groups & prog_groups
    group_names = sorted(g.replace("_", " ") for g in overlap)

    if phrase_hits or len(term_hits) >= 2:
        return "strong", 50.0, list(dict.fromkeys(phrase_hits + term_hits))[:5]
    if overlap:
        share = len(overlap) / max(len(prog_groups), 1)
        points = 35.0 if term_hits else 25.0 + 10.0 * share
        return "partial", points, list(dict.fromkeys(term_hits + group_names))
    if term_hits:
        return "partial", 15.0, term_hits
    return "none", 5.0, []


def _country_points(profile: CandidateProfile, program: Program) -> tuple:
    if not profile.target_countries:
        return 20.0, []
    hosts = program.host_countries or [u.country for u in program.universities if u.country]
    matched = [h for h in hosts if in_list(h, profile.target_countries)]
    if matched:
        return 20.0, matched
    europe_targets = any(in_group(t, "europe") for t in profile.target_countries)
    if europe_targets and any(in_group(h, "europe") for h in hosts):
        return 8.0, []
    return 0.0, []


def _location_warning(profile: CandidateProfile, program: Program) -> Optional[str]:
    """Programs move students between host countries, so they only stay at home when every host is home."""
    if profile.study_location == "both":
        return None
    home = normalize_country(profile.residence)
    hosts = program.host_countries or [u.country for u in program.universities if u.country]
    only_home = bool(hosts) and all(same_country(h, home) for h in hosts)
    if profile.study_location == "home" and not only_home:
        return f"Taught abroad ({', '.join(hosts) or 'several countries'}); you want to study in {home}."
    if profile.study_location == "abroad" and only_home:
        return f"Taught only in {home}, your own country; you want to study abroad."
    return None


def _language_points(profile: CandidateProfile, program: Program) -> tuple:
    ielts = to_ielts(profile.english_test, profile.english_score)
    if program.ielts_min is None:
        return (12.0 if ielts else 6.0), None
    if ielts is None:
        return 5.0, f"Needs about IELTS {program.ielts_min:g}; no test reported."
    if ielts >= program.ielts_min:
        return 15.0, None
    if ielts >= program.ielts_min - 0.5:
        return 8.0, f"IELTS {ielts:g} is just under the {program.ielts_min:g} requirement."
    return 3.0, f"IELTS {ielts:g} is below the {program.ielts_min:g} requirement."


def program_deadline(program: Program, intake_year: int) -> tuple:
    """(date, is_estimate) for the candidate's intake, or (None, True)."""
    est = program.deadline
    if not est:
        return None, True
    known = est.known_dates.get(str(intake_year))
    if known:
        return date.fromisoformat(known), False
    if est.month and est.day:
        return pattern_date(est, intake_year), True
    return None, True


def match_program(profile: CandidateProfile, program: Program, today: Optional[date] = None) -> ProgramMatch:
    today = today or date.today()
    reasons: List[str] = []
    warnings: List[str] = []
    eligible = True

    if profile.target_degree not in program.degrees:
        eligible = False
        warnings.append(f"Offers {', '.join(program.degrees)}; you target {profile.target_degree}.")
    if program.status == "discontinued":
        eligible = False
        warnings.append("Program discontinued or no longer admitting students.")
    nat = program.nationality
    if nat.mode == "include" and not (in_list(profile.nationality, nat.countries)
                                      or any(in_group(profile.nationality, r) for r in nat.regions)):
        eligible = False
        warnings.append(f"Only for citizens of {', '.join(nat.regions) or 'listed countries'}.")
    if in_list(profile.nationality, nat.exclude_countries):
        eligible = False
        warnings.append(f"{normalize_country(profile.nationality)} citizens are excluded.")
    location_warning = _location_warning(profile, program)
    if location_warning:
        eligible = False
        warnings.append(location_warning)

    label, field_pts, terms = field_relevance(profile, program)
    if label == "strong":
        reasons.append(f"Strong field match: {', '.join(terms)}.")
    elif label == "partial":
        reasons.append(f"Related field ({', '.join(terms)}).")
    else:
        warnings.append("Your field does not match this program's focus.")

    country_pts, matched = _country_points(profile, program)
    if matched:
        reasons.append(f"Study in your target countries: {', '.join(matched)}.")
    elif profile.target_countries:
        warnings.append(f"Host countries ({', '.join(program.host_countries) or 'n/a'}) are outside your targets.")

    lang_pts, lang_warning = _language_points(profile, program)
    if lang_warning:
        warnings.append(lang_warning)

    status_pts = STATUS_POINTS[program.status]
    if program.status == "self_funded_only" or program.scholarships_available is False:
        status_pts = min(status_pts, 3.0)
        warnings.append("No scholarships announced for the next intake (self-funded places only).")

    deadline, is_est = program_deadline(program, profile.target_intake_year)
    days_left = (deadline - today).days if deadline else None
    open_for_intake = program.status != "discontinued" and not (days_left is not None and days_left < 0)
    if days_left is not None and days_left < 0:
        warnings.append(f"The {profile.target_intake_year} deadline ({deadline.isoformat()}) has passed.")

    score = field_pts + country_pts + lang_pts + status_pts
    if not eligible:
        score = 0.0
    return ProgramMatch(
        program=program, score=round(score, 1), eligible=eligible, field_match=label, matched_terms=terms,
        host_countries_in_targets=matched, deadline=deadline, deadline_is_estimate=is_est, days_left=days_left,
        open_for_intake=open_for_intake, reasons=reasons, warnings=warnings,
    )


def rank_programs(profile: CandidateProfile, programs: Optional[List[Program]] = None, today: Optional[date] = None,
                  scholarship_id: Optional[str] = None, field: Optional[str] = None,
                  countries: Optional[List[str]] = None, include_closed: bool = False) -> List[ProgramMatch]:
    programs = programs if programs is not None else load_programs()
    if scholarship_id:
        programs = [p for p in programs if p.parent_scholarship == scholarship_id]
    if field:
        wanted = field.lower()
        programs = [p for p in programs if wanted in " ".join(p.fields + [p.name, p.acronym] + p.field_groups).lower()
                    or wanted in {g for g in FIELD_GROUPS if g in p.field_groups}]
    if countries:
        programs = [p for p in programs if any(in_list(c, p.host_countries) for c in countries)]
    matches = [match_program(profile, p, today) for p in programs]
    if not include_closed:
        matches = [m for m in matches if m.eligible and m.open_for_intake]
    matches.sort(key=lambda m: (-m.score, m.deadline or date.max))
    return matches


def chosen_programs_deadline(state: Optional[ApplicationState], programs: List[Program], intake_year: int,
                             today: date) -> Optional[DeadlineInfo]:
    """Earliest upcoming deadline among the programs the candidate chose (status.json chosen_programs)."""
    if not state or not state.chosen_programs:
        return None
    by_id = {p.id: p for p in programs}
    options = []
    for pid in state.chosen_programs:
        p = by_id.get(pid)
        if not p:
            continue
        d, est = program_deadline(p, intake_year)
        if d and d >= today:
            options.append((d, est, p))
    if not options:
        return None
    d, est, p = min(options, key=lambda x: x[0])
    return DeadlineInfo(date=d, is_estimate=est, precision="exact" if not est else "approx",
                        label=f"Earliest of your chosen programs ({p.acronym})", source=p.source or p.website)
