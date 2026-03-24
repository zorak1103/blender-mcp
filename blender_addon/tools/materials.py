"""
Material tools: create materials, assign to objects, list materials, set Principled BSDF properties.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)

_PROP_MAP = {
    "base_color": "Base Color",
    "metallic": "Metallic",
    "roughness": "Roughness",
    "emission": "Emission Color",
    "alpha": "Alpha",
}

_COLOR_PROPS = {"base_color", "emission"}


def register(mcp) -> None:
    """Register all material tools onto the FastMCP instance."""

    @mcp.tool()
    async def create_material(
        name: str,
        color: list[float] = [0.8, 0.8, 0.8, 1.0],  # noqa: B006
    ) -> str:
        """Create a new material with a Principled BSDF node set to the given base color (RGBA)."""

        def _do():
            if not name:
                raise ValueError("name must not be empty")
            if len(color) != 4:
                raise ValueError("color must have 4 components (RGBA)")
            mat = bpy.data.materials.new(name=name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = tuple(color)
            return {"name": mat.name}

        return await run_tool("create_material", _do)

    @mcp.tool()
    async def assign_material(object_name: str, material_name: str) -> str:
        """Assign a material to an object (replaces slot 0 or appends if no slots exist)."""

        def _do():
            if not object_name:
                raise ValueError("object_name must not be empty")
            if not material_name:
                raise ValueError("material_name must not be empty")
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError(f"Object '{object_name}' not found")
            if obj.data is None or not hasattr(obj.data, "materials"):
                raise ValueError(
                    f"Object '{object_name}' does not support materials (type: {obj.type})"
                )
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            return {"object": object_name, "material": material_name}

        return await run_tool("assign_material", _do)

    @mcp.tool()
    async def list_materials() -> str:
        """List all materials in the blend file."""

        def _do():
            return [{"name": m.name, "use_nodes": m.use_nodes} for m in bpy.data.materials]

        return await run_tool("list_materials", _do)

    @mcp.tool()
    async def set_material_property(
        material_name: str,
        prop: str,
        value: float | list[float],
    ) -> str:
        """Set a Principled BSDF input on a material.

        prop must be one of: base_color, metallic, roughness, emission, alpha.
        value is a float for scalar inputs or a list[float] for color inputs.
        """

        def _do():
            if not material_name:
                raise ValueError("material_name must not be empty")
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if not mat.use_nodes:
                raise ValueError(f"Material '{material_name}' does not use nodes")
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf is None:
                raise ValueError(f"No Principled BSDF node found in '{material_name}'")
            input_name = _PROP_MAP.get(prop.lower())
            if input_name is None:
                raise ValueError(
                    f"Unknown property '{prop}'. Valid values: {', '.join(_PROP_MAP)}"
                )
            socket = bsdf.inputs.get(input_name)
            if socket is None:
                raise ValueError(f"Input '{input_name}' not found on Principled BSDF")
            if prop.lower() in _COLOR_PROPS:
                if not isinstance(value, (list, tuple)) or len(value) != 4:
                    raise ValueError(f"Property '{prop}' requires a 4-component RGBA list")
            socket.default_value = value
            return {"material": material_name, "property": prop, "value": value}

        return await run_tool("set_material_property", _do)
