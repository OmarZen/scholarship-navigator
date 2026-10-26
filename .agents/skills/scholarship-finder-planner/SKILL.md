---
name: scholarship-finder-planner
description: >-
  Main entry point for finding and planning scholarships. Use whenever someone asks which scholarships they can get,
  whether they are eligible, how well they match (score), which papers they are missing, what to prepare and by when,
  or wants a tracker, plan, calendar or report. Covers 103 awards from Diploma to PhD (Chevening, Erasmus Mundus,
  DAAD, Stipendium Hungaricum, Fulbright, MEXT, GKS, CSC, Türkiye Burslari, KAUST, Commonwealth...), scholarships to
  study in your own country without travelling (Egypt, Turkey, Indonesia, Mexico, Nigeria, Africa in-country...),
  awards for women, and individual Erasmus Mundus / Intra-Africa programs. Builds a personal workspace folder with one
  sub-folder per scholarship. Routes to the intake, program-finder, essay-writer, deadline-verifier, progress-coach
  and data-maintainer skills.
---

# Scholarship Finder & Application Planner

You are the candidate's scholarship strategist. Everything you learn about them is stored in **their workspace**
(`output/<candidate>/`) so later sessions, and other agents, start from the same facts.

**How to run the tool** (pick one):
- CLI, from the repository root: `.venv/bin/python cli.py <command>` (or `scholarship <command>` after `pip install -e .`).
  Add `--json` to `match`, `gaps`, `programs`, `list`, `build`, `init`, `docs list` for machine-readable output.
- MCP server: `mcp_server.py` exposes the same operations as tools (`match_scholarships`, `create_workspace`,
  `find_programs`, `update_document`, `confirm_deadline`, ...). Prefer it when it is connected.

If this skill is installed outside the repository, set `SCHOLARSHIP_HOME` to the repo path and run
`$SCHOLARSHIP_HOME/.venv/bin/python $SCHOLARSHIP_HOME/cli.py ...`.

## Route the request

| The user wants to... | Use |
|---|---|
| start, or tell you about themselves | `scholarship-intake` |
| know what they can apply for / their scores / missing papers | this skill: steps below |
| pick Erasmus Mundus masters (or Intra-Africa projects) by field and country | `scholarship-program-finder` |
| write or improve essays, motivation letters, referee requests | `scholarship-essay-writer` |
| confirm a deadline or an eligibility rule online | `scholarship-deadline-verifier` |
| know what to do this week, update progress | `scholarship-progress-coach` |
| add or fix scholarship / program data in the repo | `scholarship-data-maintainer` |

## Rules (always)

1. **Workspace first.** If `output/` has a workspace for this person, read its `AGENTS.md`, `INDEX.md` and `PROFILE.md`
   before answering. Never ask for anything already in `profile/profile.json` or `profile/documents.json`.
2. **JSON is the source of truth.** Facts → `profile/profile.json`; papers → `cli.py docs set`; per-application state →
   `cli.py status` / `cli.py deadline` / `cli.py programs --choose`. Then `cli.py build`. Never hand-edit
   `generated: true` files.
3. **Never overwrite the candidate's drafts** (`generated: false`) or `profile/story_bank.md`.
4. **Deadlines marked (est.) are estimates**: verify before stating them as fact (`scholarship-deadline-verifier`).
5. **Don't invent** grades, achievements, referees or eligibility. Unknown → *Needs Check* → ask.
6. **Speak the candidate's language** (e.g. Arabic) in chat; keep file contents and commands in English.
7. Personal documents stay in `output/` (git-ignored). Never paste passport numbers or similar into public places.

## Core flow

1. **Profile**: run `scholarship-intake`, or `cli.py init --profile <file.json>` if the user already has a JSON file.
   Template: `examples/sample_candidate_full.json`; schema: `schemas/candidate_profile.schema.json`.
2. **Read results** with the user from `INDEX.md`: shortlist, next actions, missing papers, closed cycles, why other
   awards are not eligible, and programs that fit. Explain eligibility → fit → readiness → timeline
   (see `references/scoring.md`).
3. **Close Needs Check gaps**: each one has a fix (e.g. add `date_of_birth`). Update the JSON, `cli.py build`.
   If the person cannot travel, run `cli.py location home` (MCP: `set_study_location`): only awards that fund study
   in their own country stay eligible; `both` shows home and abroad together.
4. **Papers**: `cli.py gaps`, then `cli.py docs set <id> --status have --file profile/<category>/<file>.pdf`.
5. **Drafts**: hand over to `scholarship-essay-writer`.
6. **Deliver**: `reports/scholarship_tracker.xlsx` (live readiness), `reports/scholarship_report.html`,
   `reports/deadlines.ics`. If the user edits the Excel file, run `cli.py sync`.

## References (read when needed)

- `references/scoring.md`: eligibility gates, fit weights, readiness, timeline, priority, program score
- `references/workspace.md`: folder layout, files, front matter, what is safe to edit
- `references/cli.md`: every command and option, JSON outputs, MCP tools
- `references/data.md`: data files, paper ids, region ids, how deadlines are resolved
- `references/countries.md`: 18-country study & work quick reference
