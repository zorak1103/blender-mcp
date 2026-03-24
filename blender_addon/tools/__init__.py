"""
Tool registry: imports all tool modules and provides register_all() to wire them onto
the shared FastMCP server instance.
"""

from __future__ import annotations

from . import animation, materials, modifiers, nodes, objects, render, scene


def register_all(mcp) -> None:
    """Register all tool modules onto the given FastMCP instance."""
    for module in [scene, objects, materials, render, nodes, modifiers, animation]:
        module.register(mcp)
