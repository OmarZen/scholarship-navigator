"""
JSON-friendly facade over the planner, shared by the MCP server (mcp_server.py) and `cli.py --json`.

Every function takes and returns plain dicts / lists / strings so agents can call it without
knowing the internal models. Profiles are dicts with CandidateProfile fields plus an optional
"documents" list (see schemas/candidate_profile.schema.json).
"""

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import CandidateProfile, MatchResult, ProgramMatch
from .matcher import load_scholarships, match_profile_all
from .documents import derive_inventory, inventory_from_dicts, load_catalog, load_categories
from .programs import load_programs, rank_programs
from .roadmap import select_shortlist, build_action_plan
from . import workspace as wsp

REPO_ROOT = Path(__file__).parent.parent


def workspace_root() -> Path:
    return Path(os.environ.get("SCHOLARSHIP_WORKSPACES", REPO_ROOT / "output"))


def _profile_and_inventory(profile: Dict[str, Any]):
    data = {k: v for k, v in profile.items() if not k.startswith("_")}
    docs = data.pop("documents", None)
    p = CandidateProfile(**data)
    return p, derive_inventory(p, inventory_from_dicts(docs) if docs else None)


def _resolve_ws(workspace: Optional[str]) -> Path:
    if workspace:
        p = Path(workspace)
        if not p.is_absolute() and not wsp.profile_path(p).exists():
            p = workspace_root() / workspace
        if wsp.profile_path(p).exists():
            return p
        raise ValueError(f"Workspace '{workspace}' not found")
    found = wsp.find_workspace(None, root=workspace_root())
    if not found:
        raise ValueError("No workspace given and none (or several) found; pass the workspace folder name")
    return found


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def match_to_dict(m: MatchResult, detail: bool = True) -> Dict[str, Any]:
    s, r = m.scholarship, m.readiness
    out: Dict[str, Any] = {
        "id": s.id, "name": s.name, "country": s.country, "funding": s.funding_type, "tier": m.tier,
        "eligibility": m.eligibility_status, "match_status": m.match_status, "fit": m.fit_score,
        "readiness_percent": m.readiness_percent, "priority": m.priority_score,
        "deadline": r.deadline.isoformat() if r and r.deadline else None,
        "deadline_estimated": r.deadline_is_estimate if r else True,
        "deadline_label": r.deadline_label if r else None,
        "days_left": r.days_left if r else None,
        "timeline": r.timeline_status if r else None,
        "next_cycle_deadline": r.next_cycle_deadline.isoformat() if r and r.next_cycle_deadline else None,
        "portal": s.official_portal,
        "program_status": s.program_status,
    }
    if detail:
        out["eligibility_checks"] = [g.model_dump() for g in m.gate_checks]
        out["fit_breakdown"] = [c.model_dump() for c in m.score_breakdown]
        out["missing_papers"] = [
            {"doc": q.doc, "name": q.name, "as_worded": q.label, "state": q.state, "count": q.count,
             "count_ready": q.count_ready, "start_by": q.start_by.isoformat() if q.start_by else None,
             "lead_time_days": q.lead_time_days, "how_to_obtain": q.how_to_obtain, "issues": q.issues}
            for q in (r.missing if r else [])
        ]
        out["next_steps"] = m.next_steps
        out["strategy"] = s.strategic_tips
    return out


def program_to_dict(pm: ProgramMatch) -> Dict[str, Any]:
    p = pm.program
    return {
        "id": p.id, "acronym": p.acronym, "name": p.name, "scheme": p.parent_scholarship, "type": p.type,
        "score": pm.score, "eligible": pm.eligible, "field_match": pm.field_match, "matched_terms": pm.matched_terms,
        "host_countries": p.host_countries, "host_countries_in_targets": pm.host_countries_in_targets,
        "universities": [u.model_dump() for u in p.universities],
        "status": p.status, "scholarships_available": p.scholarships_available,
        "deadline": pm.deadline.isoformat() if pm.deadline else None, "deadline_estimated": pm.deadline_is_estimate,
        "days_left": pm.days_left, "english_requirement": p.english_requirement, "duration_months": p.duration_months,
        "website": p.website, "reasons": pm.reasons, "warnings": pm.warnings, "verified_on": p.verified_on,
    }


def _action_to_dict(a: Dict[str, Any]) -> Dict[str, Any]:
    return {**a, "start_by": a["start_by"].isoformat() if a["start_by"] else None,
            "due_by": a["due_by"].isoformat() if a["due_by"] else None}


# ---------------------------------------------------------------------------
# Catalog lookups
# ---------------------------------------------------------------------------

def list_scholarships(degree: Optional[str] = None, country: Optional[str] = None,
                      funding: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for s in load_scholarships():
        if degree and degree not in s.degrees:
            continue
        if country and country.lower() not in (s.country + " " + " ".join(s.host_countries)).lower():
            continue
        if funding and funding.lower() != s.funding_type.lower():
            continue
        out.append({"id": s.id, "name": s.name, "country": s.country, "degrees": s.degrees, "funding": s.funding_type,
                    "tier": s.tier, "program_status": s.program_status, "typical_deadline": s.timeline.typical_deadline,
                    "portal": s.official_portal})
    return out


def get_scholarship(scholarship_id: str) -> Dict[str, Any]:
    for s in load_scholarships():
        if s.id == scholarship_id:
            data = s.model_dump(mode="json")
            data["programs"] = [p.id for p in load_programs() if p.parent_scholarship == s.id]
            return data
    raise ValueError(f"Unknown scholarship id '{scholarship_id}'")


def list_document_types() -> List[Dict[str, Any]]:
    cats = load_categories()
    return [{"id": d.id, "name": d.name, "scope": d.scope, "category": d.category,
             "folder": cats.get(d.category, {}).get("folder"), "lead_time_days": d.lead_time_days,
             "validity_months": d.validity_months, "how_to_obtain": d.how_to_obtain}
            for d in load_catalog().values()]


# ---------------------------------------------------------------------------
# Matching without a workspace
# ---------------------------------------------------------------------------

def match(profile: Dict[str, Any], include_ineligible: bool = False, limit: int = 15,
          today: Optional[date] = None) -> Dict[str, Any]:
    p, inv = _profile_and_inventory(profile)
    matches = match_profile_all(p, inventory=inv, today=today)
    shortlist = select_shortlist(matches)
    shown = matches if include_ineligible else [m for m in matches if m.is_eligible]
    return {
        "candidate": p.full_name,
        "shortlist": [m.scholarship.id for m in shortlist],
        "results": [match_to_dict(m) for m in shown[:limit]],
        "not_eligible": [{"id": m.scholarship.id, "why": [g.detail for g in m.gate_checks if g.result == "fail"]}
                         for m in matches if not m.is_eligible],
        "action_plan": [_action_to_dict(a) for a in build_action_plan(p, shortlist, today or date.today())[:20]],
    }


def find_programs(profile: Optional[Dict[str, Any]] = None, field: Optional[str] = None,
                  countries: Optional[List[str]] = None, scheme: Optional[str] = None, limit: int = 20,
                  include_closed: bool = False, today: Optional[date] = None) -> List[Dict[str, Any]]:
    if profile:
        p, _ = _profile_and_inventory(profile)
    else:
        p = CandidateProfile(full_name="Anonymous", nationality="", current_degree="", target_degree="Master",
                             field_of_study=field or "", gpa=0, english_test=None)
    matches = rank_programs(p, today=today, scholarship_id=scheme, field=field, countries=countries,
                            include_closed=include_closed or not profile)
    return [program_to_dict(pm) for pm in matches[:limit]]


# ---------------------------------------------------------------------------
# Workspace operations
# ---------------------------------------------------------------------------

def _summary(res: Dict[str, Any]) -> Dict[str, Any]:
    ws: Path = res["workspace"]
    return {
        "workspace": str(ws.resolve()),
        "read_first": [str(ws / "AGENTS.md"), str(ws / "INDEX.md"), str(ws / "PROFILE.md")],
        "reports": {k: str(ws / "reports" / v) for k, v in (
            ("excel", "scholarship_tracker.xlsx"), ("html", "scholarship_report.html"), ("calendar", "deadlines.ics"),
            ("match_report", "match_report.md"), ("action_plan", "action_plan.md"))},
        "shortlist": [match_to_dict(m, detail=False) for m in res["shortlist"]],
        "next_actions": [_action_to_dict(a) for a in res["actions"] if a["bucket"] != "After submitting"][:15],
        "missing_papers": sorted({q.name for m in res["shortlist"] for q in (m.readiness.missing if m.readiness else [])}),
        "recommended_programs": [program_to_dict(pm) for pm in res.get("programs", [])[:8]],
        "profile_gaps": [g.fix for m in res["shortlist"] for g in m.gate_checks if g.result == "unknown" and g.fix],
    }


def create_workspace(profile: Dict[str, Any], name: Optional[str] = None, overwrite_profile: bool = False) -> Dict[str, Any]:
    ws = wsp.create_workspace(profile, root=workspace_root(), name=name, overwrite_profile=overwrite_profile)
    return _summary(wsp.build_workspace(ws))


def build_workspace(workspace: Optional[str] = None) -> Dict[str, Any]:
    return _summary(wsp.build_workspace(_resolve_ws(workspace)))


def workspace_summary(workspace: Optional[str] = None) -> Dict[str, Any]:
    return build_workspace(workspace)


def scholarship_brief(scholarship_id: str, workspace: Optional[str] = None) -> str:
    path = wsp.scholarship_dir(_resolve_ws(workspace), scholarship_id) / "SCHOLARSHIP.md"
    if not path.exists():
        raise ValueError(f"No brief for '{scholarship_id}' (not shortlisted). Track it with set_application_status first.")
    return path.read_text(encoding="utf-8")


def update_document(doc_id: str, status: Optional[str] = None, workspace: Optional[str] = None,
                    scholarship_id: Optional[str] = None, file: Optional[str] = None, issued: Optional[str] = None,
                    expires: Optional[str] = None, count: Optional[int] = None, translated: Optional[bool] = None,
                    certified: Optional[bool] = None, apostilled: Optional[bool] = None,
                    details: Optional[str] = None) -> Dict[str, Any]:
    if doc_id not in load_catalog():
        raise ValueError(f"Unknown document id '{doc_id}'; call list_document_types")
    ws = _resolve_ws(workspace)
    yn = lambda v: None if v is None else ("yes" if v else "no")  # noqa: E731
    wsp.set_document(ws, doc_id, scholarship_id=scholarship_id, status=status, file=file, issued=issued, expires=expires,
                     count=count, translated=yn(translated), certified=yn(certified), apostilled=yn(apostilled),
                     details=details)
    return _summary(wsp.build_workspace(ws))


def confirm_deadline(scholarship_id: str, deadline: str, source: Optional[str] = None,
                     workspace: Optional[str] = None) -> Dict[str, Any]:
    ws = _resolve_ws(workspace)
    date.fromisoformat(deadline)
    wsp.set_deadline(ws, scholarship_id, deadline, source)
    return _summary(wsp.build_workspace(ws))


def set_application_status(scholarship_id: str, status: str, workspace: Optional[str] = None,
                           notes: Optional[str] = None) -> Dict[str, Any]:
    from .models import APPLICATION_STATUSES
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"status must be one of {APPLICATION_STATUSES}")
    ws = _resolve_ws(workspace)
    wsp.set_application_status(ws, scholarship_id, status, notes)
    return _summary(wsp.build_workspace(ws))


def choose_program(program_id: str, workspace: Optional[str] = None, remove: bool = False) -> Dict[str, Any]:
    ws = _resolve_ws(workspace)
    wsp.choose_program(ws, program_id, remove=remove)
    return _summary(wsp.build_workspace(ws))


def country_guide(country: str) -> Dict[str, Any]:
    from .relocation_guide import get_relocation_guide
    from .credential_guide import get_credential_guide_for_country
    with open(REPO_ROOT / "data" / "countries.json", "r", encoding="utf-8") as f:
        countries = json.load(f)
    guide = next((c for c in countries if c.get("name", "").lower() == country.lower() or c.get("id") == country.lower()), None)
    return {"country": country, "study_and_work": guide, "visa_and_arrival": get_relocation_guide(country),
            "credential_recognition": get_credential_guide_for_country(country)}


def funding_gap(country: str, monthly_stipend: float = 0.0, months: int = 12, covers_tuition: bool = True,
                covers_flights: bool = False, covers_insurance: bool = False, private_university: bool = False) -> Dict[str, Any]:
    from .financial_calculator import calculate_financial_gap
    return calculate_financial_gap(country=country, scholarship_covers_tuition=covers_tuition,
                                   monthly_stipend_received=monthly_stipend, stipend_duration_months=months,
                                   scholarship_covers_flights=covers_flights, scholarship_covers_insurance=covers_insurance,
                                   is_private_university=private_university)


def review_essay(text: str, essay_type: str = "sop") -> Dict[str, Any]:
    from .essay_coach import review_scholarship_essay
    return review_scholarship_essay(text, essay_type=essay_type)  # type: ignore[arg-type]
