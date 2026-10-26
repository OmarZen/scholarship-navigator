#!/usr/bin/env python3
"""
Install the Scholarship Navigator skills for your AI assistant (so they work in every folder, not only in this
repository) and print the MCP server setup for that assistant.

Inside this repository nothing is needed: Claude Code reads .claude/skills/, and Codex, GitHub Copilot, Cursor,
Gemini CLI, Windsurf and Antigravity read .agents/skills/.

Usage:  python scripts/install_skills.py --tool agents      ~/.agents/skills (Codex, Copilot, Cursor, Gemini CLI, Windsurf)
        python scripts/install_skills.py --tool claude      ~/.claude/skills (Claude Code)
        python scripts/install_skills.py --tool claude-app  ZIP files to upload in the Claude app (web or desktop)
        python scripts/install_skills.py --tool cursor --mcp-only
        python scripts/install_skills.py --list
"""

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, Tuple

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "skills"
SERVER = "scholarship-navigator"

# tool -> (label, personal skills folder, MCP recipe)
TOOLS: Dict[str, Tuple[str, str, str]] = {
    "claude": ("Claude Code", "~/.claude/skills", "claude-code"),
    "claude-app": ("Claude app (claude.ai and Claude Desktop)", "dist/claude-skills", "claude-desktop"),
    "agents": ("Codex, GitHub Copilot, Cursor, Gemini CLI, Windsurf (shared folder)", "~/.agents/skills", "codex"),
    "codex": ("OpenAI Codex (CLI, IDE extension, app)", "~/.agents/skills", "codex"),
    "copilot": ("GitHub Copilot (VS Code agent mode, Copilot CLI)", "~/.copilot/skills", "vscode"),
    "cursor": ("Cursor", "~/.cursor/skills", "cursor"),
    "gemini": ("Gemini CLI", "~/.gemini/skills", "gemini"),
    "windsurf": ("Windsurf", "~/.codeium/windsurf/skills", "windsurf"),
    "antigravity": ("Google Antigravity", "~/.gemini/config/skills", "antigravity"),
}


def python_path() -> Path:
    for candidate in (REPO / ".venv" / "bin" / "python", REPO / ".venv" / "Scripts" / "python.exe"):
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def installed_note(py: Path, app: bool = False) -> str:
    if app:  # the Claude app runs skills in the cloud, where this computer's paths don't exist
        return ("\n> Installed copy of a Scholarship Navigator skill. Commands like `cli.py` only work where the "
                "repository is installed: in Claude Desktop, connect the `scholarship-navigator` MCP server "
                "(see docs/AI_TOOLS.md) and use its tools instead.\n")
    return (f"\n> Installed copy of a Scholarship Navigator skill. The tool lives in `{REPO}`: run "
            f"`\"{py}\" \"{REPO / 'cli.py'}\" <command>` (MCP server: `\"{py}\" \"{REPO / 'mcp_server.py'}\"`). "
            f"Update with `python \"{REPO / 'scripts' / 'install_skills.py'}\"`.\n")


def skill_dirs():
    return sorted(p for p in SOURCE.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def install(dest: Path, py: Path, app: bool = False) -> list:
    """Copy each skill folder into dest, replacing only our own skills, and point the copies at this repository."""
    dest.mkdir(parents=True, exist_ok=True)
    done = []
    for skill in skill_dirs():
        target = dest / skill.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)
        text = (target / "SKILL.md").read_text(encoding="utf-8")
        end = text.index("---", 3) + 3
        (target / "SKILL.md").write_text(text[:end] + "\n" + installed_note(py, app) + text[end:], encoding="utf-8")
        done.append(target)
    return done


def make_zips(dest: Path, py: Path) -> list:
    """One ZIP per skill (the skill folder at the root of the archive), as the Claude app expects."""
    staging = dest / ".staging"
    if staging.exists():
        shutil.rmtree(staging)
    zips = []
    for folder in install(staging, py, app=True):
        path = dest / f"{folder.name}.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(folder.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(staging))
        zips.append(path)
    shutil.rmtree(staging)
    return zips


def mcp_instructions(recipe: str, py: Path) -> str:
    server = str(REPO / "mcp_server.py")
    std = {"mcpServers": {SERVER: {"command": str(py), "args": [server]}}}
    as_json = json.dumps(std, indent=2)
    if recipe == "claude-code":
        return ("Run once (inside this repository .mcp.json already does it):\n"
                f"  claude mcp add --scope user {SERVER} -- \"{py}\" \"{server}\"")
    if recipe == "claude-desktop":
        return ("Claude Desktop: Settings > Developer > Edit Config, then add to claude_desktop_config.json\n"
                "(macOS ~/Library/Application Support/Claude/, Windows %APPDATA%\\Claude\\) and restart:\n" + as_json)
    if recipe == "codex":
        return (f"Codex: run once\n  codex mcp add {SERVER} -- \"{py}\" \"{server}\"\n"
                f"or add to ~/.codex/config.toml:\n  [mcp_servers.{SERVER}]\n  command = \"{py}\"\n"
                f"  args = [\"{server}\"]")
    if recipe == "vscode":
        vs = {"servers": {SERVER: {"type": "stdio", "command": str(py), "args": [server]}}}
        return ("VS Code: run \"MCP: Open User Configuration\" from the Command Palette (or create .vscode/mcp.json) "
                "and add:\n" + json.dumps(vs, indent=2))
    where = {
        "cursor": "Cursor: add to ~/.cursor/mcp.json (or .cursor/mcp.json in a project):",
        "gemini": "Gemini CLI: add to ~/.gemini/settings.json (or .gemini/settings.json in a project):",
        "windsurf": "Windsurf: add to ~/.codeium/windsurf/mcp_config.json (Cascade > MCP servers > View raw config):",
        "antigravity": ("Antigravity: Agent panel > ... > MCP Servers > Manage MCP Servers > View raw config "
                        "(~/.gemini/config/mcp_config.json), then add:"),
    }[recipe]
    return f"{where}\n{as_json}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Scholarship Navigator skills for an AI assistant")
    parser.add_argument("--tool", choices=sorted(TOOLS), default="agents")
    parser.add_argument("--dest", help="Install into this folder instead of the tool's default")
    parser.add_argument("--mcp-only", action="store_true", help="Only print the MCP server setup")
    parser.add_argument("--list", action="store_true", help="List supported tools and folders")
    args = parser.parse_args()

    if args.list:
        for key, (label, folder, _) in TOOLS.items():
            print(f"  {key:12} {label:70} {folder}")
        return 0

    label, folder, recipe = TOOLS[args.tool]
    py = python_path()
    if not args.mcp_only:
        dest = Path(args.dest).expanduser() if args.dest else (
            REPO / folder if args.tool == "claude-app" else Path(folder).expanduser())
        if args.tool == "claude-app":
            zips = make_zips(dest, py)
            print(f"Created {len(zips)} ZIP files in {dest}.")
            print("Claude app: open Customize > Skills (or Settings > Capabilities on older versions), "
                  "click 'Upload skill' and upload each ZIP. Code execution must be on.")
        else:
            done = install(dest, py)
            print(f"Installed {len(done)} skills for {label} in {dest}. Restart the assistant if it is open.")
    print("\nMCP server (optional, gives the assistant direct tools):\n" + mcp_instructions(recipe, py))
    if not (REPO / ".venv").exists():
        print(f"\nNote: create the environment first: cd \"{REPO}\" && python3 -m venv .venv && "
              ".venv/bin/pip install -e \".[mcp]\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
