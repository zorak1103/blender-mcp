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
        properties: dict | None = None,
    ) -> str:
        """Create a new material with a Principled BSDF node set to the given base color (RGBA).

        properties: optional dict of Principled BSDF inputs to set inline,
            e.g. {"metallic": 0.9, "roughness": 0.1}. Valid keys: base_color,
            metallic, roughness, emission, alpha.
        """

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
            if properties is not None:
                if bsdf is None:  # pragma: no cover  # impossible: new materials always have BSDF
                    raise ValueError("No Principled BSDF node found in new material")
                for prop_key, value in properties.items():
                    input_name = _PROP_MAP.get(prop_key.lower())
                    if input_name is None:
                        valid = ", ".join(_PROP_MAP)
                        raise ValueError(f"Unknown property '{prop_key}'. Valid: {valid}")
                    if prop_key.lower() in _COLOR_PROPS:
                        if (  # pragma: no cover
                            not isinstance(value, (list, tuple)) or len(value) != 4
                        ):
                            raise ValueError(
                                f"Property '{prop_key}' requires 4-component RGBA list"
                            )
                    bsdf.inputs[input_name].default_value = value
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
    async def assign_materials_batch(
        assignments: list[dict],
    ) -> str:
        """Assign materials to multiple objects in a single call.

        Each dict: {"object_name": str, "material_name": str}
        Per-assignment failures are recorded in "errors" and do not abort the batch.
        """

        def _do():
            if not assignments:
                raise ValueError("assignments list must not be empty")

            assigned = []
            errors = []
            for entry in assignments:
                obj_name = entry.get("object_name", "")
                mat_name = entry.get("material_name", "")
                try:
                    if not obj_name:
                        raise ValueError("object_name must not be empty")  # pragma: no cover
                    if not mat_name:
                        raise ValueError("material_name must not be empty")  # pragma: no cover
                    obj = bpy.data.objects.get(obj_name)
                    if obj is None:
                        raise ValueError(f"Object '{obj_name}' not found")
                    if obj.data is None or not hasattr(obj.data, "materials"):
                        raise ValueError(  # pragma: no cover
                            f"Object '{obj_name}' does not support materials (type: {obj.type})"
                        )
                    mat = bpy.data.materials.get(mat_name)
                    if mat is None:
                        raise ValueError(f"Material '{mat_name}' not found")  # pragma: no cover
                    if obj.data.materials:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
                    assigned.append({"object": obj_name, "material": mat_name})
                except Exception as exc:
                    errors.append(
                        {"object": obj_name or "?", "material": mat_name or "?", "reason": str(exc)}
                    )

            return {"assigned": assigned, "errors": errors, "count": len(assigned)}

        return await run_tool("assign_materials_batch", _do)

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
