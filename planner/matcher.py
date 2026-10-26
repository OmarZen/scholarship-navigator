"""
Eligibility and fit matching engine.

Every scholarship is evaluated in three independent steps:
  1. Eligibility gates  - hard rules (degree, nationality, age, work experience...). Any fail = Ineligible,
                          missing data = Needs Check (never a silent pass).
  2. Fit score (0-100)  - weighted components with a visible breakdown.
  3. Readiness (0-100%) - share of required papers the candidate already has, plus a deadline feasibility check.
A priority score combines the three to rank what to work on first.
"""

import json
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    CandidateProfile, Scholarship, MatchResult, MatchStatus, GateCheck, ScoreComponent, ApplicationState,
    ReadinessReport,
)
from .regions import normalize_country, in_group, in_list, same_country, group_title
from .fields import groups_for, keyword_hits, FIELD_GROUPS
from .deadlines import resolve_deadline, DeadlineInfo
from .documents import DocumentInventory, derive_inventory, build_readiness
from .language import to_ielts  # noqa: F401  (re-exported for callers)

DATA_DIR = Path(__file__).parent.parent / "data"

HIGH_MATCH = 80.0
MODERATE_MATCH = 62.0

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
STEP_VERB = {"essays": "Write", "letters": "Write", "forms": "Complete", "admissions": "Secure", "references": "Secure"}
TIME_FACTOR = {
    "Ready": 1.0, "On track": 1.0, "Tight": 0.75, "At risk": 0.4,
    "Not feasible this cycle": 0.1, "Deadline passed": 0.0, "Deadline unknown": 0.6,
}

CUSTOM_DIR = DATA_DIR / "custom"


def load_scholarships(data_path: Path = None, include_custom: bool = True) -> List[Scholarship]:
    """Core records from data/scholarships.json plus local additions in data/custom/*.json (same schema)."""
    if data_path is None:
        data_path = DATA_DIR / "scholarships.json"
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    records = [Scholarship(**item) for item in raw_data]
    if include_custom and data_path == DATA_DIR / "scholarships.json" and CUSTOM_DIR.exists():
        seen = {s.id for s in records}
        for path in sorted(CUSTOM_DIR.glob("*.json")):
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw if isinstance(raw, list) else [raw]:
                s = Scholarship(**item)
                if s.id not in seen:
                    records.append(s)
                    seen.add(s.id)
    return records


def _cefr_rank(level: Optional[str]) -> int:
    if not level:
        return -1
    up = level.upper()
    for i, lvl in enumerate(CEFR_ORDER):
        if lvl in up:
            return i
    return -1


# ---------------------------------------------------------------------------
# Step 1: eligibility gates
# ---------------------------------------------------------------------------

def nationality_open(nationality: str, s: Scholarship) -> Optional[bool]:
    """True / False, or None when the country list is unconfirmed or the country is on a region border."""
    return {"pass": True, "fail": False}.get(_nationality_check(nationality, s).result)


def _nationality_gate(profile: CandidateProfile, s: Scholarship) -> GateCheck:
    return _nationality_check(profile.nationality, s)


def _nationality_check(nationality: str, s: Scholarship) -> GateCheck:
    rule = s.rules.nationality
    nat = normalize_country(nationality)
    name = "Nationality"

    excluded = in_list(nat, rule.exclude_countries) or any(in_group(nat, r) for r in rule.exclude_regions)
    if excluded:
        return GateCheck(name=name, result="fail", detail=f"{nat} citizens are not eligible for this program.")

    if rule.mode == "any":
        return GateCheck(name=name, result="pass", detail=f"Open to all nationalities ({nat} included).")

    listed = in_list(nat, rule.countries)
    region_hits = [in_group(nat, r) for r in rule.regions]
    if listed or any(h is True for h in region_hits):
        where = "the eligible-country list" if listed else group_title(next(r for r, h in zip(rule.regions, region_hits) if h))
        return GateCheck(name=name, result="pass", detail=f"{nat} is on {where}.")

    if any(h is None for h in region_hits):
        return GateCheck(
            name=name, result="unknown",
            detail=f"{nat} is on the border of the eligible region ({', '.join(group_title(r) for r in rule.regions)}).",
            fix="Check the official eligibility page for your country.",
        )

    if rule.mode == "exclude":
        return GateCheck(name=name, result="pass", detail=f"{nat} is not on the excluded list.")

    if rule.mode == "verify":
        return GateCheck(
            name=name, result="unknown",
            detail=f"Eligibility depends on a country list we could not confirm for {nat}." + (f" {rule.note}" if rule.note else ""),
            fix=f"Check {s.official_portal} for your country, then record it in the scholarship's status.json notes.",
        )

    scope = ", ".join(group_title(r) for r in rule.regions) if rule.regions else "a fixed list of countries"
    return GateCheck(name=name, result="fail", detail=f"Only open to citizens of {scope}; {nat} is not listed.")


def _residence_gate(profile: CandidateProfile, s: Scholarship) -> Optional[GateCheck]:
    rule = s.rules.residence
    if not rule:
        return None
    residence = normalize_country(profile.residence)
    if rule == "home_country":
        ok: Optional[bool] = same_country(residence, profile.nationality)
        where = "your home country"
    else:
        ok = in_group(residence, rule)
        where = group_title(rule)
    if ok:
        return GateCheck(name="Residence", result="pass", detail=f"You live in {residence} ({where}).")
    if profile.country_of_residence is None:
        return GateCheck(name="Residence", result="unknown", detail=f"Applicants must live in {where}.",
                         fix="Add country_of_residence to profile.json.")
    result = "fail" if s.rules.residence_strict else "warn"
    return GateCheck(name="Residence", result=result,
                     detail=f"Applicants are expected to live in {where}; you live in {residence}.")


def _gender_gate(profile: CandidateProfile, s: Scholarship) -> Optional[GateCheck]:
    need = s.rules.gender
    if not need:
        return None
    who = "women" if need == "female" else "men"
    if profile.gender == need:
        return GateCheck(name="Gender", result="pass", detail=f"Reserved for {who}.")
    if profile.gender is None:
        return GateCheck(name="Gender", result="unknown", detail=f"Reserved for {who}.",
                         fix="Add gender to profile.json (only used for awards reserved for women or men).")
    if profile.gender == "other":
        return GateCheck(name="Gender", result="unknown", detail=f"Reserved for {who}.",
                         fix=f"Check how {s.official_portal} defines who can apply.")
    return GateCheck(name="Gender", result="fail", detail=f"Reserved for {who}.")


def study_options(s: Scholarship, home: str) -> Tuple[Optional[bool], bool]:
    """(can study in `home`, can study abroad). The first is None when a host region may or may not include `home`."""
    if s.study_location == "home":
        return True, False
    if s.study_location == "abroad":
        return False, True
    if s.study_location == "both" or not (s.host_countries or s.host_regions):
        return True, True
    abroad = bool(s.host_regions) or any(not same_country(h, home) for h in s.host_countries)
    if in_list(home, s.host_countries):
        return True, abroad
    if any(in_group(home, r) is not False for r in s.host_regions):
        return None, abroad
    return False, abroad


def where_you_study(s: Scholarship) -> str:
    places = ", ".join(s.host_countries + [group_title(r) for r in s.host_regions])
    if s.study_location == "home":
        return "your own country"
    if s.study_location == "both":
        return "your own country or abroad" + (f" ({places})" if places else "")
    return places or "any country"


def location_label(at_home: Optional[bool], abroad: bool) -> str:
    if at_home and abroad:
        return "Home or abroad"
    if at_home:
        return "Home country"
    if at_home is None:
        return "Abroad (maybe home)"
    return "Abroad"


def _study_location_gate(profile: CandidateProfile, s: Scholarship) -> Optional[GateCheck]:
    want = profile.study_location
    if want == "both":
        return None
    home = normalize_country(profile.residence)
    at_home, abroad = study_options(s, home)
    where = where_you_study(s)
    name = "Study location"
    keep_both = 'Set "study_location": "both" in profile.json if you could also study abroad.'
    if want == "home":
        if at_home:
            return GateCheck(name=name, result="pass", detail=f"You can study in {home}, without travelling.")
        if at_home is None:
            return GateCheck(name=name, result="unknown",
                             detail=f"Host universities are spread across {where}; one may be in {home}.",
                             fix=f"Check {s.official_portal} for a host university in {home}.")
        return GateCheck(name=name, result="fail",
                         detail=f"Means studying abroad ({where}); you want to study in {home}.", fix=keep_both)
    if abroad:
        return GateCheck(name=name, result="pass", detail=f"You would study abroad ({where}).")
    return GateCheck(name=name, result="fail",
                     detail=f"You would study in {home}, your own country; you want to study abroad.",
                     fix='Set "study_location": "both" in profile.json to include study at home.')


def _age_gate(profile: CandidateProfile, s: Scholarship, on: date) -> Optional[GateCheck]:
    r = s.rules
    hard = r.age_under.get(profile.target_degree) or r.age_under.get("all")
    soft = r.age_under_preferred.get(profile.target_degree) or r.age_under_preferred.get("all")
    if not (hard or soft or r.age_min):
        return None
    age = profile.age_on(on)
    limits = []
    if r.age_min:
        limits.append(f"at least {r.age_min}")
    if hard:
        limits.append(f"under {hard}")
    if soft and not hard:
        limits.append(f"typically under {soft}")
    limit_text = " and ".join(limits)
    if age is None:
        return GateCheck(name="Age", result="unknown", detail=f"Age limit: {limit_text}.",
                         fix="Add date_of_birth to profile.json.")
    if r.age_min and age < r.age_min:
        return GateCheck(name="Age", result="fail", detail=f"You will be {age}; minimum age is {r.age_min}.")
    if hard and age >= hard:
        return GateCheck(name="Age", result="fail", detail=f"You will be {age} at the deadline; limit is under {hard}.")
    if hard and age == hard - 1:
        return GateCheck(name="Age", result="warn",
                         detail=f"You will be {age}; limit is under {hard}. Check the exact birth-date cutoff.")
    if soft and age >= soft:
        return GateCheck(name="Age", result="warn", detail=f"You will be {age}; most winners are under {soft}.")
    return GateCheck(name="Age", result="pass", detail=f"You will be {age} at the deadline ({limit_text}).")


def _degree_age_gate(profile: CandidateProfile, s: Scholarship, on: date) -> Optional[GateCheck]:
    r = s.rules
    if not r.degree_age_max_years:
        return None
    if r.degree_age_applies_to and profile.target_degree not in r.degree_age_applies_to:
        return None
    if profile.graduation_year is None:
        return GateCheck(name="Degree recency", result="unknown",
                         detail=f"Your last degree must be at most {r.degree_age_max_years} years old.",
                         fix="Add graduation_year to profile.json.")
    years = on.year - profile.graduation_year
    if years > r.degree_age_max_years:
        result = "fail" if r.degree_age_strict else "warn"
        return GateCheck(name="Degree recency", result=result,
                         detail=f"Your degree will be {years} years old; limit is {r.degree_age_max_years}.")
    return GateCheck(name="Degree recency", result="pass",
                     detail=f"Degree from {profile.graduation_year} ({years} years, limit {r.degree_age_max_years}).")


def _experience_at(profile: CandidateProfile, on: date, today: date) -> float:
    years = profile.work_experience_years
    if profile.currently_employed and on > today:
        years += (on - today).days / 365.25
    return years


def _work_gate(profile: CandidateProfile, s: Scholarship, on: date, today: date) -> Optional[GateCheck]:
    need = s.rules.work_experience_years
    if need <= 0:
        return None
    have = _experience_at(profile, on, today)
    hours = s.eligibility.work_hours_required
    hours_txt = f" (~{hours:,} hours)" if hours else ""
    if have >= need:
        extra = " counting work until the deadline" if have > profile.work_experience_years else ""
        return GateCheck(name="Work experience", result="pass",
                         detail=f"{have:.1f} years{extra}; requires {need:g}{hours_txt}.")
    gap = need - have
    return GateCheck(name="Work experience", result="fail",
                     detail=f"Requires {need:g} years{hours_txt}; you will have {have:.1f} by the deadline.",
                     fix=f"Gain {gap:.1f} more years, then apply in a later cycle.")


def _return_gate(profile: CandidateProfile, s: Scholarship) -> Optional[GateCheck]:
    years = s.rules.return_obligation_years
    text = s.eligibility.return_obligation
    if years <= 0 and not (text and s.rules.return_obligation_strict):
        return None
    if not profile.willing_to_return_home:
        result = "fail" if s.rules.return_obligation_strict else "warn"
        return GateCheck(name="Return obligation", result=result,
                         detail=f"Requires returning home for {years:g} years after the award." if years else (text or ""))
    return GateCheck(name="Return obligation", result="pass",
                     detail=f"You accept returning home ({years:g} years required)." if years else "You accept the return expectation.")


def _field_gate(profile: CandidateProfile, s: Scholarship) -> Tuple[Optional[GateCheck], float, str]:
    """Returns (gate, fit fraction, detail) for the field-of-study dimension."""
    fr = s.rules.field
    texts = [profile.field_of_study, profile.current_degree, profile.thesis_title or ""] + profile.field_keywords
    if fr.mode == "any":
        return None, 1.0, "Open to all fields."
    mine = groups_for(texts)
    overlap = mine & set(fr.groups)
    hits = keyword_hits(texts, fr.keywords)
    wanted = ", ".join(fr.keywords[:6]) if fr.keywords else ", ".join(g.replace("_", " ") for g in fr.groups)
    if overlap or hits:
        why = ", ".join(sorted(hits or [g.replace("_", " ") for g in overlap]))
        gate = GateCheck(name="Field of study", result="pass", detail=f"Your field matches: {why}.") if fr.mode == "restricted" else None
        return gate, 1.0, f"Matches priority fields ({why})."
    if fr.mode == "restricted":
        gate = GateCheck(
            name="Field of study", result="fail",
            detail=f"Only for: {wanted}. Your field ({profile.field_of_study}) does not match.",
            fix="If your target program is in one of these fields, add keywords to field_keywords in profile.json.",
        )
        return gate, 0.0, "Outside the program's fields."
    return None, 0.4, f"Not in the priority fields ({wanted})."


def _other_language_gate(profile: CandidateProfile, s: Scholarship) -> Optional[GateCheck]:
    lr = s.rules.language
    if not lr.other_language:
        return None
    need = lr.other_language
    skill = next((l for l in profile.other_languages if l.language.lower() == need.lower()), None)
    if skill is None:
        return GateCheck(name=f"{need} language", result="unknown",
                         detail=f"Programs are taught in {need} ({lr.other_language_level or 'B2'}+ needed).",
                         fix=f"Add your {need} level to other_languages in profile.json.")
    if _cefr_rank(skill.level) >= _cefr_rank(lr.other_language_level or "B2"):
        return GateCheck(name=f"{need} language", result="pass", detail=f"{need} {skill.level}.")
    return GateCheck(name=f"{need} language", result="warn",
                     detail=f"{need} {skill.level or 'level unknown'}; {lr.other_language_level or 'B2'} needed.")


def run_gates(profile: CandidateProfile, s: Scholarship, on: date, today: date) -> List[GateCheck]:
    gates: List[GateCheck] = []
    if profile.target_degree not in s.degrees:
        gates.append(GateCheck(name="Degree level", result="fail",
                               detail=f"Offers {', '.join(s.degrees)}; you target {profile.target_degree}."))
        return gates
    gates.append(GateCheck(name="Degree level", result="pass", detail=f"Offers {profile.target_degree} programs."))

    if s.program_status == "discontinued":
        gates.append(GateCheck(name="Program status", result="fail",
                               detail=s.program_status_note or "This program has been discontinued."))
    elif s.program_status == "changed":
        gates.append(GateCheck(name="Program status", result="warn",
                               detail=s.program_status_note or "This program changed recently; check the official site."))

    gates.append(_nationality_gate(profile, s))
    for gate in (
        _residence_gate(profile, s), _gender_gate(profile, s), _study_location_gate(profile, s),
        _age_gate(profile, s, on), _degree_age_gate(profile, s, on),
        _work_gate(profile, s, on, today), _return_gate(profile, s), _field_gate(profile, s)[0],
        _other_language_gate(profile, s),
    ):
        if gate:
            gates.append(gate)
    return gates


def eligibility_from_gates(gates: List[GateCheck]) -> str:
    if any(g.result == "fail" for g in gates):
        return "Ineligible"
    if any(g.result == "unknown" for g in gates):
        return "Needs Check"
    return "Eligible"


# ---------------------------------------------------------------------------
# Step 2: fit score
# ---------------------------------------------------------------------------

def _academic(profile: CandidateProfile, s: Scholarship) -> Tuple[float, str]:
    g = profile.normalized_gpa
    mn = s.rules.gpa_min or 3.0
    comp = s.rules.gpa_competitive or max(mn + 0.3, 3.3)
    if g >= comp + 0.2:
        frac, txt = 1.0, f"GPA {g:.2f}/4.0 is well above the competitive level ({comp:.1f})."
    elif g >= comp:
        frac = 0.88 + 0.12 * (g - comp) / 0.2
        txt = f"GPA {g:.2f}/4.0 reaches the competitive level ({comp:.1f})."
    elif g >= mn:
        frac = 0.6 + 0.4 * (g - mn) / max(comp - mn, 0.01)
        txt = f"GPA {g:.2f}/4.0 meets the minimum ({mn:.1f}); winners usually have {comp:.1f}+."
    else:
        frac = max(0.0, 0.45 - (mn - g) * 1.5)
        txt = f"GPA {g:.2f}/4.0 is below the usual minimum ({mn:.1f})."
    if profile.class_rank_percent is not None and profile.class_rank_percent <= 10:
        frac = min(1.0, frac + 0.1)
        txt += f" Top {profile.class_rank_percent:g}% of class helps."
    return frac, txt


def _language(profile: CandidateProfile, s: Scholarship, inventory: DocumentInventory) -> Tuple[float, str]:
    lr = s.rules.language
    if lr.other_language:
        skill = next((l for l in profile.other_languages if l.language.lower() == lr.other_language.lower()), None)
        need = lr.other_language_level or "B2"
        if skill and _cefr_rank(skill.level) >= _cefr_rank(need):
            return 1.0, f"{lr.other_language} {skill.level} meets {need}."
        return 0.2, f"Needs {lr.other_language} {need}."

    ielts = to_ielts(profile.english_test, profile.english_score)
    need = lr.ielts_min
    if ielts is None:
        moi = inventory.get("english_moi_letter")
        if lr.accepts_moi and moi and moi.status == "have":
            return 0.8, "No test, but your English-medium letter is accepted by many programs."
        if not lr.required:
            return 0.7, "No English test yet. Not required to apply, but host universities may ask for one."
        return 0.2, f"No English test reported; needs IELTS {need or 6.5:g} or equivalent."

    label = f"{profile.english_test} {profile.english_score:g}" + (f" (≈ IELTS {ielts:g})" if "ielts" not in profile.english_test.lower() else "")
    if need is None:
        frac, txt = 1.0, f"{label}; no fixed minimum."
    elif ielts >= need + 0.5:
        frac, txt = 1.0, f"{label} is comfortably above the minimum ({need:g})."
    elif ielts >= need:
        frac, txt = 0.85, f"{label} meets the minimum ({need:g})."
    elif ielts >= need - 0.5:
        frac, txt = 0.45, f"{label} is just below the minimum ({need:g}); plan a retake."
    else:
        frac, txt = 0.15, f"{label} is below the minimum ({need:g})."

    low_band = profile.english_min_band
    if lr.subscore_min and low_band is not None and "ielts" in profile.english_test.lower() and low_band < lr.subscore_min:
        frac = min(frac, 0.5)
        txt += f" Lowest band {low_band:g} is under the {lr.subscore_min:g} sub-score rule."
    return frac, txt


def _experience(profile: CandidateProfile, s: Scholarship, on: date, today: date) -> Tuple[float, str]:
    need = s.rules.work_experience_years
    have = _experience_at(profile, on, today)
    if need > 0:
        if have >= need:
            return 1.0, f"{have:.1f} years meets the {need:g}-year requirement."
        return 0.0, f"{have:.1f} of the required {need:g} years."
    frac = min(1.0, 0.6 + 0.2 * have)
    return frac, f"{have:.1f} years of work experience (not required, but it strengthens the application)."


def _profile_strength(profile: CandidateProfile, s: Scholarship) -> Tuple[float, str]:
    frac = 0.0
    bits = []
    if profile.has_leadership_experience:
        frac += 0.4
        bits.append("leadership experience")
    if profile.leadership_examples:
        frac += 0.15 * min(2, len(profile.leadership_examples))
        bits.append(f"{len(profile.leadership_examples)} documented leadership stories")
    if profile.awards:
        frac += 0.15
        bits.append(f"{len(profile.awards)} award" + ("s" if len(profile.awards) != 1 else ""))
    if profile.volunteering:
        frac += 0.15
        bits.append("volunteering")
    frac = min(1.0, frac)
    txt = ("You have " + ", ".join(bits) + ".") if bits else "No leadership, awards or volunteering recorded."
    if s.rules.leadership_weight == "high" and not profile.leadership_examples:
        txt += " This award scores leadership heavily: add concrete STAR stories to profile.json."
    return frac, txt


def _research(profile: CandidateProfile) -> Tuple[float, str]:
    pubs = profile.research_publications
    frac = {0: 0.3, 1: 0.7, 2: 0.85}.get(pubs, 1.0)
    if pubs == 0 and profile.thesis_title:
        frac = 0.4
    txt = f"{pubs} publication(s)." + (" Add a writing sample or thesis chapter." if pubs == 0 else "")
    return frac, txt


def _country_preference(profile: CandidateProfile, s: Scholarship) -> Tuple[bool, str]:
    home = normalize_country(profile.residence)
    at_home, _ = study_options(s, home)
    if profile.study_location == "home":
        if at_home:
            return True, f"You can study at home in {home}."
        if at_home is None:
            return True, f"A host university may be in {home}."
        return False, f"Means leaving {home}."
    if not profile.target_countries:
        return True, "Worldwide search: any host country is fine."
    if not (s.host_countries or s.host_regions):
        return True, "Any university worldwide, including your target countries."
    hosts = s.host_countries or [s.country]
    if any(in_list(t, hosts) or any(in_group(t, r) for r in s.host_regions) or t.lower() in s.country.lower()
           for t in profile.target_countries):
        return True, "In your target countries."
    if at_home and profile.study_location == "both":
        return True, f"You can study at home in {home} (you accept home or abroad)."
    return False, f"{s.country} is outside your target countries."


def _preferences(profile: CandidateProfile, s: Scholarship) -> Tuple[float, str, bool]:
    country_ok, country_txt = _country_preference(profile, s)
    txt = [country_txt]
    funding_ok = not (profile.target_funding == "Full" and s.funding_type == "Partial")
    if not funding_ok:
        txt.append("Partial funding only, but you want full funding.")
    frac = (0.6 if country_ok else 0.0) + (0.4 if funding_ok else 0.0)
    return frac, " ".join(txt), country_ok


def score_fit(profile: CandidateProfile, s: Scholarship, inventory: DocumentInventory, on: date, today: date) -> List[ScoreComponent]:
    rules = s.rules
    research_heavy = rules.research_weight == "high"
    if profile.target_degree in ("PhD", "Postdoc"):
        research_weight = 15.0 if research_heavy else 10.0
    else:
        research_weight = 5.0 if research_heavy else 0.0
    undergraduate = profile.target_degree in ("Diploma", "Bachelor")
    weights = {
        "academic": 25.0,
        "language": 20.0,
        "experience": 15.0 if (not undergraduate or rules.work_experience_years > 0) else 0.0,
        "field": 15.0,
        "profile": 20.0 if rules.leadership_weight == "high" else 12.0,
        "research": research_weight,
        "preferences": 10.0,
    }
    academic, a_txt = _academic(profile, s)
    language, l_txt = _language(profile, s, inventory)
    experience, e_txt = _experience(profile, s, on, today)
    _, field, f_txt = _field_gate(profile, s)
    strength, p_txt = _profile_strength(profile, s)
    research, r_txt = _research(profile)
    prefs, pr_txt, _ = _preferences(profile, s)

    parts = [
        ("academic", "Academic record", academic, a_txt),
        ("language", "Language", language, l_txt),
        ("experience", "Experience", experience, e_txt),
        ("field", "Field fit", field, f_txt),
        ("profile", "Leadership & profile", strength, p_txt),
        ("research", "Research", research, r_txt),
        ("preferences", "Your preferences", prefs, pr_txt),
    ]
    return [
        ScoreComponent(key=k, name=n, weight=weights[k], points=round(weights[k] * frac, 1), detail=d)
        for k, n, frac, d in parts if weights[k] > 0
    ]


def fit_from_components(components: List[ScoreComponent]) -> float:
    total = sum(c.weight for c in components)
    return round(100.0 * sum(c.points for c in components) / total, 1) if total else 0.0


def status_from_fit(fit: float, eligibility: str) -> MatchStatus:
    if eligibility == "Ineligible":
        return "Ineligible"
    if fit >= HIGH_MATCH:
        return "High Match"
    if fit >= MODERATE_MATCH:
        return "Moderate Match"
    return "Reach / Low Match"


# ---------------------------------------------------------------------------
# Step 3: readiness + priority
# ---------------------------------------------------------------------------

def priority_from(fit: float, readiness: ReadinessReport, s: Scholarship, eligibility: str) -> float:
    if eligibility == "Ineligible":
        return 0.0
    funding_value = {"Full": 1.0, "Any": 0.75}.get(s.funding_type, 0.5)
    score = 0.55 * fit + 0.20 * readiness.percent + 10.0 * funding_value + 15.0 * TIME_FACTOR[readiness.timeline_status]
    if eligibility == "Needs Check":
        score *= 0.9
    return round(score, 1)


def _next_steps(gates: List[GateCheck], readiness: ReadinessReport, deadline: DeadlineInfo, s: Scholarship) -> List[str]:
    steps: List[str] = []
    for g in gates:
        if g.result == "unknown" and g.fix:
            steps.append(f"Confirm {g.name.lower()}: {g.fix}")
    if readiness.timeline_status == "Deadline passed":
        nxt = f" Next cycle: about {readiness.next_cycle_deadline.isoformat()}." if readiness.next_cycle_deadline else ""
        steps.append(f"The {deadline.label.lower()} deadline ({deadline.display}) has passed for this intake.{nxt}")
    elif deadline.is_estimate and deadline.date:
        steps.append(f"Verify the real deadline on {s.official_portal} (current date is an estimate: {deadline.display}).")
    for r in sorted(readiness.missing, key=lambda r: (r.start_by or date.max)):
        when = f" (start by {r.start_by.isoformat()})" if r.start_by else ""
        need = f" ({r.count_ready}/{r.count} ready)" if r.count > 1 else ""
        verb = STEP_VERB.get(r.category, "Get")
        steps.append(f"{verb}: {r.name}{need}{when}.")
    return steps


def evaluate_scholarship_match(
    profile: CandidateProfile,
    scholarship: Scholarship,
    inventory: Optional[DocumentInventory] = None,
    state: Optional[ApplicationState] = None,
    today: Optional[date] = None,
    deadline_override: Optional[DeadlineInfo] = None,
) -> MatchResult:
    today = today or date.today()
    inventory = derive_inventory(profile, inventory)
    deadline = resolve_deadline(scholarship, profile.target_intake_year, today, state, override=deadline_override)
    reference_day = deadline.date or date(profile.target_intake_year, 9, 1)

    gates = run_gates(profile, scholarship, reference_day, today)
    eligibility = eligibility_from_gates(gates)
    components = score_fit(profile, scholarship, inventory, reference_day, today)
    fit = fit_from_components(components)
    readiness = build_readiness(scholarship, profile, inventory, state, deadline, today)

    reasons = [f"{g.name}: {g.detail}" for g in gates if g.result == "pass"]
    reasons += [f"{c.name}: {c.detail}" for c in components if c.points >= 0.8 * c.weight]
    warnings = [f"{g.name}: {g.detail}" for g in gates if g.result in ("fail", "unknown", "warn")]
    warnings += [f"{c.name}: {c.detail}" for c in components if c.points < 0.6 * c.weight]
    if readiness.missing:
        warnings.append(f"Missing papers: {', '.join(r.name for r in readiness.missing[:6])}"
                        + ("..." if len(readiness.missing) > 6 else ""))
    at_home, abroad = study_options(scholarship, normalize_country(profile.residence))

    return MatchResult(
        scholarship=scholarship,
        match_score=fit if eligibility != "Ineligible" else 0.0,
        match_status=status_from_fit(fit, eligibility),
        fit_score=fit,
        eligibility_status=eligibility,  # type: ignore[arg-type]
        gate_checks=gates,
        score_breakdown=components,
        readiness=readiness,
        priority_score=priority_from(fit, readiness, scholarship, eligibility),
        tier=scholarship.tier,
        study_at_home=at_home,
        study_abroad=abroad,
        reasons_eligible=reasons,
        gaps_and_warnings=warnings,
        strategic_recommendations=[scholarship.strategic_tips],
        next_steps=_next_steps(gates, readiness, deadline, scholarship) if eligibility != "Ineligible" else [],
    )


def sort_matches(results: List[MatchResult]) -> List[MatchResult]:
    rank = {"Eligible": 0, "Needs Check": 0, "Ineligible": 1}
    return sorted(results, key=lambda r: (rank[r.eligibility_status], -r.priority_score, -r.fit_score))


def match_profile_all(
    profile: CandidateProfile,
    scholarships: List[Scholarship] = None,
    inventory: Optional[DocumentInventory] = None,
    states: Optional[Dict[str, ApplicationState]] = None,
    today: Optional[date] = None,
    programs: Optional[list] = None,
) -> List[MatchResult]:
    if scholarships is None:
        scholarships = load_scholarships()
    states = states or {}
    today = today or date.today()
    overrides: Dict[str, DeadlineInfo] = {}
    if any(st.chosen_programs for st in states.values()):
        from .programs import load_programs, chosen_programs_deadline
        programs = programs if programs is not None else load_programs()
        for sid, st in states.items():
            info = chosen_programs_deadline(st, programs, profile.target_intake_year, today)
            if info:
                overrides[sid] = info
    results = [
        evaluate_scholarship_match(profile, s, inventory=inventory, state=states.get(s.id), today=today,
                                   deadline_override=overrides.get(s.id))
        for s in scholarships
    ]
    return sort_matches(results)
