"""
Modifier stack tools: add, configure, apply, remove modifiers, list modifier stack.
"""

from __future__ import annotations

import logging
from typing import Any

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all modifier tools onto the FastMCP instance."""

    @mcp.tool()
    async def list_modifiers(object_name: str) -> str:
        """List all modifiers on an object with their type and visibility flags."""

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            return [
                {
                    "name": m.name,
                    "type": m.type,
                    "show_viewport": m.show_viewport,
                    "show_render": m.show_render,
                }
                for m in obj.modifiers
            ]

        return await run_tool("list_modifiers", _do)

    @mcp.tool()
    async def add_modifier(
        object_name: str,
        modifier_type: str,
        settings: dict = {},  # noqa: B006
    ) -> str:
        """Add a modifier to an object and optionally configure its settings.

        modifier_type is a Blender modifier type string, e.g. 'SUBSURF', 'SOLIDIFY',
        'BEVEL', 'ARRAY', 'BOOLEAN', 'MIRROR', 'DECIMATE'.
        settings is an optional dict of modifier attribute names to values.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not modifier_type:
                raise ValueError("modifier_type must not be empty")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            mod = obj.modifiers.new(name=modifier_type.title(), type=modifier_type.upper())
            for key, val in settings.items():
                if hasattr(mod, key):
                    setattr(mod, key, val)
                else:
                    logger.warning("Modifier '%s' has no attribute '%s'", mod.type, key)
            return {"name": mod.name, "type": mod.type}

        return await run_tool("add_modifier", _do)

    @mcp.tool()
    async def remove_modifier(object_name: str, modifier_name: str) -> str:
        """Remove a named modifier from an object."""

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not modifier_name:
                raise ValueError("modifier_name must not be empty")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            mod = obj.modifiers.get(modifier_name)
            if mod is None:
                raise ValueError(
                    f"Modifier '{modifier_name}' not found on '{object_name}'"
                )
            obj.modifiers.remove(mod)
            return {"removed": modifier_name, "object": object_name}

        return await run_tool("remove_modifier", _do)

    @mcp.tool()
    async def configure_modifier(
        object_name: str,
        modifier_name: str,
        settings: dict,
    ) -> str:
        """Update one or more properties on an existing modifier.

        settings is a dict of modifier attribute names to new values.
        Unknown keys are logged as warnings and skipped.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not modifier_name:
                raise ValueError("modifier_name must not be empty")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            mod = obj.modifiers.get(modifier_name)
            if mod is None:
                raise ValueError(
                    f"Modifier '{modifier_name}' not found on '{object_name}'"
                )
            updated: dict[str, Any] = {}
            for key, val in settings.items():
                if hasattr(mod, key):
                    setattr(mod, key, val)
                    updated[key] = val
                else:
                    logger.warning("Modifier '%s' has no attribute '%s'", mod.type, key)
            return {"modifier": modifier_name, "updated": updated}

        return await run_tool("configure_modifier", _do)

    @mcp.tool()
    async def apply_modifier(object_name: str, modifier_name: str) -> str:
        """Apply (bake) a modifier, removing it from the stack but keeping geometry changes.

        The object must be a mesh and will be set as the active object.
        """

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not modifier_name:
                raise ValueError("modifier_name must not be empty")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            if obj.modifiers.get(modifier_name) is None:
                raise ValueError(
                    f"Modifier '{modifier_name}' not found on '{object_name}'"
                )
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=modifier_name)
            return {"applied": modifier_name, "object": object_name}

        return await run_tool("apply_modifier", _do)
