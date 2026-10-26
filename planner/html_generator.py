"""
Interactive Single-Page HTML Dashboard & Report Generator.
Produces a responsive offline HTML report: ranked matches with eligibility checks and score breakdowns,
missing papers per scholarship, the dated action plan, deadlines, and country guides. No external dependencies.
"""

import json
from datetime import date
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import CandidateProfile, MatchResult, STUDY_LOCATION_LABEL, FUNDING_LABEL
from .matcher import location_label
from .documents import DocumentInventory
from .roadmap import select_shortlist, build_action_plan, PHASES

STATE_LABEL = {"have": "have", "partial": "partial", "in_progress": "in progress", "expiring": "expiring",
               "missing": "missing", "not_applicable": "n/a"}


def _e(x: Any) -> str:
    return escape(str(x if x is not None else ""))


def _bar(value: float, label: str) -> str:
    pct = max(0.0, min(100.0, value))
    tone = "good" if pct >= 80 else ("mid" if pct >= 55 else "low")
    return (f'<div class="meter"><div class="meter-label"><span>{_e(label)}</span><strong>{pct:.0f}</strong></div>'
            f'<div class="meter-track"><div class="meter-fill {tone}" style="width:{pct:.0f}%"></div></div></div>')


def _deadline(m: MatchResult) -> str:
    r = m.readiness
    if not r or not r.deadline:
        return "Unknown"
    return r.deadline.isoformat() + (" (est.)" if r.deadline_is_estimate else "")


def _card(m: MatchResult, rank: Optional[int]) -> str:
    s, r = m.scholarship, m.readiness
    elig_cls = {"Eligible": "ok", "Needs Check": "warn", "Ineligible": "bad"}[m.eligibility_status]
    gates = "".join(
        f'<li class="g-{g.result}"><strong>{_e(g.name)}</strong> {_e(g.detail)}'
        + (f' <em>Fix: {_e(g.fix)}</em>' if g.fix else "") + "</li>"
        for g in m.gate_checks
    )
    parts = "".join(
        f"<tr><td>{_e(c.name)}</td><td>{c.points:g} / {c.weight:g}</td><td>{_e(c.detail)}</td></tr>" for c in m.score_breakdown
    )
    papers = ""
    if r:
        papers = "".join(
            f'<tr><td>{_e(q.label)}{" <small>(optional)</small>" if q.optional else ""}'
            f'{" <small>(after submission)</small>" if q.stage == "later" else ""}</td>'
            f'<td><span class="st st-{q.state}">{STATE_LABEL[q.state]}</span></td>'
            f'<td>{q.start_by.isoformat() if q.start_by and q.units < 1 else ""}</td><td>{_e("; ".join(q.issues))}</td></tr>'
            for q in r.requirements
        )
    steps = "".join(f"<li>{_e(x)}</li>" for x in m.next_steps[:6])
    tl = r.timeline_status if r else "Deadline unknown"
    return f"""
<article class="s-card" data-name="{_e(s.name.lower())} {_e(s.country.lower())}" data-elig="{_e(m.eligibility_status)}">
  <div class="s-top">
    <div>
      <div class="s-title">{f'<span class="rank">#{rank}</span> ' if rank else ''}{_e(s.name)}</div>
      <div class="s-sub">{_e(s.country)} · {_e(location_label(m.study_at_home, m.study_abroad))} · {_e(', '.join(s.degrees))} · {_e(FUNDING_LABEL[s.funding_type])} funding · {_e(m.tier)}</div>
    </div>
    <div class="badges"><span class="badge {elig_cls}">{_e(m.eligibility_status)}</span>
      <span class="badge tl">{_e(tl)}</span></div>
  </div>
  <div class="meters">{_bar(m.fit_score, "Fit")}{_bar(m.readiness_percent, "Ready %")}</div>
  <div class="pills"><span class="pill">⏰ {_e(_deadline(m))}</span>
    <span class="pill">{_e(r.days_left if r and r.days_left is not None else '-')} days left</span>
    <span class="pill">💵 {_e(s.coverage_details.monthly_stipend)}</span></div>
  {f'<ol class="steps">{steps}</ol>' if steps else ''}
  <details><summary>Eligibility checks</summary><ul class="gates">{gates}</ul></details>
  <details><summary>Score breakdown (fit {m.fit_score:.0f}/100)</summary><table><tr><th>Part</th><th>Points</th><th>Why</th></tr>{parts}</table></details>
  {f'<details><summary>Required papers ({r.have_count}/{r.total_count} ready)</summary><table><tr><th>Paper</th><th>Status</th><th>Start by</th><th>Issues</th></tr>{papers}</table></details>' if r else ''}
  <div class="advice">{_e(s.strategic_tips)}</div>
  <a class="btn" href="{_e(s.official_portal)}" target="_blank" rel="noopener">Official portal ↗</a>
</article>"""


def generate_html_report(profile: CandidateProfile, matches: List[MatchResult], output_path: str,
                         shortlist: Optional[List[MatchResult]] = None, actions: Optional[List[Dict[str, Any]]] = None,
                         inventory: Optional[DocumentInventory] = None, today: Optional[date] = None,
                         program_matches: Optional[List[Any]] = None) -> str:
    today = today or date.today()
    shortlist = shortlist if shortlist is not None else select_shortlist(matches)
    actions = actions if actions is not None else build_action_plan(profile, shortlist, today)
    with open(Path(__file__).parent.parent / "data" / "countries.json", "r", encoding="utf-8") as f:
        countries = json.load(f)

    eligible = [m for m in matches if m.is_eligible]
    short_ids = {m.scholarship.id for m in shortlist}
    others = [m for m in eligible if m.scholarship.id not in short_ids]
    ineligible = [m for m in matches if not m.is_eligible]
    avg_ready = sum(m.readiness_percent for m in shortlist) / len(shortlist) if shortlist else 0
    kpis = [(len(matches), "Checked"), (sum(1 for m in matches if m.eligibility_status == "Eligible"), "Eligible"),
            (sum(1 for m in matches if m.eligibility_status == "Needs Check"), "Needs check"),
            (len(shortlist), "Shortlisted"), (f"{avg_ready:.0f}%", "Shortlist ready")]

    missing_rows = ""
    for m in shortlist:
        for q in (m.readiness.missing if m.readiness else []):
            missing_rows += (f"<tr><td>{_e(m.scholarship.name)}</td><td>{_e(q.label)}</td>"
                             f'<td><span class="st st-{q.state}">{STATE_LABEL[q.state]}</span></td>'
                             f"<td>{q.start_by.isoformat() if q.start_by else '-'}</td>"
                             f"<td>{q.lead_time_days[0]}-{q.lead_time_days[-1]} days</td><td>{_e(q.how_to_obtain)}</td></tr>")
    plan_html = ""
    for name, desc in PHASES:
        items = [a for a in actions if a["bucket"] == name]
        if not items:
            continue
        rows = "".join(
            f"<tr><td>{'⏰ ' if a['overdue'] else ''}{_e(a['title'])}</td><td>{a['start_by'].isoformat() if a['start_by'] else '-'}</td>"
            f"<td>{a['due_by'].isoformat() if a['due_by'] else '-'}</td><td>{_e(', '.join(a['needed_for']))}</td><td>{_e(a['details'])}</td></tr>"
            for a in items)
        plan_html += f'<h3>{_e(name)} <small>{_e(desc)}</small></h3><table><tr><th>Task</th><th>Start by</th><th>Due by</th><th>For</th><th>Details</th></tr>{rows}</table>'
    deadlines = sorted(eligible, key=lambda m: m.readiness.deadline if m.readiness and m.readiness.deadline else date.max)
    deadline_rows = "".join(
        f"<tr><td>{_e(m.scholarship.name)}</td><td>{_e(_deadline(m))}</td><td>{_e(m.readiness.days_left if m.readiness and m.readiness.days_left is not None else '-')}</td>"
        f"<td>{_e(m.readiness.timeline_status if m.readiness else '-')}</td><td>{_e(m.readiness.deadline_label if m.readiness else '')}</td>"
        f"<td>{_e(m.readiness.next_cycle_deadline.isoformat() if m.readiness and m.readiness.next_cycle_deadline else '')}</td></tr>"
        for m in deadlines)
    inel_rows = "".join(
        f"<tr><td>{_e(m.scholarship.name)}</td><td>{_e('; '.join(g.detail for g in m.gate_checks if g.result == 'fail'))}</td></tr>"
        for m in ineligible)
    country_rows = "".join(
        f"<tr><td><strong>{_e(c.get('flag', ''))} {_e(c.get('name', ''))}</strong><br><small>{_e(c.get('name_ar', ''))}</small></td>"
        f"<td>{_e(c.get('average_living_cost_per_year', ''))}</td><td>{_e(c.get('tuition_policy', ''))}</td>"
        f"<td>{_e(c.get('part_time_work_rights', ''))}</td><td>{_e(c.get('post_study_work_visa', ''))}</td></tr>"
        for c in countries)
    if program_matches is None:
        from .programs import rank_programs
        program_matches = rank_programs(profile, today=today, include_closed=True)
    program_rows = "".join(
        f'<tr class="p-row" data-text="{_e((pm.program.acronym + " " + pm.program.name + " " + " ".join(pm.program.fields) + " " + " ".join(pm.program.host_countries)).lower())}">'
        f"<td><strong>{_e(pm.program.acronym)}</strong><br><small>{_e(pm.program.name)}</small></td>"
        f"<td>{pm.score:.0f}</td><td>{_e(pm.field_match)}</td><td>{_e(', '.join(pm.program.host_countries))}</td>"
        f"<td>{_e((pm.deadline.isoformat() + (' (est.)' if pm.deadline_is_estimate else '')) if pm.deadline else 'see site')}</td>"
        f"<td>{_e(pm.program.status.replace('_', ' '))}{'' if pm.eligible else ' · not eligible'}</td>"
        f'<td><a href="{_e(pm.program.website)}" target="_blank" rel="noopener">site ↗</a></td></tr>'
        for pm in program_matches)
    kpi_html = "".join(f'<div class="kpi"><div class="num">{_e(v)}</div><div class="lbl">{_e(k)}</div></div>' for v, k in kpis)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scholarship Report - {_e(profile.full_name)}</title>
<style>
  :root {{ --primary:#1F4E79; --primary-2:#2F5597; --bg:#F8FAFC; --card:#FFFFFF; --text:#0F172A; --muted:#64748B;
          --border:#E2E8F0; --ok:#15803D; --ok-bg:#DCFCE7; --warn:#A16207; --warn-bg:#FEF9C3; --bad:#B91C1C; --bad-bg:#FEE2E2; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#0B1220; --card:#111A2C; --text:#E2E8F0; --muted:#94A3B8; --border:#22304A;
          --ok-bg:#14361F; --warn-bg:#3A3210; --bad-bg:#3F1616; --ok:#86EFAC; --warn:#FDE68A; --bad:#FCA5A5; }} }}
  * {{ box-sizing:border-box; margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  body {{ background:var(--bg); color:var(--text); line-height:1.5; padding:24px 16px; }}
  .container {{ max-width:1180px; margin:0 auto; }}
  .header {{ background:linear-gradient(135deg,var(--primary),var(--primary-2)); color:#fff; padding:28px; border-radius:16px; margin-bottom:20px; }}
  .header h1 {{ font-size:26px; }} .header p {{ color:#CBD5E1; font-size:14px; }}
  .grid {{ display:grid; grid-template-columns:2fr 3fr; gap:16px; margin-bottom:20px; }}
  @media (max-width:860px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; }}
  .card h2 {{ font-size:16px; color:var(--primary); margin-bottom:12px; }}
  @media (prefers-color-scheme: dark) {{ .card h2, .s-title {{ color:#93C5FD; }} }}
  .facts {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:13px; }}
  .facts div {{ background:var(--bg); border-radius:8px; padding:8px 10px; }} .facts span {{ display:block; font-size:11px; color:var(--muted); text-transform:uppercase; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:10px; }}
  .kpi {{ background:var(--bg); border:1px solid var(--border); border-radius:10px; padding:14px; text-align:center; }}
  .kpi .num {{ font-size:26px; font-weight:800; color:var(--primary); }} .kpi .lbl {{ font-size:11px; color:var(--muted); text-transform:uppercase; }}
  @media (prefers-color-scheme: dark) {{ .kpi .num {{ color:#93C5FD; }} }}
  .tabs {{ display:flex; gap:6px; margin-bottom:16px; overflow-x:auto; border-bottom:2px solid var(--border); padding-bottom:8px; }}
  .tab {{ background:none; border:none; padding:9px 14px; font-weight:600; color:var(--muted); border-radius:8px; cursor:pointer; white-space:nowrap; font-size:14px; }}
  .tab.active {{ background:var(--primary); color:#fff; }}
  .pane {{ display:none; }} .pane.active {{ display:block; }}
  .search {{ display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap; }}
  .search input, .search select {{ padding:9px 12px; border:1px solid var(--border); border-radius:8px; font-size:14px; background:var(--card); color:var(--text); }}
  .search input {{ flex:1; min-width:220px; }}
  .list {{ display:grid; gap:14px; }}
  .s-card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; }}
  .s-top {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-bottom:10px; }}
  .s-title {{ font-size:17px; font-weight:700; color:var(--primary); }} .s-sub {{ font-size:13px; color:var(--muted); }}
  .rank {{ color:var(--muted); font-weight:600; }}
  .badge {{ display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; margin-left:4px; }}
  .badge.ok {{ background:var(--ok-bg); color:var(--ok); }} .badge.warn {{ background:var(--warn-bg); color:var(--warn); }}
  .badge.bad {{ background:var(--bad-bg); color:var(--bad); }} .badge.tl {{ background:var(--bg); color:var(--muted); }}
  .meters {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:10px; }}
  .meter-label {{ display:flex; justify-content:space-between; font-size:12px; color:var(--muted); }}
  .meter-track {{ height:8px; background:var(--bg); border-radius:6px; overflow:hidden; border:1px solid var(--border); }}
  .meter-fill {{ height:100%; }} .meter-fill.good {{ background:#16A34A; }} .meter-fill.mid {{ background:#CA8A04; }} .meter-fill.low {{ background:#DC2626; }}
  .pills {{ display:flex; gap:6px; flex-wrap:wrap; font-size:12px; margin-bottom:10px; }}
  .pill {{ background:var(--bg); border:1px solid var(--border); padding:3px 8px; border-radius:6px; }}
  .steps {{ font-size:13px; margin:0 0 10px 18px; }}
  details {{ margin:6px 0; font-size:13px; }} summary {{ cursor:pointer; font-weight:600; color:var(--primary); }}
  @media (prefers-color-scheme: dark) {{ summary {{ color:#93C5FD; }} }}
  .gates {{ list-style:none; margin:8px 0; }} .gates li {{ padding:4px 0 4px 22px; position:relative; }}
  .gates li::before {{ position:absolute; left:0; }} .g-pass::before {{ content:"✅"; }} .g-fail::before {{ content:"❌"; }}
  .g-unknown::before {{ content:"❓"; }} .g-warn::before {{ content:"⚠️"; }} .gates em {{ color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin:8px 0; }}
  th, td {{ padding:8px 10px; text-align:left; border-bottom:1px solid var(--border); vertical-align:top; }}
  th {{ background:var(--bg); color:var(--primary); }}
  .table-wrap {{ overflow-x:auto; }}
  .st {{ padding:2px 8px; border-radius:10px; font-size:12px; font-weight:600; white-space:nowrap; }}
  .st-have, .st-not_applicable {{ background:var(--ok-bg); color:var(--ok); }} .st-partial, .st-in_progress, .st-expiring {{ background:var(--warn-bg); color:var(--warn); }}
  .st-missing {{ background:var(--bad-bg); color:var(--bad); }}
  .advice {{ background:var(--warn-bg); border-left:4px solid #F59E0B; padding:8px 12px; font-size:13px; margin:10px 0; border-radius:4px; }}
  .btn {{ display:inline-block; background:var(--primary); color:#fff; text-decoration:none; padding:7px 14px; border-radius:6px; font-size:13px; font-weight:600; }}
  h3 {{ font-size:15px; margin:16px 0 4px; }} h3 small {{ color:var(--muted); font-weight:400; }}
  .note {{ font-size:12px; color:var(--muted); margin-bottom:8px; }}
  @media print {{ .tabs, .search {{ display:none; }} .pane {{ display:block; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🎓 Scholarship Strategy Report</h1>
    <p>{_e(profile.full_name)} · {_e(profile.target_degree)} in {_e(profile.field_of_study)} · intake {profile.target_intake_year} · generated {today.isoformat()}</p>
  </div>
  <div class="grid">
    <div class="card"><h2>👤 Profile</h2><div class="facts">
      <div><span>Nationality</span>{_e(profile.nationality)}</div><div><span>GPA</span>{profile.normalized_gpa:.2f} / 4.0</div>
      <div><span>English</span>{_e(profile.english_test or 'none')} {_e(profile.english_score if profile.english_score is not None else '')}</div>
      <div><span>Work</span>{profile.work_experience_years:g} years</div>
      <div><span>Target countries</span>{_e(', '.join(profile.target_countries) or 'Worldwide')}</div>
      <div><span>Where to study</span>{_e(STUDY_LOCATION_LABEL[profile.study_location])}</div>
      <div><span>Funding</span>{_e(profile.target_funding)}</div></div></div>
    <div class="card"><h2>📊 Overview</h2><div class="kpis">{kpi_html}</div>
      <p class="note" style="margin-top:10px">Fit = how well you match (0-100). Ready = share of required papers you already have. Deadlines marked (est.) are estimates: verify them.</p></div>
  </div>
  <div class="tabs" role="tablist">
    <button class="tab active" data-tab="shortlist">⭐ Shortlist</button>
    <button class="tab" data-tab="papers">📄 Missing papers</button>
    <button class="tab" data-tab="plan">🗓️ Action plan</button>
    <button class="tab" data-tab="all">🏛️ All matches</button>
    <button class="tab" data-tab="programs">🧭 Programs</button>
    <button class="tab" data-tab="deadlines">⏰ Deadlines</button>
    <button class="tab" data-tab="countries">🌍 Countries</button>
  </div>
  <section id="pane-shortlist" class="pane active"><div class="list">{''.join(_card(m, i) for i, m in enumerate(shortlist, 1)) or '<p>No open eligible scholarships.</p>'}</div></section>
  <section id="pane-papers" class="pane"><div class="card"><h2>Missing papers across the shortlist</h2><div class="table-wrap">
    <table><tr><th>Scholarship</th><th>Paper</th><th>Status</th><th>Start by</th><th>Takes</th><th>How to get it</th></tr>{missing_rows or '<tr><td colspan="6">Nothing missing.</td></tr>'}</table></div></div></section>
  <section id="pane-plan" class="pane"><div class="card"><h2>Dated action plan</h2><div class="table-wrap">{plan_html or '<p>Nothing scheduled.</p>'}</div></div></section>
  <section id="pane-all" class="pane">
    <div class="search"><input id="q" type="search" placeholder="Search by name or country">
      <select id="elig"><option value="">All eligibility</option><option>Eligible</option><option>Needs Check</option><option>Ineligible</option></select></div>
    <div class="list" id="all-list">{''.join(_card(m, None) for m in others + ineligible)}</div>
    <div class="card" style="margin-top:14px"><h2>Why not eligible</h2><div class="table-wrap"><table><tr><th>Scholarship</th><th>Reason</th></tr>{inel_rows}</table></div></div>
  </section>
  <section id="pane-programs" class="pane"><div class="card"><h2>Programs inside scholarship schemes (Erasmus Mundus masters, Intra-Africa projects)</h2>
    <p class="note">Score = field match 50 + host country 20 + language 15 + funding status 15. You can apply to up to 3 Erasmus Mundus programs per year.</p>
    <div class="search"><input id="pq" type="search" placeholder="Filter by field, country or name (e.g. robotics, Germany)"></div>
    <div class="table-wrap"><table><tr><th>Program</th><th>Score</th><th>Field</th><th>Where you study</th><th>Deadline</th><th>Status</th><th>Link</th></tr>{program_rows}</table></div></div></section>
  <section id="pane-deadlines" class="pane"><div class="card"><h2>Deadlines (eligible scholarships)</h2><div class="table-wrap">
    <table><tr><th>Scholarship</th><th>Deadline</th><th>Days left</th><th>Timeline</th><th>Which deadline</th><th>Next cycle (est.)</th></tr>{deadline_rows}</table></div></div></section>
  <section id="pane-countries" class="pane"><div class="card"><h2>Country study & work guides</h2><div class="table-wrap">
    <table><tr><th>Country</th><th>Living cost</th><th>Tuition</th><th>Work rights</th><th>Post-study visa</th></tr>{country_rows}</table></div></div></section>
</div>
<script>
  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('pane-' + btn.dataset.tab).classList.add('active');
  }}));
  function filterAll() {{
    const q = document.getElementById('q').value.toLowerCase();
    const e = document.getElementById('elig').value;
    document.querySelectorAll('#all-list .s-card').forEach(c => {{
      const ok = (!q || c.dataset.name.includes(q)) && (!e || c.dataset.elig === e);
      c.style.display = ok ? '' : 'none';
    }});
  }}
  document.getElementById('pq').addEventListener('input', () => {{
    const q = document.getElementById('pq').value.toLowerCase();
    document.querySelectorAll('.p-row').forEach(r => {{ r.style.display = (!q || r.dataset.text.includes(q)) ? '' : 'none'; }});
  }});
  document.getElementById('q').addEventListener('input', filterAll);
  document.getElementById('elig').addEventListener('change', filterAll);
</script>
</body>
</html>
"""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(page, encoding="utf-8")
    return str(out_file.resolve())
