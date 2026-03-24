# blender-mcp

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

### Option A — Clone the repository

```bash
git clone https://github.com/your-org/blender-mcp.git
cd blender-mcp
```

The add-on directory is `blender_addon/`. No build or compilation step is needed — Blender add-ons are plain Python packages.

### Option B — Create an installable zip

Blender can install add-ons from a zip file containing the package directory:

```bash
# From the repository root:
zip -r blender_mcp_addon.zip blender_addon/
```

This produces `blender_mcp_addon.zip`, which you can install via Blender's Preferences UI (see below).

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

You can also confirm in Blender's Python console:

```python
import bpy
bpy.context.preferences.addons["blender_addon"].preferences.port  # → 8400
```

### Change the port (optional)

In **Edit → Preferences → Add-ons → Blender MCP Server**, set the **Port** field (default: `8400`) before enabling, or disable/re-enable after changing it.

---

## Connecting an MCP Client

**Important:** Blender must already be running with the add-on enabled before connecting.

### Option A — Direct HTTP (recommended)

The add-on exposes a Streamable HTTP endpoint at `http://localhost:8400/mcp`. Any MCP client
that supports HTTP transport can connect directly — no proxy, no extra Python dependencies.

**Claude Code** (`~/.claude/settings.json` or `.claude/settings.json`):

```json
{
  "mcpServers": {
    "blender-mcp": {
      "type": "http",
      "url": "http://localhost:8400/mcp"
    }
  }
}
```

**Other clients** (Cline, OpenCode, etc.): point the HTTP/SSE transport URL to
`http://localhost:8400/mcp`.

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

Replace `/absolute/path/to/blender-mcp/` with the actual path to the cloned repository.
`launcher.py` will wait up to 60 seconds for Blender to become reachable, then time out.

### Verify the connection

```bash
# HTTP check (works for both Option A and B):
curl -s -X POST http://localhost:8400/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}'
```

```bash
# stdio proxy round-trip (Option B only):
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python launcher.py
```

---

## LLM Self-Configuration

> This section is written for LLM agents that need to register this MCP server for themselves
> autonomously. Follow these steps in order.

### Step 0 — Install prerequisites (if needed)

Skip this step if Blender is already running with the add-on enabled (you can verify in Step 1).

#### 0a — Install `mcp[cli]` into Blender's bundled Python

The add-on runs inside Blender's own Python interpreter, so `mcp[cli]` must be installed there.

**Find Blender's Python executable:**

```bash
# Windows (PowerShell) — adjust version numbers as needed
ls "C:\Program Files\Blender Foundation\Blender*\*\python\bin\python.exe" 2>$null

# macOS
ls /Applications/Blender.app/Contents/Resources/*/python/bin/python3.*

# Linux
ls ~/blender-*/*/python/bin/python3.*
```

Alternatively, ask the user for the path if the above finds nothing or finds multiple versions.

**Install `mcp[cli]` once the path is known:**

```bash
# Replace <blender-python> with the full path found above
<blender-python> -m pip install "mcp[cli]"
```

**Verify:**

```bash
<blender-python> -c "import mcp; print('ok')"
```

After installation, the user must enable the add-on in Blender:
**Edit → Preferences → Add-ons → search "Blender MCP Server" → enable checkbox.**
This step requires user interaction and cannot be automated from the command line.

#### 0b — Install system Python dependencies (stdio fallback only)

Required only if using `launcher.py`. Skip if connecting via HTTP (Option A).

```bash
pip install httpx "mcp[cli]"
```

### Step 1 — Verify Blender is reachable

```bash
curl -s -X POST http://localhost:8400/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

**Expected:** a response containing `"result"` with `serverInfo.name == "blender-mcp"`.
**If the request fails or returns an error:** Blender is not running or the add-on is not enabled.
Inform the user and stop — do not proceed with registration.

### Step 2 — Register the server

Choose the appropriate config location:

| Scope | File | When to use |
|-------|------|-------------|
| This project only | `.mcp.json` in repo root | Preferred — already present in this repo |
| All projects (global) | `~/.claude/settings.json` | When working outside this repo |

The `.mcp.json` file in this repository already contains the correct entry:

```json
{
  "mcpServers": {
    "blender-mcp": {
      "type": "http",
      "url": "http://localhost:8400/mcp"
    }
  }
}
```

If you are registering globally, merge the same `"blender-mcp"` entry into the `"mcpServers"`
object in `~/.claude/settings.json` (create the object if it does not exist).

### Step 3 — Confirm registration

After writing the config, call `tools/list` to confirm the server responds:

```bash
curl -s -X POST http://localhost:8400/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <session-id-from-step-1>" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}'
```

**Expected:** a list of 32 tools including `list_scenes`, `create_object`, `render_image`, etc.
**If the tool count is wrong:** the add-on version may be outdated — inform the user.

---

## Development Setup

For active development, use a symlink instead of reinstalling the zip after every change.

### Windows

Run once in an elevated (Administrator) command prompt:

```cmd
mklink /D "%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\blender_addon" "E:\path\to\blender-mcp\blender_addon"
```

Replace `E:\path\to\blender-mcp` with the actual repository path and `4.5` with your Blender version.

### Linux / macOS

```bash
ln -s /path/to/blender-mcp/blender_addon \
  ~/.config/blender/4.5/scripts/addons/blender_addon   # Linux
  # or
  ~/Library/Application\ Support/Blender/4.5/scripts/addons/blender_addon  # macOS
```

### Reloading after changes

After editing Python source files, reload the add-on in Blender without restarting:

1. **Edit → Preferences → Add-ons** → find "Blender MCP Server"
2. Uncheck the add-on (unregisters bridge + server)
3. Check it again (re-registers with the updated code)

> **Note:** Blender caches imported modules. For deep module changes you may need to fully restart Blender.

---

## Available Tools

| Category | Tools |
|---|---|
| Scene | `list_scenes`, `get_scene_info`, `list_objects`, `get_object_info` |
| Objects | `create_object`, `delete_objects`, `transform_object`, `duplicate_object`, `select_objects`, `parent_objects` |
| Materials | `create_material`, `assign_material`, `list_materials`, `set_material_property` |
| Render | `set_render_settings`, `render_image`, `screenshot_viewport` |
| Shader nodes | `list_shader_nodes`, `add_shader_node`, `connect_nodes`, `remove_node`, `set_node_value` |
| Modifiers | `list_modifiers`, `add_modifier`, `remove_modifier`, `configure_modifier`, `apply_modifier` |
| Animation | `set_frame_range`, `set_current_frame`, `set_fps`, `insert_keyframe`, `delete_keyframe` |
