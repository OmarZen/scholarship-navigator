---
name: scholarship-deadline-verifier
description: >-
  Verify scholarship and program deadlines, eligible countries and program status on official websites, then record
  them so plans use real dates. Use when a deadline shows "(est.)", when a program's status is unknown, when the
  user asks "is this still open?" or "when is the deadline?", or before telling anyone a date as fact.
---

# Deadline & eligibility verifier

The database stores the **usual pattern** of each deadline plus dates confirmed by research (with source and
`verified_on`). Estimates must be checked before a candidate relies on them.

## What needs checking

- Workspace: tasks named "Confirm the <scholarship> deadline" in `INDEX.md`, and every `(est.)` date.
- `cli.py validate --warnings` lists records with old `data_last_reviewed` / `verified_on` or missing sources.
- Programs with status `unknown`, or deadlines in `data/programs/*.json` marked estimated.

## How to verify

1. Open the **official** page: `official_portal` of the scholarship, the program `website`, the embassy page for
   embassy-track awards (MEXT, GKS, Swiss, Fulbright), or the EACEA Erasmus Mundus catalogue. Use your web tools, or
   `cli.py scrape --url <page> --engine scrapling` (or `crawl4ai` for heavy pages).
2. Find the deadline **for the candidate's intake year** and its time zone. Note whether it is the scholarship
   deadline or a university application deadline, and whether the candidate's country has its own date.
3. If the page only shows last year's date, say so: it remains an estimate.

## Record it

- For one candidate: `cli.py deadline --scholarship <id> --date YYYY-MM-DD --source <url>`
  (MCP: `confirm_deadline`). This overrides the estimate in their plan and calendar.
- For everyone (repository data): update `timeline.deadline.known_dates["<intake year>"]`, `source` and
  `verified_on` in `data/scholarships.json` (or the program record), then `cli.py validate` and the tests.
  Follow `scholarship-data-maintainer`.

## Eligibility and status changes

If the official page shows a changed country list, age limit, discontinued program or new requirement:
update the structured rule (`eligibility.rules`, `program_status`, `program_status_note`, program `status`), keep the
published text in sync, cite the source, and rebuild affected workspaces (`cli.py build`).

Report to the user in plain words: what you checked, the date and source, and what changed in their plan.
