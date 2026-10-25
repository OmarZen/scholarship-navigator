# Candidate workspace

```
output/<candidate>/
├── AGENTS.md          rules for agents working in this folder (generated)
├── INDEX.md           shortlist, next actions, missing papers, programs, closed cycles, not eligible (generated)
├── PROFILE.md         readable profile + papers on file + missing profile info (generated)
├── manifest.json      machine-readable map: shortlist, recommended programs, every file with its type (generated)
├── profile/
│   ├── profile.json   candidate facts: SOURCE OF TRUTH
│   ├── documents.json papers held: SOURCE OF TRUTH
│   ├── story_bank.md  STAR stories (candidate-owned, created once)
│   └── identity/ academic/ language/ experience/ references/ cv/ certifications/ financial/ health_legal/
│       └── README.md  which papers belong here + status (generated); put scans next to it
├── scholarships/<id>/
│   ├── SCHOLARSHIP.md eligibility checks, score breakdown, programs that fit, papers, coverage, timeline (generated)
│   ├── status.json    application_status, deadline_confirmed, chosen_programs, per-application papers
│   ├── essays/        one draft per essay prompt (candidate-owned)
│   ├── letters/       motivation / personal statement / study plan / research proposal drafts, one per chosen program
│   ├── recommendations/referee_requests.md
│   ├── forms/         CHECKLIST.md, university_choices.md
│   ├── admissions/    offers, supervisor and nomination letters
│   └── submitted/     final PDFs and confirmations
└── reports/           scholarship_tracker.xlsx · scholarship_report.html · deadlines.ics · match_report.md · action_plan.md
```

## Front matter

Every Markdown file starts with YAML front matter.
- `generated: true`: rebuilt by `cli.py build`. Never edit by hand.
- `generated: false`: candidate-owned; never overwritten. Drafts carry `doc`, `scholarship_id`, `status`
  (`todo` → `draft` → `review` → `final`) and `word_limit`. On the next build, `status: final` marks the paper as
  ready and `draft`/`review` marks it as in progress.

## Safe updates

| Change | How |
|---|---|
| New fact about the candidate | edit `profile/profile.json` → `cli.py build` |
| Got a paper | `cli.py docs set <id> --status have --file profile/<category>/<file>.pdf [--expires YYYY-MM-DD]` |
| Recommendation letters | `cli.py docs set lor_academic --status have --count 2` |
| Per-application paper | `cli.py docs set motivation_letter --scholarship <id> --status in_progress` |
| Verified deadline | `cli.py deadline --scholarship <id> --date YYYY-MM-DD --source <url>` |
| Application status / track or skip | `cli.py status --scholarship <id> --set "Submitted"` (or `Skipped`) |
| Choose an Erasmus program | `cli.py programs --choose <program-id>` (max 3) |
| User edited the Excel file | `cli.py sync` |
