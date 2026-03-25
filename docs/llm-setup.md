# LLM Self-Configuration

> This guide is written for LLM agents that need to register this MCP server for themselves autonomously. Follow these steps in order.

## Step 0 — Install prerequisites (if needed)

Skip this step if Blender is already running with the add-on enabled (you can verify in Step 1).

### 0a — Install `mcp[cli]` into Blender's bundled Python

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

### 0b — Install system Python dependencies (stdio fallback only)

Required only if using `launcher.py`. Skip if connecting via HTTP (recommended).

```bash
pip install httpx "mcp[cli]"
```

## Step 1 — Verify Blender is reachable

```bash
curl -s -X POST http://localhost:8400/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

**Expected:** a response containing `"result"` with `serverInfo.name == "blender-mcp"`.
**If the request fails or returns an error:** Blender is not running or the add-on is not enabled. Inform the user and stop — do not proceed with registration.

## Step 2 — Register the server

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

If you are registering globally, merge the same `"blender-mcp"` entry into the `"mcpServers"` object in `~/.claude/settings.json` (create the object if it does not exist).

## Step 3 — Confirm registration

After writing the config, call `tools/list` to confirm the server responds:

```bash
curl -s -X POST http://localhost:8400/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <session-id-from-step-1>" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}'
```

**Expected:** a list of 42 tools (or 43 with `execute_python` enabled) including `list_scenes`, `create_object`, `render_image`, etc.
**If the tool count is wrong:** the add-on version may be outdated — inform the user.
