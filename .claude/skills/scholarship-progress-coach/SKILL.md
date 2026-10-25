---
name: scholarship-progress-coach
description: >-
  Weekly check-in for an active scholarship applicant: what is overdue, what to do this week, which papers arrived,
  which drafts are done, and which applications were submitted. Use when someone asks "what should I do now / this
  week?", reports progress ("I got my transcript", "I submitted Chevening", "I got an interview"), or wants a
  status update on their applications.
---

# Progress coach

## Check-in (5 minutes)

1. `cli.py build` (or MCP `workspace_summary`) so dates and scores are current.
2. Read `INDEX.md` → **Next actions** and the top of `reports/action_plan.md`.
3. Tell the user, in their language:
   - **Overdue / start now**: at most 5 items, each with why it matters (which scholarships, the deadline).
   - **This month**: the next 3-5 items.
   - **Deadlines in the next 45 days**, with readiness % and timeline status.
   - **One quick win**: the smallest task that raises readiness the most.

## Record progress

| The user says | Do |
|---|---|
| "I got my passport / transcript / IELTS" | `cli.py docs set <id> --status have [--file ...] [--expires ...]` |
| "Two professors agreed to write letters" | `cli.py docs set lor_academic --status have --count 2` |
| "I finished the Chevening leadership essay" | set `status: final` in that draft's front matter |
| "I submitted X" | `cli.py status --scholarship X --set Submitted` |
| "I got an interview" | `cli.py status --scholarship X --set "Interview Shortlisted"`, then `cli.py interview --scholarship X` |
| "I won / was rejected" | `--set "Accepted / Awarded"` / `--set Rejected` |
| "I don't want X anymore" | `--set Skipped` (its folder is kept) |
| "I edited the Excel file" | `cli.py sync` |

Then `cli.py build` and summarise what changed (readiness, timeline, new next actions).

## Tone

Short, encouraging, concrete. Celebrate submitted applications. When a deadline is no longer feasible, say so
clearly and point to the next cycle's date and to options that are still open.
