---
name: scholarship-program-finder
description: >-
  Find specific Erasmus Mundus Joint Master programs (and Intra-Africa mobility projects) that fit a person's field
  and target countries: where each program is taught (host countries and universities), its status, scholarship
  availability, deadline and English requirement. Use when someone asks "which Erasmus Mundus masters fit me",
  wants programs in robotics / data science / energy / photonics..., wants programs in a given country, or needs to
  pick their 3 Erasmus Mundus applications.
---

# Program finder (Erasmus Mundus & Intra-Africa)

Erasmus Mundus is one scholarship scheme made of many separate joint masters. Each consortium has its own
universities, countries, deadline and requirements. Candidates may apply to **at most 3 programs per year**.
Data: `data/programs/*.json` (host countries, universities, status, deadlines, verified dates and sources).

## Find programs

```bash
cli.py programs                                   # ranked for the candidate's workspace/profile
cli.py programs --field robotics --country Spain,France
cli.py programs --scheme intra-africa-mobility    # African mobility projects (Africa-only eligibility)
cli.py programs --all --json                      # include closed / discontinued / ineligible, machine-readable
```
MCP: `find_programs(profile=..., field=..., countries=[...])`.

Score = field match 50 + host country 20 + language 15 + funding status 15 (see the main skill's
`references/scoring.md`). Not eligible: discontinued programs, wrong degree level, or nationality rules
(Intra-Africa projects are for African nationals).

## Help the user choose (max 3)

Present 5-8 options as a short table: program, where you study (countries + universities), field match, deadline,
status. Then discuss:
1. **Field fit**: does their bachelor match the program's required background (`eligible_backgrounds`)?
2. **Countries**: the mobility path (e.g. semester 1 in Spain, 2 in France, thesis in Italy) vs their preferences.
3. **Timing**: deadlines are usually December to February. Earlier deadlines need earlier documents.
4. **Status**: prefer "open" or "upcoming" with scholarships available. "self_funded_only" means no Erasmus grant.

Record choices: `cli.py programs --choose <id>` (or MCP `choose_program`). This:
- makes the Erasmus Mundus deadline follow the earliest chosen program,
- creates `scholarships/erasmus-mundus/letters/motivation_letter_<id>.md`, tailored to that consortium.

## Always

- Program data changes every year. If `verified_on` is old, or status/deadline is unknown, check the program's
  website (use `scholarship-deadline-verifier`) before the user relies on it.
- The official catalogue of all current programs is
  https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en. If the user's field has no good match
  here, search it and add programs with `scholarship-data-maintainer`.
