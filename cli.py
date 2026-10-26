#!/usr/bin/env python3
"""
Global Scholarship Navigator & Application Planner CLI.
An interactive terminal interface powered by Rich for scholarship discovery, eligibility and fit scoring,
document gap analysis, dated action plans, and per-candidate workspaces (output/<candidate>/).
"""

import sys
import json
import argparse
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt
from rich import box

from planner.models import CandidateProfile, ApplicationState, APPLICATION_STATUSES, DocumentRecord, STUDY_LOCATION_LABEL, FUNDING_LABEL
from planner.matcher import load_scholarships, match_profile_all, location_label
from planner.documents import DocumentInventory, inventory_from_dicts, derive_inventory, load_catalog
from planner.roadmap import select_shortlist, build_action_plan
from planner.xlsx_generator import generate_application_workbook
from planner.calendar_exporter import export_calendar_ics
from planner.essay_coach import review_scholarship_essay, EssayType
from planner.outreach_generator import generate_supervisor_email
from planner.financial_calculator import calculate_financial_gap
from planner.html_generator import generate_html_report
from planner.portfolio_strategist import analyze_application_portfolio
from planner.lor_generator import generate_recommendation_letter, generate_recommender_brag_sheet, LORPerspective
from planner.credential_guide import get_credential_guide_for_country, load_credential_guides
from planner.interview_prep import get_interview_prep
from planner.fee_waivers import load_fee_waiver_data, generate_fee_waiver_email
from planner.relocation_guide import get_relocation_guide
from planner import workspace as wsp
from planner import api
from planner.programs import rank_programs, load_programs

console = Console()
DEFAULT_PROFILE = Path("sample_candidate.json") if Path("sample_candidate.json").exists() \
    else Path(__file__).parent / "examples" / "sample_candidate_full.json"
STATUS_COLOR = {"Eligible": "green", "Needs Check": "yellow", "Ineligible": "red"}
TIMELINE_COLOR = {"Ready": "green", "On track": "green", "Tight": "yellow", "At risk": "dark_orange",
                  "Not feasible this cycle": "red", "Deadline passed": "dim", "Deadline unknown": "dim"}


def print_banner():
    banner_text = (
        "[bold cyan]GLOBAL SCHOLARSHIP NAVIGATOR & APPLICATION PLANNER[/bold cyan]\n"
        "[dim]Eligibility & fit scoring • Missing papers • Dated action plan • Candidate workspace • Excel & HTML reports[/dim]"
    )
    console.print(Panel(banner_text, style="blue", box=box.ROUNDED))


# ---------------------------------------------------------------------------
# Context loading: --workspace (preferred) or --profile JSON
# ---------------------------------------------------------------------------

def _fail(msg: str):
    console.print(f"[bold red]{msg}[/bold red]")
    sys.exit(1)


def _json(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def resolve_workspace(args, required: bool = True) -> Optional[Path]:
    ws = wsp.find_workspace(getattr(args, "workspace", None))
    if ws is None and required:
        hint = f" '{args.workspace}'" if getattr(args, "workspace", None) else ""
        _fail(f"No workspace found{hint}. Create one with: cli.py init --profile <profile.json>")
    return ws


def load_context(args) -> Tuple[CandidateProfile, DocumentInventory, Dict[str, ApplicationState], Optional[Path]]:
    """Profile, papers and per-application state from --workspace, else from --profile (or the default sample)."""
    explicit_profile = getattr(args, "profile", None)
    ws = None if explicit_profile else wsp.find_workspace(getattr(args, "workspace", None))
    if getattr(args, "workspace", None) and ws is None:
        _fail(f"Workspace '{args.workspace}' not found.")
    location = getattr(args, "location", None)
    if ws:
        profile = wsp.load_profile(ws)
        if location:
            profile = profile.model_copy(update={"study_location": location})
        return profile, derive_inventory(profile, wsp.load_inventory(ws)), wsp.load_states(ws), ws
    path = Path(explicit_profile) if explicit_profile else DEFAULT_PROFILE
    if not path.exists():
        _fail(f"Profile file '{path}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if location:
        data["study_location"] = location
    profile = CandidateProfile(**data)
    inv = derive_inventory(profile, inventory_from_dicts(data["documents"]) if data.get("documents") else None)
    return profile, inv, {}, None


def load_profile_only(args) -> CandidateProfile:
    return load_context(args)[0]


def _matches(args):
    profile, inv, states, ws = load_context(args)
    matches = match_profile_all(profile, inventory=inv, states=states)
    return profile, inv, states, ws, matches


def _deadline_text(m) -> str:
    r = m.readiness
    if not r or not r.deadline:
        return "Unknown"
    return r.deadline.isoformat() + (" (est.)" if r.deadline_is_estimate else "")


def _summary_table(matches, title: str, limit: Optional[int] = None) -> Table:
    t = Table(title=title, box=box.ROUNDED)
    for name, style in (("#", "bold yellow"), ("Scholarship", "bold cyan"), ("Where", ""), ("Eligibility", ""), ("Fit", "bold"),
                        ("Ready", "bold"), ("Deadline", "yellow"), ("Days", ""), ("Timeline", "")):
        t.add_column(name, style=style)
    for i, m in enumerate(matches[:limit] if limit else matches, 1):
        r = m.readiness
        c = STATUS_COLOR[m.eligibility_status]
        tl = r.timeline_status if r else "-"
        t.add_row(str(i), m.scholarship.name, location_label(m.study_at_home, m.study_abroad),
                  f"[{c}]{m.eligibility_status}[/{c}]", f"{m.fit_score:.0f}",
                  f"{m.readiness_percent:.0f}%", _deadline_text(m),
                  str(r.days_left) if r and r.days_left is not None else "-",
                  f"[{TIMELINE_COLOR.get(tl, '')}]{tl}[/{TIMELINE_COLOR.get(tl, '')}]" if TIMELINE_COLOR.get(tl) else tl)
    return t


def _build_and_report(ws: Path, shortlist_size: int = 8, as_json: bool = False):
    res = wsp.build_workspace(ws, shortlist_size=shortlist_size)
    if as_json:
        _json(api._summary(res))
        return res
    console.print(_summary_table(res["shortlist"], f"[bold green]Shortlist for {res['profile'].full_name}[/bold green]"))
    if not res["shortlist"] and res["profile"].study_location == "home":
        console.print(f"[yellow]No open award in the database funds study in {res['profile'].residence} for you yet. "
                      "Add a local one with `cli.py new-scholarship <id>`, or run `cli.py location both`.[/yellow]")
    urgent = [a for a in res["actions"] if a["bucket"] == "Start now"][:8]
    if urgent:
        console.print("[bold yellow]Start now:[/bold yellow]")
        for a in urgent:
            console.print(f"  • {a['title']}" + (f" [dim](due {a['due_by'].isoformat()})[/dim]" if a["due_by"] else ""))
    console.print(f"\n[bold green]Workspace ready:[/bold green] [underline]{ws.resolve()}[/underline]")
    console.print("[dim]Open INDEX.md first. Reports: reports/scholarship_tracker.xlsx, reports/scholarship_report.html, reports/deadlines.ics[/dim]")
    return res


# ---------------------------------------------------------------------------
# Workspace commands
# ---------------------------------------------------------------------------

def cmd_init(args):
    path = Path(args.profile)
    if not path.exists():
        _fail(f"Profile file '{path}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ws = wsp.create_workspace(data, root=Path(args.out), name=args.name, overwrite_profile=args.overwrite)
    _build_and_report(ws, args.shortlist, args.json)


def cmd_build(args):
    ws = resolve_workspace(args)
    _build_and_report(ws, args.shortlist, args.json)


def cmd_docs(args):
    ws = resolve_workspace(args)
    if args.action == "list":
        inv = derive_inventory(wsp.load_profile(ws), wsp.load_inventory(ws))
        catalog = load_catalog()
        if args.json:
            _json({d: {**r.model_dump(mode="json", exclude={"doc_id"}), "expires_effective": inv.effective_expiry(d)}
                   for d, r in inv.records.items()})
            return
        t = Table(title="[bold yellow]Your papers (profile/documents.json)[/bold yellow]", box=box.ROUNDED)
        for c in ("Id", "Paper", "Status", "Count", "Expires", "Files"):
            t.add_column(c)
        for doc_id, rec in sorted(inv.records.items()):
            exp = inv.effective_expiry(doc_id)
            color = {"have": "green", "in_progress": "yellow", "missing": "red"}.get(rec.status, "dim")
            t.add_row(doc_id, catalog[doc_id].name if doc_id in catalog else doc_id, f"[{color}]{rec.status}[/{color}]",
                      str(rec.count_ready or ""), exp.isoformat() if exp else "", ", ".join(rec.files))
        console.print(t)
        console.print("[dim]All paper ids: data/document_catalog.json · update: cli.py docs set <id> --status have --file <path>[/dim]")
        return
    if not args.doc_id:
        _fail("Usage: cli.py docs set <doc_id> [--scholarship <id>] --status have ...")
    if args.doc_id not in load_catalog():
        _fail(f"Unknown paper id '{args.doc_id}'. See data/document_catalog.json.")
    rec = wsp.set_document(ws, args.doc_id, scholarship_id=args.scholarship, status=args.status, file=args.file,
                           issued=args.issued, expires=args.expires, count=args.count, translated=args.translated,
                           certified=args.certified, apostilled=args.apostilled, details=args.details, notes=args.notes)
    where = f"scholarships/{args.scholarship}/status.json" if args.scholarship else "profile/documents.json"
    console.print(f"[green]Updated {args.doc_id} → {rec.status}[/green] in {where}")
    if not args.no_build:
        _build_and_report(ws)


def cmd_gaps(args):
    profile, inv, states, ws, matches = _matches(args)
    if args.scholarship:
        chosen = [m for m in matches if m.scholarship.id == args.scholarship]
        if not chosen:
            _fail(f"Unknown scholarship id '{args.scholarship}'.")
    else:
        chosen = select_shortlist(matches, size=args.limit, include_ids=states.keys())
    if args.json:
        _json([{k: v for k, v in api.match_to_dict(m).items()
                if k in ("id", "name", "readiness_percent", "deadline", "timeline", "missing_papers")} for m in chosen])
        return
    for m in chosen:
        r = m.readiness
        t = Table(title=f"[bold cyan]{m.scholarship.name}[/bold cyan] · ready {m.readiness_percent:.0f}% · deadline {_deadline_text(m)}",
                  box=box.SIMPLE_HEAVY)
        for c in ("Paper (as the program words it)", "Status", "Start by", "Takes", "Issues / how to get it"):
            t.add_column(c, overflow="fold")
        for q in r.requirements:
            if q.units >= 1.0 and not q.issues:
                continue
            color = {"have": "green", "partial": "yellow", "in_progress": "yellow", "expiring": "yellow"}.get(q.state, "red")
            flags = (" (optional)" if q.optional else "") + (" (after submission)" if q.stage == "later" else "")
            t.add_row(q.label + flags, f"[{color}]{q.state}[/{color}]" + (f" {q.count_ready}/{q.count}" if q.count > 1 else ""),
                      q.start_by.isoformat() if q.start_by and q.units < 1 else "",
                      f"{q.lead_time_days[0]}-{q.lead_time_days[-1]}d", "; ".join(q.issues) or q.how_to_obtain)
        console.print(t if t.row_count else f"[green]{m.scholarship.name}: every paper is ready.[/green]")


def cmd_deadline(args):
    ws = resolve_workspace(args)
    date.fromisoformat(args.date)
    wsp.set_deadline(ws, args.scholarship, args.date, args.source)
    console.print(f"[green]Deadline for {args.scholarship} confirmed as {args.date}.[/green]")
    _build_and_report(ws)


def cmd_status(args):
    ws = resolve_workspace(args)
    if args.set not in APPLICATION_STATUSES:
        _fail(f"Status must be one of: {', '.join(APPLICATION_STATUSES)}")
    wsp.set_application_status(ws, args.scholarship, args.set, args.notes)
    console.print(f"[green]{args.scholarship} → {args.set}[/green]")
    _build_and_report(ws)


def cmd_sync(args):
    ws = resolve_workspace(args)
    counts = wsp.apply_workbook_edits(ws)
    console.print(f"[green]Imported from Excel:[/green] {counts['documents']} paper(s), "
                  f"{counts['scholarship_documents']} per-application paper(s), {counts['application_status']} status change(s).")
    _build_and_report(ws)


def cmd_location(args):
    ws = resolve_workspace(args)
    wsp.set_study_location(ws, args.where)
    console.print(f"[green]Where to study → {STUDY_LOCATION_LABEL[args.where]}[/green] (saved in profile/profile.json)")
    _build_and_report(ws)


# ---------------------------------------------------------------------------
# Matching & reports
# ---------------------------------------------------------------------------

def cmd_list(args):
    try:
        rows = api.list_scholarships(args.degree, args.country, args.funding, args.nationality, args.location)
    except ValueError as e:
        _fail(str(e))
    if args.json:
        _json(rows)
        return
    title = "[bold yellow]Scholarships in the database[/bold yellow]"
    if args.nationality:
        title += f" [dim](open to {args.nationality} citizens" + (f", study {args.location}" if args.location else "") + ")[/dim]"
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    for name, style in (("Scholarship Name", "bold cyan"), ("Where you study", "green"), ("Degrees", "magenta"),
                        ("Funding", "bold"), ("Typical Deadline", "yellow"), ("Status", ""), ("Official Portal", "dim")):
        table.add_column(name, style=style, no_wrap=False)
    for r in rows:
        where = r["where_you_study"] + (f" · {r['study_location']}" if args.nationality else "")
        table.add_row(r["name"] + (" [magenta](women)[/magenta]" if r["women_only"] else ""), where, ", ".join(r["degrees"]),
                      FUNDING_LABEL[r["funding"]], r["typical_deadline"], r["program_status"], r["portal"])
    console.print(table)
    console.print(f"[dim]Total shown: {table.row_count} scholarships[/dim]")


def cmd_match(args):
    profile, inv, states, ws, matches = _matches(args)
    shown = matches if args.all else [m for m in matches if m.is_eligible]
    if args.json:
        _json([api.match_to_dict(m) for m in shown[:args.limit]])
        return
    console.print(_summary_table(shown, f"[bold green]Matches for {profile.full_name}[/bold green] "
                                        f"[dim]({STUDY_LOCATION_LABEL[profile.study_location]})[/dim]", args.limit))
    for m in shown[:args.details]:
        r = m.readiness
        gates = "\n".join(f"  {'✅' if g.result == 'pass' else ('❌' if g.result == 'fail' else ('❓' if g.result == 'unknown' else '⚠️'))} "
                          f"{g.name}: {g.detail}" + (f" [dim]→ {g.fix}[/dim]" if g.fix else "") for g in m.gate_checks)
        parts = "\n".join(f"  {c.name:<22} {c.points:>5g} / {c.weight:<3g} {c.detail}" for c in m.score_breakdown)
        missing = "\n".join(("  ✗ " if q.state == "missing" else "  ◐ ") + q.name
                            + (f" [{q.state.replace('_', ' ')}]" if q.state != "missing" else "")
                            + (f" ({q.count_ready}/{q.count})" if q.count > 1 else "")
                            + (f" — start by {q.start_by.isoformat()}" if q.start_by else "") for q in (r.missing if r else []))
        c = STATUS_COLOR[m.eligibility_status]
        console.print(Panel(
            f"[bold cyan]{m.scholarship.name}[/bold cyan] ({m.scholarship.country})\n"
            f"[{c}]{m.eligibility_status}[/{c}] · fit [bold]{m.fit_score:.0f}/100[/bold] ({m.match_status}) · "
            f"ready [bold]{m.readiness_percent:.0f}%[/bold] · deadline {_deadline_text(m)} · {r.timeline_status if r else ''}\n\n"
            f"[bold]Eligibility checks[/bold]\n{gates}\n\n[bold]Fit breakdown[/bold]\n{parts}\n"
            + (f"\n[bold red]Missing papers[/bold red]\n{missing}\n" if missing else "")
            + f"\n[bold yellow]Strategy:[/bold yellow] {m.scholarship.strategic_tips}\n[dim]Portal: {m.scholarship.official_portal}[/dim]",
            box=box.ROUNDED,
        ))


def cmd_plan(args):
    profile, inv, states, ws, matches = _matches(args)
    shortlist = select_shortlist(matches, include_ids=states.keys())
    out_file = args.output or (str(ws / "reports" / "scholarship_tracker.xlsx") if ws else "scholarship_master_planner.xlsx")
    generate_application_workbook(profile, matches, out_file, inventory=inv, states=states, shortlist=shortlist)
    console.print(f"[bold green]Excel application tracker generated:[/bold green] [underline]{Path(out_file).resolve()}[/underline]")


def cmd_calendar(args):
    profile, inv, states, ws, matches = _matches(args)
    out_file = args.output or (str(ws / "reports" / "deadlines.ics") if ws else "application_deadlines.ics")
    export_calendar_ics(profile, matches, out_file, shortlist=select_shortlist(matches, include_ids=states.keys()))
    console.print(f"[bold green]iCalendar (.ics) export generated:[/bold green] [underline]{Path(out_file).resolve()}[/underline]")
    console.print("[dim]Import this file into Google Calendar, Apple Calendar, or Outlook to sync all alarms.[/dim]")


def cmd_html_report(args):
    profile, inv, states, ws, matches = _matches(args)
    out_file = args.output or (str(ws / "reports" / "scholarship_report.html") if ws else "scholarship_report.html")
    generate_html_report(profile, matches, out_file, shortlist=select_shortlist(matches, include_ids=states.keys()))
    console.print(f"[bold green]Interactive HTML report generated:[/bold green] [underline]{Path(out_file).resolve()}[/underline]")


def cmd_init_folders(args):
    profile, inv, states, ws, _ = _matches(args)
    data = profile.model_dump(mode="json")
    data["documents"] = [r.model_dump(mode="json") for r in inv.records.values()]
    dest = Path(args.dest) if args.dest else wsp.DEFAULT_ROOT / (profile.full_name.replace(" ", "-").lower())
    ws = wsp.create_workspace(data, root=dest.parent, name=dest.name)
    _build_and_report(ws)


def cmd_portfolio(args):
    profile, inv, states, ws, matches = _matches(args)
    res = analyze_application_portfolio(profile, matches)
    console.print(f"\n[bold cyan]Application Portfolio ({res['candidate']}):[/bold cyan]\n")
    for key, title, color in (("reach_opportunities", "Tier 1: Reach / Dream", "red"),
                              ("target_opportunities", "Tier 2: Target", "yellow"),
                              ("safety_opportunities", "Tier 3: Safety", "green")):
        t = Table(title=f"[bold {color}]{title}[/bold {color}]", box=box.ROUNDED)
        for c in ("Scholarship", "Country", "Fit", "Ready", "Deadline"):
            t.add_column(c)
        for r in res[key][:5]:
            t.add_row(r["name"], r["country"], f"{r['match_score']:.0f}", f"{r['readiness']:.0f}%", r["deadline"] or "-")
        console.print(t)
    console.print(Panel(
        f"[bold]Chance of at least one win (rough estimate):[/bold] [bold green]{res['estimated_overall_success_probability']}[/bold green]\n"
        f"[dim]{res['probability_note']}[/dim]\n[bold]Balance:[/bold] {res['portfolio_health']}\n\n"
        "[bold yellow]Advice:[/bold yellow]\n" + "\n".join(f"  • {rec}" for rec in res["strategic_recommendations"]),
        title="Portfolio Risk Assessment", box=box.ROUNDED,
    ))


# ---------------------------------------------------------------------------
# Writing helpers & guides (unchanged behaviour, now workspace-aware)
# ---------------------------------------------------------------------------

def cmd_draft_lor(args):
    profile = load_profile_only(args)
    perspective: LORPerspective = args.perspective
    lor_res = generate_recommendation_letter(
        profile=profile, recommender_name=args.name, recommender_title=args.title, institution_or_company=args.org,
        perspective=perspective, relationship_years=args.years,
        scholarship_target=args.scholarship or "International Postgraduate Scholarship",
    )
    console.print(Panel(
        f"[bold]Subject:[/bold] {lor_res['subject']}\n[bold]Perspective:[/bold] {lor_res['perspective']}\n\n"
        f"[bold cyan]Drafted Recommendation Letter:[/bold cyan]\n\n{lor_res['body']}\n\n"
        f"[bold yellow]Referee Instructions:[/bold yellow] {lor_res['advice']}",
        title="Tailored Recommendation Letter (Draft for Referee)", box=box.ROUNDED,
    ))
    if args.brag_sheet:
        brag = generate_recommender_brag_sheet(profile, [args.scholarship or "Postgraduate Scholarships"])
        console.print(Panel(brag, title="1-Page Recommender Brag Sheet", box=box.ROUNDED))


def cmd_credentials(args):
    if args.country:
        guide = get_credential_guide_for_country(args.country)
        console.print(Panel(
            f"[bold cyan]Country / Jurisdiction:[/bold cyan] {guide['country']}\n"
            f"[bold]Evaluation System:[/bold] {guide['evaluation_system']}\n"
            f"[bold]Estimated Cost:[/bold] {guide['estimated_cost']}\n"
            f"[bold]Processing Time:[/bold] {guide['processing_time']}\n"
            f"[bold]Official Portal:[/bold] [underline]{guide['portal_url']}[/underline]\n\n"
            f"[bold yellow]Mandatory Steps:[/bold yellow]\n" + "\n".join(f"  {idx}. {step}" for idx, step in enumerate(guide['mandatory_steps'], 1)) + "\n\n"
            f"[bold green]Pro-Tip:[/bold green] {guide['pro_tip']}",
            title=f"Credential Evaluation & Legalization Guide ({guide['country']})", box=box.ROUNDED,
        ))
    else:
        guides = load_credential_guides()
        table = Table(title="[bold yellow]Credential Evaluation & Legalization Systems[/bold yellow]", box=box.ROUNDED)
        for name, style, width in (("Country", "bold cyan", 18), ("System", "bold", 26), ("Estimated Cost", "green", 18),
                                   ("Processing Time", "yellow", 16), ("Portal", "dim", 25)):
            table.add_column(name, style=style, width=width)
        for g in guides:
            table.add_row(g["country"], g["evaluation_system"], g["estimated_cost"], g["processing_time"], g["portal_url"])
        console.print(table)


def cmd_interview(args):
    prep = get_interview_prep(args.scholarship)
    console.print(Panel(f"[bold cyan]Scholarship:[/bold cyan] {args.scholarship.title()}\n[bold]Panel Structure:[/bold] {prep['panel_format']}",
                        title=prep["title"], box=box.ROUNDED))
    for idx, q in enumerate(prep["questions"], 1):
        console.print(Panel(f"[bold yellow]Question {idx} ({q['category']}):[/bold yellow]\n\"{q['question']}\"\n\n"
                            f"[bold green]Strategic Answer Strategy (STAR / Diplomatic):[/bold green]\n{q['strategy']}", box=box.ROUNDED))
    console.print(Panel("\n".join(f"  • \"{q}\"" for q in prep["winning_questions_to_ask_panel"]),
                        title="[bold cyan]Winning Questions to Ask the Selection Panel at the End[/bold cyan]", box=box.ROUNDED))


def cmd_fee_waivers(args):
    data = load_fee_waiver_data()
    console.print("\n[bold cyan]Application Fee Waivers & Zero-Cost Pathways:[/bold cyan]\n")
    for cat in data:
        console.print(f"[bold yellow]{cat['category']}[/bold yellow]")
        for item in cat.get("regions") or cat.get("options", []):
            console.print(f"  • [bold]{item.get('system') or item.get('name')}[/bold]: {item.get('details') or item.get('description')}")
        console.print("")
    if args.email:
        profile = load_profile_only(args)
        email_res = generate_fee_waiver_email(profile=profile, university_name=args.university or "Target University",
                                              program_name=args.program or "Master of Science",
                                              department_chair_or_admissions="Admissions Committee")
        console.print(Panel(f"[bold]Subject:[/bold] {email_res['subject']}\n\n{email_res['body']}\n\n[dim]{email_res['advice']}[/dim]",
                            title="Application Fee Waiver Request Email Draft", box=box.ROUNDED))


def cmd_visa_guide(args):
    guide = get_relocation_guide(args.country)
    console.print(Panel(
        f"[bold cyan]Country:[/bold cyan] {guide['country']}\n[bold]Visa Name:[/bold] {guide['visa_name']}\n"
        f"[bold]Appointment System:[/bold] {guide['embassy_system']}\n\n"
        f"[bold yellow]Mandatory Visa Dossier Documents:[/bold yellow]\n" + "\n".join(f"  • {d}" for d in guide['visa_documents']) + "\n\n"
        f"[bold green]Verified Student Housing Platforms:[/bold green]\n" + "\n".join(f"  🏠 {h}" for h in guide['housing_platforms']) + "\n\n"
        f"[bold magenta]Arrival Week Protocol (Days 1 - 30):[/bold magenta]\n" + "\n".join(f"  ✓ {a}" for a in guide['arrival_checklist']),
        title=f"Post-Award Visa, Housing & Arrival Navigator ({guide['country']})", box=box.ROUNDED,
    ))


def cmd_countries(args):
    with open(Path(__file__).parent / "data" / "countries.json", "r", encoding="utf-8") as f:
        countries = json.load(f)
    table = Table(title="[bold yellow]Country Study & Work Guides[/bold yellow]", box=box.ROUNDED)
    for name, style, width in (("Country", "bold white", 18), ("Living Cost / Yr", "green", 18),
                               ("Tuition Policy", "dim", 30), ("Part-Time Work", "yellow", 22), ("Post-Study Visa", "magenta", 24)):
        table.add_column(name, style=style, width=width)
    for c in countries:
        tuition = c.get("tuition_policy", "")
        table.add_row(f"{c.get('flag', '')} {c.get('name', '')}", c.get("average_living_cost_per_year", ""),
                      tuition[:75] + ("..." if len(tuition) > 75 else ""), c.get("part_time_work_rights", "")[:50] + "...",
                      c.get("post_study_work_visa", "")[:50] + "...")
    console.print(table)


def cmd_review_essay(args):
    essay_path = Path(args.file)
    if not essay_path.exists():
        _fail(f"Essay file '{args.file}' not found.")
    essay_text = essay_path.read_text(encoding="utf-8")
    if essay_text.startswith("---"):
        parts = essay_text.split("---", 2)
        essay_text = parts[2] if len(parts) == 3 else essay_text
    if "## Draft" in essay_text:
        essay_text = essay_text.split("## Draft", 1)[1]
    essay_type: EssayType = args.type
    res = review_scholarship_essay(essay_text, essay_type=essay_type)
    color = "green" if res["readiness_score"] >= 80 else ("yellow" if res["readiness_score"] >= 65 else "red")
    console.print(Panel(
        f"[bold cyan]Essay Type:[/bold cyan] {res['essay_type']}\n[bold]Word Count:[/bold] {res['word_count']} words\n"
        f"[bold]Readiness Score:[/bold] [{color}]{res['readiness_score']} / 100 ({res['readiness_level']})[/{color}]\n\n"
        f"[bold green]Key Strengths:[/bold green]\n" + "\n".join(f"  ✓ {s}" for s in res['strengths']) + "\n\n"
        + (f"[bold red]Flags & Critical Gaps:[/bold red]\n" + "\n".join(f"  ⚠ {g}" for g in res['gaps_and_flags']) + "\n\n" if res['gaps_and_flags'] else "")
        + f"[bold yellow]Actionable Improvement Steps:[/bold yellow]\n" + "\n".join(f"  • {s}" for s in res['actionable_suggestions']),
        title="Admissions Essay Review & STAR Audit", box=box.ROUNDED,
    ))


def cmd_email_professor(args):
    profile = load_profile_only(args)
    email_data = generate_supervisor_email(profile=profile, professor_name=args.name, university_name=args.university,
                                           laboratory_or_field=args.field, relevant_paper_or_topic=args.paper,
                                           scholarship_target=args.scholarship or "Government / Full International Fellowship")
    console.print(Panel(
        f"[bold]Recipient:[/bold] {email_data['recipient']}\n[bold]Subject Line:[/bold] [yellow]{email_data['subject']}[/yellow]\n\n"
        f"[bold cyan]Email Body:[/bold cyan]\n\n{email_data['body']}\n\n[dim]Attachments to include: {email_data['attachments_checklist']}[/dim]",
        title="Customized Supervisor Cold Outreach Email", box=box.ROUNDED,
    ))


def cmd_finance(args):
    gap = calculate_financial_gap(country=args.country, scholarship_covers_tuition=not args.self_tuition,
                                  monthly_stipend_received=args.stipend, stipend_duration_months=args.months,
                                  scholarship_covers_flights=args.flights, scholarship_covers_insurance=args.insurance,
                                  is_private_university=args.private)
    color = "green" if gap["is_fully_funded"] else "yellow"
    cur = gap["currency"]
    console.print(Panel(
        f"[bold cyan]Country Target:[/bold cyan] {gap['country']} ({cur})\n"
        f"[bold]Estimated Gross Annual Cost:[/bold] {cur} {gap['estimated_gross_annual_cost']:,.2f}\n"
        f"[bold]Scholarship Living Stipend Inflow:[/bold] {cur} {gap['scholarship_funding_inflow']:,.2f}\n"
        f"[bold]Net Out-of-Pocket Deficit:[/bold] [{color}]{cur} {gap['net_out_of_pocket_deficit']:,.2f}[/{color}]\n\n"
        f"[bold]Cost Breakdown:[/bold]\n"
        f"  • Tuition Out-of-Pocket: {cur} {gap['breakdown']['tuition_out_of_pocket']:,.2f}\n"
        f"  • Annual Living Costs: {cur} {gap['breakdown']['living_expenses_annual']:,.2f}\n"
        f"  • Health Insurance: {cur} {gap['breakdown']['health_insurance']:,.2f}\n"
        f"  • Flights: {cur} {gap['breakdown']['travel_flights']:,.2f}\n\n"
        f"[bold yellow]Legal Visa Compliance Requirement:[/bold yellow]\n"
        f"  • Mechanism: {gap['visa_compliance']['mechanism']}\n"
        f"  • Mandatory Legal Threshold: {cur} {gap['visa_compliance']['legal_proof_threshold']:,.2f}\n"
        f"  • Remaining Amount to Freeze / Prove: [bold red]{cur} {gap['visa_compliance']['remaining_amount_to_freeze_in_bank']:,.2f}[/bold red]",
        title=f"Cost of Attendance & Visa Financial Gap ({gap['country']})", box=box.ROUNDED,
    ))


def cmd_scrape(args):
    engine_name = getattr(args, "engine", "default")
    console.print(f"[cyan]Scraping scholarship page using engine: [bold]{engine_name}[/bold] ({args.url})...[/cyan]")
    try:
        if engine_name == "scrapling":
            from scraper.scrapling_fetcher import extract_scholarship_with_scrapling
            data = extract_scholarship_with_scrapling(args.url)
            console.print(Panel(
                f"[bold green]Title:[/bold green] {data['title']}\n[bold cyan]Headings:[/bold cyan] {', '.join(data['headings'][:5])}\n\n"
                f"[bold yellow]Deadline Snippets:[/bold yellow]\n" + "\n".join(f"  • {s}" for s in data['deadline_snippets']) + "\n\n"
                f"[bold]Eligibility Snippets:[/bold]\n" + "\n".join(f"  • {s}" for s in data['eligibility_snippets']),
                title="Extracted Page Data (via Scrapling)", box=box.ROUNDED))
        elif engine_name == "crawlee":
            from scraper.crawlee_crawler import run_crawlee_sync
            for res in run_crawlee_sync([args.url], max_requests=2):
                console.print(Panel(
                    f"[bold green]Title:[/bold green] {res['title']}\n[bold cyan]Headings:[/bold cyan] {', '.join(res['headings'])}\n"
                    f"[bold]Found Funding Links:[/bold] {res['found_links_count']}\n"
                    + "\n".join(f"  • {link['title']}: {link['href']}" for link in res['sample_links']),
                    title=f"Crawlee Results: {res['url']}", box=box.ROUNDED))
        elif engine_name == "crawl4ai":
            from scraper.crawl4ai_crawler import run_crawl4ai_sync
            data = run_crawl4ai_sync(args.url)
            console.print(Panel(
                f"[bold green]Success:[/bold green] {data['success']} (HTTP {data['status_code']})\n[bold cyan]Title:[/bold cyan] {data['title']}\n"
                f"[bold]Markdown Length:[/bold] {data['markdown_length']} chars\n\n[bold yellow]Markdown Preview:[/bold yellow]\n{data['markdown_snippet']}...",
                title="Extracted Page Data (via Crawl4AI)", box=box.ROUNDED))
        else:
            from scraper.live_verifier import scrape_scholarship_url
            data = scrape_scholarship_url(args.url)
            console.print(Panel(
                f"[bold green]Title:[/bold green] {data['metadata']['title']}\n"
                f"[bold yellow]Detected Deadlines:[/bold yellow] {', '.join(data['detected_deadlines']) or 'None explicitly parsed'}\n\n"
                f"[bold cyan]Headings:[/bold cyan] {', '.join(data['metadata']['headings'][:5])}\n\n"
                f"[bold]Eligibility Snippets:[/bold]\n" + "\n".join(f"  • {s}" for s in data['eligibility_snippets']) + "\n\n"
                f"[bold]Document Snippets:[/bold]\n" + "\n".join(f"  • {s}" for s in data['document_snippets']),
                title="Extracted Page Data (via BeautifulSoup & HTTPX)", box=box.ROUNDED))
    except Exception as e:
        console.print(f"[bold red]Scraping failed:[/bold red] {e}")


def cmd_discover(args):
    console.print(f"[cyan]Discovering and extracting scholarship from URL: {args.url} (engine: {args.engine})...[/cyan]")
    try:
        from scraper.discoverer import discover_and_extract_from_url, save_discovered_scholarship
        data = discover_and_extract_from_url(args.url, engine=args.engine)
        saved_path = save_discovered_scholarship(data)
        console.print(Panel(
            f"[bold green]Extracted Title:[/bold green] {data.get('title') or data.get('metadata', {}).get('title')}\n"
            f"[bold]Headings Found:[/bold] {len(data.get('headings') or data.get('metadata', {}).get('headings', []))}\n"
            f"[bold]Detected Deadlines:[/bold] {data.get('detected_deadlines') or data.get('deadline_snippets')}\n\n"
            f"[bold green]Successfully saved to custom database:[/bold green] [underline]{saved_path}[/underline]",
            title="Discovery & Extraction Result", box=box.ROUNDED))
    except Exception as e:
        console.print(f"[bold red]Discovery failed:[/bold red] {e}")


def cmd_verify(args):
    from scraper.live_verifier import verify_scholarship_portals
    console.print("[cyan]Verifying official scholarship portals online status...[/cyan]\n")
    results = verify_scholarship_portals(limit=args.limit)
    table = Table(box=box.SIMPLE_HEAVY)
    for name, style in (("Scholarship", "bold cyan"), ("Status", "bold"), ("HTTP Code", "yellow"), ("Portal URL", "dim")):
        table.add_column(name, style=style)
    for r in results:
        table.add_row(r["name"], "[green]ONLINE[/green]" if r["is_online"] else "[red]OFFLINE / ERROR[/red]",
                      str(r["status_code"]) if r["status_code"] else "-", r["url"])
    console.print(table)



# ---------------------------------------------------------------------------
# Programs (Erasmus Mundus masters, Intra-Africa projects)
# ---------------------------------------------------------------------------

def cmd_programs(args):
    countries = [c.strip() for c in (args.country or "").split(",") if c.strip()] or None
    if args.choose or args.unchoose:
        ws = resolve_workspace(args)
        pid = args.choose or args.unchoose
        try:
            state = wsp.choose_program(ws, pid, remove=bool(args.unchoose))
        except ValueError as e:
            _fail(str(e))
        if state.scholarship_id == "erasmus-mundus" and len(state.chosen_programs) > 3:
            console.print("[yellow]Erasmus Mundus allows at most 3 applications per year: un-choose one.[/yellow]")
        console.print(f"[green]Chosen for {state.scholarship_id}:[/green] {', '.join(state.chosen_programs) or 'none'}")
        _build_and_report(ws)
        return
    has_profile = bool(args.profile or wsp.find_workspace(args.workspace) or DEFAULT_PROFILE.exists())
    if has_profile:
        profile = load_profile_only(args)
        include_closed = args.all
    else:  # no profile anywhere: list programs, scored on field only
        profile = CandidateProfile(full_name="anyone", nationality="", current_degree="", target_degree="Master",
                                   field_of_study=args.field or "", gpa=0)
        include_closed = True
    matches = rank_programs(profile, scholarship_id=args.scheme, field=args.field, countries=countries,
                            include_closed=include_closed)
    if args.json:
        _json([api.program_to_dict(pm) for pm in matches[:args.limit]])
        return
    t = Table(title=f"[bold yellow]Programs for {profile.full_name}[/bold yellow] ({len(matches)} found)", box=box.ROUNDED)
    for c in ("ID", "Program", "Score", "Field", "Where you study", "Deadline", "Status"):
        t.add_column(c, overflow="fold")
    for pm in matches[:args.limit]:
        p = pm.program
        deadline = (pm.deadline.isoformat() + (" (est.)" if pm.deadline_is_estimate else "")) if pm.deadline else "see site"
        t.add_row(p.id, f"[bold]{p.acronym}[/bold] {p.name}", f"{pm.score:.0f}", pm.field_match,
                  ", ".join(p.host_countries), deadline, p.status.replace("_", " ") + ("" if pm.eligible else " · not eligible"))
    console.print(t)
    console.print("[dim]Choose up to 3 Erasmus Mundus programs: cli.py programs --choose <id> · details: --json[/dim]")


# ---------------------------------------------------------------------------
# Data maintenance (contributors & agents)
# ---------------------------------------------------------------------------

def cmd_validate(args):
    from planner.validation import validate_data
    extra = [Path(f) for f in (args.file or [])]
    res = validate_data(stale_days=args.stale_days, extra_files=extra)
    if args.json:
        _json(res)
    else:
        for e in res["errors"]:
            console.print(f"[red]✗ {e}[/red]")
        if args.warnings:
            for w in res["warnings"]:
                console.print(f"[yellow]! {w}[/yellow]")
        console.print(f"[bold]{'OK' if res['ok'] else 'FAILED'}[/bold] · {res['counts']} · "
                      f"{len(res['errors'])} error(s), {len(res['warnings'])} warning(s)"
                      + ("" if args.warnings else " (show with --warnings)"))
    sys.exit(0 if res["ok"] else 1)


def cmd_export_schema(args):
    from planner.validation import export_schemas
    for path in export_schemas(Path(args.out)):
        console.print(f"[green]wrote[/green] {path}")


def cmd_new_scholarship(args):
    from planner.validation import scaffold_scholarship
    try:
        path = scaffold_scholarship(args.id)
    except FileExistsError as e:
        _fail(f"Already exists: {e}")
    console.print(f"[green]Scaffolded[/green] {path}\nFill every TODO from the official site, then validate with "
                  f"`cli.py validate --file {path}` and move it to data/custom/ (local) or into data/scholarships.json (pull request).")

# ---------------------------------------------------------------------------
# Interactive intake
# ---------------------------------------------------------------------------

def _ask_list(label: str) -> List[str]:
    raw = Prompt.ask(f"[bold]{label}[/bold] [dim](separate with ';', blank to skip)[/dim]", default="")
    return [x.strip() for x in raw.split(";") if x.strip()]


def cmd_assess(args):
    print_banner()
    console.print("\n[bold green]Tell me about yourself. Everything is saved to your workspace so you never have to repeat it.[/bold green]\n")
    data = {
        "full_name": Prompt.ask("[bold]Full name[/bold]", default="Prospective Scholar"),
        "nationality": Prompt.ask("[bold]Nationality (citizenship)[/bold]", default="Egypt"),
    }
    data["country_of_residence"] = Prompt.ask("[bold]Country you live in now[/bold]", default=data["nationality"])
    dob = Prompt.ask("[bold]Date of birth (YYYY-MM-DD)[/bold] [dim](for age limits, blank to skip)[/dim]", default="")
    if dob:
        data["date_of_birth"] = dob
    gender = Prompt.ask("[bold]Gender[/bold] [dim](only used for awards reserved for women or men)[/dim]",
                        choices=["female", "male", "other", "skip"], default="skip")
    if gender != "skip":
        data["gender"] = gender
    data["current_degree"] = Prompt.ask("[bold]Highest completed degree[/bold]", default="Bachelor's Degree")
    data["university"] = Prompt.ask("[bold]University[/bold]", default="") or None
    data["graduation_year"] = IntPrompt.ask("[bold]Graduation year[/bold]", default=date.today().year - 1)
    data["target_degree"] = Prompt.ask("[bold]Target degree[/bold]", choices=["Diploma", "Bachelor", "Master", "PhD", "Postdoc"], default="Master")
    data["field_of_study"] = Prompt.ask("[bold]Field of study / intended major[/bold]", default="Computer Science")
    data["gpa"] = FloatPrompt.ask("[bold]Cumulative GPA[/bold]", default=3.4)
    data["gpa_scale"] = FloatPrompt.ask("[bold]GPA scale (4.0, 5.0, 100...)[/bold]", default=4.0)
    if Confirm.ask("[bold]Have you taken an official English test?[/bold]", default=True):
        data["english_test"] = Prompt.ask("[bold]Test[/bold]", choices=["IELTS Academic", "TOEFL iBT", "Duolingo", "PTE Academic"], default="IELTS Academic")
        data["english_score"] = FloatPrompt.ask("[bold]Overall score[/bold]", default=7.0)
        when = Prompt.ask("[bold]Test date (YYYY-MM-DD)[/bold]", default="")
        if when:
            data["english_test_date"] = when
    data["work_experience_years"] = FloatPrompt.ask("[bold]Full-time work experience (years)[/bold]", default=0.0)
    data["currently_employed"] = Confirm.ask("[bold]Currently employed?[/bold]", default=data["work_experience_years"] > 0)
    data["research_publications"] = IntPrompt.ask("[bold]Publications / preprints[/bold]", default=0)
    data["leadership_examples"] = _ask_list("Leadership moments (one line each)")
    data["has_leadership_experience"] = bool(data["leadership_examples"]) or Confirm.ask("[bold]Any leadership / community experience?[/bold]", default=True)
    data["awards"] = _ask_list("Awards and honours")
    data["career_goal"] = Prompt.ask("[bold]Career goal after your studies[/bold]", default="") or None
    data["target_funding"] = Prompt.ask("[bold]Funding needed[/bold]", choices=["Full", "Partial", "Any"], default="Full")
    data["study_location"] = Prompt.ask(
        "[bold]Where do you want to study?[/bold] [dim](home = in your own country, no travel · abroad · both)[/dim]",
        choices=["both", "home", "abroad"], default="both")
    data["target_countries"] = []
    if data["study_location"] != "home":
        raw = Prompt.ask("[bold]Target countries (comma-separated, blank = worldwide)[/bold]", default="")
        data["target_countries"] = [c.strip() for c in raw.split(",") if c.strip()]
    data["target_intake_year"] = IntPrompt.ask("[bold]Target intake year[/bold]", default=date.today().year + 1)
    data["willing_to_return_home"] = Confirm.ask("[bold]OK with scholarships that require returning home for 2 years?[/bold]", default=True)

    console.print("\n[bold green]Which papers do you already have?[/bold green]")
    documents = []
    for doc_id, label in (("passport", "Valid passport"), ("degree_certificate", "Degree certificate"),
                          ("transcript", "Official transcript"), ("cv", "Up-to-date CV"),
                          ("employment_certificate", "Employment certificate"), ("police_clearance", "Police clearance")):
        documents.append({"doc_id": doc_id, "status": "have" if Confirm.ask(f"  {label}?", default=False) else "missing"})
    letters = IntPrompt.ask("  How many referees have agreed to write academic letters?", default=0)
    documents.append({"doc_id": "lor_academic", "status": "have" if letters else "missing", "count_ready": letters})
    data["documents"] = documents

    ws = wsp.create_workspace(data, root=Path(args.out), overwrite_profile=True)
    _build_and_report(ws)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _ws_arg(p):
    p.add_argument("--workspace", help="Candidate workspace folder (default: the only one under output/)")


def _profile_args(p):
    p.add_argument("--profile", help="Candidate profile JSON (alternative to --workspace)")
    _ws_arg(p)
    p.add_argument("--location", choices=["home", "abroad", "both"],
                   help="Try a study location without saving it: home (own country, no travel), abroad or both")


def main():
    parser = argparse.ArgumentParser(description="Global Scholarship Navigator & Application Planner CLI")
    sub = parser.add_subparsers(dest="subcommand", help="Available commands")

    # Workspace
    p = sub.add_parser("init", help="Create a candidate workspace (output/<name>/) from a profile JSON and build everything")
    p.add_argument("--profile", required=True, help="Profile JSON (may include a 'documents' list)")
    p.add_argument("--out", default=str(wsp.DEFAULT_ROOT), help="Parent folder for workspaces (default: output)")
    p.add_argument("--name", help="Workspace folder name (default: slug of full name)")
    p.add_argument("--overwrite", action="store_true", help="Replace an existing workspace profile.json with this file")
    p.add_argument("--shortlist", type=int, default=8, help="Number of scholarships to shortlist")
    p.add_argument("--json", action="store_true", help="Print a JSON summary instead of tables")
    p = sub.add_parser("build", help="Recompute scores, papers and plan; regenerate briefs and reports")
    _ws_arg(p)
    p.add_argument("--shortlist", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("docs", help="List or update the papers you hold")
    p.add_argument("action", choices=["list", "set"])
    p.add_argument("doc_id", nargs="?", help="Paper id from data/document_catalog.json (for 'set')")
    _ws_arg(p)
    p.add_argument("--scholarship", help="Per-application paper (essay, motivation_letter...) for this scholarship id")
    p.add_argument("--status", choices=["have", "in_progress", "missing", "not_applicable"])
    p.add_argument("--file", help="Path of the scan, relative to the workspace")
    p.add_argument("--issued", help="YYYY-MM-DD")
    p.add_argument("--expires", help="YYYY-MM-DD")
    p.add_argument("--count", type=int, help="How many are secured (recommendation letters, essays)")
    p.add_argument("--translated", help="yes/no")
    p.add_argument("--certified", help="yes/no")
    p.add_argument("--apostilled", help="yes/no")
    p.add_argument("--details")
    p.add_argument("--notes")
    p.add_argument("--no-build", action="store_true", help="Do not rebuild the workspace afterwards")
    p.add_argument("--json", action="store_true", help="JSON output (docs list)")
    p = sub.add_parser("gaps", help="Show missing papers per shortlisted scholarship")
    _profile_args(p)
    p.add_argument("--scholarship", help="Only this scholarship id")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("deadline", help="Record a verified deadline for a scholarship")
    _ws_arg(p)
    p.add_argument("--scholarship", required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--source", help="URL where you verified it")
    p = sub.add_parser("status", help="Set the application status of a scholarship")
    _ws_arg(p)
    p.add_argument("--scholarship", required=True)
    p.add_argument("--set", required=True, help=" | ".join(APPLICATION_STATUSES))
    p.add_argument("--notes")
    p = sub.add_parser("sync", help="Import edits made in reports/scholarship_tracker.xlsx and rebuild")
    _ws_arg(p)
    p = sub.add_parser("location", help="Choose where to study: home (own country, no travel), abroad, or both")
    p.add_argument("where", choices=["home", "abroad", "both"])
    _ws_arg(p)
    p = sub.add_parser("assess", help="Interactive interview that creates your workspace")
    p.add_argument("--out", default=str(wsp.DEFAULT_ROOT))

    # Programs & data maintenance
    p = sub.add_parser("programs", help="Find Erasmus Mundus masters / Intra-Africa programs; choose up to 3")
    _profile_args(p)
    p.add_argument("--field", help="Filter by field text, e.g. robotics, data, energy")
    p.add_argument("--country", help="Host countries, comma-separated, e.g. Germany,France")
    p.add_argument("--scheme", choices=["erasmus-mundus", "intra-africa-mobility"])
    p.add_argument("--all", action="store_true", help="Include closed, discontinued and ineligible programs")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--choose", metavar="PROGRAM_ID", help="Add to your chosen programs (workspace)")
    p.add_argument("--unchoose", metavar="PROGRAM_ID", help="Remove from your chosen programs")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("validate", help="Validate scholarship, program and catalog data")
    p.add_argument("--file", action="append", help="Also validate this scholarship JSON file (repeatable)")
    p.add_argument("--stale-days", type=int, default=240)
    p.add_argument("--warnings", action="store_true", help="Show warnings")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("export-schema", help="Write JSON Schemas for profiles, papers, scholarships and programs")
    p.add_argument("--out", default="schemas")
    p = sub.add_parser("new-scholarship", help="Scaffold a new scholarship record in data/custom/drafts/")
    p.add_argument("id", help="kebab-case id, e.g. heinrich-boll-foundation")

    # Matching & reports
    p = sub.add_parser("list", help="List scholarships in the database (filter by degree, host country, who can apply)")
    p.add_argument("--degree", choices=["Diploma", "Bachelor", "Master", "PhD", "Postdoc"])
    p.add_argument("--country", help="Host country text, e.g. Germany")
    p.add_argument("--funding", choices=["Full", "Partial"])
    p.add_argument("--nationality", help="Only awards open to citizens of this country, e.g. Egypt")
    p.add_argument("--location", choices=["home", "abroad", "both"],
                   help="With --nationality: study in that country (home) or outside it (abroad)")
    p.add_argument("--json", action="store_true")
    sub.add_parser("countries", help="Display country study & work guides")
    p = sub.add_parser("match", help="Eligibility, fit score breakdown and readiness for every scholarship")
    _profile_args(p)
    p.add_argument("--limit", type=int, default=20, help="Rows in the summary table")
    p.add_argument("--details", type=int, default=3, help="How many detailed panels to print")
    p.add_argument("--all", action="store_true", help="Include ineligible scholarships")
    p.add_argument("--json", action="store_true", help="Full results as JSON (for agents)")
    p = sub.add_parser("plan", help="Generate the Excel application tracker")
    _profile_args(p)
    p.add_argument("--output", help="Output .xlsx (default: workspace reports/ or scholarship_master_planner.xlsx)")
    p = sub.add_parser("calendar", help="Generate an iCalendar (.ics) file with deadline and start-by reminders")
    _profile_args(p)
    p.add_argument("--output")
    p = sub.add_parser("html-report", help="Generate the interactive single-page HTML report")
    _profile_args(p)
    p.add_argument("--output")
    p = sub.add_parser("init-folders", help="(Legacy) create a workspace from a profile; same as init")
    _profile_args(p)
    p.add_argument("--dest", help="Workspace folder path")
    p = sub.add_parser("portfolio", help="Reach / Target / Safety tiers with a rough win estimate")
    _profile_args(p)

    # Writing helpers & guides
    p = sub.add_parser("review-essay", help="Review an essay for STAR method, cliches, and metrics")
    p.add_argument("--file", required=True, help="Essay text or a workspace draft .md file")
    p.add_argument("--type", choices=["chevening_leadership", "chevening_networking", "chevening_study_uk", "chevening_career",
                                      "fulbright_personal", "fulbright_study", "sop"], default="chevening_leadership")
    p = sub.add_parser("email-professor", help="Cold outreach email to a prospective supervisor")
    p.add_argument("--name", required=True)
    p.add_argument("--university", required=True)
    p.add_argument("--field", required=True)
    p.add_argument("--paper")
    p.add_argument("--scholarship", default="Swiss Government Excellence / Full Fellowship")
    _profile_args(p)
    p = sub.add_parser("finance", help="Cost of attendance, partial scholarship deficit and blocked account")
    p.add_argument("--country", required=True)
    p.add_argument("--stipend", type=float, default=0.0)
    p.add_argument("--months", type=int, default=12)
    p.add_argument("--self-tuition", action="store_true")
    p.add_argument("--flights", action="store_true")
    p.add_argument("--insurance", action="store_true")
    p.add_argument("--private", action="store_true")
    p = sub.add_parser("draft-lor", help="Draft a recommendation letter and brag sheet for a referee")
    p.add_argument("--name", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--org", required=True)
    p.add_argument("--perspective", choices=["academic_research", "academic_teaching", "professional_leadership"], default="academic_research")
    p.add_argument("--years", type=int, default=3)
    p.add_argument("--scholarship", default="International Postgraduate Scholarship")
    p.add_argument("--brag-sheet", action="store_true")
    _profile_args(p)
    p = sub.add_parser("credentials", help="Credential evaluation and apostille guide")
    p.add_argument("--country")
    p = sub.add_parser("interview", help="Interview questions with STAR strategies")
    p.add_argument("--scholarship", default="chevening")
    p = sub.add_parser("fee-waivers", help="Application fee waivers and request email drafts")
    p.add_argument("--email", action="store_true")
    p.add_argument("--university", default="Target University")
    p.add_argument("--program", default="Master of Science")
    _profile_args(p)
    p = sub.add_parser("visa-guide", help="Post-award visa, housing and arrival checklist")
    p.add_argument("--country", default="Germany")

    # Scraping
    p = sub.add_parser("scrape", help="Scrape a live scholarship page")
    p.add_argument("--url", required=True)
    p.add_argument("--engine", choices=["default", "scrapling", "crawl4ai", "crawlee"], default="scrapling")
    p = sub.add_parser("verify", help="Check that official portals are online")
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("discover", help="Scrape and save a new scholarship from a URL")
    p.add_argument("--url", required=True)
    p.add_argument("--engine", choices=["scrapling", "crawl4ai", "crawlee", "default"], default="scrapling")

    args = parser.parse_args()
    if not args.subcommand:
        print_banner()
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "init": cmd_init, "build": cmd_build, "docs": cmd_docs, "gaps": cmd_gaps, "deadline": cmd_deadline,
        "status": cmd_status, "sync": cmd_sync, "location": cmd_location, "assess": cmd_assess, "list": cmd_list, "countries": cmd_countries,
        "match": cmd_match, "plan": cmd_plan, "calendar": cmd_calendar, "html-report": cmd_html_report,
        "init-folders": cmd_init_folders, "portfolio": cmd_portfolio, "review-essay": cmd_review_essay,
        "email-professor": cmd_email_professor, "finance": cmd_finance, "draft-lor": cmd_draft_lor,
        "credentials": cmd_credentials, "interview": cmd_interview, "fee-waivers": cmd_fee_waivers,
        "visa-guide": cmd_visa_guide, "scrape": cmd_scrape, "verify": cmd_verify, "discover": cmd_discover,
        "programs": cmd_programs, "validate": cmd_validate, "export-schema": cmd_export_schema,
        "new-scholarship": cmd_new_scholarship,
    }
    dispatch[args.subcommand](args)


if __name__ == "__main__":
    main()
