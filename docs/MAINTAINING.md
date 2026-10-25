# Maintainer guide

## 1. What is already configured on GitHub

| Area | Setting | Where to change it |
|---|---|---|
| Branch protection | ruleset **"Protect main"**: pull request required, 1 code-owner approval, stale approvals dismissed, conversations resolved, checks `test (3.11)` `test (3.12)` `hygiene` green and up to date, linear history, no force-push, no deletion. Admins may merge their own PRs (bypass "for pull requests only"). | Settings → Rules → Rulesets |
| Reviewers | `.github/CODEOWNERS`: every file is owned by the maintainers listed there | the file itself |
| Merging | squash merge only, PR title/body as the commit message, head branches deleted after merge | Settings → General → Pull Requests |
| Fork PRs | GitHub Actions on PRs from first-time contributors need a maintainer's approval before running; workflows get a read-only token | Settings → Actions → General |
| Security | private vulnerability reporting, Dependabot alerts + security fixes, secret scanning + push protection | Settings → Code security |
| Community | Issues (forms in `.github/ISSUE_TEMPLATE/`), Discussions, PR template, labels, auto-labeling (`.github/labeler.yml`), welcome message for first-time contributors, stale bot | Settings → General → Features; `.github/` |
| Discovery | description + 12 topics | repo home page → ⚙️ next to "About" |

Still manual (no API): **Settings → General → Social preview → Upload** `docs/assets/social-preview.png`. This is the
image shown when the repo link is shared on WhatsApp, X, LinkedIn or Facebook.

## 2. Reviewing a community pull request

1. **Read the PR description and checklist.** For data changes, every changed fact needs an official source link and
   a verification date. If one is missing, add the `needs source` label and ask for it.
2. **First-time contributor?** Their CI run waits for you: open the PR → "Approve and run workflows". Skim the
   diff first and never approve a run that changes `.github/workflows/` in a suspicious way.
3. **Check it out locally when it touches code or many records:**
   ```bash
   gh pr checkout <number>
   .venv/bin/python cli.py validate --warnings
   .venv/bin/python -m unittest discover tests
   ```
4. **Verify the facts.** Open 1-2 of the cited official pages and spot-check deadlines, country lists and amounts.
   Structured rules (`eligibility.rules`, document ids) must agree with the quoted text.
5. **Review on GitHub:** *Files changed* → comment on lines → **Request changes** (contributor pushes more commits)
   or **Approve**. Add `verified` to data PRs you checked.
6. **Merge:** "Squash and merge" with a clear title (`data: confirm EDISS 2027 deadline`). The branch is deleted
   automatically and the contributor appears in the README contributors wall.

Your own changes: branch → PR → wait for the checks → `gh pr merge --squash --admin` (the admin bypass lets you merge
without a second reviewer, but never lets anyone push to `main` directly).

## 3. Adding more maintainers

1. Settings → Collaborators → **Add people** → role **Maintain** (or **Write** for reviewers who shouldn't change
   settings).
2. Add them to `.github/CODEOWNERS`, e.g. `/data/ @OmarZen @new-maintainer`, so they can approve data PRs.
3. With several maintainers you can raise `required_approving_review_count` to 2 in the ruleset.

## 4. Changing the rules

The ruleset definition is versioned in [`.github/rulesets/protect-main.json`](../.github/rulesets/protect-main.json).
Edit it in a PR, then apply:

```bash
gh api repos/OmarZen/scholarship-navigator/rulesets --jq '.[] | "\(.id) \(.name)"'    # find the id
gh api --method PUT repos/OmarZen/scholarship-navigator/rulesets/<id> --input .github/rulesets/protect-main.json
```

## 5. Yearly data refresh (every September-October)

```bash
.venv/bin/python cli.py validate --warnings --stale-days 200   # what needs re-checking
```
Work through the warnings with the `scholarship-deadline-verifier` and `scholarship-data-maintainer` skills: update
`known_dates`, program `status`, country lists and `verified_on`, then regenerate the pages:

```bash
python scripts/build_catalog_docs.py && .venv/bin/python scripts/make_readme_assets.py
```
Open a "good first issue" for each batch of unverified records: they are the best entry point for new contributors.

## 6. Releases

1. Update `CHANGELOG.md` and the version in `pyproject.toml` (in a PR).
2. After merging: `gh release create v2.1.0 --generate-notes`.
