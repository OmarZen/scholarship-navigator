---
name: scholarship-data-maintainer
description: >-
  Add or update scholarships and programs in the open-source database (data/scholarships.json, data/programs/,
  data/custom/) with official sources, structured eligibility rules, paper requirements and deadlines, then validate
  and test. Use when someone shares a new scholarship or a list of programs to add, reports outdated information, or
  wants to contribute data to the repository.
---

# Data maintainer

Quality rules: **official sources only** (program or government site; aggregators only as leads) · every record has
`source` / `verified_on` / `data_last_reviewed` · unknown → leave null and say so in notes · never copy
eligibility you could not confirm.

## Add a scholarship

1. `cli.py new-scholarship <kebab-id>` → `data/custom/drafts/<id>.json` with every field to fill
   (schema: `schemas/scholarship.schema.json`).
2. From the official pages fill:
   - published text: `eligibility.*` text fields, `timeline.*`, `coverage_details`, `strategic_tips`;
   - structured rules in `eligibility.rules`: nationality (`any` / `include` / `exclude` / `verify` with `countries`
     or `regions` from `data/regions.json`), `gpa_min` / `gpa_competitive` on a 4.0 scale, `language.ielts_min`,
     `age_under` per degree ("under 35" → 35), `work_experience_years`, `field` (`any` / `priority` / `restricted`
     with groups: computing, engineering, natural_sciences, health, agriculture, environment, economics_business,
     social_sciences, humanities), `return_obligation_years`;
   - `documents`: one entry per required paper, `doc` = id from `data/document_catalog.json`, `label` = the program's
     own wording, plus `count`, `words`, `items` (essay prompts), `degrees`, `stage: later`, `optional`,
     `alternatives`, `requires` (certified, translated, apostille, signed, template);
   - `timeline.deadline`: `month`, `day`, `years_before_intake` (1 when the deadline falls the year before an autumn
     intake), `precision`, `label`, `source`, `verified_on`, `known_dates {"2027": "YYYY-MM-DD"}`.
3. `cli.py validate --file data/custom/drafts/<id>.json --warnings` until there are no errors.
4. Local use: move it to `data/custom/<id>.json` (loaded automatically). To contribute: add it to
   `data/scholarships.json` and open a pull request (see CONTRIBUTING.md).

If a needed paper type is missing from the catalog, add it to `data/document_catalog.json` (name, category, scope,
lead_time_days, validity_months, how_to_obtain).

## Add or update programs (Erasmus Mundus masters, Intra-Africa projects)

Edit `data/programs/<scheme>.json`, one object per program (schema: `schemas/program.schema.json`):
`id` (kebab-case acronym), `acronym`, `name`, `type`, `parent_scholarship`, `website`, `fields`, `field_groups`,
`degrees`, `duration_months`, `language`, `coordinator`, `universities` [{university, city, country}],
`host_countries`, `status` (open / upcoming / self_funded_only / discontinued / unknown), `scholarships_available`,
`deadline` {month, day, years_before_intake, known_dates}, `english_requirement`, `ielts_min`, `eligible_backgrounds`,
`eligible_nationalities`, `nationality` rule, `source`, `verified_on`, `confidence`, `notes`.
Use short English country names that match `data/regions.json` (e.g. "Czech Republic", "Cote d'Ivoire").

## Finish

```bash
cli.py validate --warnings
.venv/bin/python -m unittest discover tests
cli.py export-schema            # only if you changed planner/models.py
python scripts/sync_skills.py   # only if you changed skills/
```
Summarise what you added or changed, with sources and anything left unverified.
