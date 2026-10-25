## What does this change?

<!-- One or two sentences. Link the issue it closes, e.g. "Closes #12". -->

## Type

- [ ] 📅 Data (scholarship / program / deadline / rule)
- [ ] ✨ Feature
- [ ] 🐛 Fix
- [ ] 📝 Docs / skills
- [ ] 🧹 Chore

## For data changes

| Record | Field(s) changed | Official source | Checked on |
|---|---|---|---|
|  |  |  |  |

## Checklist

- [ ] My branch is not `main`, and this PR targets `main`
- [ ] `.venv/bin/python -m unittest discover tests` passes
- [ ] `.venv/bin/python cli.py validate --warnings` shows no errors
- [ ] Every changed fact links an official source and a verification date
- [ ] No personal data (nothing from `output/`, no real profiles or documents)
- [ ] If I changed `skills/`, `planner/models.py` or `data/`: I ran `scripts/sync_skills.py`, `cli.py export-schema`,
      `scripts/build_catalog_docs.py` as needed
