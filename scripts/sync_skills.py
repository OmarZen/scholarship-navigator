#!/usr/bin/env python3
"""
Copy the agent skills from skills/ (source of truth) to every place agents look for them:

  .claude/skills/<name>/      Claude Code
  .agent/skills/<name>/       Antigravity
  SKILL.md                    repository root copy of the main skill (reference links rewritten)

Usage:  python scripts/sync_skills.py          write the copies
        python scripts/sync_skills.py --check  exit 1 if any copy is out of date (used by tests / CI)
"""

import shutil
import sys
from pathlib import Path
from typing import Dict

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "skills"
TARGETS = [REPO / ".claude" / "skills", REPO / ".agent" / "skills"]
MAIN_SKILL = "scholarship-finder-planner"
ROOT_NOTE = ("<!-- Generated from skills/scholarship-finder-planner/SKILL.md by scripts/sync_skills.py. "
             "Edit the source, then run the script. -->\n")


def expected_files() -> Dict[Path, str]:
    files: Dict[Path, str] = {}
    for skill_dir in sorted(p for p in SOURCE.iterdir() if p.is_dir()):
        for src in sorted(skill_dir.rglob("*")):
            if src.is_file() and not src.name.startswith("."):
                text = src.read_text(encoding="utf-8")
                for target in TARGETS:
                    files[target / src.relative_to(SOURCE)] = text
    main = (SOURCE / MAIN_SKILL / "SKILL.md").read_text(encoding="utf-8")
    front_end = main.index("---", 3) + 3
    root = main[:front_end] + "\n" + ROOT_NOTE + main[front_end:]
    files[REPO / "SKILL.md"] = root.replace("`references/", f"`skills/{MAIN_SKILL}/references/")
    return files


def stale(files: Dict[Path, str]) -> list:
    out = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    for target in TARGETS:
        if target.exists():
            for p in target.rglob("*"):
                if p.is_file() and p not in files and (SOURCE / p.relative_to(target).parts[0]).exists():
                    out.append(p)
    return out


def main() -> int:
    files = expected_files()
    if "--check" in sys.argv:
        bad = stale(files)
        for p in bad:
            print(f"out of date: {p.relative_to(REPO)}")
        return 1 if bad else 0
    for target in TARGETS:
        for skill_dir in (p for p in SOURCE.iterdir() if p.is_dir()):
            dest = target / skill_dir.name
            if dest.exists():
                shutil.rmtree(dest)
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"synced {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
