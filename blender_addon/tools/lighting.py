"""
Light configuration tools: configure type, energy, color, and spot settings.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)

_VALID_LIGHT_TYPES = {"POINT", "SUN", "SPOT", "AREA"}


def register(mcp) -> None:
    """Register all lighting tools onto the FastMCP instance."""

    @mcp.tool()
    async def configure_light(
        name: str,
        light_type: str | None = None,
        energy: float | None = None,
        color: list[float] | None = None,
        radius: float | None = None,
        spot_size: float | None = None,
        spot_blend: float | None = None,
    ) -> str:
        """Configure properties of an existing light object.

        light_type must be one of: POINT, SUN, SPOT, AREA.
        color is RGB (3 components). spot_size is in radians; spot_blend is 0.0–1.0.
        spot_size and spot_blend are only valid when the light type is SPOT.
        """

        def _do():  # noqa: PLR0912
            if not name:
                raise ValueError("name must not be empty")
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Object '{name}' not found")
            if obj.type != "LIGHT":
                raise ValueError(f"Object '{name}' is not a light (type: {obj.type})")
            if light_type is not None and light_type.upper() not in _VALID_LIGHT_TYPES:
                valid = ", ".join(sorted(_VALID_LIGHT_TYPES))
                raise ValueError(f"Invalid light_type '{light_type}'. Valid: {valid}")
            if color is not None and len(color) != 3:
                raise ValueError("color must have exactly 3 components (RGB)")
            effective_type = light_type.upper() if light_type is not None else obj.data.type
            if (spot_size is not None or spot_blend is not None) and effective_type != "SPOT":
                raise ValueError("spot_size and spot_blend are only valid for SPOT lights")

            if light_type is not None:
                obj.data.type = light_type.upper()
            if energy is not None:
                obj.data.energy = energy
            if color is not None:
                obj.data.color = tuple(color)
            if radius is not None:
                obj.data.shadow_soft_size = radius
            if spot_size is not None:
                obj.data.spot_size = spot_size
            if spot_blend is not None:
                obj.data.spot_blend = spot_blend

            return {
                "name": name,
                "light_type": obj.data.type,
                "energy": obj.data.energy,
                "color": list(obj.data.color),
                "radius": obj.data.shadow_soft_size,
            }

        return await run_tool("configure_light", _do)
