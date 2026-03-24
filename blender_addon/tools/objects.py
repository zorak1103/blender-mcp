"""
Object CRUD and transform tools: create, delete, transform, duplicate, select, parent.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)


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

        return await run_tool("create_object", _do)

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

        return await run_tool("delete_objects", _do)

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

        return await run_tool("transform_object", _do)

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

        return await run_tool("duplicate_object", _do)

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

        return await run_tool("select_objects", _do)

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

        return await run_tool("parent_objects", _do)

    @mcp.tool()
    async def create_object_grid(
        type: str,
        name_prefix: str,
        count: list[int],
        spacing: list[float] = [2.0, 2.0, 2.0],  # noqa: B006
        origin: list[float] = [0.0, 0.0, 0.0],  # noqa: B006
        scale: list[float] = [1.0, 1.0, 1.0],  # noqa: B006
    ) -> str:
        """Create a 3-D grid of objects in a single call.

        type must be one of: MESH_CUBE, MESH_SPHERE, MESH_CYLINDER, MESH_PLANE,
        MESH_CONE, MESH_TORUS, CAMERA, LIGHT, EMPTY.
        count is [nx, ny, nz] — number of objects along each axis (each >= 1).
        Objects are named {name_prefix}_{ix}_{iy}_{iz}.
        """

        def _do():
            if not name_prefix:
                raise ValueError("name_prefix must not be empty")
            op = _TYPE_MAP.get(type.upper())
            if op is None:
                raise ValueError(f"Unknown type '{type}'. Valid types: {', '.join(_TYPE_MAP)}")
            if len(count) != 3 or any(c < 1 for c in count):
                raise ValueError("count must have exactly 3 elements, each >= 1")
            if len(spacing) != 3:
                raise ValueError("spacing must have exactly 3 elements")  # pragma: no cover
            if len(origin) != 3:
                raise ValueError("origin must have exactly 3 elements")  # pragma: no cover
            if len(scale) != 3:
                raise ValueError("scale must have exactly 3 elements")  # pragma: no cover

            created = []
            for ix in range(count[0]):
                for iy in range(count[1]):
                    for iz in range(count[2]):
                        loc = (
                            origin[0] + ix * spacing[0],
                            origin[1] + iy * spacing[1],
                            origin[2] + iz * spacing[2],
                        )
                        op(location=loc)
                        obj = bpy.context.active_object
                        obj.name = f"{name_prefix}_{ix}_{iy}_{iz}"
                        obj.scale = tuple(scale)
                        created.append(obj.name)

            return {"created": created, "count": len(created), "grid": list(count)}

        return await run_tool("create_object_grid", _do)

    @mcp.tool()
    async def create_objects_batch(
        objects: list[dict],
    ) -> str:
        """Create multiple objects in a single call.

        Each dict: {"type": str, "name": str, "location"?: [x,y,z],
                    "rotation"?: [x,y,z], "scale"?: [x,y,z]}
        type must be one of: MESH_CUBE, MESH_SPHERE, MESH_CYLINDER, MESH_PLANE,
        MESH_CONE, MESH_TORUS, CAMERA, LIGHT, EMPTY.
        Per-object failures are recorded in "errors" and do not abort the batch.
        """

        def _do():
            if not objects:
                raise ValueError("objects list must not be empty")

            created = []
            errors = []
            for entry in objects:
                obj_name = entry.get("name", "")
                try:
                    obj_type = entry.get("type", "")
                    if not obj_name:
                        raise ValueError("name must not be empty")  # pragma: no cover
                    op = _TYPE_MAP.get(str(obj_type).upper())
                    if op is None:
                        raise ValueError(
                            f"Unknown type '{obj_type}'. Valid types: {', '.join(_TYPE_MAP)}"
                        )
                    loc = tuple(entry.get("location", [0.0, 0.0, 0.0]))
                    rot = tuple(entry.get("rotation", [0.0, 0.0, 0.0]))
                    sc = tuple(entry.get("scale", [1.0, 1.0, 1.0]))
                    op(location=loc)
                    obj = bpy.context.active_object
                    obj.name = obj_name
                    obj.rotation_euler = rot
                    obj.scale = sc
                    created.append(obj.name)
                except Exception as exc:
                    errors.append({"name": obj_name or "?", "error": str(exc)})

            return {"created": created, "errors": errors, "count": len(created)}

        return await run_tool("create_objects_batch", _do)
