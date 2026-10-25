"""
Document catalog, candidate document inventory, and per-scholarship gap analysis.

Readiness units (kept identical to the Excel formulas in xlsx_generator):
  have -> min(1, count_ready / count) · in_progress -> 0.5 · not_applicable -> 1 · missing -> 0
  a paper that expires before the deadline is capped at 0.5.
"""

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    CandidateProfile, CatalogDocument, DocumentRecord, DocumentRequirement, RequirementStatus,
    ReadinessReport, ApplicationState, Scholarship,
)
from .deadlines import DeadlineInfo

CATALOG_PATH = Path(__file__).parent.parent / "data" / "document_catalog.json"
DEADLINE_BUFFER_DAYS = 7

GENERIC_DOC = CatalogDocument(
    id="other", name="Other document", category="forms", scope="per_scholarship",
    lead_time_days=[7, 21], how_to_obtain="See the official program page.",
)


@lru_cache(maxsize=1)
def _raw_catalog() -> Dict:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_catalog() -> Dict[str, CatalogDocument]:
    return {doc_id: CatalogDocument(id=doc_id, **spec) for doc_id, spec in _raw_catalog()["documents"].items()}


def load_categories() -> Dict[str, Dict[str, str]]:
    return _raw_catalog()["categories"]


def catalog_doc(doc_id: str) -> CatalogDocument:
    return load_catalog().get(doc_id, GENERIC_DOC)


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return date(year, month, 28)


class DocumentInventory:
    """The candidate's papers, keyed by catalog id (profile/documents.json)."""

    def __init__(self, records: Optional[Dict[str, DocumentRecord]] = None):
        self.records: Dict[str, DocumentRecord] = records or {}

    def get(self, doc_id: str) -> Optional[DocumentRecord]:
        return self.records.get(doc_id)

    def set(self, record: DocumentRecord) -> None:
        self.records[record.doc_id] = record

    def effective_expiry(self, doc_id: str) -> Optional[date]:
        rec = self.get(doc_id)
        if not rec:
            return None
        if rec.expires:
            return rec.expires
        validity = catalog_doc(doc_id).validity_months
        if rec.issued and validity:
            return add_months(rec.issued, validity)
        return None

    @classmethod
    def load(cls, path: Path) -> "DocumentInventory":
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw.get("documents", raw) if isinstance(raw, dict) else raw
        records: Dict[str, DocumentRecord] = {}
        if isinstance(items, dict):
            for doc_id, spec in items.items():
                records[doc_id] = DocumentRecord(doc_id=doc_id, **{k: v for k, v in spec.items() if k != "doc_id"})
        else:
            for spec in items:
                rec = DocumentRecord(**spec)
                records[rec.doc_id] = rec
        return cls(records)

    def save(self, path: Path) -> None:
        catalog = load_catalog()
        payload = {
            "_help": (
                "Your papers, keyed by document id (see data/document_catalog.json). "
                "status: have | in_progress | missing | not_applicable. count_ready: number of letters secured "
                "for recommendation letters. files: paths relative to the workspace folder. "
                "Update with `cli.py docs set <doc_id> --status have --file ...` or edit this file, then run `cli.py build`."
            ),
            "documents": {},
        }
        for doc_id in sorted(self.records, key=lambda d: (catalog_doc(d).category, d)):
            rec = self.records[doc_id]
            data = rec.model_dump(mode="json", exclude={"doc_id"}, exclude_none=True)
            data = {"name": catalog.get(doc_id, GENERIC_DOC).name, **data}
            payload["documents"][doc_id] = data
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")


def _clean_record_spec(spec: Dict) -> Dict:
    return {k: v for k, v in spec.items() if k in DocumentRecord.model_fields}


def inventory_from_dicts(items) -> DocumentInventory:
    inv = DocumentInventory()
    if isinstance(items, dict):
        items = [{"doc_id": k, **v} for k, v in items.items()]
    for spec in items or []:
        inv.set(DocumentRecord(**_clean_record_spec(spec)))
    return inv


def derive_inventory(profile: CandidateProfile, base: Optional[DocumentInventory] = None) -> DocumentInventory:
    """Fill in what the profile already proves (e.g. a reported English test)."""
    inv = DocumentInventory(dict(base.records) if base else {})
    if profile.english_test and profile.english_score is not None:
        rec = inv.get("english_test")
        if rec is None:
            inv.set(DocumentRecord(
                doc_id="english_test",
                status="have",
                issued=profile.english_test_date,
                details=f"{profile.english_test} {profile.english_score:g}"
                + (f" (lowest band {profile.english_min_band:g})" if profile.english_min_band else ""),
                notes="Derived from profile.json",
            ))
        elif rec.issued is None and profile.english_test_date:
            rec.issued = profile.english_test_date
    return inv


def _lookup(req: DocumentRequirement, cat: CatalogDocument, inventory: DocumentInventory,
            state: Optional[ApplicationState], doc_id: Optional[str] = None) -> Tuple[Optional[DocumentRecord], int]:
    doc_id = doc_id or req.doc
    if cat.scope == "per_scholarship":
        rec = state.documents.get(doc_id) if state else None
        return rec, (rec.effective_count if rec else 0)
    if cat.satisfied_by:
        own = inventory.get(doc_id)
        count = (own.effective_count if own else 0) + sum(
            (inventory.get(x).effective_count if inventory.get(x) else 0) for x in cat.satisfied_by
        )
        statuses = [r for r in [own] + [inventory.get(x) for x in cat.satisfied_by] if r]
        if count == 0 and any(r.status == "in_progress" for r in statuses):
            return DocumentRecord(doc_id=doc_id, status="in_progress"), 0
        if count == 0 and statuses and all(r.status == "not_applicable" for r in statuses):
            return DocumentRecord(doc_id=doc_id, status="not_applicable"), 0
        return (DocumentRecord(doc_id=doc_id, status="have", count_ready=count) if count else own), count
    rec = inventory.get(doc_id)
    return rec, (rec.effective_count if rec else 0)


def _state_and_units(rec: Optional[DocumentRecord], count_ready: int, required: int) -> Tuple[str, float]:
    if rec and rec.status == "not_applicable":
        return "not_applicable", 1.0
    if count_ready >= required:
        return "have", 1.0
    if count_ready > 0:
        return "partial", count_ready / required
    if rec and rec.status == "in_progress":
        return "in_progress", 0.5
    return "missing", 0.0


def evaluate_requirement(
    req: DocumentRequirement,
    profile: CandidateProfile,
    inventory: DocumentInventory,
    state: Optional[ApplicationState],
    deadline: Optional[date],
) -> Optional[RequirementStatus]:
    if req.degrees and profile.target_degree not in req.degrees:
        return None

    cat = catalog_doc(req.doc)
    rec, count_ready = _lookup(req, cat, inventory, state)
    status, units = _state_and_units(rec, count_ready, req.count)
    via: Optional[str] = None

    if units < 1.0:
        for alt in req.alternatives:
            alt_cat = catalog_doc(alt)
            alt_rec, alt_count = _lookup(req, alt_cat, inventory, state, doc_id=alt)
            alt_status, alt_units = _state_and_units(alt_rec, alt_count, 1)
            if alt_units > units:
                rec, count_ready, status, units, via = alt_rec, max(alt_count, 1), alt_status, alt_units, alt
                break

    issues: List[str] = []
    expiry_doc = via or req.doc
    if status in ("have", "partial") and cat.scope == "shared":
        expiry = inventory.effective_expiry(expiry_doc)
        if expiry and deadline and expiry < deadline:
            status, units = "expiring", min(units, 0.5)
            issues.append(f"Expires {expiry.isoformat()}, before the deadline: renew or retake")
    if rec and status in ("have", "partial", "expiring"):
        if "translated" in req.requires and rec.translated is False:
            issues.append("Needs a certified translation")
        if "apostille" in req.requires and rec.apostilled is False:
            issues.append("Needs apostille / consular legalization")
        if ("certified" in req.requires or "notarized" in req.requires) and rec.certified is False:
            issues.append("Needs certified / notarized copies")
    if "signed" in req.requires:
        issues.append("Must be hand-signed")
    if "template" in req.requires:
        issues.append("Use the program's official template/form")
    if status == "partial":
        issues.append(f"{count_ready} of {req.count} secured")

    start_by = None
    if units < 1.0 and deadline:
        lead = cat.lead_min if status in ("in_progress", "partial", "expiring") else cat.lead_max
        start_by = deadline - timedelta(days=lead + DEADLINE_BUFFER_DAYS)

    return RequirementStatus(
        doc=req.doc,
        name=cat.name if cat.id != "other" else req.label,
        label=req.label,
        scope=cat.scope,
        category=cat.category,
        stage=req.stage,
        optional=req.optional,
        count=req.count,
        count_ready=min(count_ready, req.count),
        state=status,  # type: ignore[arg-type]
        units=round(units, 3),
        lead_time_days=cat.lead_time_days,
        start_by=start_by,
        issues=issues,
        how_to_obtain=cat.how_to_obtain,
        requires=req.requires,
        words=req.words,
        items=req.items,
        notes=req.notes,
        satisfied_via=via,
    )


def build_readiness(
    scholarship: Scholarship,
    profile: CandidateProfile,
    inventory: DocumentInventory,
    state: Optional[ApplicationState],
    deadline_info: DeadlineInfo,
    today: date,
) -> ReadinessReport:
    deadline = deadline_info.date
    reqs = [
        r for r in (evaluate_requirement(req, profile, inventory, state, deadline) for req in scholarship.documents)
        if r is not None
    ]
    core = [r for r in reqs if r.stage == "application" and not r.optional]
    percent = round(100.0 * sum(r.units for r in core) / len(core), 1) if core else 0.0

    days_left = (deadline - today).days if deadline else None
    missing = [r for r in core if r.units < 1.0]
    longest = 0
    if missing:
        longest = max(
            (catalog_doc(r.doc).lead_min if r.state in ("in_progress", "partial", "expiring") else catalog_doc(r.doc).lead_max)
            for r in missing
        )

    if deadline is None:
        status = "Deadline unknown"
    elif days_left is not None and days_left < 0:
        status = "Deadline passed"
    elif not missing:
        status = "Ready"
    else:
        slack = days_left - longest - DEADLINE_BUFFER_DAYS
        shortest_needed = max(catalog_doc(r.doc).lead_min for r in missing)
        if slack >= 14:
            status = "On track"
        elif slack >= 0:
            status = "Tight"
        elif days_left - shortest_needed - 2 >= 0:
            status = "At risk"
        else:
            status = "Not feasible this cycle"

    return ReadinessReport(
        percent=percent,
        requirements=reqs,
        deadline=deadline,
        deadline_is_estimate=deadline_info.is_estimate,
        deadline_precision=deadline_info.precision,
        deadline_label=deadline_info.label,
        deadline_source=deadline_info.source,
        next_cycle_deadline=deadline_info.next_cycle,
        days_left=days_left,
        timeline_status=status,  # type: ignore[arg-type]
        longest_missing_lead_days=longest,
    )


def shared_documents_needed(scholarships: List[Scholarship], profile: CandidateProfile) -> List[str]:
    """Catalog ids of shared papers needed by any of the given scholarships (for seeding documents.json)."""
    needed: List[str] = []
    for s in scholarships:
        for req in s.documents:
            if req.optional or (req.degrees and profile.target_degree not in req.degrees):
                continue
            ids = [req.doc] + req.alternatives
            for doc_id in ids[:1]:
                cat = catalog_doc(doc_id)
                if cat.scope != "shared":
                    continue
                for d in (cat.satisfied_by[:1] if cat.satisfied_by else [doc_id]):
                    if d not in needed:
                        needed.append(d)
    return needed
