---
name: scholarship-essay-writer
description: >-
  Write, improve and review scholarship essays, motivation letters, personal statements, study plans, research
  proposals, development-impact statements and referee requests inside the candidate's workspace. Use when someone
  asks to write or fix a Chevening essay, an Erasmus Mundus or DAAD motivation letter, a Swedish Institute statement,
  a Fulbright personal statement, a statement of purpose, or wants feedback on a draft.
---

# Essay & letter writer

Every shortlisted scholarship folder already contains drafts with the program's own wording, word limit, structure
and the candidate's facts:
`output/<name>/scholarships/<id>/essays/*.md`, `letters/*.md`, `recommendations/referee_requests.md`.

## Before writing

1. Read `PROFILE.md`, `profile/story_bank.md` and the scholarship's `SCHOLARSHIP.md` (strategy, what it pays,
   who it is for).
2. Open the draft file. Keep its front matter; write under `## Draft`.
3. If the story bank has no material for the prompt, **interview the candidate** for one concrete story (situation,
   task, actions, results with numbers) and add it to `profile/story_bank.md` first. Never invent facts, numbers,
   employers or awards.

## Writing rules

- Use STAR: Situation (1-2 sentences) · Task · Action (most words, "I" not "we") · Result (numbers) · the link to
  this scholarship's mission and the candidate's goal.
- Respect the word limit (front matter `word_limit`). Aim for 90-100% of it.
- Tailor every letter: name the program's universities, modules, labs or mobility path. Never reuse a letter
  unchanged across scholarships. Erasmus Mundus has one letter per chosen program
  (`letters/motivation_letter_<program>.md`).
- Government awards (Chevening, Fulbright, DAAD EPOS, Australia Awards, SI) weigh the return-home impact: be
  concrete about the problem at home (`home_country_problem`) and the first role after graduating.
- Plain, specific language. No clichés ("since I was a child", "passion", "dream").
- Write in the language the program requires (usually English), even if you chat with the candidate in Arabic.

## Program notes

| Scholarship | Pieces | Notes |
|---|---|---|
| Chevening | 4 × 500 words: leadership, networking, studying in the UK, career plan | concrete influence; 3 UK courses that connect logically |
| Erasmus Mundus | motivation letter per program | why this consortium and mobility path; background fit |
| DAAD EPOS / Helmut-Schmidt | hand-signed motivation letter (≤ 2 pages) | development impact; employer letter matters |
| Swedish Institute | motivation + SDG statements in the portal; SI CV template | leadership with SDG link; strict templates |
| Fulbright | personal statement + study objectives | personal story + rigorous academic plan |
| Australia Awards / Manaaki | development impact statement | link to the country's priority sectors |

## Review loop

1. `cli.py review-essay --file <draft.md> --type <type>` (types: chevening_leadership, chevening_networking,
   chevening_study_uk, chevening_career, fulbright_personal, fulbright_study, sop). Or MCP `review_essay`.
2. Fix the flagged issues and re-run until readiness ≥ 80.
3. Set `status: review` while the candidate checks it, then `status: final`. On the next `cli.py build` the paper
   counts as ready.

## Referee requests

`recommendations/referee_requests.md` has an email template. Generate a brag sheet with
`cli.py draft-lor --name "<referee>" --title "<title>" --org "<org>" --brag-sheet`. Ask referees at least 4 weeks
before the deadline; record secured letters with `cli.py docs set lor_academic --status have --count N`.
