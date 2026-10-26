"""
Candidate workspace: one folder per candidate that holds their profile, papers, one sub-folder per
shortlisted scholarship, and all generated reports.

    output/<candidate>/
      AGENTS.md  INDEX.md  PROFILE.md  manifest.json
      profile/profile.json  profile/documents.json  profile/story_bank.md  profile/<category>/
      scholarships/<id>/SCHOLARSHIP.md  status.json  essays/ letters/ recommendations/ forms/ admissions/ submitted/
      reports/scholarship_tracker.xlsx  scholarship_report.html  deadlines.ics  match_report.md  action_plan.md

JSON files are the source of truth. Files whose front matter says `generated: false` are never overwritten.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import CandidateProfile, ApplicationState, DocumentRecord, MatchResult, RequirementStatus
from .documents import (
    DocumentInventory, derive_inventory, inventory_from_dicts, shared_documents_needed, load_categories,
)
from .matcher import load_scholarships, match_profile_all
from .roadmap import select_shortlist, build_action_plan
from .programs import load_programs, rank_programs
from . import briefs

DEFAULT_ROOT = Path("output")
CORE_SHARED_DOCS = ["passport", "degree_certificate", "transcript", "cv", "english_test", "lor_academic"]
WRITING_DOCS = {"motivation_letter", "personal_statement", "study_plan", "research_proposal", "development_impact_plan"}
FORM_DOCS = {"application_form", "university_application", "signed_declaration", "online_test", "cv_template", "portfolio"}
ADMISSION_DOCS = {"admission_letter", "supervisor_acceptance", "host_professor_cv", "nomination_letter"}
SCHOLARSHIP_SUBFOLDERS = ["essays", "letters", "recommendations", "forms", "admissions", "submitted"]
PROFILE_HELP = (
    "Candidate facts used by every agent and report. Fill as many fields as you can: missing fields make "
    "eligibility checks inconclusive. Run `cli.py build` after editing."
)


# ---------------------------------------------------------------------------
# Paths & IO
# ---------------------------------------------------------------------------

def profile_path(ws: Path) -> Path:
    return ws / "profile" / "profile.json"


def documents_path(ws: Path) -> Path:
    return ws / "profile" / "documents.json"


def scholarship_dir(ws: Path, scholarship_id: str) -> Path:
    return ws / "scholarships" / scholarship_id


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_once(path: Path, text: str) -> bool:
    if path.exists():
        return False
    _write(path, text)
    return True


def _write_json(path: Path, payload: Any) -> None:
    _write(path, json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")


def save_profile(ws: Path, profile: CandidateProfile) -> None:
    _write_json(profile_path(ws), {"_help": PROFILE_HELP, **profile.model_dump(mode="json")})


def load_profile(ws: Path) -> CandidateProfile:
    with open(profile_path(ws), "r", encoding="utf-8") as f:
        return CandidateProfile(**json.load(f))


def load_inventory(ws: Path) -> DocumentInventory:
    return DocumentInventory.load(documents_path(ws))


def load_states(ws: Path) -> Dict[str, ApplicationState]:
    states: Dict[str, ApplicationState] = {}
    for path in sorted((ws / "scholarships").glob("*/status.json")):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        raw.pop("_help", None)
        raw["documents"] = {k: {"doc_id": k, **v} for k, v in (raw.get("documents") or {}).items()}
        state = ApplicationState(**raw)
        states[state.scholarship_id] = state
    return states


def _compact_record(rec: DocumentRecord) -> Dict[str, Any]:
    data = rec.model_dump(mode="json", exclude={"doc_id"}, exclude_none=True)
    if not data.get("files"):
        data.pop("files", None)
    if not data.get("count_ready"):
        data.pop("count_ready", None)
    return data


def save_state(ws: Path, state: ApplicationState) -> None:
    data = state.model_dump(mode="json", exclude={"documents"})
    data["documents"] = {doc_id: _compact_record(rec) for doc_id, rec in state.documents.items()}
    payload = {
        "_help": ("Per-application state. application_status, deadline_confirmed (YYYY-MM-DD) and documents are read by "
                  "`cli.py build`. Paper status: have | in_progress | missing | not_applicable. Prefer `cli.py status`, "
                  "`cli.py deadline` and `cli.py docs set --scholarship`; draft files marked `status: final` count as done."),
        **data,
    }
    _write_json(scholarship_dir(ws, state.scholarship_id) / "status.json", payload)


def find_workspace(explicit: Optional[str] = None, root: Path = DEFAULT_ROOT) -> Optional[Path]:
    """Resolve --workspace, or the only workspace under output/ when there is exactly one."""
    if explicit:
        p = Path(explicit)
        return p if profile_path(p).exists() else None
    if not root.exists():
        return None
    found = [p.parent.parent for p in root.glob("*/profile/profile.json")]
    return found[0] if len(found) == 1 else None


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_workspace(profile_data: Dict[str, Any], root: Path = DEFAULT_ROOT, name: Optional[str] = None,
                     overwrite_profile: bool = False) -> Path:
    data = {k: v for k, v in profile_data.items() if not k.startswith("_")}
    documents = data.pop("documents", None)
    profile = CandidateProfile(**data)
    ws = Path(root) / (name or briefs.slugify(profile.full_name) or "candidate")
    (ws / "profile").mkdir(parents=True, exist_ok=True)

    if overwrite_profile or not profile_path(ws).exists():
        save_profile(ws, profile)
    if not documents_path(ws).exists():
        inv = derive_inventory(profile, inventory_from_dicts(documents) if documents else None)
        inv.save(documents_path(ws))
    elif documents:
        inv = load_inventory(ws)
        for doc_id, rec in inventory_from_dicts(documents).records.items():
            inv.records.setdefault(doc_id, rec)
        inv.save(documents_path(ws))
    return ws


# ---------------------------------------------------------------------------
# Draft status sync
# ---------------------------------------------------------------------------

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def _front_matter(path: Path) -> Dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta


def sync_drafts(ws: Path, state: ApplicationState) -> bool:
    """Upgrade per-application paper status from draft front matter (status: draft | review | final)."""
    folder = scholarship_dir(ws, state.scholarship_id)
    tally: Dict[str, Dict[str, int]] = {}
    for path in list(folder.glob("essays/*.md")) + list(folder.glob("letters/*.md")):
        meta = _front_matter(path)
        doc, status = meta.get("doc"), meta.get("status", "todo")
        if not doc:
            continue
        t = tally.setdefault(doc, {"final": 0, "working": 0})
        if status == "final":
            t["final"] += 1
        elif status in ("draft", "review"):
            t["working"] += 1
    changed = False
    for doc, t in tally.items():
        rec = state.documents.get(doc) or DocumentRecord(doc_id=doc)
        if t["final"] and (rec.status != "have" or rec.count_ready < t["final"]):
            rec.status, rec.count_ready = "have", max(rec.count_ready, t["final"])
            changed = True
        elif t["working"] and rec.status == "missing":
            rec.status = "in_progress"
            changed = True
        state.documents[doc] = rec
    return changed


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _seed_inventory(inv: DocumentInventory, profile: CandidateProfile, shortlist: List[MatchResult]) -> bool:
    needed = list(CORE_SHARED_DOCS)
    if profile.work_experience_years > 0:
        needed += ["lor_professional", "employment_certificate"]
    needed += shared_documents_needed([m.scholarship for m in shortlist], profile)
    changed = False
    for doc_id in needed:
        if doc_id not in inv.records:
            inv.set(DocumentRecord(doc_id=doc_id, status="missing"))
            changed = True
    return changed


def _seed_state(state: ApplicationState, m: MatchResult) -> None:
    for req in (m.readiness.requirements if m.readiness else []):
        if req.scope == "per_scholarship" and req.doc not in state.documents:
            state.documents[req.doc] = DocumentRecord(doc_id=req.doc, status="missing")


def _create_drafts(ws: Path, m: MatchResult, profile: CandidateProfile, today: date,
                   chosen_programs: Sequence[Any] = ()) -> List[str]:
    s = m.scholarship
    folder = scholarship_dir(ws, s.id)
    for sub in SCHOLARSHIP_SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    reqs: List[RequirementStatus] = m.readiness.requirements if m.readiness else []
    deadline = m.readiness.deadline if m.readiness else None

    for req in reqs:
        if req.doc == "essay":
            prompts = req.items or [f"Essay {i}" for i in range(1, req.count + 1)]
            for i, prompt in enumerate(prompts, 1):
                _write_once(folder / "essays" / f"{i:02d}_{briefs.slugify(prompt)}.md",
                            briefs.essay_template(s.name, s.id, req, i, prompt, today))
        elif req.doc in WRITING_DOCS:
            _write_once(folder / "letters" / f"{req.doc}.md", briefs.letter_template(s.name, s.id, req, profile, today))
        elif req.doc == "university_choices":
            _write_once(folder / "forms" / "university_choices.md", briefs.university_choices_template(s.name, s.id, req, today))

    refs = [q for q in reqs if q.category == "references"]
    if refs:
        _write_once(folder / "recommendations" / "referee_requests.md",
                    briefs.referee_request_template(s.name, s.id, refs, profile, deadline, today))
    forms = [q for q in reqs if q.doc in FORM_DOCS]
    if forms:
        _write_once(folder / "forms" / "CHECKLIST.md",
                    briefs.forms_checklist_template(s.name, s.id, forms, s.official_portal, today))
    admissions = [q for q in reqs if q.doc in ADMISSION_DOCS]
    if admissions:
        _write_once(folder / "admissions" / "README.md", briefs.admissions_template(s.name, s.id, admissions, today))
    _write_once(folder / "submitted" / "README.md", briefs.submitted_readme(s.name, s.id, today))
    for program in chosen_programs:
        _write_once(folder / "letters" / f"motivation_letter_{program.id}.md",
                    briefs.program_letter_template(s.name, s.id, program, profile, today))

    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*.md")
                  if p.name != "SCHOLARSHIP.md" and p.parent != folder)


def _manifest(ws: Path, profile: CandidateProfile, matches: List[MatchResult], shortlist: List[MatchResult],
              today: date) -> Dict[str, Any]:
    files = []
    for p in sorted(ws.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            rel = str(p.relative_to(ws))
            meta = _front_matter(p) if p.suffix == ".md" else {}
            files.append({"path": rel, "type": meta.get("type") or p.suffix.lstrip("."),
                          "generated": meta.get("generated", "true" if rel.startswith("reports/") else None)})
    return {
        "candidate": profile.full_name,
        "generated_on": today.isoformat(),
        "read_first": ["AGENTS.md", "INDEX.md", "PROFILE.md"],
        "sources_of_truth": {
            "profile": "profile/profile.json",
            "documents": "profile/documents.json",
            "applications": "scholarships/<id>/status.json",
        },
        "shortlist": [
            {
                "id": m.scholarship.id, "name": m.scholarship.name, "folder": f"scholarships/{m.scholarship.id}",
                "fit": m.fit_score, "readiness": m.readiness_percent, "eligibility": m.eligibility_status,
                "deadline": m.readiness.deadline.isoformat() if m.readiness and m.readiness.deadline else None,
                "deadline_estimated": m.readiness.deadline_is_estimate if m.readiness else True,
                "timeline": m.readiness.timeline_status if m.readiness else None,
                "missing": [r.doc for r in (m.readiness.missing if m.readiness else [])],
            }
            for m in shortlist
        ],
        "not_eligible": [m.scholarship.id for m in matches if not m.is_eligible],
        "files": files,
    }


def build_workspace(ws: Path, shortlist_size: int = 8, today: Optional[date] = None, reports: bool = True) -> Dict[str, Any]:
    from .xlsx_generator import generate_application_workbook
    from .html_generator import generate_html_report
    from .calendar_exporter import export_calendar_ics

    today = today or date.today()
    ws = Path(ws)
    profile = load_profile(ws)
    inventory = derive_inventory(profile, load_inventory(ws))
    states = load_states(ws)
    for state in states.values():
        if sync_drafts(ws, state):
            save_state(ws, state)

    scholarships = load_scholarships()
    programs = load_programs()
    matches = match_profile_all(profile, scholarships, inventory=inventory, states=states, today=today, programs=programs)
    skipped = {sid for sid, st in states.items() if st.application_status in ("Skipped", "Rejected")}
    shortlist = select_shortlist(matches, size=shortlist_size, include_ids=states.keys(), exclude_ids=skipped)

    _seed_inventory(inventory, profile, shortlist)
    inventory.save(documents_path(ws))
    for m in shortlist:
        state = states.get(m.scholarship.id) or ApplicationState(scholarship_id=m.scholarship.id)
        _seed_state(state, m)
        states[m.scholarship.id] = state
        save_state(ws, state)

    # Re-score with the seeded inventory and states so every report reads the same numbers.
    matches = match_profile_all(profile, scholarships, inventory=inventory, states=states, today=today, programs=programs)
    program_matches = rank_programs(profile, programs, today)
    all_program_matches = rank_programs(profile, programs, today, include_closed=True)
    by_id = {p.id: p for p in programs}
    shortlist = select_shortlist(matches, size=shortlist_size, include_ids=states.keys(), exclude_ids=skipped)
    actions = build_action_plan(profile, shortlist, today)

    for m in shortlist:
        sid = m.scholarship.id
        state = states.get(sid)
        chosen = [by_id[c] for c in (state.chosen_programs if state else []) if c in by_id]
        drafts = _create_drafts(ws, m, profile, today, chosen)
        scheme_programs = [pm for pm in program_matches if pm.program.parent_scholarship == sid]
        has_programs = any(p.parent_scholarship == sid for p in programs)
        _write(scholarship_dir(ws, sid) / "SCHOLARSHIP.md",
               briefs.render_scholarship(m, profile, state, drafts, today, scheme_programs if has_programs else None))

    for cat_id, cat in load_categories().items():
        if cat["folder"].startswith("profile/"):
            _write(ws / cat["folder"] / "README.md", briefs.render_category_readme(cat_id, inventory, today))
    _write_once(ws / "profile" / "story_bank.md", briefs.story_bank_template(profile, today))

    _write(ws / "AGENTS.md", briefs.render_agents_md(profile, today))
    _write(ws / "PROFILE.md", briefs.render_profile(profile, inventory, today))
    eligible_schemes = {m.scholarship.id for m in matches if m.is_eligible}
    index_programs = [pm for pm in program_matches if pm.program.parent_scholarship in eligible_schemes]
    _write(ws / "INDEX.md", briefs.render_index(profile, matches, shortlist, actions, inventory, today, skipped,
                                                index_programs))

    if reports:
        rep = ws / "reports"
        rep.mkdir(parents=True, exist_ok=True)
        _write(rep / "match_report.md", briefs.render_match_report(profile, matches, today))
        _write(rep / "action_plan.md", briefs.render_action_plan(profile, actions, today))
        generate_application_workbook(profile, matches, str(rep / "scholarship_tracker.xlsx"), inventory=inventory,
                                      states=states, shortlist=shortlist, actions=actions, today=today,
                                      program_matches=all_program_matches)
        generate_html_report(profile, matches, str(rep / "scholarship_report.html"), shortlist=shortlist,
                             actions=actions, inventory=inventory, today=today, program_matches=all_program_matches)
        export_calendar_ics(profile, matches, str(rep / "deadlines.ics"), shortlist=shortlist, actions=actions, today=today)

    manifest = _manifest(ws, profile, matches, shortlist, today)
    manifest["recommended_programs"] = [
        {"id": pm.program.id, "acronym": pm.program.acronym, "scheme": pm.program.parent_scholarship,
         "score": pm.score, "host_countries": pm.program.host_countries, "website": pm.program.website,
         "deadline": pm.deadline.isoformat() if pm.deadline else None}
        for pm in index_programs[:10]
    ]
    _write_json(ws / "manifest.json", manifest)
    return {"workspace": ws, "profile": profile, "matches": matches, "shortlist": shortlist, "actions": actions,
            "inventory": inventory, "states": states, "programs": program_matches}


# ---------------------------------------------------------------------------
# Updates (used by the CLI and by agents)
# ---------------------------------------------------------------------------

def _parse_bool(v: Optional[str]) -> Optional[bool]:
    if v is None:
        return None
    return v.strip().lower() in ("1", "true", "yes", "y")


def set_document(ws: Path, doc_id: str, scholarship_id: Optional[str] = None, status: Optional[str] = None,
                 file: Optional[str] = None, issued: Optional[str] = None, expires: Optional[str] = None,
                 count: Optional[int] = None, translated: Optional[str] = None, certified: Optional[str] = None,
                 apostilled: Optional[str] = None, details: Optional[str] = None, notes: Optional[str] = None) -> DocumentRecord:
    if scholarship_id:
        states = load_states(ws)
        state = states.get(scholarship_id) or ApplicationState(scholarship_id=scholarship_id)
        rec = state.documents.get(doc_id) or DocumentRecord(doc_id=doc_id)
    else:
        inv = load_inventory(ws)
        rec = inv.get(doc_id) or DocumentRecord(doc_id=doc_id)

    if status:
        rec.status = status  # type: ignore[assignment]
    if file and file not in rec.files:
        rec.files.append(file)
    if issued:
        rec.issued = date.fromisoformat(issued)
    if expires:
        rec.expires = date.fromisoformat(expires)
    if count is not None:
        rec.count_ready = count
    for attr, raw in (("translated", translated), ("certified", certified), ("apostilled", apostilled)):
        if raw is not None:
            setattr(rec, attr, _parse_bool(raw))
    if details:
        rec.details = details
    if notes:
        rec.notes = notes

    if scholarship_id:
        state.documents[doc_id] = rec
        save_state(ws, state)
    else:
        inv.set(rec)
        inv.save(documents_path(ws))
    return rec


def apply_workbook_edits(ws: Path) -> Dict[str, int]:
    """Copy edits made in reports/scholarship_tracker.xlsx back into the JSON sources of truth."""
    from .xlsx_generator import read_workbook_edits
    path = ws / "reports" / "scholarship_tracker.xlsx"
    if not path.exists():
        return {"documents": 0, "scholarship_documents": 0, "application_status": 0}
    edits = read_workbook_edits(str(path))
    counts = {"documents": 0, "scholarship_documents": 0, "application_status": 0}

    inv = load_inventory(ws)
    for doc_id, e in edits["documents"].items():
        if e["status"] not in ("have", "in_progress", "missing", "not_applicable"):
            continue
        is_new = doc_id not in inv.records
        if is_new and e["status"] == "missing" and not e.get("files"):
            continue  # untouched row for a paper the candidate never tracked
        rec = inv.get(doc_id) or DocumentRecord(doc_id=doc_id)
        before = rec.model_dump()
        rec.status, rec.count_ready = e["status"], e["count_ready"]
        for key in ("issued", "translated", "certified", "apostilled", "details"):
            if e.get(key) is not None:
                setattr(rec, key, e[key])
        if e.get("files"):
            rec.files = e["files"]
        expiry_was_derived = rec.expires is None and inv.effective_expiry(doc_id) == e.get("expires")
        if e.get("expires") and not expiry_was_derived:
            rec.expires = e["expires"]
        if rec.model_dump() != before or is_new:
            counts["documents"] += 1
        inv.set(rec)
    inv.save(documents_path(ws))

    states = load_states(ws)
    for sid, docs in edits["scholarship_documents"].items():
        state = states.get(sid) or ApplicationState(scholarship_id=sid)
        for doc_id, e in docs.items():
            rec = state.documents.get(doc_id) or DocumentRecord(doc_id=doc_id)
            if (rec.status, rec.count_ready) != (e["status"], e["count_ready"]):
                rec.status, rec.count_ready = e["status"], e["count_ready"]
                counts["scholarship_documents"] += 1
            state.documents[doc_id] = rec
        states[sid] = state
    for sid, status in edits["application_status"].items():
        state = states.get(sid)
        current = state.application_status if state else "Not Started"
        if status and status != current:
            # Setting a status on a non-shortlisted scholarship starts tracking it (it gets its own folder).
            state = state or ApplicationState(scholarship_id=sid)
            state.application_status = status
            states[sid] = state
            counts["application_status"] += 1
    if edits.get("has_programs_sheet"):
        chosen_by_scheme = edits.get("chosen_programs", {})
        for sid in set(chosen_by_scheme) | {k for k, st in states.items() if st.chosen_programs}:
            chosen = chosen_by_scheme.get(sid, [])  # a scheme missing here had every "Chosen" cell set to "no"
            state = states.get(sid) or ApplicationState(scholarship_id=sid)
            if sorted(chosen) != sorted(state.chosen_programs):
                state.chosen_programs = chosen
                counts["chosen_programs"] = counts.get("chosen_programs", 0) + 1
            states[sid] = state
    for state in states.values():
        save_state(ws, state)
    return counts


def set_deadline(ws: Path, scholarship_id: str, deadline: str, source: Optional[str] = None,
                 today: Optional[date] = None) -> ApplicationState:
    states = load_states(ws)
    state = states.get(scholarship_id) or ApplicationState(scholarship_id=scholarship_id)
    state.deadline_confirmed = date.fromisoformat(deadline)
    state.deadline_source = source
    state.deadline_verified_on = today or date.today()
    save_state(ws, state)
    return state


def set_application_status(ws: Path, scholarship_id: str, status: str, notes: Optional[str] = None) -> ApplicationState:
    states = load_states(ws)
    state = states.get(scholarship_id) or ApplicationState(scholarship_id=scholarship_id)
    state.application_status = status
    if notes:
        state.notes = (state.notes + "\n" if state.notes else "") + notes
    save_state(ws, state)
    return state


def set_study_location(ws: Path, study_location: str) -> CandidateProfile:
    """Study at home (no travel), abroad, or both. Edits profile/profile.json in place and keeps its other keys."""
    path = profile_path(ws)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    raw["study_location"] = study_location
    profile = CandidateProfile(**raw)
    _write_json(path, raw)
    return profile


def choose_program(ws: Path, program_id: str, remove: bool = False) -> ApplicationState:
    """Add (or remove) a program to its scheme's chosen_programs (e.g. up to 3 Erasmus Mundus masters)."""
    programs = {p.id: p for p in load_programs()}
    if program_id not in programs:
        raise ValueError(f"Unknown program id '{program_id}'")
    sid = programs[program_id].parent_scholarship
    states = load_states(ws)
    state = states.get(sid) or ApplicationState(scholarship_id=sid)
    if remove:
        state.chosen_programs = [c for c in state.chosen_programs if c != program_id]
    elif program_id not in state.chosen_programs:
        state.chosen_programs.append(program_id)
    save_state(ws, state)
    return state
