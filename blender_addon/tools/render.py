"""
Render tools: configure render settings, render to file, capture viewport screenshot.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
from collections.abc import Callable
from typing import Any

import bpy

from ..bridge import bridge

logger = logging.getLogger(__name__)

_VALID_ENGINES = {"CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"}


def _validate_path(path: str, param: str) -> None:
    """Reject empty paths and path traversal components."""
    if not path:
        raise ValueError(f"{param} must not be empty")
    if ".." in os.path.normpath(path).split(os.sep):
        raise ValueError(f"{param} must not contain '..' path traversal components")


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
    """Register all render tools onto the FastMCP instance."""

    @mcp.tool()
    async def set_render_settings(
        engine: str | None = None,
        resolution_x: int | None = None,
        resolution_y: int | None = None,
        samples: int | None = None,
        output_path: str | None = None,
    ) -> str:
        """Configure render settings on the active scene.

        engine must be one of: CYCLES, BLENDER_EEVEE_NEXT, BLENDER_WORKBENCH.
        All parameters are optional; only provided values are changed.
        """

        def _do():
            scene = bpy.context.scene
            if engine is not None:
                engine_upper = engine.upper()
                if engine_upper not in _VALID_ENGINES:
                    valid = ", ".join(sorted(_VALID_ENGINES))
                    raise ValueError(f"Unknown engine '{engine}'. Valid values: {valid}")
                scene.render.engine = engine_upper
            if resolution_x is not None:
                scene.render.resolution_x = resolution_x
            if resolution_y is not None:
                scene.render.resolution_y = resolution_y
            if samples is not None:
                if scene.render.engine == "CYCLES":
                    scene.cycles.samples = samples
                else:
                    scene.eevee.taa_render_samples = samples
            if output_path is not None:
                _validate_path(output_path, "output_path")
                scene.render.filepath = output_path
            return {
                "engine": scene.render.engine,
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                "output_path": scene.render.filepath,
            }

        return await _run_tool("set_render_settings", _do)

    @mcp.tool()
    async def render_image(filepath: str, file_format: str = "PNG") -> str:
        """Render the active scene to a file.

        filepath is the output path (absolute or Blender-relative).
        file_format defaults to PNG; other common values: JPEG, OPEN_EXR.
        Note: this blocks Blender's main thread for the duration of the render.
        """

        def _do():
            _validate_path(filepath, "filepath")
            scene = bpy.context.scene
            scene.render.filepath = filepath
            scene.render.image_settings.file_format = file_format.upper()
            bpy.ops.render.render(write_still=True)
            return {
                "filepath": filepath,
                "format": file_format.upper(),
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            }

        return await _run_tool("render_image", _do)

    @mcp.tool()
    async def screenshot_viewport(filepath: str) -> str:
        """Save the current 3D viewport as an image without rendering.

        filepath is the output path for the screenshot PNG.
        Raises if no VIEW_3D area is found in the current screen.
        """

        def _do():
            _validate_path(filepath, "filepath")
            for area in bpy.context.screen.areas:
                if area.type == "VIEW_3D":
                    with bpy.context.temp_override(area=area):
                        bpy.ops.screen.screenshot_area(
                            filepath=filepath, check_existing=False
                        )
                    return {"filepath": filepath, "area_type": "VIEW_3D"}
            raise RuntimeError("No VIEW_3D area found in the current screen layout")

        return await _run_tool("screenshot_viewport", _do)
