"""
Executive Excel (.xlsx) application tracker.

Sheets: How to Use · Dashboard · Ranked Matches · one detail sheet per shortlisted scholarship ·
Requirements · My Documents · Action Plan · Timeline · All Scholarships · Country Guides.

Readiness is live: editing a paper's status in *My Documents* (or a per-application paper in *Requirements*)
recalculates readiness in *Ranked Matches*, the detail sheets and the dashboard. `cli.py sync` copies those
edits back into the workspace JSON files.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import openpyxl
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from .models import APPLICATION_STATUSES, ApplicationState, CandidateProfile, MatchResult, FUNDING_LABEL
from .documents import DocumentInventory, catalog_doc, derive_inventory, load_catalog, load_categories
from .roadmap import PHASES, build_action_plan, select_shortlist
from .matcher import location_label

FONT_NAME = "Arial"
NAVY = "1F4E79"
NAVY_2 = "2F5597"
ICE = "D9E1F2"
ALT = "F8F9FA"
INPUT_YELLOW = "FFF2CC"
GREEN = "E2EFDA"
AMBER = "FFEB9C"
RED = "FCE4D6"
GREY = "EDEDED"
WHITE = "FFFFFF"

F_TITLE = Font(name=FONT_NAME, size=16, bold=True, color=WHITE)
F_H2 = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
F_TH = Font(name=FONT_NAME, size=10, bold=True, color=WHITE)
F_REG = Font(name=FONT_NAME, size=10)
F_BOLD = Font(name=FONT_NAME, size=10, bold=True)
F_LINK = Font(name=FONT_NAME, size=10, color="0563C1", underline="single")
F_XREF = Font(name=FONT_NAME, size=10, color="008000")
F_KPI = Font(name=FONT_NAME, size=18, bold=True, color=NAVY)
F_NOTE = Font(name=FONT_NAME, size=9, italic=True, color="595959")

FILL = {k: PatternFill(start_color=v, end_color=v, fill_type="solid")
        for k, v in dict(navy=NAVY, navy2=NAVY_2, ice=ICE, alt=ALT, input=INPUT_YELLOW, green=GREEN,
                         amber=AMBER, red=RED, grey=GREY, white=WHITE).items()}
THIN = Side(border_style="thin", color="D3D3D3")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

DOC_STATUSES = "have,in_progress,missing,not_applicable"
SHEET_REQ = "Requirements"
SHEET_DOCS = "My Documents"
SHEET_MATCH = "Ranked Matches"
SHEET_PLAN = "Action Plan"

# Column letters shared by the writer, the formulas and read_workbook_edits().
MATCH_COLS = ["Rank", "ID", "Scholarship", "Country", "Where you study", "Degrees", "Funding", "Eligibility", "Match", "Fit (0-100)",
              "Academic", "Language", "Experience", "Field", "Leadership", "Research", "Preferences", "Readiness",
              "Deadline", "Deadline type", "Days left", "Timeline", "Tier", "Priority", "Application status",
              "Key gaps", "Portal"]
REQ_COLS = ["Scholarship ID", "Scholarship", "Paper (as worded)", "Paper ID", "Scope", "Stage", "Optional",
            "Count needed", "Status", "Count ready", "Expires", "Deadline", "Ready units", "Start by",
            "Takes (days)", "Issues", "How to get it", "Where to file"]
DOC_COLS = ["Paper ID", "Paper", "Category", "Status", "Count ready", "Effective count", "Issued", "Expires",
            "Translated", "Certified", "Apostilled", "Files", "Details", "Needed by (# scholarships)", "How to get it"]
PLAN_COLS = ["When", "Task", "Start by", "Due by", "Days until start", "For", "Details", "Status"]
COMPONENT_KEYS = ["academic", "language", "experience", "field", "profile", "research", "preferences"]


def col(headers: Sequence[str], name: str) -> str:
    return get_column_letter(headers.index(name) + 1)


def _q(sheet: str) -> str:
    return f"'{sheet}'" if " " in sheet else sheet


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _header(ws: Worksheet, row: int, headers: Sequence[str], fill: str = "navy", height: int = 30) -> None:
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.font, c.fill, c.alignment, c.border = F_TH, FILL[fill], CENTER, BORDER
    ws.row_dimensions[row].height = height


def _cell(ws: Worksheet, row: int, column: int, value: Any, font: Font = F_REG, fill: Optional[str] = None,
          align: Alignment = WRAP, fmt: Optional[str] = None):
    c = ws.cell(row=row, column=column, value=value)
    c.font, c.alignment, c.border = font, align, BORDER
    if fill:
        c.fill = FILL[fill]
    if fmt:
        c.number_format = fmt
    return c


def _merge_header(ws: Worksheet, row: int, spans: Sequence[tuple]) -> None:
    for start, end in spans:
        ws.merge_cells(start_row=row, start_column=start, end_row=row, end_column=end)


def _print_setup(ws: Worksheet) -> None:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True


def _widths(ws: Worksheet, widths: Dict[str, float]) -> None:
    for letter, w in widths.items():
        ws.column_dimensions[letter].width = w


def _title(ws: Worksheet, text: str, span: int, subtitle: Optional[str] = None) -> int:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
    c = ws.cell(row=1, column=1, value=text)
    c.font, c.fill, c.alignment = F_TITLE, FILL["navy"], Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 30
    if subtitle:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
        s = ws.cell(row=2, column=1, value=subtitle)
        s.font, s.alignment = F_NOTE, Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
        ws.row_dimensions[2].height = 28
        return 4
    return 3


def _section(ws: Worksheet, row: int, text: str, span: int = 6) -> int:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    c = ws.cell(row=row, column=1, value=text)
    c.font = F_H2
    c.border = Border(bottom=Side(border_style="medium", color=NAVY))
    return row + 1


def _status_formatting(ws: Worksheet, rng: str, first_cell: str) -> None:
    for value, fill in (("have", "green"), ("not_applicable", "grey"), ("partial", "amber"),
                        ("in_progress", "amber"), ("missing", "red")):
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'{first_cell}="{value}"'], fill=FILL[fill]))


def _percent_scale(ws: Worksheet, rng: str) -> None:
    ws.conditional_formatting.add(rng, ColorScaleRule(start_type="num", start_value=0, start_color="F8CBAD",
                                                      mid_type="num", mid_value=0.5, mid_color="FFEB9C",
                                                      end_type="num", end_value=1, end_color="C6EFCE"))


def _sheet_name_for(index: int, name: str, used: set) -> str:
    base = f"{index:02d} {name}"
    for ch in "[]:*?/\\'":
        base = base.replace(ch, "")
    candidate = base[:31].rstrip()
    n = 2
    while candidate in used:
        candidate = f"{base[:28].rstrip()} {n}"
        n += 1
    used.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------

def _how_to_use(wb: openpyxl.Workbook, profile: CandidateProfile, today: date) -> None:
    ws = wb.active
    ws.title = "How to Use"
    ws.sheet_view.showGridLines = False
    row = _title(ws, "SCHOLARSHIP APPLICATION TRACKER", 4,
                 f"{profile.full_name} · {profile.target_degree} · intake {profile.target_intake_year} · generated {today.isoformat()}")
    row = _section(ws, row, "What the numbers mean", 4)
    for k, v in [
        ("Eligibility", "Hard rules (degree, nationality, age, work experience, field...). Eligible / Needs Check (information missing) / Ineligible."),
        ("Fit (0-100)", "How well your profile matches: academic record, language, experience, field, leadership, research, preferences. High ≥ 80, moderate ≥ 62."),
        ("Readiness", "Share of the required papers you already have (have = 1, in progress = 0.5, missing = 0; papers expiring before the deadline count 0.5). Updates live."),
        ("Timeline", "Whether the remaining papers can be ready in time, given how long each one takes to get."),
        ("Priority", "55% fit + 20% readiness + funding value + time left. Recomputed by `cli.py build`."),
        ("Deadline type", "Confirmed (you verified it) · Published (official date found) · Estimated (usual pattern: verify on the official site)."),
    ]:
        _cell(ws, row, 1, k, F_BOLD, "ice")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        _cell(ws, row, 2, v)
        ws.row_dimensions[row].height = 32
        row += 1
    row = _section(ws, row + 1, "How to update this workbook", 4)
    _cell(ws, row, 1, "Yellow cells", F_BOLD, "input")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
    _cell(ws, row, 2, "are the only cells you should edit: paper status and counts (My Documents, and per-application rows in Requirements), application status, and task status.")
    ws.row_dimensions[row].height = 32
    row += 1
    _cell(ws, row, 1, "Example", F_BOLD, "ice")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
    _cell(ws, row, 2, "Got your passport scan? In My Documents set passport → Status = have. Readiness rises in every scholarship that needs it.")
    row += 1
    _cell(ws, row, 1, "Save your edits", F_BOLD, "ice")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
    _cell(ws, row, 2, "Run `.venv/bin/python cli.py sync --workspace <folder>` to copy your edits into the workspace JSON and rebuild everything.")
    ws.row_dimensions[row].height = 30
    row += 1
    _cell(ws, row, 1, "Sheets", F_BOLD, "ice")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
    _cell(ws, row, 2, "Dashboard → Ranked Matches → one sheet per shortlisted scholarship → Requirements → My Documents → Action Plan → Timeline → Programs (Erasmus Mundus masters etc.: mark up to 3 as Chosen) → All Scholarships → Country Guides.")
    _widths(ws, {"A": 22, "B": 40, "C": 40, "D": 40})


def _ranked_matches(wb: openpyxl.Workbook, matches: List[MatchResult], states: Dict[str, ApplicationState]) -> Dict[str, int]:
    ws = wb.create_sheet(SHEET_MATCH)
    _header(ws, 1, MATCH_COLS)
    ws.freeze_panes = "D2"
    rows: Dict[str, int] = {}
    req_m, req_a, req_f, req_g = (col(REQ_COLS, n) for n in ("Ready units", "Scholarship ID", "Stage", "Optional"))
    dv = DataValidation(type="list", formula1='"' + ",".join(APPLICATION_STATUSES) + '"', allow_blank=True)
    ws.add_data_validation(dv)

    for i, m in enumerate(matches, start=2):
        s, r = m.scholarship, m.readiness
        rows[s.id] = i
        comps = {c.key: c for c in m.score_breakdown}
        fill = "alt" if i % 2 == 0 else None
        state = states.get(s.id)
        dtype = "-" if not (r and r.deadline) else ("Estimated" if r.deadline_is_estimate else
                                                    ("Confirmed" if r.deadline_label == "Confirmed by you" else "Published"))
        gaps = [g.detail for g in m.gate_checks if g.result in ("fail", "unknown")]
        gaps += [f"Missing: {q.name}" for q in (r.missing if r else [])][:4]
        values = [
            i - 1, s.id, s.name, s.country, location_label(m.study_at_home, m.study_abroad), ", ".join(s.degrees),
            FUNDING_LABEL[s.funding_type], m.eligibility_status, m.match_status,
            m.fit_score,
            *[(comps[k].points / comps[k].weight if k in comps and comps[k].weight else None) for k in COMPONENT_KEYS],
            None, r.deadline if r and r.deadline else None, dtype, None, r.timeline_status if r else "-", m.tier,
            m.priority_score, state.application_status if state else "Not Started", "\n".join(gaps), s.official_portal,
        ]
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        ws.cell(row=i, column=MATCH_COLS.index("Fit (0-100)") + 1).font = F_BOLD
        for k in COMPONENT_KEYS:
            ws.cell(row=i, column=MATCH_COLS.index(k.title() if k != "profile" else "Leadership") + 1).number_format = "0%"

        rc = ws.cell(row=i, column=MATCH_COLS.index("Readiness") + 1)
        if m.is_eligible:
            rc.value = (f'=IFERROR(AVERAGEIFS({SHEET_REQ}!${req_m}:${req_m},{SHEET_REQ}!${req_a}:${req_a},$B{i},'
                        f'{SHEET_REQ}!${req_f}:${req_f},"application",{SHEET_REQ}!${req_g}:${req_g},"no"),"")')
        else:
            rc.value = "-"
        rc.number_format = "0%"
        ws.cell(row=i, column=MATCH_COLS.index("Deadline") + 1).number_format = "yyyy-mm-dd"
        dcol = col(MATCH_COLS, "Deadline")
        ws.cell(row=i, column=MATCH_COLS.index("Days left") + 1).value = f'=IF(ISNUMBER({dcol}{i}),{dcol}{i}-TODAY(),"")'
        status_cell = ws.cell(row=i, column=MATCH_COLS.index("Application status") + 1)
        status_cell.fill = FILL["input"]
        dv.add(status_cell)
        portal = ws.cell(row=i, column=MATCH_COLS.index("Portal") + 1)
        portal.hyperlink, portal.font = s.official_portal, F_LINK
        ws.row_dimensions[i].height = 45

    last = len(matches) + 1
    elig = col(MATCH_COLS, "Eligibility")
    ws.conditional_formatting.add(f"{elig}2:{elig}{last}", FormulaRule(formula=[f'${elig}2="Eligible"'], fill=FILL["green"]))
    ws.conditional_formatting.add(f"{elig}2:{elig}{last}", FormulaRule(formula=[f'${elig}2="Needs Check"'], fill=FILL["amber"]))
    ws.conditional_formatting.add(f"{elig}2:{elig}{last}", FormulaRule(formula=[f'${elig}2="Ineligible"'], fill=FILL["red"]))
    fit = col(MATCH_COLS, "Fit (0-100)")
    ws.conditional_formatting.add(f"{fit}2:{fit}{last}", ColorScaleRule(start_type="num", start_value=40, start_color="F8CBAD",
                                                                     mid_type="num", mid_value=70, mid_color="FFEB9C",
                                                                     end_type="num", end_value=95, end_color="C6EFCE"))
    _percent_scale(ws, f"{col(MATCH_COLS, 'Academic')}2:{col(MATCH_COLS, 'Readiness')}{last}")
    days = col(MATCH_COLS, "Days left")
    ws.conditional_formatting.add(f"{days}2:{days}{last}", FormulaRule(formula=[f'AND(ISNUMBER(${days}2),${days}2<0)'], fill=FILL["grey"]))
    ws.conditional_formatting.add(f"{days}2:{days}{last}", FormulaRule(formula=[f'AND(ISNUMBER(${days}2),${days}2>=0,${days}2<45)'], fill=FILL["red"]))
    ws.auto_filter.ref = f"A1:{get_column_letter(len(MATCH_COLS))}{last}"
    named = {"Rank": 6, "ID": 20, "Scholarship": 34, "Country": 18, "Where you study": 16, "Degrees": 16, "Funding": 9,
             "Eligibility": 12, "Match": 15, "Fit (0-100)": 9, "Deadline": 12, "Deadline type": 12, "Days left": 9,
             "Timeline": 18, "Tier": 9, "Priority": 9, "Application status": 20, "Key gaps": 48, "Portal": 30}
    widths = {col(MATCH_COLS, name): w for name, w in named.items()}
    widths.update({get_column_letter(MATCH_COLS.index("Academic") + 1 + k): 11 for k in range(8)})
    _widths(ws, widths)
    return rows


def _requirements(wb: openpyxl.Workbook, matches: List[MatchResult]) -> Dict[tuple, int]:
    ws = wb.create_sheet(SHEET_REQ)
    _header(ws, 1, REQ_COLS)
    ws.freeze_panes = "D2"
    docs = _q(SHEET_DOCS)
    catalog = load_catalog()
    categories = load_categories()
    dv = DataValidation(type="list", formula1=f'"{DOC_STATUSES},partial"', allow_blank=True)
    ws.add_data_validation(dv)
    C = {n: col(REQ_COLS, n) for n in REQ_COLS}
    rows: Dict[tuple, int] = {}
    i = 2
    for m in matches:
        if not m.is_eligible or not m.readiness:
            continue
        for q in m.readiness.requirements:
            lookup = q.satisfied_via or q.doc
            cat = catalog.get(lookup) or catalog_doc(q.doc)
            folder = categories.get(cat.category, {}).get("folder", "forms")
            where = folder + "/" if cat.scope == "shared" else f"scholarships/{m.scholarship.id}/{folder}/"
            values = [m.scholarship.id, m.scholarship.name, q.label, lookup, cat.scope, q.stage, "yes" if q.optional else "no",
                      q.count, None, None, None, m.readiness.deadline, None, q.start_by if q.units < 1 else None,
                      f"{q.lead_time_days[0]}-{q.lead_time_days[-1]}", "; ".join(q.issues), q.how_to_obtain, where]
            fill = "alt" if i % 2 == 0 else None
            for j, v in enumerate(values, 1):
                _cell(ws, i, j, v, fill=fill)
            st, cnt, exp, dl, units, need = (f"{C[n]}{i}" for n in ("Status", "Count ready", "Expires", "Deadline", "Ready units", "Count needed"))
            if cat.scope == "shared":
                family = [lookup] + cat.satisfied_by
                if len(family) > 1:
                    arr = "{" + ",".join(f'"{d}"' for d in family) + "}"
                    ws[cnt] = f"=SUMPRODUCT(({docs}!$A$2:$A$300={arr})*{docs}!$F$2:$F$300)"
                    raw = f'IF(SUMPRODUCT(({docs}!$A$2:$A$300={arr})*({docs}!$D$2:$D$300="in_progress"))>0,"in_progress","missing")'
                    ws[exp] = ""
                else:
                    ws[cnt] = f"=IFERROR(VLOOKUP($D{i},{docs}!$A:$F,6,FALSE),0)"
                    raw = f'IFERROR(VLOOKUP($D{i},{docs}!$A:$D,4,FALSE),"missing")'
                    ws[exp] = f'=IFERROR(IF(VLOOKUP($D{i},{docs}!$A:$H,8,FALSE)="","",VLOOKUP($D{i},{docs}!$A:$H,8,FALSE)),"")'
                ws[st] = f'=IF({raw}="not_applicable","not_applicable",IF({cnt}>={need},"have",IF({cnt}>0,"partial",IF({raw}="in_progress","in_progress","missing"))))'
                ws[cnt].font = ws[st].font = ws[exp].font = F_XREF
                base = f'IF({st}="not_applicable",1,IF(OR({st}="have",{st}="partial"),MIN(1,MAX(1,{cnt})/{need}),IF({st}="in_progress",0.5,0)))'
                ws[units] = f"=IF(AND(ISNUMBER({exp}),ISNUMBER({dl}),{exp}<{dl}),MIN(0.5,{base}),{base})"
            else:
                ws[st] = q.state if q.state != "expiring" else "have"
                ws[cnt] = q.count_ready
                ws[st].fill = ws[cnt].fill = FILL["input"]
                dv.add(ws[st])
                ws[units] = f'=IF({st}="not_applicable",1,IF(OR({st}="have",{st}="partial"),MIN(1,MAX(1,{cnt})/{need}),IF({st}="in_progress",0.5,0)))'
            for c_ in (exp, dl, f"{C['Start by']}{i}"):
                ws[c_].number_format = "yyyy-mm-dd"
            ws[units].number_format = "0%"
            rows[(m.scholarship.id, q.doc, q.label)] = i
            i += 1
    last = max(i - 1, 2)
    _status_formatting(ws, f"{C['Status']}2:{C['Status']}{last}", f"${C['Status']}2")
    _percent_scale(ws, f"{C['Ready units']}2:{C['Ready units']}{last}")
    ws.auto_filter.ref = f"A1:{get_column_letter(len(REQ_COLS))}{last}"
    _widths(ws, {"A": 20, "B": 28, "C": 46, "D": 20, "E": 13, "F": 11, "G": 9, "H": 9, "I": 13, "J": 9, "K": 12,
                 "L": 12, "M": 10, "N": 12, "O": 10, "P": 34, "Q": 50, "R": 28})
    return rows


def _my_documents(wb: openpyxl.Workbook, inventory: DocumentInventory, matches: List[MatchResult]) -> None:
    ws = wb.create_sheet(SHEET_DOCS)
    _header(ws, 1, DOC_COLS)
    ws.freeze_panes = "C2"
    catalog = load_catalog()
    categories = load_categories()
    ids = list(inventory.records)
    for m in matches:
        if m.is_eligible and m.readiness:
            for q in m.readiness.requirements:
                cat = catalog_doc(q.satisfied_via or q.doc)
                if cat.scope != "shared":
                    continue
                for d in [q.satisfied_via or q.doc] + cat.satisfied_by:
                    if d not in ids:
                        ids.append(d)
    ids.sort(key=lambda d: (catalog_doc(d).category, d))
    dv = DataValidation(type="list", formula1=f'"{DOC_STATUSES}"', allow_blank=False)
    dv_bool = DataValidation(type="list", formula1='"yes,no"', allow_blank=True)
    ws.add_data_validation(dv)
    ws.add_data_validation(dv_bool)
    req_d = col(REQ_COLS, "Paper ID")
    yn = {True: "yes", False: "no", None: ""}
    for i, doc_id in enumerate(ids, start=2):
        rec = inventory.get(doc_id)
        cat = catalog.get(doc_id) or catalog_doc(doc_id)
        expiry = inventory.effective_expiry(doc_id)
        values = [doc_id, cat.name, categories.get(cat.category, {}).get("title", cat.category),
                  rec.status if rec else "missing", rec.count_ready if rec else 0, None,
                  rec.issued if rec else None, expiry, yn[rec.translated if rec else None],
                  yn[rec.certified if rec else None], yn[rec.apostilled if rec else None],
                  "\n".join(rec.files) if rec else "", (rec.details or "") if rec else "", None, cat.how_to_obtain]
        fill = "alt" if i % 2 == 0 else None
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        ws[f"F{i}"] = f'=IF(D{i}="have",MAX(1,E{i}),0)'
        ws[f"N{i}"] = f"=COUNTIF({SHEET_REQ}!${req_d}:${req_d},A{i})"
        for c_ in ("D", "E", "G", "H", "I", "J", "K", "L", "M"):
            ws[f"{c_}{i}"].fill = FILL["input"]
        dv.add(ws[f"D{i}"])
        for c_ in ("I", "J", "K"):
            dv_bool.add(ws[f"{c_}{i}"])
        ws[f"G{i}"].number_format = ws[f"H{i}"].number_format = "yyyy-mm-dd"
    last = max(len(ids) + 1, 2)
    _status_formatting(ws, f"D2:D{last}", "$D2")
    note_row = last + 2
    ws.cell(row=note_row, column=1, value="Yellow cells are editable. Status: have · in_progress · missing · not_applicable. "
            "Count ready: number of recommendation letters secured. Run `cli.py sync` to save edits back to documents.json.").font = F_NOTE
    _widths(ws, {"A": 22, "B": 38, "C": 26, "D": 14, "E": 9, "F": 9, "G": 12, "H": 12, "I": 10, "J": 10, "K": 10,
                 "L": 30, "M": 30, "N": 12, "O": 60})


def _action_plan(wb: openpyxl.Workbook, actions: List[Dict[str, Any]]) -> None:
    ws = wb.create_sheet(SHEET_PLAN)
    _header(ws, 1, PLAN_COLS)
    ws.freeze_panes = "C2"
    dv = DataValidation(type="list", formula1='"Not started,In progress,Done,Skipped"', allow_blank=True)
    ws.add_data_validation(dv)
    for i, a in enumerate(actions, start=2):
        values = ["Overdue" if a["overdue"] else a["bucket"], a["title"], a["start_by"], a["due_by"], None,
                  ", ".join(a["needed_for"]), a["details"], "Not started"]
        fill = "alt" if i % 2 == 0 else None
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        ws[f"C{i}"].number_format = ws[f"D{i}"].number_format = "yyyy-mm-dd"
        ws[f"E{i}"] = f'=IF(ISNUMBER(C{i}),C{i}-TODAY(),"")'
        ws[f"H{i}"].fill = FILL["input"]
        dv.add(ws[f"H{i}"])
        ws.row_dimensions[i].height = 42
    last = max(len(actions) + 1, 2)
    ws.conditional_formatting.add(f"A2:A{last}", FormulaRule(formula=['$A2="Overdue"'], fill=FILL["red"]))
    ws.conditional_formatting.add(f"A2:A{last}", FormulaRule(formula=['$A2="Start now"'], fill=FILL["amber"]))
    ws.conditional_formatting.add(f"H2:H{last}", FormulaRule(formula=['$H2="Done"'], fill=FILL["green"]))
    ws.auto_filter.ref = f"A1:H{last}"
    _widths(ws, {"A": 15, "B": 50, "C": 12, "D": 12, "E": 10, "F": 36, "G": 70, "H": 13})


def _timeline(wb: openpyxl.Workbook, matches: List[MatchResult], intake_year: int) -> None:
    from .deadlines import pattern_date
    ws = wb.create_sheet("Timeline")
    headers = ["Scholarship", "Country", "Eligibility", "Applications open", "Deadline", "Deadline type", "Days left",
               "Other dates", "Interviews", "Results", "Course starts", "Timeline", "Next cycle (est.)"]
    _header(ws, 1, headers, fill="navy2")
    ws.freeze_panes = "B2"
    active = [m for m in matches if m.is_eligible]
    active.sort(key=lambda m: (m.readiness.deadline if m.readiness and m.readiness.deadline else date.max))
    for i, m in enumerate(active, start=2):
        s, r = m.scholarship, m.readiness
        est = s.timeline.deadline
        extra_text = "; ".join(f"{x.label}: {pattern_date(x, intake_year).isoformat()}" for x in (est.extra if est else []))
        values = [s.name, s.country, m.eligibility_status, s.timeline.opening_month, r.deadline if r else None,
                  ("Estimated" if r and r.deadline_is_estimate else "Confirmed / published") if r and r.deadline else "-",
                  None, extra_text, s.timeline.interview_period or "-", s.timeline.result_announcement or "-",
                  s.timeline.course_start or "-", r.timeline_status if r else "-",
                  r.next_cycle_deadline if r and r.next_cycle_deadline else None]
        fill = "alt" if i % 2 == 0 else None
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        ws[f"E{i}"].number_format = ws[f"M{i}"].number_format = "yyyy-mm-dd"
        ws[f"E{i}"].font = F_BOLD
        ws[f"G{i}"] = f'=IF(ISNUMBER(E{i}),E{i}-TODAY(),"")'
    last = max(len(active) + 1, 2)
    ws.conditional_formatting.add(f"G2:G{last}", FormulaRule(formula=['AND(ISNUMBER($G2),$G2<0)'], fill=FILL["grey"]))
    ws.conditional_formatting.add(f"G2:G{last}", FormulaRule(formula=['AND(ISNUMBER($G2),$G2>=0,$G2<45)'], fill=FILL["red"]))
    _widths(ws, {"A": 36, "B": 18, "C": 12, "D": 24, "E": 12, "F": 14, "G": 9, "H": 40, "I": 28, "J": 28, "K": 20,
                 "L": 20, "M": 14})


def _all_scholarships(wb: openpyxl.Workbook, matches: List[MatchResult]) -> None:
    ws = wb.create_sheet("All Scholarships")
    headers = ["ID", "Scholarship", "Organization", "Country", "Degrees", "Funding", "Tuition", "Monthly stipend",
               "Flights", "Health insurance", "Accommodation", "Visa fees", "Other allowances", "Nationalities",
               "Grades", "Language", "Work experience", "Age limit", "Fields", "Return obligation", "Applications open",
               "Deadline (as published)", "Interviews", "Results", "Course starts", "Required papers", "Portal",
               "Application system", "Strategy", "Program status", "Data reviewed"]
    _header(ws, 1, headers)
    ws.freeze_panes = "C2"
    yn = lambda b: "Yes" if b else "No"  # noqa: E731
    for i, m in enumerate(sorted(matches, key=lambda m: m.scholarship.name), start=2):
        s = m.scholarship
        c, e, t = s.coverage_details, s.eligibility, s.timeline
        values = [s.id, s.name, s.organization, s.country, ", ".join(s.degrees), FUNDING_LABEL[s.funding_type], yn(c.tuition_covered),
                  c.monthly_stipend, yn(c.airfare_covered), yn(c.health_insurance), yn(c.accommodation_covered),
                  yn(c.visa_fees_covered), c.additional_allowances or "-", e.eligible_nationalities, e.gpa_requirement,
                  e.language_requirements,
                  f"{e.work_experience_years:g} yrs" + (f" ({e.work_hours_required:,} h)" if e.work_hours_required else ""),
                  e.age_limit or "-", e.field_restrictions, e.return_obligation or "None", t.opening_month,
                  t.typical_deadline, t.interview_period or "-", t.result_announcement or "-", t.course_start or "-",
                  "\n".join(f"• {d.label}" for d in s.documents), s.official_portal, s.application_portal_system,
                  s.strategic_tips, s.program_status + (f": {s.program_status_note}" if s.program_status_note else ""),
                  s.data_last_reviewed or "-"]
        fill = "alt" if i % 2 == 0 else None
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        link = ws.cell(row=i, column=headers.index("Portal") + 1)
        link.hyperlink, link.font = s.official_portal, F_LINK
        ws.row_dimensions[i].height = 120
    for idx, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(idx)].width = 44 if h in ("Required papers", "Strategy", "Nationalities", "Fields", "Language", "Grades") else 18
    ws.column_dimensions["B"].width = 32


PROGRAM_COLS = ["Rank", "Program ID", "Acronym", "Program", "Scheme", "Score", "Field match", "Eligible", "Status",
                "Scholarships next intake", "Deadline", "Deadline type", "Days left", "Where you study", "Universities",
                "English requirement", "Months", "Website", "Chosen", "Notes"]
SHEET_PROGRAMS = "Programs"


def _programs_sheet(wb: openpyxl.Workbook, program_matches: List[Any], states: Dict[str, ApplicationState]) -> None:
    ws = wb.create_sheet(SHEET_PROGRAMS)
    _header(ws, 1, PROGRAM_COLS)
    ws.freeze_panes = "E2"
    chosen = {c for st in states.values() for c in st.chosen_programs}
    dv = DataValidation(type="list", formula1='"yes,no"', allow_blank=True)
    ws.add_data_validation(dv)
    yn = {True: "yes", False: "no", None: "unknown"}
    for i, pm in enumerate(program_matches, start=2):
        p = pm.program
        values = [i - 1, p.id, p.acronym, p.name, p.parent_scholarship, pm.score, pm.field_match,
                  "yes" if pm.eligible else "no", p.status.replace("_", " "), yn[p.scholarships_available],
                  pm.deadline, ("Estimated" if pm.deadline_is_estimate else "Published") if pm.deadline else "-", None,
                  ", ".join(p.host_countries), "\n".join(f"{u.university} ({u.country})" for u in p.universities),
                  p.english_requirement or "", p.duration_months, p.website, "yes" if p.id in chosen else "no",
                  "; ".join(pm.warnings + ([p.notes] if p.notes else []))]
        fill = "alt" if i % 2 == 0 else None
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        dcol, days = col(PROGRAM_COLS, "Deadline"), col(PROGRAM_COLS, "Days left")
        ws[f"{dcol}{i}"].number_format = "yyyy-mm-dd"
        ws[f"{days}{i}"] = f'=IF(ISNUMBER({dcol}{i}),{dcol}{i}-TODAY(),"")'
        site = ws.cell(row=i, column=PROGRAM_COLS.index("Website") + 1)
        site.hyperlink, site.font = p.website, F_LINK
        ch = ws.cell(row=i, column=PROGRAM_COLS.index("Chosen") + 1)
        ch.fill = FILL["input"]
        dv.add(ch)
        ws.row_dimensions[i].height = 48
    last = max(len(program_matches) + 1, 2)
    sc = col(PROGRAM_COLS, "Score")
    ws.conditional_formatting.add(f"{sc}2:{sc}{last}", ColorScaleRule(start_type="num", start_value=20, start_color="F8CBAD",
                                                                   mid_type="num", mid_value=60, mid_color="FFEB9C",
                                                                   end_type="num", end_value=95, end_color="C6EFCE"))
    el = col(PROGRAM_COLS, "Eligible")
    ws.conditional_formatting.add(f"{el}2:{el}{last}", FormulaRule(formula=[f'${el}2="no"'], fill=FILL["red"]))
    ws.auto_filter.ref = f"A1:{get_column_letter(len(PROGRAM_COLS))}{last}"
    _widths(ws, {"A": 6, "B": 16, "C": 12, "D": 40, "E": 18, "F": 8, "G": 10, "H": 9, "I": 14, "J": 12, "K": 12,
                 "L": 11, "M": 9, "N": 30, "O": 44, "P": 26, "Q": 8, "R": 30, "S": 9, "T": 40})


def _country_guides(wb: openpyxl.Workbook) -> None:
    ws = wb.create_sheet("Country Guides")
    with open(Path(__file__).parent.parent / "data" / "countries.json", "r", encoding="utf-8") as f:
        countries = json.load(f)
    headers = ["Country", "Living cost / year", "Tuition policy", "Part-time work", "Post-study work visa",
               "Proof of funds", "Admission portal"]
    _header(ws, 1, headers)
    for i, c in enumerate(countries, start=2):
        values = [f"{c.get('flag', '')} {c.get('name', '')} ({c.get('name_ar', '')})",
                  c.get("average_living_cost_per_year", ""), c.get("tuition_policy", ""), c.get("part_time_work_rights", ""),
                  c.get("post_study_work_visa", ""), c.get("proof_of_funds_requirement", ""), c.get("study_portal", "")]
        fill = "alt" if i % 2 == 0 else None
        for j, v in enumerate(values, 1):
            _cell(ws, i, j, v, fill=fill)
        ws.row_dimensions[i].height = 80
    _widths(ws, {"A": 26, "B": 24, "C": 44, "D": 36, "E": 44, "F": 40, "G": 30})


def _detail_sheet(wb: openpyxl.Workbook, rank: int, m: MatchResult, match_row: int, req_rows: Dict[tuple, int],
                  used: set) -> str:
    s, r = m.scholarship, m.readiness
    name = _sheet_name_for(rank, s.name, used)
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    row = _title(ws, s.name, 7, f"{s.organization} · {s.country} · {', '.join(s.degrees)} · {FUNDING_LABEL[s.funding_type]} funding")
    mq = _q(SHEET_MATCH)

    row = _section(ws, row, "At a glance", 7)
    glance = [
        ("Eligibility", m.eligibility_status, None),
        ("Fit score", m.fit_score, None),
        ("Readiness", f"={mq}!{col(MATCH_COLS, 'Readiness')}{match_row}", "0%"),
        ("Deadline", r.deadline if r and r.deadline else "Unknown", "yyyy-mm-dd"),
        ("Deadline type", f"={mq}!{col(MATCH_COLS, 'Deadline type')}{match_row}", None),
        ("Days left", f"={mq}!{col(MATCH_COLS, 'Days left')}{match_row}", None),
        ("Timeline", r.timeline_status if r else "-", None),
        ("Application status", f"={mq}!{col(MATCH_COLS, 'Application status')}{match_row}", None),
        ("Tier", m.tier, None),
        ("Portal", s.official_portal, None),
    ]
    if r and r.next_cycle_deadline:
        glance.insert(4, ("Next cycle (est.)", r.next_cycle_deadline, "yyyy-mm-dd"))
    for label, value, fmt in glance:
        _cell(ws, row, 1, label, F_BOLD, "ice")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        c = _cell(ws, row, 2, value, F_XREF if isinstance(value, str) and value.startswith("=") else F_REG, fmt=fmt)
        if label == "Portal":
            c.hyperlink, c.font = s.official_portal, F_LINK
        row += 1

    if m.next_steps:
        row = _section(ws, row + 1, "What to do next", 7)
        for step in m.next_steps[:8]:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
            _cell(ws, row, 1, f"• {step}")
            ws.row_dimensions[row].height = 28
            row += 1

    row = _section(ws, row + 1, "Eligibility checks", 7)
    _header(ws, row, ["Check", "Result", "Detail", "", "", "Fix", ""], fill="navy2", height=20)
    _merge_header(ws, row, [(3, 5), (6, 7)])
    row += 1
    for g in m.gate_checks:
        _cell(ws, row, 1, g.name, F_BOLD)
        _cell(ws, row, 2, g.result, fill={"pass": "green", "fail": "red", "unknown": "amber", "warn": "amber"}[g.result], align=CENTER)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=5)
        _cell(ws, row, 3, g.detail)
        ws.merge_cells(start_row=row, start_column=6, end_row=row, end_column=7)
        _cell(ws, row, 6, g.fix or "")
        ws.row_dimensions[row].height = 30
        row += 1

    row = _section(ws, row + 1, "Fit score breakdown", 7)
    _header(ws, row, ["Part", "Points", "Max", "Why", "", "", ""], fill="navy2", height=20)
    _merge_header(ws, row, [(4, 7)])
    row += 1
    first = row
    for c_ in m.score_breakdown:
        _cell(ws, row, 1, c_.name, F_BOLD)
        _cell(ws, row, 2, c_.points, align=CENTER)
        _cell(ws, row, 3, c_.weight, align=CENTER)
        ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=7)
        _cell(ws, row, 4, c_.detail)
        ws.row_dimensions[row].height = 30
        row += 1
    _cell(ws, row, 1, "Fit (0-100)", F_BOLD, "ice")
    _cell(ws, row, 2, f"=ROUND(100*SUM(B{first}:B{row - 1})/SUM(C{first}:C{row - 1}),1)", F_BOLD, "ice", CENTER)
    row += 1

    if r:
        row = _section(ws, row + 1, "Required papers", 7)
        _header(ws, row, ["Paper (as the program words it)", "Status", "Ready", "Start by", "Where to file", "Issues", "How to get it"],
                fill="navy2", height=20)
        row += 1
        status_first = row
        rq = SHEET_REQ
        for q in r.requirements:
            rr = req_rows.get((s.id, q.doc, q.label))
            label = q.label + (" (optional)" if q.optional else "") + (" (after submission)" if q.stage == "later" else "")
            _cell(ws, row, 1, label)
            if rr:
                _cell(ws, row, 2, f"={rq}!{col(REQ_COLS, 'Status')}{rr}", F_XREF, align=CENTER)
                _cell(ws, row, 3, f"={rq}!{col(REQ_COLS, 'Ready units')}{rr}", F_XREF, align=CENTER, fmt="0%")
                _cell(ws, row, 5, f"={rq}!{col(REQ_COLS, 'Where to file')}{rr}", F_XREF)
            else:
                _cell(ws, row, 2, q.state, align=CENTER)
                _cell(ws, row, 3, q.units, align=CENTER, fmt="0%")
                _cell(ws, row, 5, "")
            _cell(ws, row, 4, q.start_by if q.units < 1 else None, fmt="yyyy-mm-dd")
            _cell(ws, row, 6, "; ".join(q.issues))
            _cell(ws, row, 7, q.how_to_obtain)
            ws.row_dimensions[row].height = 42
            row += 1
        _status_formatting(ws, f"B{status_first}:B{max(row - 1, status_first)}", f"$B{status_first}")

    cov = s.coverage_details
    row = _section(ws, row + 1, "What the scholarship pays", 7)
    for label, value in [("Tuition", cov.tuition_covered), ("Monthly stipend", cov.monthly_stipend), ("Flights", cov.airfare_covered),
                         ("Health insurance", cov.health_insurance), ("Accommodation", cov.accommodation_covered),
                         ("Visa fees", cov.visa_fees_covered), ("Other allowances", cov.additional_allowances or "-")]:
        _cell(ws, row, 1, label, F_BOLD, "ice")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
        _cell(ws, row, 2, ("Yes" if value else "No") if isinstance(value, bool) else value)
        row += 1

    e, t = s.eligibility, s.timeline
    row = _section(ws, row + 1, "Official eligibility & timeline (as published)", 7)
    for label, value in [("Nationalities", e.eligible_nationalities), ("Grades", e.gpa_requirement), ("Language", e.language_requirements),
                         ("Age", e.age_limit or "No limit stated"), ("Fields", e.field_restrictions),
                         ("Return obligation", e.return_obligation or "None"), ("Applications open", t.opening_month),
                         ("Deadline (as published)", t.typical_deadline), ("Interviews", t.interview_period or "-"),
                         ("Results", t.result_announcement or "-"), ("Course starts", t.course_start or "-")]:
        _cell(ws, row, 1, label, F_BOLD, "ice")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
        _cell(ws, row, 2, value)
        ws.row_dimensions[row].height = 30
        row += 1

    row = _section(ws, row + 1, "Strategy", 7)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
    _cell(ws, row, 1, s.strategic_tips)
    ws.row_dimensions[row].height = 60
    _widths(ws, {"A": 34, "B": 14, "C": 10, "D": 14, "E": 30, "F": 34, "G": 50})
    return name


def _dashboard(wb: openpyxl.Workbook, profile: CandidateProfile, matches: List[MatchResult], shortlist: List[MatchResult],
               match_rows: Dict[str, int], detail_names: Dict[str, str], actions: List[Dict[str, Any]], today: date) -> None:
    ws = wb.create_sheet("Dashboard", 1)
    ws.sheet_view.showGridLines = False
    row = _title(ws, f"SCHOLARSHIP DASHBOARD: {profile.full_name.upper()}", 9,
                 f"{profile.target_degree} in {profile.field_of_study} · intake {profile.target_intake_year} · "
                 f"{profile.nationality} · GPA {profile.normalized_gpa:.2f}/4.0 · "
                 f"{profile.english_test or 'no English test'} {profile.english_score or ''} · generated {today.isoformat()}")
    mq = _q(SHEET_MATCH)
    elig = col(MATCH_COLS, "Eligibility")
    match_col = col(MATCH_COLS, "Match")
    tl = col(MATCH_COLS, "Timeline")
    last = len(matches) + 1
    kpis = [
        ("Scholarships checked", f"=COUNTA({mq}!B2:B{last})", None),
        ("Eligible", f'=COUNTIF({mq}!{elig}2:{elig}{last},"Eligible")', None),
        ("Needs check", f'=COUNTIF({mq}!{elig}2:{elig}{last},"Needs Check")', None),
        ("High matches", f'=COUNTIF({mq}!{match_col}2:{match_col}{last},"High Match")', None),
        ("Deadline passed", f'=COUNTIF({mq}!{tl}2:{tl}{last},"Deadline passed")', None),
    ]
    rd = col(MATCH_COLS, "Readiness")
    if shortlist:
        refs = ",".join(f"{mq}!{rd}{match_rows[m.scholarship.id]}" for m in shortlist)
        kpis.append(("Shortlist readiness (avg)", f"=IFERROR(AVERAGE({refs}),0)", "0%"))
    for j, (label, formula, fmt) in enumerate(kpis):
        top = ws.cell(row=row, column=j + 1, value=formula)
        top.font, top.alignment, top.fill = F_KPI, CENTER, FILL["ice"]
        if fmt:
            top.number_format = fmt
        lab = ws.cell(row=row + 1, column=j + 1, value=label)
        lab.font, lab.alignment = F_NOTE, CENTER
    ws.row_dimensions[row].height = 40
    row += 3

    row = _section(ws, row, "Shortlist (ranked by priority)", 9)
    _header(ws, row, ["#", "Scholarship", "Country", "Fit", "Readiness", "Deadline", "Days left", "Timeline", "Details"], fill="navy2", height=22)
    row += 1
    for i, m in enumerate(shortlist, 1):
        mr = match_rows[m.scholarship.id]
        r = m.readiness
        _cell(ws, row, 1, i, align=CENTER)
        _cell(ws, row, 2, m.scholarship.name, F_BOLD)
        _cell(ws, row, 3, m.scholarship.country)
        _cell(ws, row, 4, m.fit_score, align=CENTER)
        _cell(ws, row, 5, f"={mq}!{rd}{mr}", F_XREF, align=CENTER, fmt="0%")
        _cell(ws, row, 6, r.deadline if r and r.deadline else "-", fmt="yyyy-mm-dd")
        _cell(ws, row, 7, f"={mq}!{col(MATCH_COLS, 'Days left')}{mr}", F_XREF, align=CENTER)
        _cell(ws, row, 8, r.timeline_status if r else "-")
        sheet = detail_names.get(m.scholarship.id)
        link = _cell(ws, row, 9, "Open sheet →" if sheet else "", F_LINK if sheet else F_REG)
        if sheet:
            link.hyperlink = f"#'{sheet}'!A1"
        row += 1
    if shortlist:
        _percent_scale(ws, f"E{row - len(shortlist)}:E{row - 1}")

    row = _section(ws, row + 1, "Next actions", 9)
    _header(ws, row, ["When", "Task", "", "", "Start by", "Due by", "For", "", ""], fill="navy2", height=22)
    _merge_header(ws, row, [(2, 4), (7, 9)])
    row += 1
    for a in [a for a in actions if a["bucket"] != "After submitting"][:12]:
        _cell(ws, row, 1, "Overdue" if a["overdue"] else a["bucket"], fill="red" if a["overdue"] else None)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        _cell(ws, row, 2, a["title"])
        _cell(ws, row, 5, a["start_by"], fmt="yyyy-mm-dd")
        _cell(ws, row, 6, a["due_by"], fmt="yyyy-mm-dd")
        ws.merge_cells(start_row=row, start_column=7, end_row=row, end_column=9)
        names = a["needed_for"]
        _cell(ws, row, 7, ", ".join(names[:2]) + (f" +{len(names) - 2} more" if len(names) > 2 else ""))
        ws.row_dimensions[row].height = 28
        row += 1
    _widths(ws, {"A": 16, "B": 34, "C": 16, "D": 16, "E": 16, "F": 16, "G": 12, "H": 18, "I": 14})


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def generate_application_workbook(profile: CandidateProfile, matches: List[MatchResult], output_path: str,
                                  inventory: Optional[DocumentInventory] = None,
                                  states: Optional[Dict[str, ApplicationState]] = None,
                                  shortlist: Optional[List[MatchResult]] = None,
                                  actions: Optional[List[Dict[str, Any]]] = None,
                                  today: Optional[date] = None,
                                  program_matches: Optional[List[Any]] = None) -> str:
    today = today or date.today()
    inventory = derive_inventory(profile, inventory)
    states = states or {}
    shortlist = shortlist if shortlist is not None else select_shortlist(matches)
    actions = actions if actions is not None else build_action_plan(profile, shortlist, today)

    wb = openpyxl.Workbook()
    _how_to_use(wb, profile, today)
    match_rows = _ranked_matches(wb, matches, states)
    used = set(wb.sheetnames) | {"Dashboard", SHEET_REQ, SHEET_DOCS, SHEET_PLAN, "Timeline", "Programs", "All Scholarships", "Country Guides"}
    req_rows = _requirements(wb, matches)
    detail_names: Dict[str, str] = {}
    for rank, m in enumerate(shortlist, 1):
        detail_names[m.scholarship.id] = _detail_sheet(wb, rank, m, match_rows[m.scholarship.id], req_rows, used)
    _my_documents(wb, inventory, matches)
    _action_plan(wb, actions)
    _timeline(wb, matches, profile.target_intake_year)
    if program_matches is None:
        from .programs import rank_programs
        program_matches = rank_programs(profile, today=today, include_closed=True)
    _programs_sheet(wb, program_matches, states)
    _all_scholarships(wb, matches)
    _country_guides(wb)
    _dashboard(wb, profile, matches, shortlist, match_rows, detail_names, actions, today)

    # Order: How to Use, Dashboard, Ranked Matches, detail sheets, Requirements, My Documents, Action Plan, rest.
    order = ["How to Use", "Dashboard", SHEET_MATCH] + list(detail_names.values()) + [
        SHEET_REQ, SHEET_DOCS, SHEET_PLAN, "Timeline", SHEET_PROGRAMS, "All Scholarships", "Country Guides"]
    wb._sheets = [wb[n] for n in order]  # noqa: SLF001 - openpyxl has no public reorder API
    wb.active = 1
    for sheet in wb.worksheets:
        _print_setup(sheet)
        sheet.sheet_view.tabSelected = sheet.title == "Dashboard"
    wb.calculation.fullCalcOnLoad = True
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def read_workbook_edits(path: str) -> Dict[str, Any]:
    """Read the user-editable cells back (for `cli.py sync`)."""
    wb = openpyxl.load_workbook(path, data_only=False)
    edits: Dict[str, Any] = {"documents": {}, "scholarship_documents": {}, "application_status": {}}
    if SHEET_DOCS in wb.sheetnames:
        ws = wb[SHEET_DOCS]
        for row in ws.iter_rows(min_row=2, values_only=True):
            doc_id = row[0]
            if not doc_id or not isinstance(doc_id, str) or " " in doc_id:
                continue
            yn = lambda v: None if v in (None, "") else str(v).lower() in ("yes", "true", "1")  # noqa: E731
            edits["documents"][doc_id] = {
                "status": row[3], "count_ready": int(row[4] or 0),
                "issued": row[6].date() if hasattr(row[6], "date") else None,
                "expires": row[7].date() if hasattr(row[7], "date") else None,
                "translated": yn(row[8]), "certified": yn(row[9]), "apostilled": yn(row[10]),
                "files": [f for f in str(row[11] or "").splitlines() if f.strip()], "details": row[12] or None,
            }
    if SHEET_REQ in wb.sheetnames:
        ws = wb[SHEET_REQ]
        scope_i, status_i, count_i = REQ_COLS.index("Scope"), REQ_COLS.index("Status"), REQ_COLS.index("Count ready")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0] or row[scope_i] != "per_scholarship":
                continue
            status = row[status_i]
            if isinstance(status, str) and not status.startswith("="):
                edits["scholarship_documents"].setdefault(row[0], {})[row[3]] = {
                    "status": "have" if status == "partial" else status, "count_ready": int(row[count_i] or 0)}
    edits["chosen_programs"] = {}
    edits["has_programs_sheet"] = SHEET_PROGRAMS in wb.sheetnames
    if SHEET_PROGRAMS in wb.sheetnames:
        ws = wb[SHEET_PROGRAMS]
        id_i, scheme_i, ch_i = PROGRAM_COLS.index("Program ID"), PROGRAM_COLS.index("Scheme"), PROGRAM_COLS.index("Chosen")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[id_i] and str(row[ch_i] or "").lower() == "yes":
                edits["chosen_programs"].setdefault(row[scheme_i], []).append(row[id_i])
    if SHEET_MATCH in wb.sheetnames:
        ws = wb[SHEET_MATCH]
        st_i = MATCH_COLS.index("Application status")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[1]:
                edits["application_status"][row[1]] = row[st_i]
    return edits
