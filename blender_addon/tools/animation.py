"""
Animation tools: insert/delete keyframes, set frame range, set current frame, set FPS.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
from collections.abc import Callable
from typing import Any

import bpy

from ..bridge import bridge

logger = logging.getLogger(__name__)


async def _run_tool(tool_name: str, fn: Callable[[], Any]) -> str:
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
    """Register all animation tools onto the FastMCP instance."""

    @mcp.tool()
    async def set_frame_range(start: int, end: int) -> str:
        """Set the animation frame range on the active scene."""

        def _do():
            if start < 0:
                raise ValueError("start frame must be >= 0")
            if end <= start:
                raise ValueError("end frame must be greater than start frame")
            scene = bpy.context.scene
            scene.frame_start = start
            scene.frame_end = end
            return {"frame_start": scene.frame_start, "frame_end": scene.frame_end}

        return await _run_tool("set_frame_range", _do)

    @mcp.tool()
    async def set_current_frame(frame: int) -> str:
        """Move the timeline playhead to the given frame number."""

        def _do():
            if frame < 0:
                raise ValueError("frame must be >= 0")
            bpy.context.scene.frame_set(frame)
            return {"current_frame": bpy.context.scene.frame_current}

        return await _run_tool("set_current_frame", _do)

    @mcp.tool()
    async def set_fps(fps: int) -> str:
        """Set the frames-per-second rate on the active scene."""

        def _do():
            if fps <= 0:
                raise ValueError("fps must be a positive integer")
            bpy.context.scene.render.fps = fps
            return {"fps": bpy.context.scene.render.fps}

        return await _run_tool("set_fps", _do)

    @mcp.tool()
    async def insert_keyframe(
        object_name: str,
        data_path: str,
        frame: int,
        index: int = -1,
    ) -> str:
        """Insert a keyframe on an object's data path at the given frame.

        data_path examples: 'location', 'rotation_euler', 'scale'.
        index=-1 inserts keyframes on all channels of the property.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not data_path:
                raise ValueError("data_path must not be empty")
            if frame < 0:
                raise ValueError("frame must be >= 0")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            bpy.context.scene.frame_set(frame)
            obj.keyframe_insert(data_path=data_path, frame=frame, index=index)
            return {"object": object_name, "data_path": data_path, "frame": frame}

        return await _run_tool("insert_keyframe", _do)

    @mcp.tool()
    async def delete_keyframe(
        object_name: str,
        data_path: str,
        frame: int,
        index: int = -1,
    ) -> str:
        """Delete a keyframe from an object's data path at the given frame.

        Returns success=true if a keyframe was found and removed, false otherwise.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not data_path:
                raise ValueError("data_path must not be empty")
            if frame < 0:
                raise ValueError("frame must be >= 0")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            success = obj.keyframe_delete(data_path=data_path, frame=frame, index=index)
            return {
                "object": object_name,
                "data_path": data_path,
                "frame": frame,
                "success": success,
            }

        return await _run_tool("delete_keyframe", _do)
