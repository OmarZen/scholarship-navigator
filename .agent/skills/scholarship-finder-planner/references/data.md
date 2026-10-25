# Data files

| File | Contents |
|---|---|
| `data/scholarships.json` | 35 scholarships: coverage, published eligibility text, structured `eligibility.rules`, `documents` (paper ids), `timeline.deadline` (pattern + `known_dates` + source), `host_countries`, `tier`, `program_status` |
| `data/programs/*.json` | individual programs per scheme (Erasmus Mundus masters, Intra-Africa projects): fields, host countries, universities, status, deadlines, English requirement |
| `data/custom/*.json` | local scholarship additions (same schema as scholarships.json); drafts in `data/custom/drafts/` are not loaded |
| `data/document_catalog.json` | every paper type: lead time, validity, how to get it, folder |
| `data/regions.json` | country groups (`africa`, `dac_oda`, `eu`, `eu_eea_ch`, `europe`, `latin_america`) and name aliases (e.g. "Egyptian" → Egypt) |
| `data/countries.json` | 18-country study & work guides |
| `data/document_templates.json` | SOP, CV, LOR and research-proposal frameworks used by drafts |
| `schemas/*.schema.json` | JSON Schemas for candidate profiles, papers, application state, scholarships, programs |

## Common paper ids

passport · national_id · passport_photo · birth_certificate · proof_of_residence · degree_certificate · transcript ·
secondary_certificate · course_descriptions · credential_evaluation · english_test · english_moi_letter ·
other_language_test · standardized_test · employment_certificate · lor_academic · lor_professional ·
lor_leadership · lor_any · cv · cv_europass · writing_sample · awards_certificates · income_documents ·
medical_certificate · police_clearance · motivation_letter · personal_statement · essay · study_plan ·
research_proposal · development_impact_plan · application_form · university_choices · university_application ·
admission_letter · supervisor_acceptance · nomination_letter. Full list: `cli.py docs list` or the catalog file.

## How a deadline is chosen

1. Date the candidate confirmed (`cli.py deadline`, stored in `status.json`).
2. Earliest upcoming deadline of the candidate's chosen programs (Erasmus Mundus).
3. Published date for the intake year (`timeline.deadline.known_dates["2027"]`).
4. Usual pattern (`month`, `day`, `years_before_intake`) → shown as **(est.)**.

If the date has passed, the scholarship moves to "closed for this cycle" with the next cycle's estimate.
