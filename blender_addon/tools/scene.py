"""
Scene inspection tools: list scenes, get scene info, list objects, get object info.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging

import bpy

from ..bridge import bridge

logger = logging.getLogger(__name__)


async def _run_tool(tool_name: str, fn) -> str:
    """Shared async wrapper: runs fn on the main thread and returns JSON."""
    try:
        fut = bridge.run_on_main_thread(fn)  # type: ignore[union-attr]
        result = fut.result(timeout=30)
        return json.dumps(result)
    except concurrent.futures.TimeoutError:
        return json.dumps({"error": "Main thread timeout after 30s", "tool": tool_name})
    except Exception as exc:
        logger.exception("Tool %s failed", tool_name)
        return json.dumps({"error": str(exc), "tool": tool_name})


def register(mcp) -> None:
    """Register all scene tools onto the FastMCP instance."""

    @mcp.tool()
    async def list_scenes() -> str:
        """List all scenes in the blend file."""

        def _do():
            return [
                {
                    "name": s.name,
                    "frame_start": s.frame_start,
                    "frame_end": s.frame_end,
                    "object_count": len(s.objects),
                }
                for s in bpy.data.scenes
            ]

        return await _run_tool("list_scenes", _do)

    @mcp.tool()
    async def get_scene_info(scene_name: str = "") -> str:
        """Return detailed info about a scene. Uses the active scene if scene_name is empty."""

        def _do():
            if scene_name and scene_name not in bpy.data.scenes:
                raise ValueError(f"Scene '{scene_name}' not found")
            scene = bpy.data.scenes[scene_name] if scene_name else bpy.context.scene
            objects = [{"name": o.name, "type": o.type} for o in scene.objects]
            collections = [c.name for c in scene.collection.children_recursive]
            return {
                "name": scene.name,
                "objects": objects,
                "collections": collections,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "fps": scene.render.fps,
            }

        return await _run_tool("get_scene_info", _do)

    @mcp.tool()
    async def list_objects(scene_name: str = "") -> str:
        """List all objects in a scene with type, location, and visibility."""

        def _do():
            scene = bpy.data.scenes.get(scene_name) if scene_name else bpy.context.scene
            if scene is None:
                raise ValueError(f"Scene '{scene_name}' not found")
            return [
                {
                    "name": o.name,
                    "type": o.type,
                    "location": list(o.location),
                    "visible": not o.hide_viewport,
                }
                for o in scene.objects
            ]

        return await _run_tool("list_objects", _do)

    @mcp.tool()
    async def get_object_info(name: str) -> str:
        """Return detailed info about an object.

        Includes transforms, dimensions, materials, modifiers, and parent.
        """

        def _do():
            if not name:
                raise ValueError("name must not be empty")
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Object '{name}' not found")
            data = getattr(obj, "data", None)
            materials = (
                [m.name for m in data.materials if m] if data and hasattr(data, "materials") else []
            )
            return {
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation_euler": list(obj.rotation_euler),
                "scale": list(obj.scale),
                "dimensions": list(obj.dimensions),
                "materials": materials,
                "modifiers": [m.name for m in obj.modifiers],
                "parent": obj.parent.name if obj.parent else None,
            }

        return await _run_tool("get_object_info", _do)
