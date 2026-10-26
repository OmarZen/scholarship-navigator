# Contributing to Scholarship Navigator

First: thank you. Every scholarship you add, every deadline you correct, every bug you fix helps a student somewhere
apply on time instead of missing out. You don't need to be a developer to help.

- [Ways to contribute](#ways-to-contribute)
- [Your first contribution in 10 minutes](#your-first-contribution-in-10-minutes)
- [Development setup](#development-setup)
- [Data rules (the most important part)](#data-rules-the-most-important-part)
- [Adding a scholarship](#adding-a-scholarship)
- [Adding or updating programs](#adding-or-updating-programs)
- [Code contributions](#code-contributions)
- [Pull request rules](#pull-request-rules)
- [How review works](#how-review-works)

---

## Ways to contribute

| You can... | Skills needed | How |
|---|---|---|
| Report an outdated deadline or wrong rule | none | open a **Data correction** issue with the official link |
| Suggest a scholarship we don't have | none | open a **New scholarship** issue |
| Add a scholarship or program | JSON editing | pull request (guide below) |
| Verify `(est.)` deadlines and `unknown` program statuses | web research | pull request updating `known_dates` / `status` with sources |
| Translate the README or skill instructions | a second language | pull request under `docs/i18n/` |
| Improve scoring, reports, CLI, MCP server | Python | pull request with tests |
| Write guides (essays, visas, countries) | writing | pull request in `data/` or `skills/` |
| Share the project with students who need it | none | ⭐ star it, post it in your student groups |

Good first issues are labelled **`good first issue`**. Unverified deadlines (`cli.py validate --warnings`) are always
a great place to start.

---

## Your first contribution in 10 minutes

1. **Fork** the repository on GitHub (top-right "Fork" button).
2. **Clone your fork** and create a branch. Never work on `main`:
   ```bash
   git clone https://github.com/<your-username>/scholarship-navigator.git
   cd scholarship-navigator
   git checkout -b data/fix-chevening-deadline
   ```
3. **Make your change** (for example, update a `known_dates` entry in `data/scholarships.json`, with its source).
4. **Check it**:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -e ".[mcp]"
   .venv/bin/python cli.py validate --warnings
   .venv/bin/python -m unittest discover tests
   ```
5. **Commit and push**, then open a **pull request** from your branch to `main`:
   ```bash
   git commit -am "data: confirm Chevening 2027/28 deadline (source: chevening.org)"
   git push origin data/fix-chevening-deadline
   ```
6. Fill in the pull request template. A maintainer reviews it, usually within a few days.

Branch names: `data/...` for data, `feat/...` for features, `fix/...` for bugs, `docs/...` for documentation.

---

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[mcp]"          # core + MCP server
.venv/bin/pip install -e ".[mcp,scrape]"   # + live web scraping engines (heavier)
```

| Check | Command |
|---|---|
| Unit tests | `.venv/bin/python -m unittest discover tests` |
| Data validation | `.venv/bin/python cli.py validate --warnings` |
| JSON Schemas up to date | `.venv/bin/python cli.py export-schema` (after changing `planner/models.py`) |
| Skills copies in sync | `python scripts/sync_skills.py` (after changing `skills/`) |
| Catalogue pages up to date | `python scripts/build_catalog_docs.py` (after changing `data/`) |
| README screenshots | `.venv/bin/python scripts/make_readme_assets.py` (optional) |

CI runs all of these on every pull request; a red check blocks merging.

---

## Data rules (the most important part)

People make life decisions based on this data. Please follow these rules strictly.

1. **Official sources only.** The program's own website, a government or embassy page, or the EACEA Erasmus Mundus
   catalogue. Blogs, aggregators and social media posts are *leads* to find the official page, never the source.
2. **Every fact has a source and a date.** Scholarships: `timeline.deadline.source`, `verified_on`,
   `eligibility.rules.nationality.source`, `data_last_reviewed`. Programs: `source`, `verified_on`, `confidence`.
3. **Unknown stays unknown.** Use `null` and explain in `notes`. A wrong date is worse than no date.
4. **Quote, then structure.** Text fields (`eligible_nationalities`, `gpa_requirement`, each document `label`) keep
   the program's own wording. The structured fields (`eligibility.rules`, document `doc` ids) are what the
   matcher uses. They must agree.
5. **No personal data, ever.** Nothing from `output/`, no real candidate profiles, no screenshots with names.
6. **One change, one reason.** Don't mix a data update with a code refactor in the same pull request.

---

## Adding a scholarship

```bash
.venv/bin/python cli.py new-scholarship my-new-scholarship
# → data/custom/drafts/my-new-scholarship.json with every field to fill
```

Fill every `TODO` from the official pages. The field-by-field guide is in
[`skills/scholarship-data-maintainer/SKILL.md`](skills/scholarship-data-maintainer/SKILL.md). The essentials:

- **Nationality rule**: `any`, `include` (only listed countries/regions), `exclude`, or `verify` (list not
  confirmed). Region ids come from `data/regions.json` (`africa`, `dac_oda`, `eu_eea_ch`, `europe`, `latin_america`).
- **Numbers on a 4.0 scale**: `gpa_min` (hard minimum) and `gpa_competitive` (typical winner).
- **Age**: `"under 35"` becomes `"age_under": {"Master": 35}`.
- **Degrees**: any of `Diploma`, `Bachelor`, `Master`, `PhD`, `Postdoc`.
- **Funding**: `Full`, `Partial`, or `Any` when the same scheme gives full *or* partial awards (e.g. 25-100% by
  merit); `Any` is shown as "Full or partial".
- **Women only**: `"gender": "female"` inside `eligibility.rules`.
- **Where scholars study**: `host_countries` / `host_regions`. Add `study_location` only when those can't express
  it: `"home"` (in-country or online from home), `"both"` (your own country or abroad), `"abroad"` (mobility
  required). Candidates who can't travel rely on this, so get it right.
- **Documents**: one entry per required paper, `doc` from `data/document_catalog.json`, `label` = program wording.
- **Deadline**: `month`, `day`, `years_before_intake` (1 when the deadline falls the year before an autumn
  intake), plus `known_dates` like `{"2027": "2027-01-15"}` when officially published.

Validate, then move it into `data/scholarships.json` for your pull request:

```bash
.venv/bin/python cli.py validate --file data/custom/drafts/my-new-scholarship.json --warnings
```

(To use a record only on your own machine, put it in `data/custom/` instead. It is loaded automatically.)

## Adding or updating programs

Programs are the individual masters inside a scheme (Erasmus Mundus Joint Masters, Intra-Africa projects):
`data/programs/erasmus_mundus.json` and `data/programs/intra_africa.json`, schema
[`schemas/program.schema.json`](schemas/program.schema.json). Edit records directly, or import research notes in
bulk:

```bash
python scripts/import_programs.py my-research.json --verified YYYY-MM-DD
```

Always record the host countries and universities, the `status` for the coming intake, and the deadline with its
source.

---

## Code contributions

- Python 3.10+, standard library + `pydantic`, `openpyxl`, `rich`. New dependencies need a good reason; scraping
  dependencies stay optional (`[scrape]`).
- Match the style of the surrounding code: type hints, small functions, docstrings on modules and public functions.
- **Keep scores explainable.** Every point added to a fit or program score needs a human-readable `detail` string
  the user will see.
- **Never break a candidate's workspace.** Files with `generated: false` must never be overwritten; JSON sources of
  truth must stay backwards compatible (add optional fields, don't rename).
- Add or update tests in `tests/` for every behaviour change.
- Agent-facing changes: keep `planner/api.py`, `mcp_server.py` and `cli.py --json` in step, and update the skills
  in `skills/` (then run `scripts/sync_skills.py`).

---

## Pull request rules

`main` is protected. Nobody, including maintainers, pushes to it directly. Every change goes through a pull request
that:

1. comes from a branch (or a fork), never from `main`;
2. passes all CI checks (tests, data validation, skills/catalogue/schema sync);
3. has at least **one approving review** from a code owner (see `.github/CODEOWNERS`);
4. resolves every review conversation;
5. is up to date with `main` before merging (squash merge keeps history clean);
6. for data: links the official source for every changed fact in the description.

Commit messages: start with a type, `data:`, `feat:`, `fix:`, `docs:`, `test:` or `chore:`, followed by a short
description in the present tense.

## How review works

**Every pull request is reviewed by a maintainer before it is merged.** This is enforced by GitHub settings, not just
good intentions:

```text
 you: fork → branch → commit → open PR
                         │
                         ▼
  🤖 automatic:  labels by area (data / code / skills / documentation / translation / tests / ci)
                 welcome message on your first PR
                 CI: tests on Python 3.11 + 3.12 · data validation · skills/catalogue/schema sync · privacy hygiene
                 (for first-time contributors a maintainer approves the first CI run; that's a GitHub safety rule)
                         │
                         ▼
  👀 maintainer review:  sources official and recent? rules match the quoted text? tests added? no personal data?
                         → "Request changes" (you push more commits to the same branch)  or  "Approve"
                         │
                         ▼
  ✅ merge:  squash-merged into main · your branch is deleted · your profile appears in the README contributors wall
```

What the `main` branch requires (GitHub ruleset "Protect main"):

- a pull request: nobody, maintainers included, pushes to `main` directly;
- **1 approving review from a code owner** (`.github/CODEOWNERS`), with stale approvals dismissed after new pushes;
- all review conversations resolved;
- green checks `test (3.11)`, `test (3.12)` and `hygiene`, on a branch that is up to date with `main`;
- linear history (squash merges); no force-pushes; `main` can't be deleted.

Expect friendly questions rather than silent rejections. Pull requests with no activity for 14 days are marked
`stale` and closed 7 days later (you can always reopen them).

### Labels

| Label | Meaning |
|---|---|
| `good first issue` | small, well-defined task: a great first contribution |
| `help wanted` | maintainers would love help with this |
| `data` · `new scholarship` | scholarship / program data; a new record |
| `needs source` | waiting for an official source link before it can be merged |
| `verified` | facts checked against official sources |
| `code` · `skills` · `documentation` · `translation` · `tests` · `ci` | the area a pull request touches (added automatically) |
| `stale` · `pinned` | inactive (closes soon) · never marked stale |

By contributing you agree that your contribution is licensed under the project's [MIT License](LICENSE) and you
follow our [Code of Conduct](CODE_OF_CONDUCT.md).
