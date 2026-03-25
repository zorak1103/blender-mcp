"""
Scripting tools: run Python/bpy code inside Blender (opt-in, disabled by default).

Two execution modes are supported, controlled by add-on preferences:

- **Restricted** (default): Sandboxed execution. Only bpy, mathutils, math, json,
  re, and a small set of safe standard-library modules are available. Filesystem,
  network, subprocess, and dangerous built-ins (open, globals, compile, etc.) are
  blocked. This mode is a safety net against accidental damage — it is not a
  complete security boundary against a determined attacker.

- **Unrestricted / YOLO**: Full Python standard-library access, identical to running
  code in Blender's built-in Python console. Requires the "Unrestricted Mode (YOLO)"
  preference to be enabled in addition to allow_execute_python.
"""

from __future__ import annotations

import logging

from ._helpers import run_tool

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all scripting tools onto the FastMCP instance."""

    @mcp.tool()
    async def execute_python(code: str) -> str:
        """Run Python code inside Blender.

        WARNING: Only available when explicitly enabled in add-on preferences.

        Two execution modes are available (set in Add-on Preferences):

        - **Restricted** (default): Sandboxed. Only bpy, mathutils, math, json, re,
          and a limited set of safe standard-library modules are available.
          Filesystem access (open, os, shutil), network (socket, http, urllib),
          subprocess, and dangerous built-ins are blocked.

        - **Unrestricted (YOLO)**: Full Python standard-library access. Grants the
          same permissions as Blender's built-in Python console. Requires the
          "Unrestricted Mode (YOLO)" preference to be separately enabled.

        To return data to the caller, assign to '__result__' in your code.
        Example: __result__ = [obj.name for obj in bpy.data.objects]
        """

        def _do():
            import traceback  # noqa: PLC0415

            import bpy  # noqa: PLC0415

            if not code or not code.strip():
                raise ValueError("code must be a non-empty string")

            from blender_addon import server as server_mod  # noqa: PLC0415
            from blender_addon.tools._sandbox import (  # noqa: PLC0415
                make_restricted_namespace,
                make_unrestricted_namespace,
            )

            mathutils_mod = __import__("mathutils")
            unrestricted = server_mod.execute_python_unrestricted
            if unrestricted:
                namespace = make_unrestricted_namespace(bpy, mathutils_mod)
            else:
                namespace = make_restricted_namespace(bpy, mathutils_mod)

            mode = "unrestricted" if unrestricted else "restricted"
            try:
                exec(code, namespace)  # noqa: S102
                return {"result": namespace.get("__result__"), "status": "ok", "mode": mode}
            except Exception as exc:
                return {
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "tool": "execute_python",
                    "mode": mode,
                }

        return await run_tool("execute_python", _do)
