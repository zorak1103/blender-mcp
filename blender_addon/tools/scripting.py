"""
Scripting tools: run arbitrary Python/bpy code inside Blender (opt-in, disabled by default).
"""

from __future__ import annotations

import logging

from ._helpers import run_tool

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all scripting tools onto the FastMCP instance."""

    @mcp.tool()
    async def execute_python(code: str) -> str:
        """Run arbitrary Python code inside Blender.

        WARNING: Only available when explicitly enabled in add-on preferences.
        Runs with full access to bpy and the Python standard library.
        Use at your own risk.

        To return data to the caller, assign to a variable called '__result__'
        in your code. Example: __result__ = [obj.name for obj in bpy.data.objects]
        """

        def _do():
            import traceback

            import bpy  # noqa: PLC0415
            from mathutils import Euler, Matrix, Quaternion, Vector  # noqa: PLC0415

            if not code or not code.strip():
                raise ValueError("code must be a non-empty string")

            namespace = {
                "bpy": bpy,
                "mathutils": __import__("mathutils"),
                "Vector": Vector,
                "Matrix": Matrix,
                "Euler": Euler,
                "Quaternion": Quaternion,
                "__result__": None,
            }
            try:
                exec(code, namespace)  # noqa: S102
                return {"result": namespace.get("__result__"), "status": "ok"}
            except Exception as exc:
                return {
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "tool": "execute_python",
                }

        return await run_tool("execute_python", _do)
