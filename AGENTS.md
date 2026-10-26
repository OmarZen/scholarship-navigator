# AGENTS.md

Instructions for AI coding and assistant agents (Claude Code, Codex, Cursor, Gemini CLI, Copilot, Antigravity...)
working in this repository.

## What this repository is

An open-source scholarship navigator. Given a person's profile it checks eligibility for 103 scholarships (Diploma
to PhD; abroad or in the person's own country, see `study_location`) and individual Erasmus Mundus / Intra-Africa
programs, scores fit (0-100), measures readiness from the papers they hold,
plans every task backwards from real deadlines, and writes a personal workspace (`output/<name>/`) with one folder
per scholarship, drafts, an Excel tracker, an HTML report and a calendar.

## If you are helping someone find scholarships

Use the skills in `skills/` (mirrored in `.claude/skills/` and `.agents/skills/`; setup per assistant in
`docs/AI_TOOLS.md`). Start with
`skills/scholarship-finder-planner/SKILL.md`; it routes to:

| Skill | For |
|---|---|
| `scholarship-intake` | interviewing the person and building their profile |
| `scholarship-program-finder` | picking Erasmus Mundus masters / Intra-Africa projects by field and country |
| `scholarship-essay-writer` | essays, motivation letters, referee requests |
| `scholarship-deadline-verifier` | confirming estimated deadlines and eligibility online |
| `scholarship-progress-coach` | weekly check-ins and progress updates |
| `scholarship-data-maintainer` | adding or fixing scholarship/program data |

Interfaces: the CLI (`.venv/bin/python cli.py <command>`, add `--json` for machine-readable output) or the MCP
server (`mcp_server.py`, configured in `.mcp.json`).

Rules: read the person's `output/<name>/AGENTS.md`, `INDEX.md` and `PROFILE.md` before answering; store facts in the
JSON sources of truth, never in generated files; never invent grades, achievements or eligibility; treat `(est.)`
deadlines as unverified; answer in the person's language; ask whether they can travel (`study_location`: home,
abroad or both) and never push someone to study abroad.

## If you are changing the code or data

- Setup: `python3 -m venv .venv && .venv/bin/pip install -e ".[mcp,dev]"` (add `scrape` for the scrapers).
- Tests: `.venv/bin/python -m unittest discover tests`. Data check: `.venv/bin/python cli.py validate --warnings`.
- Code map: `planner/models.py` (pydantic models) · `matcher.py` (eligibility gates, fit, readiness, priority) ·
  `documents.py` (paper catalog & gaps) · `deadlines.py` · `programs.py` (program finder) · `roadmap.py` (shortlist,
  dated plan) · `workspace.py` + `briefs.py` (workspace files) · `xlsx_generator.py`, `html_generator.py`,
  `calendar_exporter.py` (reports) · `api.py` (JSON facade used by `mcp_server.py` and `cli.py --json`) ·
  `validation.py` (data validation, schemas, scaffolds).
- Data: `data/scholarships.json`, `data/programs/*.json`, `data/document_catalog.json`, `data/regions.json`. Every
  fact needs an official source and a verified date; see `CONTRIBUTING.md`.
- After changing `planner/models.py`: `cli.py export-schema`. After changing `skills/`: `python scripts/sync_skills.py`
  (tests fail if the copies drift).
- Never commit anything under `output/`: it holds people's personal documents.
