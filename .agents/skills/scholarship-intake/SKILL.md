---
name: scholarship-intake
description: >-
  Interview a person about their background and goals and turn the answers into a scholarship profile and workspace.
  Use when someone wants to start finding scholarships, says "help me find a scholarship", shares their CV, grades or
  test scores, or when a workspace is missing or has "Needs Check" gaps (missing date of birth, graduation year,
  English test date...). Works in any language (Arabic, French, English...).
---

# Scholarship intake interview

Goal: a complete `profile.json` (schema: `schemas/candidate_profile.schema.json`, example:
`examples/sample_candidate_full.json`) and a built workspace, without asking for anything twice.

## Before asking anything

- If `output/<name>/profile/profile.json` exists, read it and `PROFILE.md` ("Missing profile information") and only
  ask for what is missing.
- If the user shared a CV, transcript or certificate, extract what you can first and confirm it with them.

## Ask in small groups (3-5 questions at a time), in the user's language

1. **Identity**: full name · nationality (citizenship) · country of residence · date of birth (age limits matter) ·
   gender only if they are happy to share it (it is used only for awards reserved for women).
2. **Education**: highest degree and university · graduation year · GPA **and its scale** (e.g. 3.4/4, 82/100,
   "Very good") · class rank if known · thesis/project title.
3. **Target**: degree (Diploma / Bachelor / Master / PhD / Postdoc) · field + 3-5 keywords (e.g. "embedded systems,
   machine learning") · **can they travel?** study in their own country only, abroad only, or both · target
   countries or worldwide · intake year · funding needed (Full / Partial / Any).
4. **Languages**: English test, overall score, test date, lowest band · other languages with CEFR level.
5. **Experience**: years of full-time work after graduating · still employed? · job title / employer ·
   publications.
6. **Impact**: 2-3 leadership moments with numbers · awards · volunteering · career goal · the problem at home they
   want to solve · do they accept a 2-year return-home obligation?
7. **Papers already held**: passport (+ expiry) · degree certificate · transcript · CV · how many referees agreed
   (academic / professional) · employment letter · police clearance · medical certificate · translations/apostille.

## Converting answers

- GPA: keep the original number and scale (`gpa`, `gpa_scale`); the tool normalizes. For letter grades, ask for
  the numeric equivalent on the transcript.
- Work experience: count full-time months after the first degree, as years (e.g. 2.5).
- Where to study → `study_location`: `"home"` if they cannot or will not leave the country they live in (for
  example family reasons), `"abroad"` if they only want to go abroad, `"both"` (default) otherwise. With `"home"`,
  leave `target_countries` empty. Ask this gently and never push someone to travel.
- `gender`: `"female"`, `"male"` or `"other"`; leave it out if they prefer not to say (women-only awards then show
  as Needs Check).
- Papers go in `"documents": [{"doc_id": "passport", "status": "have", "expires": "2030-05-01"}, ...]` using ids from
  `data/document_catalog.json` (`cli.py docs list` after the first build). Recommendation letters use
  `"count_ready"`.
- Leave unknown fields out. Never guess dates, scores or nationality.

## Create the workspace

Save the JSON (e.g. `profiles/<name>.json`, outside the repo if you are unsure) and run
`cli.py init --profile <file> --json`, or call the MCP tool `create_workspace`. Then show the user:
1. how many scholarships they are eligible for, and the top of the shortlist (fit, readiness, deadline),
2. anything marked Needs Check and the one fact that would resolve it,
3. the "Start now" actions.

For a returning user, update `profile/profile.json` and run `cli.py build` instead of `init`.

## Privacy

Explain once that everything stays in their local `output/` folder. Don't ask for passport numbers, national ID
numbers or bank details; the tool never needs them.
