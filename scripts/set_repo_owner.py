#!/usr/bin/env python3
"""
Replace the YOUR_GITHUB_USER placeholder (badges, links, CODEOWNERS, issue templates...) with the real GitHub
account or organization that hosts the repository, and optionally the repository name.

Usage:  python scripts/set_repo_owner.py <github-user-or-org> [--repo scholarship-navigator]
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLACEHOLDER = "YOUR_GITHUB_USER"
DEFAULT_REPO = "scholarship-navigator"
SKIP_DIRS = {".git", ".venv", "output", "__pycache__", "node_modules"}
SUFFIXES = {".md", ".yml", ".yaml", ".toml", ".json", ".txt", ".py", ""}


def files():
    for path in REPO.rglob("*"):
        if path.is_file() and not (set(path.relative_to(REPO).parts) & SKIP_DIRS) and path.suffix in SUFFIXES \
                and path.name != Path(__file__).name:
            yield path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("owner")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="repository name if it is not scholarship-navigator")
    args = ap.parse_args()
    changed = 0
    for path in files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PLACEHOLDER not in text:
            continue
        new = text.replace(f"{PLACEHOLDER}/{DEFAULT_REPO}", f"{args.owner}/{args.repo}").replace(PLACEHOLDER, args.owner)
        path.write_text(new, encoding="utf-8")
        changed += 1
        print(f"updated {path.relative_to(REPO)}")
    print(f"{changed} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
