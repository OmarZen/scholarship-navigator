#!/usr/bin/env python3
"""
Refresh the contributors list in README.md, between <!-- CONTRIBUTORS:START --> and <!-- CONTRIBUTORS:END -->,
from the GitHub API: every account with a merged commit, with avatar and a link to its profile. Bots are left out.

Usage:  python scripts/update_contributors.py          rewrite the list
        python scripts/update_contributors.py --check  exit 1 if the list is out of date

Env:    GITHUB_TOKEN (optional, raises the API rate limit) · GITHUB_REPOSITORY (default OmarZen/scholarship-navigator)
The workflow .github/workflows/contributors.yml runs this weekly and after every merge.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
START, END = "<!-- CONTRIBUTORS:START -->", "<!-- CONTRIBUTORS:END -->"
PER_ROW = 7


def fetch_contributors(repo: str) -> List[Dict]:
    people, page = [], 1
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "scholarship-navigator"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    while True:
        url = f"https://api.github.com/repos/{repo}/contributors?per_page=100&page={page}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            batch = json.load(r)
        if not batch:
            return people
        people += batch
        page += 1


def is_person(c: Dict) -> bool:
    return c.get("type") == "User" and not c.get("login", "").endswith("[bot]")


def render(contributors: List[Dict]) -> str:
    people = [c for c in contributors if is_person(c)]
    cells = [
        f'<td align="center" valign="top" width="14%"><a href="{c["html_url"]}">'
        f'<img src="{c["avatar_url"]}&s=100" width="80" alt="@{c["login"]}" /><br /><sub><b>@{c["login"]}</b></sub></a>'
        f'<br /><sub>{c["contributions"]} commit{"s" if c["contributions"] != 1 else ""}</sub></td>'
        for c in people
    ]
    rows = ["  <tr>\n    " + "\n    ".join(cells[i:i + PER_ROW]) + "\n  </tr>" for i in range(0, len(cells), PER_ROW)]
    return f"{START}\n<table>\n" + "\n".join(rows) + f"\n</table>\n{END}"


def replace_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise ValueError(f"README.md has no {START} ... {END} block")
    return pattern.sub(lambda _: block, text)


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "OmarZen/scholarship-navigator")
    text = README.read_text(encoding="utf-8")
    new = replace_block(text, render(fetch_contributors(repo)))
    if "--check" in sys.argv:
        print("contributors list is up to date" if new == text else "out of date: README.md contributors")
        return 0 if new == text else 1
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("updated README.md contributors")
    else:
        print("contributors list is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
