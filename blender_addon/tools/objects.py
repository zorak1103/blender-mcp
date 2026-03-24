"""
Object CRUD and transform tools: create, delete, transform, duplicate, select, parent.
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


_TYPE_MAP = {
    "MESH_CUBE": lambda **kw: bpy.ops.mesh.primitive_cube_add(**kw),
    "MESH_SPHERE": lambda **kw: bpy.ops.mesh.primitive_uv_sphere_add(**kw),
    "MESH_CYLINDER": lambda **kw: bpy.ops.mesh.primitive_cylinder_add(**kw),
    "MESH_PLANE": lambda **kw: bpy.ops.mesh.primitive_plane_add(**kw),
    "MESH_CONE": lambda **kw: bpy.ops.mesh.primitive_cone_add(**kw),
    "MESH_TORUS": lambda **kw: bpy.ops.mesh.primitive_torus_add(**kw),
    "CAMERA": lambda **kw: bpy.ops.object.camera_add(**kw),
    "LIGHT": lambda **kw: bpy.ops.object.light_add(**kw),
    "EMPTY": lambda **kw: bpy.ops.object.empty_add(**kw),
}


def register(mcp) -> None:
    """Register all object tools onto the FastMCP instance."""

    @mcp.tool()
    async def create_object(
        type: str,
        name: str,
        location: list[float] = [0.0, 0.0, 0.0],
        rotation: list[float] = [0.0, 0.0, 0.0],
        scale: list[float] = [1.0, 1.0, 1.0],
    ) -> str:
        """Create a new object of the given type.

        type must be one of: MESH_CUBE, MESH_SPHERE, MESH_CYLINDER, MESH_PLANE,
        MESH_CONE, MESH_TORUS, CAMERA, LIGHT, EMPTY.
        """

        def _do():
            if not name:
                raise ValueError("name must not be empty")
            if len(location) != 3:
                raise ValueError("location must have 3 components")
            op = _TYPE_MAP.get(type.upper())
            if op is None:
                raise ValueError(
                    f"Unknown type '{type}'. Valid types: {', '.join(_TYPE_MAP)}"
                )
            op(location=tuple(location))
            obj = bpy.context.active_object
            obj.name = name
            obj.rotation_euler = tuple(rotation)
            obj.scale = tuple(scale)
            return {"name": obj.name, "type": obj.type, "location": list(obj.location)}

        return await _run_tool("create_object", _do)

    @mcp.tool()
    async def delete_objects(names: list[str]) -> str:
        """Delete objects by name. Returns lists of deleted and not-found names."""

        def _do():
            bpy.ops.object.select_all(action="DESELECT")
            not_found = []
            for n in names:
                obj = bpy.data.objects.get(n)
                if obj:
                    obj.select_set(True)
                else:
                    not_found.append(n)
            bpy.ops.object.delete()
            deleted = [n for n in names if n not in not_found]
            return {"deleted": deleted, "not_found": not_found}

        return await _run_tool("delete_objects", _do)

    @mcp.tool()
    async def transform_object(
        name: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> str:
        """Set the location, rotation (Euler XYZ radians), and/or scale of an object."""

        def _do():
            if not name:
                raise ValueError("name must not be empty")
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Object '{name}' not found")
            if location is not None:
                obj.location = tuple(location)
            if rotation is not None:
                obj.rotation_euler = tuple(rotation)
            if scale is not None:
                obj.scale = tuple(scale)
            return {
                "name": obj.name,
                "location": list(obj.location),
                "rotation_euler": list(obj.rotation_euler),
                "scale": list(obj.scale),
            }

        return await _run_tool("transform_object", _do)

    @mcp.tool()
    async def duplicate_object(name: str, linked: bool = False) -> str:
        """Duplicate an object. If linked=True, the duplicate shares mesh data with the original."""

        def _do():
            if not name:
                raise ValueError("name must not be empty")
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Object '{name}' not found")
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate(linked=linked)
            new_obj = bpy.context.active_object
            return {"original": name, "duplicate": new_obj.name, "linked": linked}

        return await _run_tool("duplicate_object", _do)

    @mcp.tool()
    async def select_objects(names: list[str], deselect_others: bool = True) -> str:
        """Select objects by name. Optionally deselect all others first."""

        def _do():
            if deselect_others:
                bpy.ops.object.select_all(action="DESELECT")
            selected, not_found = [], []
            for n in names:
                obj = bpy.data.objects.get(n)
                if obj:
                    obj.select_set(True)
                    selected.append(n)
                else:
                    not_found.append(n)
            return {"selected": selected, "not_found": not_found}

        return await _run_tool("select_objects", _do)

    @mcp.tool()
    async def parent_objects(
        child_name: str, parent_name: str, keep_transform: bool = True
    ) -> str:
        """Parent child_name to parent_name.

        If keep_transform=True, the child's world position is preserved.
        """

        def _do():
            if not child_name or not parent_name:
                raise ValueError("child_name and parent_name must not be empty")
            child = bpy.data.objects.get(child_name)
            parent = bpy.data.objects.get(parent_name)
            if child is None:
                raise ValueError(f"Object '{child_name}' not found")
            if parent is None:
                raise ValueError(f"Object '{parent_name}' not found")
            child.parent = parent
            if keep_transform:
                child.matrix_parent_inverse = parent.matrix_world.inverted()
            return {"child": child_name, "parent": parent_name}

        return await _run_tool("parent_objects", _do)
