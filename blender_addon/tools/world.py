"""
World/background control tools: set background color and strength.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all world tools onto the FastMCP instance."""

    @mcp.tool()
    async def set_world_settings(
        background_color: list[float] | None = None,
        strength: float | None = None,
    ) -> str:
        """Configure the world background color and/or strength.

        background_color is RGBA (4 components). strength controls the emission intensity.
        At least one parameter must be provided.
        """

        def _do():
            if background_color is None and strength is None:
                raise ValueError("At least one of background_color or strength must be provided")
            if background_color is not None and len(background_color) != 4:
                raise ValueError("background_color must have exactly 4 components (RGBA)")

            world = bpy.context.scene.world
            if world is None:
                world = bpy.data.worlds.new("World")
                bpy.context.scene.world = world
            world.use_nodes = True

            bg = world.node_tree.nodes.get("Background")
            if bg is None:
                raise ValueError("World node tree has no Background node")

            if background_color is not None:
                bg.inputs["Color"].default_value = tuple(background_color)
            if strength is not None:
                bg.inputs["Strength"].default_value = strength

            return {
                "background_color": list(bg.inputs["Color"].default_value),
                "strength": bg.inputs["Strength"].default_value,
            }

        return await run_tool("set_world_settings", _do)
