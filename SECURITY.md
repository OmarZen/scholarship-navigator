# Security & Privacy Policy

## Personal data

Scholarship Navigator runs **entirely on your own computer**. Candidate profiles, scanned documents, drafts and
reports live in `output/`, which is git-ignored and never uploaded by the tool. The tool never asks for passport
numbers, national ID numbers or bank details.

If you use it through an AI assistant, your messages are processed by that assistant's provider under their own
privacy terms.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Use GitHub's private reporting: **Security tab → Report a vulnerability**. Include what you found, how to reproduce
it, and its impact. You'll get an answer within 7 days.

Examples worth reporting:
- a way the tool could write outside the workspace folder or overwrite a candidate's own drafts;
- a scholarship or program link in `data/` that points to a malicious, phishing or compromised site;
- personal data accidentally committed to the repository.

## Suspicious links in the data

Program websites change hands and sometimes get compromised. If a link in `data/scholarships.json` or
`data/programs/` looks wrong, report it privately as above, or open a **Data correction** issue if it is simply
outdated. Maintainers replace bad links with the official EACEA catalogue or government page.
