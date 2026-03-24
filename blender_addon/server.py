"""
MCP server setup and lifecycle management.

Creates the FastMCP instance, registers all tool modules, and runs the server
in a background daemon thread using Streamable HTTP transport on localhost:8400.
"""

from __future__ import annotations

import logging
import threading

from mcp.server.fastmcp import FastMCP

from .tools import register_all

logger = logging.getLogger(__name__)

# Module-level singletons — set by setup()
mcp: FastMCP | None = None
_server_thread: threading.Thread | None = None
PORT: int = 8400


def setup(port: int = 8400, allow_execute_python: bool = False) -> None:
    """Instantiate the FastMCP server and register all tool modules."""
    global mcp, PORT

    PORT = port
    mcp = FastMCP("blender-mcp", host="127.0.0.1", port=port)
    register_all(mcp, allow_execute_python=allow_execute_python)
    logger.info("MCP server configured on port %d", port)


def start() -> None:
    """Start the MCP server in a background daemon thread."""
    global _server_thread

    if mcp is None:
        raise RuntimeError("Call setup() before start()")

    def _run() -> None:
        mcp.run(transport="streamable-http")  # type: ignore[union-attr]

    _server_thread = threading.Thread(target=_run, daemon=True, name="mcp-server")
    _server_thread.start()
    logger.info("MCP server starting on http://localhost:%d/mcp", PORT)


def stop() -> None:
    """Signal the MCP server to shut down and wait for the thread to exit."""
    # FastMCP (uvicorn-backed) will exit when the daemon thread is abandoned on process end.
    # For explicit teardown we join with a short timeout.
    if _server_thread is not None and _server_thread.is_alive():
        _server_thread.join(timeout=5)
    logger.info("MCP server stopped")
