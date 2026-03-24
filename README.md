# blender-mcp

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets LLMs such as Claude control Blender — creating scenes, manipulating objects, assigning materials, configuring shader nodes, applying modifiers, setting keyframes, and rendering.

```
Claude Code ──stdio──> launcher.py ──HTTP──> Blender (GUI)
                                              └─ MCP Server on localhost:8400
```

Blender must be running with the add-on enabled. `launcher.py` is a thin stdio-to-HTTP proxy that bridges Claude Code's subprocess transport to Blender's in-process HTTP server.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Blender 4.0 or newer | Must run in GUI mode (not headless) |
| Python 3.11+ (system) | For `launcher.py`; must have `httpx` and `mcp[cli]` |
| `mcp[cli]` in Blender's Python | Separate install — see below |

### 1. Install launcher dependencies (system Python)

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

## Connecting Claude Code

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

Replace `/absolute/path/to/blender-mcp/` with the actual path to the cloned repository. The `python` command must be the interpreter where you installed `httpx` and `mcp[cli]` in the system step above.

**Important:** Blender must already be running with the add-on enabled before Claude Code starts a session. `launcher.py` will wait up to 60 seconds for Blender to become reachable, then time out.

### Verify the connection

```bash
# Quick HTTP check (Blender must be running):
curl http://localhost:8400/mcp

# Full stdio round-trip:
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python launcher.py
```

The second command should print a JSON response listing all available tools (`list_scenes`, `create_object`, `render_image`, etc.).

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
