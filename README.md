# blender-mcp

[![CI](https://github.com/zorak1103/blender-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/zorak1103/blender-mcp/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/zorak1103/blender-mcp)](https://github.com/zorak1103/blender-mcp/releases/latest)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Blender](https://img.shields.io/badge/Blender-4.0+-ea7600?logo=blender&logoColor=white)](https://www.blender.org/)
[![MCP](https://img.shields.io/badge/MCP-compatible-6750a4)](https://modelcontextprotocol.io/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: GPL v3](https://img.shields.io/github/license/zorak1103/blender-mcp)](https://github.com/zorak1103/blender-mcp/blob/master/LICENSE.txt)

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets LLMs such as Claude control Blender — creating scenes, manipulating objects, assigning materials, configuring shader nodes, applying modifiers, setting keyframes, and rendering.

```
                  ┌──── HTTP (recommended) ────────────────┐
Claude Code ──────┤                                         ├──> Blender (GUI)
  / any client    └──stdio──> launcher.py ──HTTP ───────────┘     └─ MCP Server on localhost:8400
```

Blender must be running with the add-on enabled. The add-on exposes a Streamable HTTP MCP endpoint at `http://localhost:8400/mcp` — any MCP client that supports HTTP transport can connect directly. For clients that only support stdio transport, `launcher.py` acts as a thin stdio-to-HTTP proxy.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Blender 4.0 or newer | Must run in GUI mode (not headless) |
| Python 3.11+ (system) | Only needed for `launcher.py` (stdio fallback); must have `httpx` and `mcp[cli]` |
| `mcp[cli]` in Blender's Python | Separate install — see below |

### 1. Install launcher dependencies (optional — stdio fallback only)

> Skip this step if you are connecting via HTTP (recommended).

```bash
pip install httpx "mcp[cli]"
```

### 2. Install `mcp[cli]` into Blender's bundled Python

Blender ships its own Python interpreter. The add-on runs inside it, so `mcp[cli]` must be installed there separately.

Find Blender's Python executable — its exact path depends on your OS and Blender version:

| OS | Typical path |
|---|---|
| Linux | `~/blender-4.x.x/4.x/python/bin/python3.11` |
| macOS | `/Applications/Blender.app/Contents/Resources/4.x/python/bin/python3.11` |
| Windows | `C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\bin\python.exe` |

Then run:

```bash
# Linux / macOS
/path/to/blender/4.x/python/bin/python3.11 -m pip install "mcp[cli]"

# Windows (PowerShell)
& "C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\bin\python.exe" -m pip install "mcp[cli]"
```

---

## Getting the Add-on

### Option A — Download a release (recommended)

Download `blender_mcp_addon-vX.Y.Z.zip` from the [latest GitHub Release](https://github.com/zorak1103/blender-mcp/releases/latest) and install it directly in Blender (see [Installing and Activating in Blender](#installing-and-activating-in-blender)).

### Option B — Clone the repository

```bash
git clone https://github.com/zorak1103/blender-mcp.git
cd blender-mcp
```

The add-on directory is `blender_addon/`. No build or compilation step is needed — Blender add-ons are plain Python packages.

### Option C — Build the zip locally

Blender can install add-ons from a zip file containing the package directory.
Requires [Hatch](https://hatch.pypa.io/) (`pip install hatch`):

```bash
hatch run package
```

Or without Hatch:

```bash
zip -r blender_mcp_addon.zip blender_addon/
```

---

## Installing and Activating in Blender

### From a zip file

1. Open Blender and go to **Edit → Preferences → Add-ons**.
2. Click **Install…** and select `blender_mcp_addon.zip`.
3. Search for **"Blender MCP Server"** and enable the checkbox.

### From the cloned directory

1. Open Blender and go to **Edit → Preferences → Add-ons**.
2. Click **Install…**, navigate into the repository, and select the `blender_addon` folder itself (or its `__init__.py`).
3. Search for **"Blender MCP Server"** and enable the checkbox.

### Verify activation

After enabling, the Blender Info bar (top of the screen) should show:

```
Blender MCP Server registered, port=8400
```

### Change the port (optional)

In **Edit → Preferences → Add-ons → Blender MCP Server**, set the **Port** field (default: `8400`) before enabling, or disable/re-enable after changing it.

---

## Connecting an MCP Client

**Important:** Blender must already be running with the add-on enabled before connecting.

### Option A — Direct HTTP (recommended)

The add-on exposes a Streamable HTTP endpoint at `http://localhost:8400/mcp`. Any MCP client
that supports HTTP transport can connect directly — no proxy, no extra Python dependencies.

The MCP endpoint requires a Bearer token that the add-on generates on first start and writes to
`~/.config/blender-mcp/token`. Export it as an environment variable before launching your client:

```bash
# bash / Git Bash / WSL (add to ~/.bashrc for persistence)
export BLENDER_MCP_TOKEN="$(cat ~/.config/blender-mcp/token)"
```

```powershell
# PowerShell — set permanently in the user environment
[Environment]::SetEnvironmentVariable(
  "BLENDER_MCP_TOKEN",
  (Get-Content "$HOME\.config\blender-mcp\token"),
  "User")
```

**Claude Code** — the `.mcp.json` at the repository root is already configured with the
`Authorization: Bearer ${BLENDER_MCP_TOKEN}` header. Set the env var above, then start
(or restart) Claude Code — no further setup is needed inside this repository.
To register globally (outside this repo):

```bash
claude mcp add --transport http --scope user \
  --header "Authorization: Bearer \${BLENDER_MCP_TOKEN}" \
  blender-mcp http://localhost:8400/mcp
```

**Other clients** (Cline, OpenCode, etc.): point the HTTP/SSE transport URL to
`http://localhost:8400/mcp` and add the `Authorization: Bearer <token>` header.

> **Note for Claude Code users:** MCP servers from `.mcp.json` require either `"enableAllProjectMcpServers": true` in `.claude/settings.local.json`, or explicit approval via the dialog that appears on first launch. If the tools are not available and no dialog appeared, add `"enableAllProjectMcpServers": true` to `.claude/settings.local.json` and restart Claude Code.

### Option B — stdio proxy (fallback)

If your MCP client only supports stdio transport, use `launcher.py` as a thin proxy.
This requires system Python with `httpx` and `mcp[cli]` installed (see Prerequisites).

Add the following to `~/.claude/settings.json` (global) or `.claude/settings.json` (project-level):

```json
{
  "mcpServers": {
    "blender-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/blender-mcp/launcher.py"]
    }
  }
}
```

`launcher.py` will wait up to 60 seconds for Blender to become reachable, then time out.

### Verify the connection

```bash
# HTTP check (works for both Option A and B):
export BLENDER_MCP_TOKEN="$(cat ~/.config/blender-mcp/token)"
curl -s -X POST http://localhost:8400/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $BLENDER_MCP_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}'
```

```bash
# stdio proxy round-trip (Option B only):
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python launcher.py
```

---

## Troubleshooting

### MCP tools not available in Claude Code / approval dialog never appeared

Claude Code loads servers from `.mcp.json` only when `enableAllProjectMcpServers` is `true` or the user approves them via a one-time dialog. If neither happened, the server silently stays inactive.

**Fix:** add or update `.claude/settings.local.json` in the repository root:

```json
{
  "enableAllProjectMcpServers": true
}
```

Then restart Claude Code. The blender-mcp tools should appear immediately.

### `curl http://localhost:8400/mcp` returns 401 Unauthorized

The MCP endpoint requires a Bearer token. Make sure `BLENDER_MCP_TOKEN` is set and matches the content of `~/.config/blender-mcp/token` (written by the add-on on first start):

```bash
export BLENDER_MCP_TOKEN="$(cat ~/.config/blender-mcp/token)"
```

Then restart Claude Code (or whichever client you are using) so it picks up the new environment variable.

### `curl http://localhost:8400/mcp` returns "Not Acceptable"

This is expected and means the server **is** running. The endpoint requires specific headers. Use the full POST check from [Verify the connection](#verify-the-connection) instead.

### The add-on appears enabled but tools/list returns an error or times out

- Confirm the Info bar shows `Blender MCP Server registered, port=8400` after enabling the add-on.
- If you changed the port, update the URL in `.mcp.json` accordingly.
- Try disabling and re-enabling the add-on in **Edit → Preferences → Add-ons**.

### `mcp[cli]` not found when enabling the add-on in Blender

The package must be installed into Blender's **own** Python, not the system Python. Re-run the install command using the Blender Python executable (see [Prerequisites](#prerequisites)).

---

## Available Tools

| Category | Tools |
|---|---|
| Scene | `list_scenes`, `get_scene_info`, `list_objects`, `get_object_info` |
| Objects | `create_object`, `delete_objects`, `transform_object`, `duplicate_object`, `select_objects`, `parent_objects`, `create_object_grid`, `create_objects_batch` |
| Materials | `create_material`, `assign_material`, `assign_materials_batch`, `list_materials`, `set_material_property` |
| Render | `set_render_settings`, `render_image`, `screenshot_viewport` |
| Shader nodes | `list_shader_nodes`, `add_shader_node`, `connect_nodes`, `remove_node`, `set_node_value` |
| Modifiers | `list_modifiers`, `add_modifier`, `remove_modifier`, `configure_modifier`, `apply_modifier`, `add_modifiers_batch`, `apply_modifiers_batch`, `remove_modifiers_batch` |
| Animation | `set_frame_range`, `set_current_frame`, `set_fps`, `insert_keyframe`, `delete_keyframe` |
| Lighting | `configure_light` |
| Camera | `set_active_camera`, `look_at` |
| World | `set_world_settings` |
| Scripting (opt-in) | `execute_python` — see [Security](docs/security.md) for modes and risks |

---

## Further Reading

| Topic | File |
|---|---|
| Security & `execute_python` modes | [docs/security.md](docs/security.md) |
| Development setup, testing, releasing | [docs/development.md](docs/development.md) |
| LLM agent self-configuration guide | [docs/llm-setup.md](docs/llm-setup.md) |
