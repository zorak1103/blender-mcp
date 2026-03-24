"""
Tool registry: imports all tool modules and provides register_all() to wire them onto
the shared FastMCP server instance.
"""

from __future__ import annotations

from . import animation, camera, lighting, materials, modifiers, nodes, objects, render, scene


def register_all(mcp) -> None:
    """Register all tool modules onto the given FastMCP instance."""
    modules = [scene, objects, materials, render, nodes, modifiers, animation, lighting, camera]
    for module in modules:
        module.register(mcp)
