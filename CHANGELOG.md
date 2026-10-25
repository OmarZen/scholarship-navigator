# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-10-25

### Added
- **Eligibility engine** with pass / fail / needs-check gates: nationality (official country lists for 16 programs,
  OECD DAC list), residence, age, degree recency, work experience, field restrictions, return obligation, teaching
  language.
- **Fit score (0-100)** with a visible per-part breakdown, and **readiness %** from the papers a candidate holds.
- **Document catalog** of 47 standard paper types with lead times, validity and how to obtain them; per-scholarship
  missing-paper lists with start-by dates.
- **Dated action plan** scheduled backwards from deadlines; deadlines resolved as confirmed / published / estimated.
- **Program finder**: 56 Erasmus Mundus Joint Masters and Intra-Africa projects with host countries, universities,
  status and 2027 deadlines; choose up to 3 and get tailored motivation-letter drafts.
- **Candidate workspace** (`output/<name>/`) with `AGENTS.md`, `INDEX.md`, `PROFILE.md`, `manifest.json`, one folder per
  scholarship, essay/letter templates, and reports.
- **Excel tracker** with live readiness formulas and a `sync` command to import edits; HTML report; `.ics` calendar with
  "start by" reminders.
- **AI agent support**: 7 skills (`skills/`, mirrored for Claude Code and Antigravity), `AGENTS.md`, `CLAUDE.md`, an
  MCP server with 15 tools, and `--json` output on the main CLI commands.
- Contributor tooling: `validate`, `export-schema`, `new-scholarship`, `scripts/import_programs.py`, generated
  catalogue pages, CI workflow.

### Changed
- Deadlines, nationality lists and program statuses re-verified against official sources (October 2026): e.g.
  Chevening 2027/28 closed 6 Oct 2026, Vanier CGS discontinued, Global Rhodes suspended, Ernst Mach moved to 1 Dec.
- Scraping dependencies are optional (`pip install -e ".[scrape]"`).

## [1.0.0]

- Initial release: 34 scholarships, keyword matching, Excel and HTML reports, country guides, essay and letter helpers,
  scraping engines.
