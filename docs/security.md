# Security: `execute_python` Tool

The `execute_python` tool lets connected MCP clients run Python code inside Blender. Because it grants powerful capabilities, it is **disabled by default** and requires explicit opt-in. When enabled, it operates in one of two modes.

## Restricted Mode (default)

When you enable `execute_python`, it starts in **restricted mode** — a sandboxed environment that limits what connected clients can do.

**Allowed in restricted mode:**
- Blender API: `bpy`, `mathutils`, `Vector`, `Matrix`, `Euler`, `Quaternion`
- Safe standard-library modules: `math`, `json`, `re`, `collections`, `itertools`, `functools`, `copy`, `random`, `colorsys`, `datetime`, `enum`, `typing`, `dataclasses`
- Safe built-in functions: `len`, `range`, `print`, `list`, `dict`, `type`, `isinstance`, `getattr`, etc.

**Blocked in restricted mode:**
- Filesystem access: `open`, the `os`, `shutil`, `pathlib`, and `tempfile` modules
- Network access: the `socket`, `http`, `urllib`, `ftplib`, and `smtplib` modules
- Process execution: the `subprocess` and `multiprocessing` modules, and OS process-spawning functions
- Low-level Python access: `ctypes`, `importlib`
- Dangerous built-ins: `globals`, `locals`, `compile`, `breakpoint`, `exit`, `input`, `help`, `memoryview`

**Important limitation:** Restricted mode is a **safety net, not a security boundary**. Python's dynamic nature makes it impossible to fully prevent all sandbox escape vectors. A determined attacker could potentially use dynamic Python features to circumvent restrictions. This mode protects against **accidental** dangerous operations — it is appropriate when you trust the AI assistant's intent but want to limit the blast radius of mistakes.

## Unrestricted Mode (YOLO)

> **WARNING: This mode grants connected MCP clients full, unrestricted access to your system.**

Unrestricted mode removes all sandbox restrictions. Code runs with the same permissions as Blender itself — identical to typing code directly into Blender's built-in Python console.

**What an unrestricted client can do:**
- Read, modify, or delete any file on your system
- Make arbitrary network connections
- Spawn processes and execute shell commands
- Install software or modify system configuration
- Access environment variables, credentials, or secrets stored on disk
- Anything else your user account can do

**When to use it:** Only enable unrestricted mode when you fully trust ALL connected MCP clients and explicitly need capabilities that restricted mode blocks (e.g., reading/writing project files from within a Blender script).

## How to Enable

1. Open **Edit → Preferences → Add-ons → Blender MCP Server**
2. Check **"Allow execute_python Tool (DANGEROUS)"** to enable the tool in restricted mode (default)
3. _(Optional)_ Check **"Unrestricted Mode (YOLO) — EXTREMELY DANGEROUS"** to remove all sandbox restrictions

The execution mode can be switched at runtime without restarting Blender. The tool response always includes a `"mode"` field (`"restricted"` or `"unrestricted"`) so clients know which context they are operating in.

## Implementation Notes

The sandbox is implemented in `blender_addon/tools/_sandbox.py`:
- `SAFE_BUILTINS` — whitelist dict replacing `__builtins__` in the execution namespace
- `ALLOWED_MODULES` — frozenset of importable module names
- `_safe_import` — `__import__` replacement that enforces the allowlist
- `make_restricted_namespace` / `make_unrestricted_namespace` — namespace builders used by `execute_python`

The active mode is stored as `server.execute_python_unrestricted` (module-level variable) and read at tool-call time, so switching between modes takes effect immediately without restarting Blender.
