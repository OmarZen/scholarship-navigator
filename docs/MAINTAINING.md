# Maintainer guide

## 1. Publish the repository

```bash
python scripts/set_repo_owner.py <your-github-user>      # fills badges, links, CODEOWNERS
git add -A && git commit -m "chore: initial public release v2.0.0"
gh repo create <your-github-user>/scholarship-navigator --public --source . --push \
  --description "Find scholarships you can actually win: eligibility, fit scores, missing papers and a dated plan. Works with AI agents (MCP + skills)."
gh repo edit --enable-discussions --enable-issues \
  --add-topic scholarships --add-topic erasmus-mundus --add-topic mcp --add-topic ai-agents \
  --add-topic claude --add-topic study-abroad --add-topic students --add-topic open-data
```

Then on GitHub: **Settings → General → Pull Requests**: allow **squash merging** only and tick
**"Automatically delete head branches"**. **Settings → Code security**: enable **Private vulnerability reporting**,
**Dependabot alerts** and **Secret scanning**.

## 2. Protect `main` (nobody pushes directly)

The rules live in [`.github/rulesets/protect-main.json`](../.github/rulesets/protect-main.json):

| Rule | Effect |
|---|---|
| `pull_request` | every change to `main` must come through a pull request with **1 approval** from a code owner; new pushes dismiss old approvals; all review threads must be resolved |
| `required_status_checks` | CI jobs `test (3.11)`, `test (3.12)` and `hygiene` must pass, on a branch that is up to date with `main` |
| `non_fast_forward` | no force-pushes |
| `deletion` | `main` cannot be deleted |
| `required_linear_history` | clean history (squash or rebase merges) |
| bypass: repository **admins**, mode `pull_request` | you (the admin) still cannot push directly, but you can merge your *own* pull request without a second reviewer, so a solo maintainer is never locked out |

**Option A: one command** (after the first push, with the GitHub CLI logged in):

```bash
gh api --method POST repos/<owner>/scholarship-navigator/rulesets --input .github/rulesets/protect-main.json
gh api repos/<owner>/scholarship-navigator/rulesets          # check it is there
```

**Option B: in the browser.** **Settings → Rules → Rulesets → New ruleset → Import a ruleset** → choose
`.github/rulesets/protect-main.json` → **Create**. Or build it by hand: *New branch ruleset* → name "Protect main" →
Enforcement **Active** → Target **Include default branch** → tick *Restrict deletions*, *Require linear history*,
*Require a pull request before merging* (1 approval, dismiss stale approvals, require review from Code Owners,
require conversation resolution), *Require status checks to pass* (add `test (3.11)`, `test (3.12)`, `hygiene`;
require branches to be up to date), *Block force pushes* → Bypass list: **Repository admin**, "For pull requests
only".

Notes:
- Status checks appear in the picker only after the workflow has run once (push a branch or open a test PR).
- Rulesets are free on public repositories. Private repositories need GitHub Pro / Team.
- When more maintainers join, add them to `.github/CODEOWNERS` (e.g. `/data/ @maintainer-a @maintainer-b`) and raise
  `required_approving_review_count` if you want two reviewers.
- To change the rules later, edit the JSON, then
  `gh api --method PUT repos/<owner>/scholarship-navigator/rulesets/<id> --input .github/rulesets/protect-main.json`.

## 3. Yearly data refresh (every September-October)

Deadlines for the next intake are published in autumn.

```bash
.venv/bin/python cli.py validate --warnings --stale-days 200   # what needs re-checking
```
Work through the warnings with the `scholarship-deadline-verifier` and `scholarship-data-maintainer` skills: update
`known_dates`, program `status`, country lists and `verified_on`, then regenerate the pages:

```bash
python scripts/build_catalog_docs.py && .venv/bin/python scripts/make_readme_assets.py
```

## 4. Releases

1. Update `CHANGELOG.md` and the version in `pyproject.toml`.
2. Merge through a pull request.
3. `gh release create v2.1.0 --generate-notes`.
