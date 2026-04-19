"""
Animation tools: insert/delete keyframes, set frame range, set current frame, set FPS.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)

#: Data paths that callers may keyframe. Restricts the RNA path surface to
#: standard object transform and visibility properties, preventing accidental
#: or malicious animation of modifier internals or other arbitrary attributes.
ALLOWED_DATA_PATHS: frozenset[str] = frozenset({
    "color",
    "delta_location",
    "delta_rotation_euler",
    "delta_rotation_quaternion",
    "delta_scale",
    "hide_render",
    "hide_viewport",
    "location",
    "rotation_axis_angle",
    "rotation_euler",
    "rotation_quaternion",
    "scale",
})


def _validate_data_path(data_path: str) -> None:
    """Raise ValueError if data_path is not in ALLOWED_DATA_PATHS.

    Indexed access such as ``location[0]`` is accepted by stripping the
    ``[...]`` suffix before checking the base property name.
    """
    base = data_path.split("[")[0].strip()
    if base not in ALLOWED_DATA_PATHS:
        raise ValueError(
            f"data_path {data_path!r} is not allowed. "
            f"Allowed paths: {', '.join(sorted(ALLOWED_DATA_PATHS))}"
        )


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

        return await run_tool("set_frame_range", _do)

    @mcp.tool()
    async def set_current_frame(frame: int) -> str:
        """Move the timeline playhead to the given frame number."""

        def _do():
            if frame < 0:
                raise ValueError("frame must be >= 0")
            bpy.context.scene.frame_set(frame)
            return {"current_frame": bpy.context.scene.frame_current}

        return await run_tool("set_current_frame", _do)

    @mcp.tool()
    async def set_fps(fps: int) -> str:
        """Set the frames-per-second rate on the active scene."""

        def _do():
            if fps <= 0:
                raise ValueError("fps must be a positive integer")
            bpy.context.scene.render.fps = fps
            return {"fps": bpy.context.scene.render.fps}

        return await run_tool("set_fps", _do)

    @mcp.tool()
    async def insert_keyframe(
        object_name: str,
        data_path: str,
        frame: int,
        index: int = -1,
    ) -> str:
        """Insert a keyframe on an object's data path at the given frame.

        data_path must be one of the allowed transform/visibility properties:
        location, rotation_euler, rotation_quaternion, rotation_axis_angle,
        scale, hide_render, hide_viewport, color, delta_location, delta_scale,
        delta_rotation_euler, delta_rotation_quaternion.
        Indexed access like 'location[0]' is also accepted.
        index=-1 inserts keyframes on all channels of the property.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not data_path:
                raise ValueError("data_path must not be empty")
            _validate_data_path(data_path)
            if frame < 0:
                raise ValueError("frame must be >= 0")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            bpy.context.scene.frame_set(frame)
            obj.keyframe_insert(data_path=data_path, frame=frame, index=index)
            return {"object": object_name, "data_path": data_path, "frame": frame}

        return await run_tool("insert_keyframe", _do)

    @mcp.tool()
    async def delete_keyframe(
        object_name: str,
        data_path: str,
        frame: int,
        index: int = -1,
    ) -> str:
        """Delete a keyframe from an object's data path at the given frame.

        data_path must be one of the allowed transform/visibility properties
        (same set as insert_keyframe). Returns success=true if a keyframe was
        found and removed, false otherwise.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not data_path:
                raise ValueError("data_path must not be empty")
            _validate_data_path(data_path)
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

        return await run_tool("delete_keyframe", _do)
