"""
Markdown renderers for the candidate workspace: agent rules, index, profile, per-scholarship briefs,
match report, and the one-time draft templates (essays, letters, referee requests, form checklists).

Every generated file starts with YAML front matter. `generated: true` files are rebuilt by `cli.py build`;
`generated: false` files belong to the candidate and are never overwritten.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import CandidateProfile, MatchResult, RequirementStatus, ApplicationState, ProgramMatch, Program
from .documents import DocumentInventory, load_catalog, load_categories, catalog_doc

TEMPLATES_PATH = Path(__file__).parent.parent / "data" / "document_templates.json"

STATE_ICON = {
    "have": "✅ have", "partial": "🟡 partial", "in_progress": "🟡 in progress", "expiring": "⚠️ expiring",
    "missing": "❌ missing", "not_applicable": "➖ n/a",
}
GATE_ICON = {"pass": "✅", "fail": "❌", "unknown": "❓", "warn": "⚠️"}
TIMELINE_ICON = {
    "Ready": "🟢", "On track": "🟢", "Tight": "🟡", "At risk": "🟠", "Not feasible this cycle": "🔴",
    "Deadline passed": "⚫", "Deadline unknown": "⚪",
}
PROFILE_GAP_FIELDS = [
    ("date_of_birth", "date of birth (age limits)"),
    ("graduation_year", "graduation year (degree-recency rules)"),
    ("country_of_residence", "country of residence (residence rules)"),
    ("english_test_date", "English test date (2-year validity)"),
    ("english_min_band", "lowest English sub-score (band minimums)"),
    ("university", "university name (letters and CV)"),
    ("leadership_examples", "leadership stories (essays, profile score)"),
    ("career_goal", "career goal (motivation letters)"),
    ("home_country_problem", "problem you want to solve at home (impact statements)"),
    ("field_keywords", "field keywords (field matching)"),
]


def front_matter(meta: Dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(json.dumps(x, ensure_ascii=False) for x in v)}]")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif v is None:
            lines.append(f"{k}: null")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) and (':' in v or v != v.strip()) else v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    def cell(x: Any) -> str:
        return str("" if x is None else x).replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(out) + "\n"


def slugify(text: str) -> str:
    keep = "".join(c.lower() if c.isalnum() else "-" for c in text)
    return "-".join(p for p in keep.split("-") if p)[:60]


def deadline_text(m: MatchResult) -> str:
    r = m.readiness
    if not r or not r.deadline:
        return "Unknown"
    return r.deadline.isoformat() + (" (est.)" if r.deadline_is_estimate else "")


def days_text(m: MatchResult) -> str:
    r = m.readiness
    if not r or r.days_left is None:
        return "-"
    return f"{r.days_left}" if r.days_left >= 0 else "passed"


def _load_templates() -> Dict[str, Any]:
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Workspace-level files
# ---------------------------------------------------------------------------

def render_agents_md(profile: CandidateProfile, today: date) -> str:
    return front_matter({"type": "agent_rules", "generated": True, "updated": today.isoformat()}) + f"""# Rules for agents working in this folder

This is the scholarship workspace of **{profile.full_name}**. Follow these rules every time.

## Read in this order
1. `INDEX.md`: map of every file, ranked shortlist, next actions, missing papers.
2. `PROFILE.md`: who the candidate is (generated from `profile/profile.json`).
3. `scholarships/<id>/SCHOLARSHIP.md`: the brief for the scholarship you are working on.
4. `profile/story_bank.md`: before writing any essay or letter.

## Sources of truth
| What | File | How to change it |
|---|---|---|
| Candidate facts | `profile/profile.json` | Edit the JSON, then `cli.py build` |
| Papers the candidate holds | `profile/documents.json` | `cli.py docs set <doc_id> --status have --file <path>` |
| Per-application state | `scholarships/<id>/status.json` | `cli.py docs set <doc_id> --scholarship <id> ...`, `cli.py status`, `cli.py deadline` |
| Everything else (`generated: true`) | Markdown & reports | Rebuilt by `cli.py build`: never hand-edit |

## Do
- Never ask the candidate for information that is already in `profile/profile.json` or `documents.json`.
- When you learn a new fact (date of birth, a new award, a referee), write it to the JSON and rebuild.
- Save drafts only inside the scholarship folder (`essays/`, `letters/`, `recommendations/`, `forms/`). Keep the front matter and set `status: draft | review | final`.
- Store scanned papers under `profile/<category>/` and record the path in `documents.json`.
- Treat deadlines marked **(est.)** as unverified: check the official site and record the date with `cli.py deadline --scholarship <id> --date YYYY-MM-DD --source <url>`.
- For Erasmus Mundus, help the candidate pick up to 3 programs (`cli.py programs`, then `cli.py programs --choose <id>`); each choice gets its own motivation-letter draft.
- Answer the candidate in their own language; keep files and commands in English.
- Run `cli.py review-essay --file <essay>` on essays before calling them final.

## Don't
- Don't overwrite files whose front matter says `generated: false`; they are the candidate's work.
- Don't invent achievements, grades, or referees. Ask, or leave a `TODO:`.
- Don't copy one motivation letter to several scholarships unchanged.
"""


def render_index(profile: CandidateProfile, matches: List[MatchResult], shortlist: List[MatchResult],
                 actions: List[Dict[str, Any]], inventory: DocumentInventory, today: date,
                 skipped: Sequence[str] = (), programs: Optional[Sequence[ProgramMatch]] = None) -> str:
    eligible = [m for m in matches if m.is_eligible]
    passed = [m for m in eligible if m.readiness and m.readiness.timeline_status in ("Deadline passed", "Not feasible this cycle")]
    ineligible = [m for m in matches if not m.is_eligible]

    out = front_matter({
        "type": "workspace_index", "generated": True, "candidate": profile.full_name,
        "target": f"{profile.target_degree} {profile.target_intake_year}", "updated": today.isoformat(),
        "shortlist": [m.scholarship.id for m in shortlist],
    })
    out += f"# Scholarship workspace: {profile.full_name}\n\n"
    out += (f"**Target:** {profile.target_degree} in {profile.field_of_study}, intake {profile.target_intake_year} · "
            f"**Nationality:** {profile.nationality} · **Updated:** {today.isoformat()}\n\n")
    out += ("> Agents: read `AGENTS.md` for the rules, then `PROFILE.md`. JSON files are the source of truth; "
            "Markdown files with `generated: true` are rebuilt by `cli.py build`.\n\n")

    out += "## Shortlist (ranked by priority)\n\n"
    out += ("Priority = 55% fit + 20% readiness + funding value + time left. "
            "**Fit** = how well you match. **Ready** = share of papers you already have.\n\n")
    rows = []
    for i, m in enumerate(shortlist, 1):
        r = m.readiness
        rows.append([
            i, f"[{m.scholarship.name}](scholarships/{m.scholarship.id}/SCHOLARSHIP.md)", m.scholarship.country,
            f"{m.fit_score:.0f}", f"{m.readiness_percent:.0f}%", deadline_text(m), days_text(m),
            f"{TIMELINE_ICON.get(r.timeline_status, '')} {r.timeline_status}" if r else "-",
            m.eligibility_status, m.tier,
        ])
    out += md_table(["#", "Scholarship", "Country", "Fit", "Ready", "Deadline", "Days", "Timeline", "Eligibility", "Tier"], rows)

    out += "\n## Next actions\n\n"
    upcoming = [a for a in actions if a["bucket"] != "After submitting"][:15]
    if upcoming:
        out += md_table(
            ["When", "Task", "Start by", "Due by", "For"],
            [[("⏰ overdue" if a["overdue"] else a["bucket"]), a["title"],
              a["start_by"].isoformat() if a["start_by"] else "-", a["due_by"].isoformat() if a["due_by"] else "-",
              ", ".join(a["needed_for"][:3]) + ("..." if len(a["needed_for"]) > 3 else "")] for a in upcoming],
        )
        out += "\nFull plan: `reports/action_plan.md` and the *Action Plan* sheet in `reports/scholarship_tracker.xlsx`.\n"
    else:
        out += "Nothing scheduled: all shortlisted applications are ready.\n"

    if programs:
        out += "\n## Programs that fit you (Erasmus Mundus and others)\n\n"
        out += render_programs_table(programs, limit=8)
        out += "\nFull list: *Programs* sheet in the Excel tracker, or `cli.py programs`.\n"

    out += "\n## Missing papers across the shortlist\n\n"
    missing: Dict[str, Dict[str, Any]] = {}
    for m in shortlist:
        for req in (m.readiness.missing if m.readiness else []):
            entry = missing.setdefault(req.doc, {"name": req.name, "for": [], "start": req.start_by, "lead": req.lead_time_days, "scope": req.scope})
            entry["for"].append(m.scholarship.name)
            if req.start_by and (entry["start"] is None or req.start_by < entry["start"]):
                entry["start"] = req.start_by
    if missing:
        rows = sorted(missing.values(), key=lambda e: (e["start"] or date.max))
        out += md_table(
            ["Paper", "Type", "Needed for", "Start by", "Takes"],
            [[e["name"], "shared" if e["scope"] == "shared" else "per scholarship", ", ".join(e["for"]),
              e["start"].isoformat() if e["start"] else "-", f"{e['lead'][0]}-{e['lead'][-1]} days"] for e in rows],
        )
    else:
        out += "None. Every shortlisted application has its papers.\n"

    if passed:
        out += "\n## Eligible, but closed or too late for this cycle\n\n"
        out += md_table(
            ["Scholarship", "Fit", "Deadline", "Next cycle (est.)"],
            [[m.scholarship.name, f"{m.fit_score:.0f}", deadline_text(m),
              m.readiness.next_cycle_deadline.isoformat() if m.readiness.next_cycle_deadline else "-"] for m in passed],
        )

    skipped_matches = [m for m in matches if m.scholarship.id in set(skipped)]
    if skipped_matches:
        out += "\n## Skipped or rejected (folders kept)\n\n"
        out += "\n".join(f"- {m.scholarship.name} (`scholarships/{m.scholarship.id}/`)" for m in skipped_matches) + "\n"

    out += "\n## Not eligible\n\n"
    out += md_table(
        ["Scholarship", "Why"],
        [[m.scholarship.name, "; ".join(g.detail for g in m.gate_checks if g.result == "fail")] for m in ineligible],
    )

    have = sum(1 for r in inventory.records.values() if r.status == "have")
    out += f"\n## File map\n\n"
    out += f"""```
AGENTS.md                  rules for agents (read first)
INDEX.md                   this file
PROFILE.md                 who the candidate is (generated from profile/profile.json)
manifest.json              machine-readable map of this workspace
profile/
  profile.json             candidate facts: SOURCE OF TRUTH
  documents.json           papers held ({have} marked 'have'): SOURCE OF TRUTH
  story_bank.md            STAR stories reused across essays (candidate-owned)
  identity/ academic/ language/ experience/ references/ cv/ certifications/ financial/ health_legal/
scholarships/<id>/
  SCHOLARSHIP.md           requirements, score breakdown, missing papers, plan (generated)
  status.json              application status, confirmed deadline, per-application papers
  essays/ letters/         drafts (candidate-owned)
  recommendations/         referee requests
  forms/ admissions/       portal steps, offers, supervisor letters
  submitted/               final PDFs and confirmation emails
reports/
  scholarship_tracker.xlsx  full workbook (dashboard, scores, papers, plan)
  scholarship_report.html   interactive report
  deadlines.ics             calendar with reminders
  match_report.md           every scholarship with its score breakdown
  action_plan.md            dated plan
```
"""
    return out


def render_profile(profile: CandidateProfile, inventory: DocumentInventory, today: date) -> str:
    p = profile
    out = front_matter({"type": "candidate_profile", "generated": True, "source": "profile/profile.json",
                        "updated": today.isoformat()})
    out += f"# {p.full_name}\n\n"
    age = p.age_on(today)
    facts = [
        ("Nationality", p.nationality),
        ("Lives in", p.residence),
        ("Age", f"{age} (born {p.date_of_birth.isoformat()})" if age is not None else "unknown"),
        ("Email", p.email or "-"),
        ("Target", f"{p.target_degree} · {p.field_of_study} · intake {p.target_intake_year}"),
        ("Funding wanted", p.target_funding),
        ("Target countries", ", ".join(p.target_countries) or "Worldwide"),
        ("Returns home after study", "Yes" if p.willing_to_return_home else "No"),
    ]
    out += md_table(["", ""], facts)

    out += "\n## Education\n\n"
    out += md_table(["", ""], [
        ("Current degree", p.current_degree),
        ("University", p.university or "-"),
        ("Graduation year", p.graduation_year or "-"),
        ("GPA", f"{p.gpa:g} / {p.gpa_scale:g}" + (f" (≈ {p.normalized_gpa:.2f} / 4.0)" if p.gpa_scale != 4.0 else "")),
        ("Class rank", f"Top {p.class_rank_percent:g}%" if p.class_rank_percent else "-"),
        ("Thesis / project", p.thesis_title or "-"),
        ("Field keywords", ", ".join(p.field_keywords) or "-"),
    ])

    out += "\n## Languages\n\n"
    lang_rows = [("English", f"{p.english_test or 'No test'} {p.english_score if p.english_score is not None else ''}".strip()
                  + (f", taken {p.english_test_date.isoformat()}" if p.english_test_date else "")
                  + (f", lowest band {p.english_min_band:g}" if p.english_min_band else ""))]
    lang_rows += [(l.language, " ".join(x for x in [l.level or "", l.certificate or ""] if x) or "-") for l in p.other_languages]
    out += md_table(["Language", "Level"], lang_rows)

    out += "\n## Experience & research\n\n"
    out += md_table(["", ""], [
        ("Work experience", f"{p.work_experience_years:g} years" + (" (still employed)" if p.currently_employed else "")),
        ("Current role", " at ".join(x for x in [p.current_job_title, p.current_employer] if x) or "-"),
        ("Publications", f"{p.research_publications}" + (": " + "; ".join(p.publications) if p.publications else "")),
        ("Skills", ", ".join(p.skills) or "-"),
    ])

    def bullets(items: List[str], empty: str) -> str:
        return "\n".join(f"- {i}" for i in items) + "\n" if items else f"_{empty}_\n"

    out += "\n## Leadership & impact\n\n" + bullets(p.leadership_examples, "None recorded. Add STAR stories to profile.json and story_bank.md.")
    out += "\n**Awards**\n\n" + bullets(p.awards, "None recorded.")
    out += "\n**Volunteering**\n\n" + bullets(p.volunteering, "None recorded.")

    out += "\n## Goals\n\n"
    out += f"- **Career goal:** {p.career_goal or 'TODO: not recorded'}\n"
    out += f"- **Problem to solve at home:** {p.home_country_problem or 'TODO: not recorded'}\n"
    if p.notes:
        out += f"- **Notes:** {p.notes}\n"

    out += "\n## Papers on file\n\n"
    catalog = load_catalog()
    categories = load_categories()
    rows = []
    for doc_id, rec in sorted(inventory.records.items(), key=lambda kv: (catalog_doc(kv[0]).category, kv[0])):
        cat = catalog.get(doc_id)
        rows.append([
            cat.name if cat else doc_id, f"`{doc_id}`", categories.get(cat.category, {}).get("title", "-") if cat else "-",
            STATE_ICON.get(rec.status, rec.status) + (f" ×{rec.count_ready}" if rec.count_ready > 1 else ""),
            inventory.effective_expiry(doc_id).isoformat() if inventory.effective_expiry(doc_id) else "-",
            ", ".join(rec.files) or "-", rec.details or "",
        ])
    out += md_table(["Paper", "Id", "Folder", "Status", "Expires", "Files", "Details"], rows) if rows else "_No papers recorded yet._\n"

    gaps = [label for field, label in PROFILE_GAP_FIELDS if not getattr(p, field)]
    if gaps:
        out += "\n## Missing profile information\n\nAdding these to `profile/profile.json` makes the scores more accurate:\n\n"
        out += "\n".join(f"- {g}" for g in gaps) + "\n"
    return out


def render_category_readme(cat_id: str, inventory: DocumentInventory, today: date) -> str:
    cat = load_categories()[cat_id]
    docs = [d for d in load_catalog().values() if d.category == cat_id]
    out = front_matter({"type": "folder_guide", "generated": True, "category": cat_id, "updated": today.isoformat()})
    out += f"# {cat['title']}\n\nPut scans (PDF, 300 dpi) of these papers here, then record the path in `profile/documents.json`.\n\n"
    rows = []
    for d in docs:
        rec = inventory.get(d.id)
        rows.append([d.name, f"`{d.id}`", STATE_ICON.get(rec.status, rec.status) if rec else "not tracked",
                     ", ".join(rec.files) if rec and rec.files else f"{d.id}.pdf", d.how_to_obtain])
    out += md_table(["Paper", "Id", "Status", "File", "How to get it"], rows)
    return out


def render_programs_table(matches: Sequence[ProgramMatch], chosen: Sequence[str] = (), limit: int = 10) -> str:
    rows = []
    for i, pm in enumerate(list(matches)[:limit], 1):
        p = pm.program
        deadline = (pm.deadline.isoformat() + (" (est.)" if pm.deadline_is_estimate else "")) if pm.deadline else "see site"
        mark = "⭐ " if p.id in chosen else ""
        rows.append([i, f"{mark}**{p.acronym}**: {p.name}", f"{pm.score:.0f}", pm.field_match,
                     ", ".join(p.host_countries) or "-", deadline, p.status.replace("_", " "), f"[site]({p.website})"])
    if not rows:
        return "_No matching programs found._\n"
    return md_table(["#", "Program", "Score", "Field", "Where you study", "Deadline", "Status", "Link"], rows)


# ---------------------------------------------------------------------------
# Per-scholarship brief
# ---------------------------------------------------------------------------

def _req_location(req: RequirementStatus, s_id: str) -> str:
    cats = load_categories()
    folder = cats.get(req.category, {}).get("folder", "forms")
    return folder + "/" if req.scope == "shared" else f"scholarships/{s_id}/{folder}/"


def render_scholarship(m: MatchResult, profile: CandidateProfile, state: Optional[ApplicationState],
                       drafts: List[str], today: date, programs: Optional[Sequence[ProgramMatch]] = None) -> str:
    s, r = m.scholarship, m.readiness
    cov = s.coverage_details
    out = front_matter({
        "type": "scholarship_brief", "generated": True, "scholarship_id": s.id, "updated": today.isoformat(),
        "fit": m.fit_score, "readiness": m.readiness_percent, "eligibility": m.eligibility_status,
        "deadline": r.deadline.isoformat() if r and r.deadline else None,
        "deadline_estimated": r.deadline_is_estimate if r else True,
        "application_status": state.application_status if state else "Not Started",
    })
    out += f"# {s.name}\n\n"
    out += f"{s.organization} · {s.country} · {', '.join(s.degrees)} · **{s.funding_type} funding** · tier: {m.tier}\n\n"
    if s.program_status != "active":
        out += f"> ⚠️ Program status: **{s.program_status}**. {s.program_status_note or ''}\n\n"

    out += "## At a glance\n\n"
    tl = r.timeline_status if r else "Deadline unknown"
    glance = [
        ("Eligibility", f"{m.eligibility_status}"),
        ("Fit score", f"{m.fit_score:.0f} / 100 ({m.match_status})"),
        ("Readiness", f"{m.readiness_percent:.0f}% of papers ({r.have_count}/{r.total_count})" if r else "-"),
        ("Deadline", f"{deadline_text(m)} · {r.deadline_label}" if r else "Unknown"),
        ("Days left", days_text(m)),
        ("Timeline", f"{TIMELINE_ICON.get(tl, '')} {tl}"),
        ("Application status", state.application_status if state else "Not Started"),
        ("Portal", f"{s.official_portal} ({s.application_portal_system})"),
    ]
    if r and r.next_cycle_deadline:
        glance.insert(5, ("Next cycle (est.)", r.next_cycle_deadline.isoformat()))
    if s.timeline.deadline and s.timeline.deadline.note:
        glance.append(("Deadline note", s.timeline.deadline.note))
    if r and r.deadline_source:
        glance.append(("Deadline source", r.deadline_source))
    out += md_table(["", ""], glance)

    if m.next_steps:
        out += "\n## What to do next\n\n" + "\n".join(f"{i}. {step}" for i, step in enumerate(m.next_steps[:10], 1)) + "\n"

    if programs is not None:
        chosen = state.chosen_programs if state else []
        out += "\n## Programs that fit you\n\n"
        out += ("Ranked by field match, host country, language and funding. "
                + ("You can apply to **up to 3** Erasmus Mundus programs per year. " if s.id == "erasmus-mundus" else "")
                + "Choose with `cli.py programs --choose <id>`; your deadline then follows your chosen programs.\n\n")
        out += render_programs_table(programs, chosen)
        if chosen:
            out += "\n**Chosen:** " + ", ".join(f"`{c}`" for c in chosen) + "\n"

    out += "\n## Eligibility checks\n\n"
    out += md_table(["Check", "Result", "Detail", "Fix"],
                    [[g.name, f"{GATE_ICON[g.result]} {g.result}", g.detail, g.fix or ""] for g in m.gate_checks])

    out += "\n## Fit score breakdown\n\n"
    out += md_table(["Part", "Points", "Why"],
                    [[c.name, f"{c.points:g} / {c.weight:g}", c.detail] for c in m.score_breakdown])
    out += f"\n**Total: {m.fit_score:.0f} / 100.** High match ≥ 80, moderate ≥ 62.\n"

    if r:
        out += "\n## Required papers\n\n"
        rows = []
        for q in r.requirements:
            need = f"{q.count_ready}/{q.count}" if q.count > 1 else ""
            flags = []
            if q.optional:
                flags.append("optional")
            if q.stage == "later":
                flags.append("after submission")
            if q.satisfied_via:
                flags.append(f"via {q.satisfied_via}")
            rows.append([
                q.label, f"`{q.doc}`", f"{STATE_ICON.get(q.state, q.state)} {need}".strip(),
                ", ".join(flags), q.start_by.isoformat() if q.start_by and q.units < 1 else "",
                _req_location(q, s.id), "; ".join(q.issues),
            ])
        out += md_table(["Paper (as the program words it)", "Id", "Status", "Notes", "Start by", "Where", "Issues"], rows)
        missing = r.missing
        if missing:
            out += "\n### How to get the missing papers\n\n"
            for q in missing:
                out += f"- **{q.name}** (takes {q.lead_time_days[0]}-{q.lead_time_days[-1]} days): {q.how_to_obtain}\n"

    out += "\n## What the scholarship pays\n\n"
    out += md_table(["Item", "Covered"], [
        ("Tuition", "Yes" if cov.tuition_covered else "No"),
        ("Monthly stipend", cov.monthly_stipend),
        ("Flights", "Yes" if cov.airfare_covered else "No"),
        ("Health insurance", "Yes" if cov.health_insurance else "No"),
        ("Accommodation", "Yes" if cov.accommodation_covered else "No"),
        ("Visa fees", "Yes" if cov.visa_fees_covered else "No"),
        ("Other allowances", cov.additional_allowances or "-"),
    ])

    e = s.eligibility
    out += "\n## Official eligibility (as published)\n\n"
    out += md_table(["", ""], [
        ("Nationalities", e.eligible_nationalities), ("Grades", e.gpa_requirement), ("Language", e.language_requirements),
        ("Work experience", f"{e.work_experience_years:g} years" + (f" ({e.work_hours_required:,} hours)" if e.work_hours_required else "")),
        ("Age", e.age_limit or "No limit stated"), ("Fields", e.field_restrictions), ("Return obligation", e.return_obligation or "None"),
    ])

    t = s.timeline
    out += "\n## Timeline\n\n"
    out += md_table(["Stage", "When"], [
        (k, v) for k, v in [
            ("Applications open", t.opening_month), ("Deadline (as published)", t.typical_deadline),
            ("Nomination", t.sending_partner_nomination), ("Interviews", t.interview_period),
            ("Results", t.result_announcement), ("University offer by", t.university_offer_deadline),
            ("Course starts", t.course_start),
        ] if v
    ])

    out += f"\n## Strategy\n\n{s.strategic_tips}\n"
    if drafts:
        out += "\n## Drafts in this folder\n\n" + "\n".join(f"- [`{d}`]({d})" for d in drafts) + "\n"
    if state and state.notes:
        out += f"\n## Notes\n\n{state.notes}\n"
    return out


def render_match_report(profile: CandidateProfile, matches: List[MatchResult], today: date) -> str:
    out = front_matter({"type": "match_report", "generated": True, "updated": today.isoformat()})
    out += f"# Match report: {profile.full_name}\n\nAll {len(matches)} scholarships, ranked by priority.\n\n"
    out += md_table(
        ["#", "Scholarship", "Eligibility", "Fit", "Ready", "Deadline", "Timeline", "Priority"],
        [[i, m.scholarship.name, m.eligibility_status, f"{m.fit_score:.0f}", f"{m.readiness_percent:.0f}%",
          deadline_text(m), m.readiness.timeline_status if m.readiness else "-", f"{m.priority_score:.0f}"]
         for i, m in enumerate(matches, 1)],
    )
    for m in matches:
        out += f"\n## {m.scholarship.name}\n\n"
        out += f"**{m.eligibility_status}** · fit {m.fit_score:.0f} · ready {m.readiness_percent:.0f}% · deadline {deadline_text(m)}\n\n"
        out += "\n".join(f"- {GATE_ICON[g.result]} **{g.name}**: {g.detail}" for g in m.gate_checks) + "\n"
        out += "\n".join(f"- {c.name}: {c.points:g}/{c.weight:g}: {c.detail}" for c in m.score_breakdown) + "\n"
    return out


def render_action_plan(profile: CandidateProfile, actions: List[Dict[str, Any]], today: date) -> str:
    from .roadmap import PHASES
    out = front_matter({"type": "action_plan", "generated": True, "updated": today.isoformat()})
    out += f"# Action plan: {profile.full_name}\n\nScheduled backwards from each deadline using how long every paper takes.\n"
    for name, desc in PHASES:
        items = [a for a in actions if a["bucket"] == name]
        if not items:
            continue
        out += f"\n## {name}\n\n_{desc}_\n\n"
        out += md_table(
            ["Task", "Start by", "Due by", "For", "Details"],
            [[("⏰ " if a["overdue"] else "") + a["title"], a["start_by"].isoformat() if a["start_by"] else "-",
              a["due_by"].isoformat() if a["due_by"] else "-", ", ".join(a["needed_for"]), a["details"]] for a in items],
        )
    return out


# ---------------------------------------------------------------------------
# One-time templates (candidate-owned: generated: false)
# ---------------------------------------------------------------------------

def _draft_header(s_id: str, doc: str, title: str, today: date, **extra: Any) -> str:
    meta = {"type": "draft", "generated": False, "scholarship_id": s_id, "doc": doc, "title": title,
            "status": "todo", "created": today.isoformat()}
    meta.update(extra)
    return front_matter(meta)


def story_bank_template(profile: CandidateProfile, today: date) -> str:
    out = front_matter({"type": "story_bank", "generated": False, "created": today.isoformat()})
    out += ("# Story bank\n\nReusable stories for essays, interviews and referee briefs. Write each one in STAR form "
            "with numbers. Essays should pull from here instead of inventing new material.\n")
    seeds = list(profile.leadership_examples) or ["TODO: a time you led a team through a hard problem"]
    seeds += ["TODO: a time you influenced someone without authority", "TODO: a failure and what you changed afterwards",
              "TODO: why this field (the moment it clicked)"]
    for i, seed in enumerate(seeds, 1):
        out += f"""
## Story {i}: {seed}

- **Situation:**
- **Task:**
- **Action (what *you* did):**
- **Result (numbers):**
- **Skills shown:** leadership / networking / resilience / technical
- **Used in:**
"""
    return out


def essay_template(s_name: str, s_id: str, req: RequirementStatus, idx: int, prompt: str, today: date) -> str:
    words = req.words
    out = _draft_header(s_id, "essay", prompt, today, word_limit=words, index=idx)
    p = prompt.lower()
    review = "sop"
    if s_id == "chevening":
        review = next((t for key, t in (("lead", "chevening_leadership"), ("network", "chevening_networking"),
                                        ("uk", "chevening_study_uk"), ("career", "chevening_career")) if key in p), "sop")
    out += f"""# {s_name}: essay {idx}: {prompt}

**Word limit:** {words or 'see portal'} · **Review:** `cli.py review-essay --file <path to this file> --type {review}`

## What the panel looks for
- One or two concrete stories (from `profile/story_bank.md`), told with STAR: Situation, Task, Action, Result.
- Numbers in the Result (people, money, time, %).
- A clear link from the story to your goal and to this scholarship's mission.

## Outline
1. Hook: the situation in one sentence.
2. Your task and why it was hard.
3. What you did (most of the words go here).
4. Result, with numbers.
5. What it shows about you and how it connects to {s_name}.

## Draft

TODO: write here.
"""
    return out


def letter_template(s_name: str, s_id: str, req: RequirementStatus, profile: CandidateProfile, today: date) -> str:
    tpl = _load_templates()
    out = _draft_header(s_id, req.doc, req.label, today, word_limit=req.words)
    out += f"# {s_name}: {req.name}\n\n**As the program words it:** {req.label}\n\n"
    if req.words:
        out += f"**Word limit:** {req.words}\n\n"
    if req.doc == "research_proposal":
        out += "## Structure\n\n" + "\n".join(f"- {sec}" for sec in tpl["research_proposal"]["sections"]) + "\n"
    else:
        out += "## Structure\n\n"
        for sec in tpl["statement_of_purpose"]["structure"]:
            out += f"- **{sec['section']}:** {sec['description']}\n"
    out += "\n## Facts to use (from your profile)\n\n"
    facts = [
        f"Degree: {profile.current_degree}" + (f", {profile.university}" if profile.university else ""),
        f"GPA {profile.gpa:g}/{profile.gpa_scale:g}",
        f"{profile.work_experience_years:g} years of work" + (f" as {profile.current_job_title}" if profile.current_job_title else ""),
        f"Career goal: {profile.career_goal or 'TODO'}",
        f"Problem at home: {profile.home_country_problem or 'TODO'}",
    ]
    out += "\n".join(f"- {f}" for f in facts) + "\n\n## Draft\n\nTODO: write here.\n"
    return out


def referee_request_template(s_name: str, s_id: str, reqs: List[RequirementStatus], profile: CandidateProfile,
                             deadline: Optional[date], today: date) -> str:
    out = _draft_header(s_id, "references", "Referee requests", today)
    out += f"# {s_name}: recommendation letters\n\n"
    out += md_table(["Needed", "Count", "Requirements"],
                    [[q.label, q.count, ", ".join(q.requires) or "-"] for q in reqs])
    due = deadline.isoformat() if deadline else "the deadline"
    out += f"""
## Referees for this application

| Name | Role | Email | Asked on | Status |
|---|---|---|---|---|
| TODO |  |  |  |  |

## Request email (edit before sending)

Subject: Recommendation letter for the {s_name}

Dear [Name],

I am applying for the {s_name} to pursue a {profile.target_degree} in {profile.field_of_study}. Because you know my work
from [course / project / job], I would be very grateful if you could write a recommendation letter for me.

The letter is due by {due}. I will send you my CV, a one-page brag sheet (`cli.py draft-lor --brag-sheet`) and the
submission instructions. I am happy to meet to go over anything that would help.

Thank you for considering this.

Best regards,
{profile.full_name}
"""
    return out


def university_choices_template(s_name: str, s_id: str, req: RequirementStatus, today: date) -> str:
    out = _draft_header(s_id, "university_choices", req.label, today)
    out += f"# {s_name}: program choices\n\n{req.label}\n\n"
    out += md_table(["#", "University", "Program", "Program deadline", "Why it fits", "Applied?"],
                    [[i, "", "", "", "", ""] for i in range(1, max(req.count, 1) + 1)])
    return out


def forms_checklist_template(s_name: str, s_id: str, reqs: List[RequirementStatus], portal: str, today: date) -> str:
    out = _draft_header(s_id, "forms", "Forms and portal steps", today)
    out += f"# {s_name}: forms and portal steps\n\nPortal: {portal}\n\n"
    out += "\n".join(f"- [ ] {q.label}" + (f" ({q.notes})" if q.notes else "") for q in reqs) + "\n"
    return out


def admissions_template(s_name: str, s_id: str, reqs: List[RequirementStatus], today: date) -> str:
    out = _draft_header(s_id, "admissions", "Offers and supervisor letters", today)
    out += f"# {s_name}: offers, nominations and supervisor letters\n\nSave the letters you receive in this folder.\n\n"
    out += "\n".join(f"- [ ] {q.label}" + (f" ({q.notes})" if q.notes else "") for q in reqs) + "\n"
    if any(q.doc == "supervisor_acceptance" for q in reqs):
        out += ("\n## Supervisor outreach\n\nDraft emails with `cli.py email-professor --name ... --university ... "
                "--field ... --workspace <this workspace>` and log replies here.\n\n| Professor | University | Sent | Reply |\n|---|---|---|---|\n")
    return out


def submitted_readme(s_name: str, s_id: str, today: date) -> str:
    out = _draft_header(s_id, "submission", "Submission records", today)
    return out + f"# {s_name}: submission records\n\nSave the final PDFs you uploaded and the confirmation email/screenshot here.\n"


def program_letter_template(s_name: str, s_id: str, program: Program, profile: CandidateProfile, today: date) -> str:
    tpl = _load_templates()
    out = _draft_header(s_id, "motivation_letter", f"Motivation letter: {program.acronym}", today, program=program.id)
    unis = "; ".join(f"{u.university} ({u.country})" for u in program.universities) or ", ".join(program.host_countries)
    out += f"""# {program.acronym} motivation letter ({s_name})

**Program:** {program.name}
**Universities / mobility path:** {unis}
**Website:** {program.website}
**English requirement:** {program.english_requirement or 'see website'}
**Background they want:** {program.eligible_backgrounds or 'see website'}

Each consortium reads its own letter: name its universities, its mobility path and 1-2 courses or labs you want.

## Structure
"""
    for sec in tpl["statement_of_purpose"]["structure"]:
        out += f"- **{sec['section']}:** {sec['description']}\n"
    out += f"""
## Facts to use (from your profile)

- Degree: {profile.current_degree}{', ' + profile.university if profile.university else ''}
- Career goal: {profile.career_goal or 'TODO'}
- Problem at home: {profile.home_country_problem or 'TODO'}

## Draft

TODO: write here.
"""
    return out
