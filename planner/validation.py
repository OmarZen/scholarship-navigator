"""
Data validation, JSON Schema export and record scaffolding for contributors and agents.

    cli.py validate            check data/scholarships.json, data/custom/*.json and data/programs/*.json
    cli.py export-schema       write schemas/*.schema.json from the pydantic models
    cli.py new-scholarship ID  scaffold data/custom/drafts/<ID>.json
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError, create_model

from .models import (
    ApplicationState, CandidateProfile, DocumentRecord, Program, Scholarship,
)
from .documents import load_catalog, load_categories
from .fields import FIELD_GROUPS
from .regions import _load as load_regions

DATA_DIR = Path(__file__).parent.parent / "data"
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def _age_days(value: Optional[str], today: date) -> Optional[int]:
    if not value:
        return None
    try:
        return (today - date.fromisoformat(value[:10])).days
    except ValueError:
        return None


def _check_scholarship(s: Scholarship, where: str, today: date, stale_days: int, errors: List[str], warnings: List[str]) -> None:
    catalog, groups = load_catalog(), load_regions()["groups"]
    tag = f"{where}:{s.id}"
    if not s.documents:
        errors.append(f"{tag}: no documents listed")
    for req in s.documents:
        for doc in [req.doc] + req.alternatives:
            if doc not in catalog:
                errors.append(f"{tag}: unknown paper id '{doc}' (see data/document_catalog.json)")
    rules = s.rules
    for region in rules.nationality.regions + rules.nationality.exclude_regions + s.host_regions:
        if region not in groups:
            errors.append(f"{tag}: unknown region '{region}' (see data/regions.json)")
    if rules.residence and rules.residence != "home_country" and rules.residence not in groups:
        errors.append(f"{tag}: unknown residence region '{rules.residence}'")
    for g in rules.field.groups:
        if g not in FIELD_GROUPS:
            errors.append(f"{tag}: unknown field group '{g}'")
    nat = rules.nationality
    if nat.mode == "include" and not (nat.countries or nat.regions):
        errors.append(f"{tag}: nationality mode 'include' needs countries or regions")
    if nat.mode == "verify" and not nat.countries:
        warnings.append(f"{tag}: nationality is 'verify' with no list: every candidate will be Needs Check")
    if not s.official_portal.startswith("http"):
        errors.append(f"{tag}: official_portal must be a URL")
    if not s.timeline.deadline:
        warnings.append(f"{tag}: no deadline pattern: deadlines will show as Unknown")
    elif not s.timeline.deadline.source:
        warnings.append(f"{tag}: deadline has no source URL")
    age = _age_days(s.data_last_reviewed, today)
    if age is None:
        warnings.append(f"{tag}: data_last_reviewed missing")
    elif age > stale_days:
        warnings.append(f"{tag}: data last reviewed {age} days ago: re-verify")


def _check_program(p: Program, scholarship_ids: set, today: date, stale_days: int,
                   errors: List[str], warnings: List[str]) -> None:
    tag = f"programs:{p.id}"
    if p.parent_scholarship not in scholarship_ids:
        errors.append(f"{tag}: parent_scholarship '{p.parent_scholarship}' does not exist")
    for g in p.field_groups:
        if g not in FIELD_GROUPS:
            errors.append(f"{tag}: unknown field group '{g}'")
    if not p.website.startswith("http"):
        errors.append(f"{tag}: website must be a URL")
    if not p.host_countries:
        warnings.append(f"{tag}: no host countries")
    if p.status == "unknown":
        warnings.append(f"{tag}: status unknown: check the program site")
    age = _age_days(p.verified_on, today)
    if age is None:
        warnings.append(f"{tag}: verified_on missing")
    elif age > stale_days:
        warnings.append(f"{tag}: verified {age} days ago: re-verify")


def validate_data(stale_days: int = 240, today: Optional[date] = None, extra_files: Optional[List[Path]] = None) -> Dict[str, Any]:
    today = today or date.today()
    errors: List[str] = []
    warnings: List[str] = []
    ids: Dict[str, str] = {}
    counts = {"scholarships": 0, "custom": 0, "programs": 0}

    sources = [(DATA_DIR / "scholarships.json", "scholarships")]
    sources += [(p, f"custom/{p.name}") for p in sorted((DATA_DIR / "custom").glob("*.json"))]
    sources += [(p, str(p)) for p in (extra_files or [])]
    for path, where in sources:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"{where}: cannot read JSON ({e})")
            continue
        for item in raw if isinstance(raw, list) else [raw]:
            try:
                s = Scholarship(**item)
            except ValidationError as e:
                errors.append(f"{where}:{item.get('id', '?')}: {e.error_count()} schema error(s): {e.errors()[0]['loc']} {e.errors()[0]['msg']}")
                continue
            if s.id in ids:
                errors.append(f"{where}:{s.id}: duplicate id (also in {ids[s.id]})")
            ids[s.id] = where
            counts["scholarships" if where == "scholarships" else "custom"] += 1
            _check_scholarship(s, where, today, stale_days, errors, warnings)

    program_ids: set = set()
    for path in sorted((DATA_DIR / "programs").glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"programs/{path.name}: cannot read JSON ({e})")
            continue
        for item in raw:
            try:
                p = Program(**item)
            except ValidationError as e:
                errors.append(f"programs/{path.name}:{item.get('id', '?')}: {e.errors()[0]['loc']} {e.errors()[0]['msg']}")
                continue
            if p.id in program_ids:
                errors.append(f"programs:{p.id}: duplicate id")
            program_ids.add(p.id)
            counts["programs"] += 1
            _check_program(p, set(ids), today, stale_days, errors, warnings)

    for doc_id, doc in load_catalog().items():
        if doc.category not in load_categories():
            errors.append(f"document_catalog:{doc_id}: unknown category '{doc.category}'")

    return {"ok": not errors, "counts": counts, "errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# JSON Schemas
# ---------------------------------------------------------------------------

ProfileInput = create_model(
    "CandidateProfileInput",
    __base__=CandidateProfile,
    documents=(List[DocumentRecord], []),
)

SCHEMAS = {
    "candidate_profile": ProfileInput,
    "document_record": DocumentRecord,
    "application_state": ApplicationState,
    "scholarship": Scholarship,
    "program": Program,
}


def schema_documents() -> Dict[str, str]:
    return {name: json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n"
            for name, model in SCHEMAS.items()}


def export_schemas(directory: Path = SCHEMA_DIR) -> List[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in schema_documents().items():
        path = directory / f"{name}.schema.json"
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------

def scholarship_template(scholarship_id: str, today: Optional[date] = None) -> Dict[str, Any]:
    today = today or date.today()
    return {
        "id": scholarship_id,
        "name": "TODO: official scholarship name",
        "country": "TODO: host country",
        "organization": "TODO: funding body",
        "degrees": ["Master"],
        "funding_type": "Full",
        "coverage_details": {
            "tuition_covered": True, "monthly_stipend": "TODO: e.g. €1,200/month", "airfare_covered": False,
            "health_insurance": False, "accommodation_covered": False, "visa_fees_covered": False,
            "additional_allowances": None,
        },
        "eligibility": {
            "eligible_nationalities": "TODO: as published",
            "gpa_requirement": "TODO: as published",
            "language_requirements": "TODO: as published",
            "work_experience_years": 0, "work_hours_required": 0, "age_limit": None,
            "field_restrictions": "TODO: as published", "return_obligation": None,
            "rules": {
                "nationality": {"mode": "any", "countries": [], "regions": [], "exclude_countries": [],
                                "source": "TODO: URL of the official eligibility page"},
                "gpa_min": 3.0, "gpa_competitive": 3.4,
                "language": {"required": True, "ielts_min": 6.5, "accepts_moi": False},
                "age_under": {}, "work_experience_years": 0,
                "field": {"mode": "any", "groups": [], "keywords": []},
                "return_obligation_years": 0, "leadership_weight": "normal", "research_weight": "normal",
            },
        },
        "timeline": {
            "opening_month": "TODO", "typical_deadline": "TODO: as published",
            "deadline": {"month": 1, "day": 15, "years_before_intake": 0, "precision": "approx",
                         "label": "TODO: which deadline this is", "source": "TODO: URL",
                         "verified_on": today.isoformat(), "known_dates": {}},
        },
        "documents": [
            {"doc": "passport", "label": "Copy of passport"},
            {"doc": "transcript", "label": "TODO: as worded by the program"},
            {"doc": "motivation_letter", "label": "TODO: as worded by the program", "words": None},
            {"doc": "lor_academic", "label": "TODO", "count": 2},
        ],
        "official_portal": "https://TODO",
        "application_portal_system": "TODO",
        "strategic_tips": "TODO: 2-3 sentences of practical advice",
        "host_countries": [],
        "tier": "Target",
        "program_status": "active",
        "data_last_reviewed": today.isoformat(),
    }


def scaffold_scholarship(scholarship_id: str, directory: Path = DATA_DIR / "custom" / "drafts") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{scholarship_id}.json"
    if path.exists():
        raise FileExistsError(str(path))
    path.write_text(json.dumps(scholarship_template(scholarship_id), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
