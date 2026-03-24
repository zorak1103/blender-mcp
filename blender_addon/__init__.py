"""
Blender MCP Server add-on entry point.

Registers the add-on with Blender, starts the main-thread bridge and the MCP HTTP server
on enable, and tears everything down on disable.
"""

from __future__ import annotations

import logging

import bpy

from . import bridge as bridge_module
from . import server as server_module

logger = logging.getLogger(__name__)

bl_info = {
    "name": "Blender MCP Server",
    "author": "blender-mcp",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "category": "System",
    "description": "Exposes Blender via MCP (Model Context Protocol) over HTTP",
}


class BlenderMCPPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    port: bpy.props.IntProperty(  # type: ignore[assignment]
        name="Port",
        description="Port on which the MCP HTTP server listens",
        default=8400,
        min=1024,
        max=65535,
    )

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "port")


def register() -> None:
    bpy.utils.register_class(BlenderMCPPreferences)

    prefs = bpy.context.preferences.addons[__name__].preferences
    port: int = prefs.port  # type: ignore[assignment]

    bridge_module.bridge = bridge_module.MainThreadBridge()
    bridge_module.bridge.start()

    server_module.setup(port=port)
    server_module.start()

    logger.info("Blender MCP Server registered, port=%d", port)


def unregister() -> None:
    server_module.stop()

    if bridge_module.bridge is not None:
        bridge_module.bridge.stop()
        bridge_module.bridge = None

    bpy.utils.unregister_class(BlenderMCPPreferences)

    logger.info("Blender MCP Server unregistered")
