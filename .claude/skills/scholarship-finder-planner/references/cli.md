# CLI and MCP reference

Run from the repository root: `.venv/bin/python cli.py <command>` (or `scholarship <command>` after `pip install -e .`).
Commands that need a candidate accept `--workspace <folder>` (default: the only workspace under `output/`) or
`--profile <file.json>`.

## Workspace

| Command | Purpose | JSON |
|---|---|---|
| `init --profile F [--name N] [--overwrite] [--shortlist 8]` | create `output/<name>/` and build everything | `--json` |
| `assess` | interactive interview → workspace | |
| `build [--shortlist 8]` | recompute and regenerate all files | `--json` |
| `docs list` | papers held | `--json` |
| `docs set <id> [--scholarship S] --status have\|in_progress\|missing\|not_applicable [--file P] [--issued D] [--expires D] [--count N] [--translated yes] [--certified yes] [--apostilled yes] [--details T] [--no-build]` | update a paper | |
| `gaps [--scholarship S]` | missing papers with start-by dates | `--json` |
| `deadline --scholarship S --date YYYY-MM-DD --source URL` | record a verified deadline | |
| `location home\|abroad\|both` | where the candidate will study (saved in `profile.json`, then rebuild) | |
| `status --scholarship S --set "<status>" [--notes T]` | Not Started, Preparing Documents, Drafting Essays, Awaiting LORs, Ready to Submit, Submitted, Interview Shortlisted, Accepted / Awarded, Rejected, Skipped | |
| `sync` | import edits made in the Excel tracker | |

## Matching, programs, reports

| Command | Purpose |
|---|---|
| `match [--limit 20] [--details 3] [--all] [--location home\|abroad\|both] [--json]` | eligibility, fit breakdown, readiness for every scholarship (`--location` tries a study location without saving it) |
| `programs [--field robotics] [--country Germany,France] [--scheme erasmus-mundus] [--all] [--json]` | rank Erasmus Mundus / Intra-Africa programs |
| `programs --choose ID` / `--unchoose ID` | choose up to 3 Erasmus Mundus programs |
| `list [--degree Diploma\|Bachelor\|Master\|PhD] [--country X] [--funding Full] [--nationality N [--location home\|abroad\|both]] [--json]` | browse scholarships; `--nationality` keeps awards open to that citizenship, `--location home` keeps those that fund study in that country |
| `portfolio` | Reach / Target / Safety with a rough win estimate |
| `plan`, `html-report`, `calendar` | regenerate one report |

## Writing & guides

`review-essay --file F --type chevening_leadership|chevening_networking|chevening_study_uk|chevening_career|fulbright_personal|fulbright_study|sop` ·
`email-professor --name --university --field [--paper]` · `draft-lor --name --title --org [--perspective] --brag-sheet` ·
`fee-waivers --email --university` · `finance --country C --stipend N --months 12 [--insurance] [--flights] [--self-tuition]` ·
`credentials [--country C]` · `interview --scholarship chevening` · `visa-guide --country C` · `countries`

## Data & scraping

`validate [--warnings] [--file F] [--json]` · `export-schema` · `new-scholarship <id>` ·
`scrape --url U --engine scrapling|crawl4ai|crawlee|default` · `verify --limit N` · `discover --url U`
(scraping needs the optional dependencies: `pip install -e ".[scrape]"`).

## MCP tools (mcp_server.py)

`list_scholarships` · `get_scholarship` · `match_scholarships(profile)` · `find_programs(profile?, field?, countries?)` ·
`list_document_types` · `create_workspace(profile)` · `workspace_summary` · `scholarship_brief` · `set_study_location` · `update_document` ·
`confirm_deadline` · `set_application_status` · `choose_program` · `country_guide` · `funding_gap` · `review_essay`.
Prompt: `intake_interview(language)`. Workspaces live in `$SCHOLARSHIP_WORKSPACES` (default `<repo>/output`).
