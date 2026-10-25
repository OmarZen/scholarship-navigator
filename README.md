<div align="center">

# 🎓 Scholarship Navigator

### Find the scholarships you can actually win, and never miss a deadline again.

Eligibility checks · match scores · missing papers · a dated plan · essay drafts<br>
**Free, open source, and built to work inside your AI assistant.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![Tests](https://github.com/OmarZen/scholarship-navigator/actions/workflows/tests.yml/badge.svg)](https://github.com/OmarZen/scholarship-navigator/actions/workflows/tests.yml)
[![MCP ready](https://img.shields.io/badge/MCP-ready-8A2BE2.svg)](#-use-it-with-your-ai-assistant)
[![Scholarships](https://img.shields.io/badge/scholarships-35-F59E0B.svg)](docs/SCHOLARSHIPS.md)
[![Programs](https://img.shields.io/badge/Erasmus%20Mundus%20%26%20Intra--Africa%20programs-56-F59E0B.svg)](docs/PROGRAMS.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[![GitHub stars](https://img.shields.io/github/stars/OmarZen/scholarship-navigator?style=social)](https://github.com/OmarZen/scholarship-navigator/stargazers)
[![Contributors](https://img.shields.io/github/contributors/OmarZen/scholarship-navigator?color=0E8A16)](https://github.com/OmarZen/scholarship-navigator/graphs/contributors)
[![Last commit](https://img.shields.io/github/last-commit/OmarZen/scholarship-navigator?color=1D76DB)](https://github.com/OmarZen/scholarship-navigator/commits/main)
[![Good first issues](https://img.shields.io/github/issues/OmarZen/scholarship-navigator/good%20first%20issue?label=good%20first%20issues&color=7057ff)](https://github.com/OmarZen/scholarship-navigator/issues?q=is%3Aopen+label%3A%22good+first+issue%22)

[**Quick start**](#-quick-start) · [**Use with AI**](#-use-it-with-your-ai-assistant) · [**Features**](#-features) · [**What's covered**](#-whats-covered) · [**Contribute**](#-contributing) · [**العربية**](#-بالعربي)

<img src="docs/assets/report.png" alt="Scholarship Navigator report: shortlist with fit and readiness scores" width="900">

</div>

---

## The problem

Every year, thousands of strong students miss fully funded scholarships. Usually they were good enough. What went
wrong was something else:

- they found out about the scholarship **after the deadline**;
- they spent weeks on an application they were **never eligible for** (wrong nationality, age or field);
- they were **one paper short**: a missing recommendation letter, an expired IELTS, a transcript without apostille;
- the information was spread across **hundreds of outdated blog posts** and WhatsApp forwards.

**Scholarship Navigator fixes that.** Tell it about yourself once. It checks every rule, scores how well you
match, lists exactly which papers you're missing, and builds a plan with real dates, backwards from each deadline.

---

## ✨ What it looks like

> **You:** I'm Egyptian, BSc in electronics engineering, GPA 3.58/4, IELTS 7.0, 3 years of work. I want a fully
> funded master's in AI or embedded systems in Europe, starting 2027.
>
> **Your AI assistant (using Scholarship Navigator):**
> - ✅ You're eligible for **22 of 35** scholarships. ❌ 13 aren't open to you, and here's why (nationality list, age limit, field).
> - 🥇 **Erasmus Mundus**: fit **98/100**, papers **56%** ready, deadline **15 Jan 2027** (estimated, verify). Start your motivation letter by **9 Dec**.
> - 🧭 Programs that fit you: **DEAI** (Belgium · Spain · Austria · France · Italy), **EDISS** (Finland · Sweden · Italy · Spain), **EMINENT**. Pick up to 3.
> - ⏰ **Chevening already closed** on 6 Oct 2026. Next round ≈ Oct 2027.
> - 📄 Missing papers: 2nd academic reference, Europass CV, proof of residence, medical certificate.
> - 📁 Everything is saved in `output/ahmed-mansour/`: one folder per scholarship, essay drafts, an Excel tracker and a calendar.

That's a real run on the demo profile in [`examples/sample_candidate_full.json`](examples/sample_candidate_full.json).

---

## 🆚 Why not just a list, or just a chatbot?

| | Scholarship lists & blogs | Asking a chatbot | **Scholarship Navigator** |
|---|:---:|:---:|:---:|
| Tells you if **you** are eligible, rule by rule | ❌ | ⚠️ guesses | ✅ official country lists, age, degree, experience, field |
| A score, and **why** | ❌ | ❌ | ✅ 0-100 with a visible breakdown |
| Exactly which **papers** you're missing, and when to start | ❌ | ⚠️ generic | ✅ 47 paper types with lead times |
| Deadlines with **source and verification date** | ⚠️ often stale | ❌ training-data dates | ✅ confirmed / published / estimated |
| **Remembers you** across sessions | ❌ | ❌ | ✅ personal workspace |
| Drafts tailored to **each** program | ❌ | ⚠️ | ✅ the program's own prompts and word limits |
| Excel tracker, HTML report, calendar | ❌ | ❌ | ✅ |
| Free, private, open source | varies | ❌ | ✅ runs on your computer |

---

## 🚀 Quick start

```bash
git clone https://github.com/OmarZen/scholarship-navigator.git
cd scholarship-navigator
python3 -m venv .venv && .venv/bin/pip install -e ".[mcp]"
```

Then either **talk to your AI assistant** in this folder (next section), or run the interview yourself:

```bash
.venv/bin/python cli.py assess        # answers a few questions → builds output/<your-name>/
```

Or copy [`sample_candidate.json`](sample_candidate.json) (dummy data showing every field), fill in your own details
and run `.venv/bin/python cli.py init --profile my_profile.json`.

Open `output/<your-name>/INDEX.md` and `reports/scholarship_tracker.xlsx`. That's it.

---

## 🤖 Use it with your AI assistant

Scholarship Navigator ships with **7 agent skills**, an **MCP server** with 15 tools, and an `AGENTS.md`, so any
modern assistant knows how to use it.

| Assistant | Setup |
|---|---|
| **Claude Code** | open the folder: skills in `.claude/skills/` and the MCP server in `.mcp.json` load automatically |
| **Claude Desktop · Cursor · Windsurf** | add the MCP server (below) |
| **Codex · Gemini CLI · GitHub Copilot** | read `AGENTS.md` automatically |
| **Antigravity** | skills in `.agent/skills/` |

```json
{
  "mcpServers": {
    "scholarship-navigator": {
      "command": "/path/to/scholarship-navigator/.venv/bin/python",
      "args": ["/path/to/scholarship-navigator/mcp_server.py"]
    }
  }
}
```

Then just ask, in any language:

```text
"Help me find a fully funded master's scholarship. Interview me first."
"Which Erasmus Mundus programs fit a civil engineer who wants Spain or Portugal?"
"What should I do this week for my applications?"
"Write my Chevening leadership essay from my story bank."
"ساعدني ألاقي منحة ماجستير ممولة بالكامل في أوروبا"
```

| Skill | What it does |
|---|---|
| 🧭 `scholarship-finder-planner` | the main entry: matching, scores, missing papers, plan, reports |
| 🗣️ `scholarship-intake` | interviews you (in your language) and builds your profile |
| 🎯 `scholarship-program-finder` | picks Erasmus Mundus / Intra-Africa programs by field and country |
| ✍️ `scholarship-essay-writer` | essays, motivation letters, referee requests, with a review loop |
| 🔎 `scholarship-deadline-verifier` | turns estimated deadlines into verified facts |
| 📆 `scholarship-progress-coach` | weekly check-ins: what's due, what's done |
| 🛠️ `scholarship-data-maintainer` | adds and updates scholarships with official sources |

---

## 🧩 Features

| | |
|---|---|
| ✅ **Eligibility engine** | nationality (official lists, OECD DAC list), residence, age, degree level, degree recency, work experience, restricted fields, return-home obligations, teaching language. Missing info → *Needs Check* with the exact fix. |
| 📊 **Fit score 0-100** | academic record vs each scholarship's minimum *and* competitive level, language (TOEFL / Duolingo / PTE converted), experience, field, leadership, research, your preferences. Every point is explained. |
| 📄 **Missing papers** | what you have, what's missing, how long each paper takes, when to start, and expiry checks (e.g. an IELTS that expires before the deadline). |
| 🗓️ **Dated action plan** | scheduled backwards from deadlines; shared papers become one task; overdue items flagged. |
| 🧭 **Program finder** | 56 Erasmus Mundus and Intra-Africa programs with host countries, universities, status and 2027 deadlines; choose 3, get tailored letters. |
| 📁 **Personal workspace** | one folder per scholarship with essay and letter drafts that use the program's own prompts; your work is never overwritten. |
| 📈 **Excel tracker** | dashboard, ranked matches, one sheet per scholarship, live readiness formulas, `sync` your edits back. |
| 🌐 **HTML report + 📅 calendar** | offline interactive report and an `.ics` file with deadline and "start by" reminders. |
| ✍️ **Writing helpers** | STAR essay review, supervisor cold emails, recommendation-letter drafts and brag sheets, fee-waiver emails. |
| 🌍 **Life-after-award guides** | funding-gap and blocked-account calculator, credential recognition and apostille, visa and arrival checklists, study and work rules for 18 countries. |

<details>
<summary><b>📸 More screenshots</b></summary>

**Excel dashboard**

<img src="docs/assets/dashboard.png" alt="Excel dashboard with shortlist and next actions" width="900">

**`cli.py match`**

<img src="docs/assets/terminal-match.svg" alt="Terminal: ranked scholarship matches" width="900">

**`cli.py programs`**

<img src="docs/assets/terminal-programs.svg" alt="Terminal: Erasmus Mundus programs that fit the profile" width="900">

</details>

---

## 🧠 How it works

```mermaid
flowchart LR
    A["🗣️ You or your AI assistant<br/>tell your story once"] --> B["👤 profile.json<br/>+ papers you hold"]
    B --> C{"✅ Eligibility gates<br/>nationality · age · degree<br/>experience · field"}
    C -- "not eligible" --> X["❌ shown with the reason"]
    C -- "eligible / needs check" --> D["📊 Fit 0-100<br/>📄 Readiness %"]
    D --> E["🗓️ Dated plan<br/>backwards from deadlines"]
    E --> F["📁 Your workspace<br/>briefs · drafts · Excel · HTML · calendar"]
    F -. "you add papers, finish drafts" .-> B
```

| Step | Measures | Result |
|---|---|---|
| **Eligibility** | hard rules | Eligible · Needs Check · Ineligible |
| **Fit** | academic, language, experience, field, leadership, research, preferences | High ≥ 80 · Moderate ≥ 62 |
| **Readiness** | share of required papers you hold | updates live |
| **Timeline** | days left vs how long the missing papers take | On track · Tight · At risk · Not feasible · Passed |
| **Priority** | 55% fit + 20% readiness + funding + time left | ranks your shortlist |

Full details: [scoring reference](skills/scholarship-finder-planner/references/scoring.md).

---

## 📚 What's covered

**35 scholarships** in 28 countries plus multi-country schemes ([full table](docs/SCHOLARSHIPS.md)):
Chevening · Gates Cambridge · Rhodes · Erasmus Mundus · DAAD EPOS · DAAD Helmut-Schmidt · Eiffel ·
Stipendium Hungaricum · Swedish Institute · Danish Government · Finland · Italy MAECI & DSU · Ireland GOI-IES ·
NL Scholarship · VLIR-UOS · Master Mind · Ernst Mach · Czech Government · NAWA Banach · Fundación Carolina ·
Swiss Excellence · Fulbright · Vanier · Australia Awards · Manaaki NZ · MEXT · GKS · CSC · Taiwan ICDF ·
Türkiye Burslari · MBZUAI · KAUST · SINGA · Mastercard Foundation · Intra-Africa Mobility.

**56 programs** taught in **37 host countries** ([full table](docs/PROGRAMS.md)): Erasmus Mundus Joint Masters in
engineering, energy, AI & data, cybersecurity, robotics, photonics, quantum, materials, nuclear, agriculture,
design and more, plus Intra-Africa mobility projects. Each lists its universities, status, 2027 deadline and
English requirement.

**Plus:** 47 paper types · study and work guides for 18 countries · credential recognition (uni-assist, CIMEA, WES,
apostille) · visa and housing checklists.

Every deadline, country list and program status carries its **official source and verification date** (last full
review: October 2026).

---

## 🗂️ Your workspace

```text
output/<your-name>/
├── INDEX.md            ← start here: shortlist, next actions, missing papers, programs that fit you
├── PROFILE.md          ← who you are, papers on file, missing profile info
├── AGENTS.md           ← rules any AI assistant follows in this folder
├── profile/            ← profile.json · documents.json · story_bank.md · identity/ academic/ language/ ...
├── scholarships/
│   └── erasmus-mundus/ ← SCHOLARSHIP.md · status.json · essays/ · letters/ · recommendations/ · forms/ · submitted/
└── reports/            ← scholarship_tracker.xlsx · scholarship_report.html · deadlines.ics · action_plan.md
```

<details>
<summary><b>🛠️ All commands</b></summary>

| Command | Purpose |
|---|---|
| `assess` · `init --profile F` · `build` | create or refresh your workspace |
| `match [--details N] [--json]` | eligibility, fit breakdown and readiness for every scholarship |
| `programs [--field robotics] [--country Spain,France] [--choose ID]` | Erasmus Mundus / Intra-Africa program finder |
| `gaps` · `docs list` · `docs set <paper> --status have` | missing papers; record what you have |
| `deadline --scholarship S --date D --source URL` | record a verified deadline |
| `status --scholarship S --set Submitted` | track each application |
| `sync` | import edits you made in the Excel tracker |
| `plan` · `html-report` · `calendar` · `portfolio` | individual reports |
| `review-essay` · `email-professor` · `draft-lor --brag-sheet` · `fee-waivers --email` | writing helpers |
| `finance` · `credentials` · `interview` · `visa-guide` · `countries` · `list` | guides and calculators |
| `validate` · `export-schema` · `new-scholarship` | data maintenance |
| `scrape` · `discover` · `verify` | live web checks (`pip install -e ".[scrape]"`) |

Run commands as `.venv/bin/python cli.py <command>`, or as `scholarship <command>` after `pip install -e .`. Most
commands accept `--json`.

</details>

---

## 🗺️ Roadmap

- [x] Eligibility engine, fit scores, readiness, dated plans
- [x] Erasmus Mundus & Intra-Africa program finder
- [x] Agent skills, MCP server, `AGENTS.md`
- [ ] More scholarships: Asia-Pacific, US and Canadian university fellowships, foundation awards
- [ ] Funded PhD positions finder
- [ ] Automatic deadline monitoring (alert when an official page changes)
- [ ] Web app for people without an AI assistant
- [ ] Translations of the interface and guides (Arabic, French, Spanish, Portuguese, Turkish...)

Want one of these? [Open an issue](https://github.com/OmarZen/scholarship-navigator/issues) or send a pull request.

---

## 🤝 Contributing

The most valuable contribution is **accurate data**: a new scholarship, a corrected deadline, a verified program
status. No coding needed; [CONTRIBUTING.md](CONTRIBUTING.md) walks you through your first pull request in 10
minutes. Developers: tests, CI and JSON schemas are ready for you.

<a href="https://github.com/OmarZen/scholarship-navigator/issues?q=is%3Aopen+label%3A%22good+first+issue%22"><b>🌱 Good first issues</b></a> ·
<a href="https://github.com/OmarZen/scholarship-navigator/issues/new/choose"><b>➕ Suggest a scholarship</b></a> ·
<a href="https://github.com/OmarZen/scholarship-navigator/issues/new/choose"><b>📅 Report an outdated deadline</b></a> ·
<a href="https://github.com/OmarZen/scholarship-navigator/discussions"><b>💬 Ask a question</b></a> ·
<a href="CONTRIBUTING.md"><b>🧑‍💻 Contribute code</b></a>

**How contributions are reviewed:** you open a pull request from your fork → tests and data checks run
automatically → it is labelled by area → a maintainer reviews it (every pull request is reviewed before merging)
→ squash-merged into `main`. Nobody pushes to `main` directly. Details: [CONTRIBUTING.md](CONTRIBUTING.md#how-review-works).

### 💛 Contributors

Every merged pull request puts your profile here.

<a href="https://github.com/OmarZen/scholarship-navigator/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=OmarZen/scholarship-navigator" alt="Contributors to Scholarship Navigator" />
</a>

---

## ❓ FAQ

<details><summary><b>Is it free?</b></summary>
Yes. MIT-licensed, no accounts, no ads, no paid tier.
</details>

<details><summary><b>Does it apply for me?</b></summary>
No. It tells you where you can apply, what you're missing, when to start each step, and drafts your texts. You
submit on the official portals yourself.
</details>

<details><summary><b>Is my data safe?</b></summary>
Everything stays on your computer in <code>output/</code>, which is git-ignored. The tool never needs passport
numbers, ID numbers or bank details. If you use an AI assistant, your conversation follows that provider's privacy
terms.
</details>

<details><summary><b>How accurate are the deadlines?</b></summary>
Each one is marked <i>confirmed</i> (you verified it), <i>published</i> (official date found, with its source) or
<i>estimated</i> (the usual yearly pattern). Always confirm on the official site before applying. The plan tells you
which ones to check.
</details>

<details><summary><b>My scholarship isn't listed.</b></summary>
Run <code>cli.py new-scholarship &lt;id&gt;</code>, fill in the template from the official page, and it's matched like
the others. Then please share it with everyone through a pull request.
</details>

<details><summary><b>Do I need to know how to code?</b></summary>
No. With an AI assistant you just chat. Without one, <code>cli.py assess</code> asks you questions and builds
everything.
</details>

---

## 🌍 بالعربي

**Scholarship Navigator** أداة مجانية ومفتوحة المصدر بتساعدك تلاقي المنح اللي تقدر تكسبها فعلاً. بتحكي عن نفسك مرة واحدة، وهي:

- ✅ بتقولك إنت مؤهل لأنهي منح، والسبب لو مش مؤهل.
- 📊 بتديك درجة توافق من ١٠٠ مع شرح كل جزء فيها.
- 📄 بتقولك الورق الناقص، وتبدأ تجهز كل ورقة امتى.
- 🗓️ بتعملك خطة بمواعيد حقيقية، محسوبة من آخر ميعاد لكل منحة.
- 🧭 بتختارلك برامج إيراسموس موندوس المناسبة لتخصصك والدول اللي بتحبها.
- 📁 بتعملك مجلد لكل منحة، فيه مسودات المقالات وخطابات النية وملف Excel ونتيجة تقويم.

تقدر تستخدمها مع Claude أو Cursor أو أي مساعد ذكاء اصطناعي، وتكلمه بالعربي عادي.
الشرح الكامل بالعربي: [docs/i18n/README.ar.md](docs/i18n/README.ar.md)

---

## ⚠️ Disclaimer

Scholarship Navigator is an independent community project, not affiliated with any scholarship provider,
government or university. Data was researched from official sources (October 2026) but rules and deadlines change
every year: always confirm on the official website. Scores are guidance, not predictions of selection.

## ⭐ Support the project

If it helped you (or could help someone you know):

- **star the repository**, so more students find it;
- **share it** in your university, student and scholarship groups;
- **add one scholarship** from your country.

<a href="https://star-history.com/#OmarZen/scholarship-navigator&Date">
  <img src="https://api.star-history.com/svg?repos=OmarZen/scholarship-navigator&type=Date" alt="Star history" width="600" />
</a>

## License

[MIT](LICENSE) © 2026 [OmarZen](https://github.com/OmarZen).
