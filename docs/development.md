# Development Setup

## Running tests and lint locally

Requires [Hatch](https://hatch.pypa.io/) (`pip install hatch`) or [uv](https://docs.astral.sh/uv/) (`pip install uv`).

```bash
hatch run check       # lint + typecheck + unit tests (full pre-commit check)
hatch run lint        # ruff check only
hatch run test        # unit tests only (no Blender required)
hatch run coverage    # unit tests + coverage report
hatch run test-e2e    # E2E tests (requires running Blender with add-on enabled)
hatch run package     # build blender_mcp_addon.zip
```

Equivalent commands with uv:

```bash
uv run ruff check .
uv run pytest tests/unit/ -v
```

## Releasing a new version

Releases are automated via GitHub Actions. To cut a release:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The release pipeline will:
1. Run lint + typecheck + unit tests (gate)
2. Patch `bl_info["version"]` and `pyproject.toml` from the tag
3. Build `blender_mcp_addon.zip`
4. Create a GitHub Release with the zip as a downloadable artifact

## Symlink for active development

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
