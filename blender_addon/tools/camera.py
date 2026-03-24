"""
Camera tools: set the active scene camera and orient objects toward a target.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all camera tools onto the FastMCP instance."""

    @mcp.tool()
    async def set_active_camera(name: str) -> str:
        """Set the active camera for the current scene."""

        def _do():
            if not name:
                raise ValueError("name must not be empty")
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Object '{name}' not found")
            if obj.type != "CAMERA":
                raise ValueError(f"Object '{name}' is not a camera (type: {obj.type})")
            bpy.context.scene.camera = obj
            return {"active_camera": obj.name}

        return await run_tool("set_active_camera", _do)

    @mcp.tool()
    async def look_at(
        name: str,
        target: list[float],
    ) -> str:
        """Orient an object (typically a camera or light) to point at a target location.

        target is a world-space [x, y, z] coordinate. Works on any object type.
        """

        def _do():
            from mathutils import Vector  # noqa: PLC0415 (Blender-only, inside _do)

            if not name:
                raise ValueError("name must not be empty")
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Object '{name}' not found")
            if len(target) != 3:
                raise ValueError("target must have exactly 3 components [x, y, z]")

            target_vec = Vector(target)
            direction = target_vec - obj.location
            rot_quat = direction.to_track_quat("-Z", "Y")
            obj.rotation_euler = rot_quat.to_euler()

            return {
                "name": name,
                "target": list(target),
                "rotation_euler": list(obj.rotation_euler),
            }

        return await run_tool("look_at", _do)
