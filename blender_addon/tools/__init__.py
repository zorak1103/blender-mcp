"""
Tool registry: imports all tool modules and provides register_all() to wire them onto
the shared FastMCP server instance.
"""

from __future__ import annotations

from . import (
    animation,
    camera,
    lighting,
    materials,
    modifiers,
    nodes,
    objects,
    render,
    scene,
    world,
)


def register_all(mcp, allow_execute_python: bool = False) -> None:
    """Register all tool modules onto the given FastMCP instance."""
    modules = [
        scene, objects, materials, render, nodes, modifiers, animation, lighting, camera, world,
    ]
    for module in modules:
        module.register(mcp)
    if allow_execute_python:  # pragma: no cover  # tested via E2E with Blender preference enabled
        from . import scripting  # noqa: PLC0415

        scripting.register(mcp)
