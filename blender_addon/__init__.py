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


def _on_allow_execute_python_update(self, context: bpy.types.Context) -> None:  # pragma: no cover
    """Dynamically register execute_python on the running server when preference is toggled."""
    if not self.allow_execute_python:
        logger.info("execute_python disabled — restart add-on to deregister the tool")
        return
    if server_module.mcp is None:
        return  # server not started yet; register() will handle it
    from .tools import scripting  # noqa: PLC0415

    scripting.register(server_module.mcp)
    logger.info("execute_python tool registered at runtime")


def _on_unrestricted_update(self, context: bpy.types.Context) -> None:  # pragma: no cover
    """Update the execute_python execution mode at runtime when the preference changes."""
    server_module.execute_python_unrestricted = self.execute_python_unrestricted
    mode = "unrestricted (YOLO)" if self.execute_python_unrestricted else "restricted"
    logger.info("execute_python mode changed to %s", mode)


class BlenderMCPPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    port: bpy.props.IntProperty(  # type: ignore[assignment]
        name="Port",
        description="Port on which the MCP HTTP server listens",
        default=8400,
        min=1024,
        max=65535,
    )

    allow_execute_python: bpy.props.BoolProperty(  # type: ignore[assignment]
        name="Allow execute_python Tool (DANGEROUS)",
        description=(
            "WARNING: Enables the execute_python MCP tool, which lets connected "
            "AI clients run Python code inside Blender. Default restricted mode "
            "blocks filesystem, network, and subprocess access. "
            "Only enable if you trust ALL connected MCP clients."
        ),
        default=False,
        update=_on_allow_execute_python_update,
    )

    execute_python_unrestricted: bpy.props.BoolProperty(  # type: ignore[assignment]
        name="Unrestricted Mode (YOLO) — EXTREMELY DANGEROUS",
        description=(
            "WARNING: Removes ALL sandbox restrictions from execute_python. "
            "Connected clients gain FULL access to the filesystem, network, "
            "subprocess execution, and the entire Python standard library — "
            "equivalent to running arbitrary code in a terminal with Blender's "
            "permissions. Only enable if you fully trust ALL connected clients "
            "and accept responsibility for any consequences. Use at your own risk!"
        ),
        default=False,
        update=_on_unrestricted_update,
    )

    def draw(self, context: bpy.types.Context) -> None:  # pragma: no cover  # Blender UI only
        self.layout.prop(self, "port")

        # execute_python section
        box = self.layout.box()
        box.alert = True
        col = box.column(align=True)
        col.label(text="SECURITY WARNING", icon="ERROR")
        col.label(text="execute_python lets AI clients run code inside Blender.")
        col.label(text="Default: restricted mode (no filesystem/network/subprocess).")
        col.label(text="Only enable if you trust ALL connected clients.")
        col.prop(self, "allow_execute_python")

        # YOLO mode sub-section — only visible when execute_python is enabled
        if self.allow_execute_python:
            yolo_box = box.box()
            yolo_box.alert = True
            yolo_col = yolo_box.column(align=True)
            yolo_col.label(text="UNRESTRICTED MODE (YOLO)", icon="ERROR")
            yolo_col.label(text="Removes ALL sandbox restrictions.")
            yolo_col.label(text="Grants full filesystem, network & subprocess access.")
            yolo_col.label(text="Equivalent to running code directly in a terminal.")
            yolo_col.prop(self, "execute_python_unrestricted")


def register() -> None:
    bpy.utils.register_class(BlenderMCPPreferences)

    prefs = bpy.context.preferences.addons[__name__].preferences
    port: int = prefs.port  # type: ignore[assignment]
    allow_execute_python: bool = prefs.allow_execute_python  # type: ignore[assignment]
    unrestricted: bool = prefs.execute_python_unrestricted  # type: ignore[assignment]

    bridge_module.bridge = bridge_module.MainThreadBridge()
    bridge_module.bridge.start()

    server_module.setup(
        port=port, allow_execute_python=allow_execute_python, unrestricted=unrestricted
    )
    server_module.start()

    logger.info("Blender MCP Server registered, port=%d", port)


def unregister() -> None:
    server_module.stop()

    if bridge_module.bridge is not None:
        bridge_module.bridge.stop()
        bridge_module.bridge = None

    bpy.utils.unregister_class(BlenderMCPPreferences)

    logger.info("Blender MCP Server unregistered")
