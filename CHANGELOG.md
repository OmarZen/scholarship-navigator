# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-10-26

### Added
- **Study at home or abroad.** New profile field `study_location` (`home` = study in your own country without
  travelling, `abroad`, `both` by default) with a *Study location* eligibility check, `cli.py location`,
  `match --location`, `list --nationality X --location home`, and the MCP tool `set_study_location`. Where an award
  lets you study is derived from its host countries (KAUST is "home" for Saudis), or set with the new scholarship
  field `study_location` for mobility schemes (Erasmus Mundus, Intra-Africa) and in-country programs.
- **Diploma** degree level, and a **gender** rule for awards reserved for women (`gender` in the profile is optional
  and used only for those awards).
- **68 new scholarships (103 in total)**, researched from official sources in October 2026: Commonwealth, Clarendon,
  Knight-Hennessy, Heinrich Böll, Deutschlandstipendium, DAAD doctoral and In-Country/In-Region, Schwarzman, Yenching,
  JJ/WBGSP, ADB-Japan, ICCR, KNB, Malaysia, Brunei, HBKU, Khalifa, Pan African University, AIMS, MEXT technical
  colleges, GKS Associate, ICTP Diploma, AMCI, AAUW, IAEA MSCFP, Russia, Mexico, Aga Khan, JISP, Bolashak, Saudi
  Custodian, TÜBİTAK 2210/2211, LPDP, PTDF, SECIHTI, Becas Chile, and 25 Egypt-related awards (Future Scholars,
  Zewail City, AUC, Nile University, Sawiris, E-JUST, ASRT, ITI, DEPI, missions, Onsi Sawiris, British Council Women
  in STEM, GREAT, Tahtawi, Al-Azhar, Study in Egypt...). Ended programs that people still ask about (USAID Egypt,
  OWSD PhD) are kept as discontinued with an explanation.
- `docs/AI_TOOLS.md`: step-by-step setup for Claude Code, the Claude app, Codex, GitHub Copilot, Cursor, Gemini CLI,
  Windsurf and Antigravity; `scripts/install_skills.py` installs the skills for any of them and prints the MCP
  settings; `GEMINI.md`.
- README contributors table refreshed by `scripts/update_contributors.py` and a weekly workflow.

### Changed
- Skills are mirrored to `.agents/skills/` (read by Codex, Copilot, Cursor, Gemini CLI, Windsurf, Antigravity)
  instead of `.agent/skills/`.
- Funding `Any` means a scheme gives full or partial awards and is shown as "Full or partial".
- SINGA now excludes Singapore citizens and Master Mind excludes Russian nationals (official rules); Master Mind is
  marked as under review for 2027-28.
- Star history chart uses the canonical lowercase repository URL (the mixed-case one now redirects, which broke the
  image on GitHub) and has a dark-mode version.

## [2.0.0] - 2026-10-25

### Added
- **Eligibility engine** with pass / fail / needs-check gates: nationality (official country lists for 16 programs,
  OECD DAC list), residence, age, degree recency, work experience, field restrictions, return obligation, teaching
  language.
- **Fit score (0-100)** with a visible per-part breakdown, and **readiness %** from the papers a candidate holds.
- **Document catalog** of 47 standard paper types with lead times, validity and how to obtain them; per-scholarship
  missing-paper lists with start-by dates.
- **Dated action plan** scheduled backwards from deadlines; deadlines resolved as confirmed / published / estimated.
- **Program finder**: 56 Erasmus Mundus Joint Masters and Intra-Africa projects with host countries, universities,
  status and 2027 deadlines; choose up to 3 and get tailored motivation-letter drafts.
- **Candidate workspace** (`output/<name>/`) with `AGENTS.md`, `INDEX.md`, `PROFILE.md`, `manifest.json`, one folder per
  scholarship, essay/letter templates, and reports.
- **Excel tracker** with live readiness formulas and a `sync` command to import edits; HTML report; `.ics` calendar with
  "start by" reminders.
- **AI agent support**: 7 skills (`skills/`, mirrored for Claude Code and Antigravity), `AGENTS.md`, `CLAUDE.md`, an
  MCP server with 15 tools, and `--json` output on the main CLI commands.
- Contributor tooling: `validate`, `export-schema`, `new-scholarship`, `scripts/import_programs.py`, generated
  catalogue pages, CI workflow.

### Changed
- Deadlines, nationality lists and program statuses re-verified against official sources (October 2026): e.g.
  Chevening 2027/28 closed 6 Oct 2026, Vanier CGS discontinued, Global Rhodes suspended, Ernst Mach moved to 1 Dec.
- Scraping dependencies are optional (`pip install -e ".[scrape]"`).

## [1.0.0]

- Initial release: 34 scholarships, keyword matching, Excel and HTML reports, country guides, essay and letter helpers,
  scraping engines.
