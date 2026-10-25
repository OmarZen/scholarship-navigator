# How scoring works

## 1. Eligibility gates (pass / fail / unknown / warn)

Checked in this order: degree level · program status (discontinued → fail) · nationality (official country lists,
verified 2026-10) · residence · age (`age_under` hard limits, `age_under_preferred` soft) · degree recency · work
experience (counts months until the deadline when `currently_employed`) · return obligation · restricted field ·
teaching language (e.g. Spanish for Fundación Carolina).

- Any **fail** → `Ineligible` (score 0, reason shown).
- Any **unknown** → `Needs Check`. Every unknown has a `fix` (usually a missing profile field). Never treat it as a pass.
- **warn** → eligible, with a caution (e.g. one year from the age limit).

## 2. Fit score (0-100)

Weighted parts, normalized over the parts that apply:

| Part | Weight | Measures |
|---|---|---|
| Academic record | 25 | Normalized GPA vs the scholarship's `gpa_min` and `gpa_competitive` (full marks need competitive + 0.2; top-10% class rank adds a bonus) |
| Language | 20 | IELTS-equivalent (TOEFL/Duolingo/PTE converted) vs `ielts_min`, sub-band rule, or the required other language |
| Experience | 15 | Required years met, or a mild bonus when not required (not used for Bachelor targets) |
| Field fit | 15 | Candidate field groups/keywords vs the scholarship's priority or restricted fields |
| Leadership & profile | 12 (20 for leadership-heavy awards) | Leadership, documented STAR stories, awards, volunteering |
| Research | 10-15 for PhD/Postdoc, 5 for research-heavy awards | Publications, thesis |
| Preferences | 10 | Host country in target list (6) · funding level matches (4) |

High match ≥ 80 · moderate ≥ 62 · below that: reach / low match.

## 3. Readiness (%)

Average over required papers at the application stage (optional and after-submission papers excluded):
`have` = 1 · `partial` = share secured (e.g. 1 of 2 letters = 0.5) · `in_progress` = 0.5 · `missing` = 0 ·
`not_applicable` = 1 · a paper expiring before the deadline counts at most 0.5. Alternatives count (e.g. an
English-medium letter instead of IELTS where accepted). The Excel file uses the same formula live.

## 4. Timeline status

Compares days left with the longest lead time among missing papers (data/document_catalog.json) plus a 7-day buffer:
`Ready` · `On track` (≥ 14 days slack) · `Tight` · `At risk` (only possible if fast) · `Not feasible this cycle` ·
`Deadline passed` (shows the next cycle's estimated date) · `Deadline unknown`.

## 5. Priority and shortlist

`priority = 0.55 × fit + 0.20 × readiness + 10 × funding value (full 1, partial 0.5) + 15 × time factor`, × 0.9 if
Needs Check. The shortlist is the top open, eligible scholarships, plus any the candidate tracks, minus Skipped/Rejected.

## 6. Program score (Erasmus Mundus masters, Intra-Africa projects)

`field relevance 50` (strong keyword match 50, related field group 25-35, none 5) · `host country 20` (in target list,
or 8 if same region) · `language 15` · `funding status 15` (open 15, upcoming 12, unknown 8, self-funded only 3).
Discontinued programs, wrong degree level or excluded nationality → not eligible. Candidates can apply to at most
3 Erasmus Mundus programs per year; chosen programs drive the Erasmus deadline.

## 7. Portfolio win chance

`cli.py portfolio` uses fixed base rates per tier adjusted by fit. It is a rough heuristic, not admission
statistics: say so whenever you quote it.
