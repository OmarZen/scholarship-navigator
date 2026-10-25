@AGENTS.md

## Claude Code notes

- Project skills are in `.claude/skills/` (generated from `skills/` by `scripts/sync_skills.py`; edit `skills/`).
- The MCP server is declared in `.mcp.json` (`scholarship-navigator`). When it is connected, prefer its tools over
  shelling out to the CLI.
