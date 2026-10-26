# Use Scholarship Navigator with your AI assistant

Scholarship Navigator gives an AI assistant three things:

- **7 skills** (`skills/`): instructions that teach the assistant how to interview you, match scholarships, write
  essays and keep your plan up to date;
- an **MCP server** (`mcp_server.py`): direct tools such as `match_scholarships`, `create_workspace` and
  `set_study_location`;
- **`AGENTS.md`**: the project rules, read automatically by most coding assistants.

You need the skills, the MCP server, or both. The skills alone already work: the assistant runs `cli.py` for you.

## Step 0: install the project (once)

```bash
git clone https://github.com/OmarZen/scholarship-navigator.git
cd scholarship-navigator
python3 -m venv .venv
.venv/bin/pip install -e ".[mcp]"          # Windows: .venv\Scripts\pip install -e ".[mcp]"
```

## Two ways to use it

1. **Open this folder in your assistant** (simplest). The skills load by themselves:
   `.claude/skills/` for Claude Code, and `.agents/skills/` for Codex, GitHub Copilot, Cursor, Gemini CLI,
   Windsurf and Antigravity.
2. **Install the skills for every folder** with one command, then ask about scholarships from anywhere:

   ```bash
   python scripts/install_skills.py --tool <tool>     # see the table below; --list shows all
   ```

   The script copies the skills to your assistant's personal skills folder, points them at this repository, and
   prints the exact MCP settings for your tool with your real paths filled in. Run it again after `git pull` to
   update.

| Assistant | Open this folder | Install for every folder | MCP server |
|---|---|---|---|
| **Claude Code** | ✅ automatic (skills + `.mcp.json`) | `--tool claude` → `~/.claude/skills` | automatic here; `claude mcp add` elsewhere |
| **Claude app** (claude.ai, Claude Desktop) | – | `--tool claude-app` → ZIPs to upload | Claude Desktop config file |
| **OpenAI Codex** (CLI, IDE, app) | ✅ `AGENTS.md` + `.agents/skills` | `--tool codex` → `~/.agents/skills` | `codex mcp add` |
| **GitHub Copilot** (VS Code, Copilot CLI) | ✅ `AGENTS.md` + `.agents/skills` | `--tool copilot` → `~/.copilot/skills` | `.vscode/mcp.json` |
| **Cursor** | ✅ `AGENTS.md` + `.agents/skills` | `--tool cursor` → `~/.cursor/skills` | `~/.cursor/mcp.json` |
| **Gemini CLI** | ✅ `GEMINI.md` + `.agents/skills` | `--tool gemini` → `~/.gemini/skills` | `~/.gemini/settings.json` |
| **Windsurf** | ✅ `.agents/skills` | `--tool windsurf` → `~/.codeium/windsurf/skills` | `~/.codeium/windsurf/mcp_config.json` |
| **Google Antigravity** | ✅ `.agents/skills` | `--tool antigravity` → `~/.gemini/config/skills` | `~/.gemini/config/mcp_config.json` |
| Any other MCP client | – | `--tool agents` → `~/.agents/skills` | the JSON below |

In the MCP examples below, replace `/path/to/scholarship-navigator` with the folder you cloned (the install
script prints them for you with the right paths). On Windows the Python path is
`C:\path\to\scholarship-navigator\.venv\Scripts\python.exe`.

---

## Claude Code

1. `cd scholarship-navigator && claude`
2. That's it: the skills in `.claude/skills/` and the MCP server in `.mcp.json` load automatically (approve the
   server when asked). Type `/mcp` to see it.
3. Ask: *"Help me find a fully funded master's scholarship. Interview me first."*

Everywhere else:

```bash
python scripts/install_skills.py --tool claude
claude mcp add --scope user scholarship-navigator -- /path/to/scholarship-navigator/.venv/bin/python /path/to/scholarship-navigator/mcp_server.py
```

## Claude app (claude.ai and Claude Desktop)

**Skills**

1. `python scripts/install_skills.py --tool claude-app` creates one ZIP per skill in `dist/claude-skills/`.
2. In Claude, open **Customize → Skills** (older versions: **Settings → Capabilities**), make sure code execution
   is on, click **Upload skill** and upload each ZIP. Start with `scholarship-finder-planner.zip` and
   `scholarship-intake.zip`.

**MCP server (Claude Desktop only)**: Settings → Developer → **Edit Config**, add this to
`claude_desktop_config.json`, then restart Claude Desktop:

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

The Claude app runs uploaded skills in the cloud, so it cannot run `cli.py` from your computer. Connect the MCP
server in Claude Desktop to get matching, workspaces and plans.

## OpenAI Codex (CLI, IDE extension, app)

1. `cd scholarship-navigator && codex`
2. Codex reads `AGENTS.md` and the skills in `.agents/skills/` automatically. Type `/skills` to see them, or
   `$scholarship-finder-planner` to call one.

Everywhere else:

```bash
python scripts/install_skills.py --tool codex          # copies to ~/.agents/skills
codex mcp add scholarship-navigator -- /path/to/scholarship-navigator/.venv/bin/python /path/to/scholarship-navigator/mcp_server.py
```

or add the server to `~/.codex/config.toml`:

```toml
[mcp_servers.scholarship-navigator]
command = "/path/to/scholarship-navigator/.venv/bin/python"
args = ["/path/to/scholarship-navigator/mcp_server.py"]
```

## GitHub Copilot (VS Code agent mode, Copilot CLI, cloud agent)

1. Open the folder in VS Code and switch Copilot Chat to **Agent** mode.
2. Copilot reads `AGENTS.md` and the skills in `.agents/skills/` (and `.claude/skills/`) automatically.

Everywhere else: `python scripts/install_skills.py --tool copilot` (copies to `~/.copilot/skills`).

**MCP server**: run **MCP: Open User Configuration** from the Command Palette (or create `.vscode/mcp.json` in
a project) and add:

```json
{
  "servers": {
    "scholarship-navigator": {
      "type": "stdio",
      "command": "/path/to/scholarship-navigator/.venv/bin/python",
      "args": ["/path/to/scholarship-navigator/mcp_server.py"]
    }
  }
}
```

## Cursor

1. Open the folder in Cursor. The Agent reads `AGENTS.md` and the skills in `.agents/skills/` automatically;
   type `/` in the Agent chat to call a skill.

Everywhere else: `python scripts/install_skills.py --tool cursor` (copies to `~/.cursor/skills`).

**MCP server**: Cursor Settings → MCP → **Add new MCP server**, or add to `~/.cursor/mcp.json` (all projects) or
`.cursor/mcp.json` (one project):

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

## Gemini CLI

1. `cd scholarship-navigator && gemini`
2. Gemini CLI reads `GEMINI.md` (which imports `AGENTS.md`) and the skills in `.agents/skills/`. Type
   `/skills list` to see them; Gemini asks before it activates one.

Everywhere else: `python scripts/install_skills.py --tool gemini` (copies to `~/.gemini/skills`).

**MCP server**: add to `~/.gemini/settings.json` (all projects) or `.gemini/settings.json` (one project):

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

## Windsurf

1. Open the folder. Cascade discovers the skills in `.agents/skills/` automatically; `@`-mention one to use it.

Everywhere else: `python scripts/install_skills.py --tool windsurf` (copies to `~/.codeium/windsurf/skills`).

**MCP server**: Cascade → MCP servers → **View raw config** (`~/.codeium/windsurf/mcp_config.json`) and add the
same `mcpServers` block as for Cursor.

## Google Antigravity

1. Open the folder. Antigravity loads workspace skills from `.agents/skills/`.

Everywhere else: `python scripts/install_skills.py --tool antigravity` (copies to `~/.gemini/config/skills`).

**MCP server**: Agent panel → **…** → MCP Servers → **Manage MCP Servers** → **View raw config**
(`~/.gemini/config/mcp_config.json`) and add the same `mcpServers` block as for Cursor.

## Any other assistant

- Agents that read `AGENTS.md` (Zed, Aider, Jules, OpenCode, ...) understand the project when you open the folder.
- Agents that support Agent Skills usually read `~/.agents/skills`: `python scripts/install_skills.py --tool agents`.
- Any MCP client can start the server with `/path/to/scholarship-navigator/.venv/bin/python /path/to/scholarship-navigator/mcp_server.py`
  (stdio). Workspaces are saved in `scholarship-navigator/output/` unless you set `SCHOLARSHIP_WORKSPACES`.

## Check that it works

Ask: *"List the scholarships I can study in my own country without travelling. I'm Egyptian."* The assistant
should call `list_scholarships` (MCP) or run `cli.py list --nationality Egypt --location home`.

Tools change quickly. If a folder or menu above has moved, check your assistant's documentation for "Agent Skills"
and "MCP servers", and please [open an issue](https://github.com/OmarZen/scholarship-navigator/issues) so we can
update this page.
