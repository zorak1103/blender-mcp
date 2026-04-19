"""
MCP server setup and lifecycle management.

Creates the FastMCP instance, registers all tool modules, and runs the server
in a background daemon thread using Streamable HTTP transport on localhost:8400.

Authentication
--------------
A shared-secret Bearer token is generated on first start and written to
~/.config/blender-mcp/token (mode 0o600).  The launcher reads the same file
and injects the Authorization header on every forwarded request.  Any caller
that cannot present the token receives 401 Unauthorized.
"""

from __future__ import annotations

import logging
import pathlib
import secrets
import stat
import threading

from mcp.server.auth.middleware.bearer_auth import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from .tools import register_all

logger = logging.getLogger(__name__)

# Module-level singletons — set by setup()
mcp: FastMCP | None = None
_server_thread: threading.Thread | None = None
PORT: int = 8400

#: Whether execute_python runs without sandbox restrictions (YOLO mode).
#: Read at tool-call time by scripting.py so mode changes take effect immediately.
execute_python_unrestricted: bool = False

# Path where the shared-secret token is persisted between add-on restarts.
TOKEN_PATH: pathlib.Path = pathlib.Path.home() / ".config" / "blender-mcp" / "token"


def get_or_create_token() -> str:
    """Return the shared-secret Bearer token, creating it on first call.

    The token file is created with permissions 0o600 (owner read/write only).
    Subsequent calls return the existing token unchanged.
    """
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TOKEN_PATH.exists():
        TOKEN_PATH.write_text(secrets.token_hex(32), encoding="ascii")
        TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return TOKEN_PATH.read_text(encoding="ascii").strip()


class _StaticTokenVerifier:
    """TokenVerifier that accepts a single pre-shared secret."""

    def __init__(self, token: str) -> None:
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token == self._token:
            return AccessToken(
                token=token,
                client_id="blender-mcp-local",
                scopes=[],
                expires_at=None,
            )
        return None


def setup(
    port: int = 8400,
    allow_execute_python: bool = False,
    unrestricted: bool = False,
) -> None:
    """Instantiate the FastMCP server and register all tool modules."""
    global mcp, PORT, execute_python_unrestricted

    PORT = port
    execute_python_unrestricted = unrestricted

    token = get_or_create_token()
    base_url = f"http://127.0.0.1:{port}"
    mcp = FastMCP(
        "blender-mcp",
        host="127.0.0.1",
        port=port,
        auth=AuthSettings(
            issuer_url=base_url,  # type: ignore[arg-type]
            resource_server_url=f"{base_url}/mcp",  # type: ignore[arg-type]
        ),
        token_verifier=_StaticTokenVerifier(token),
    )
    register_all(mcp, allow_execute_python=allow_execute_python)
    logger.info("MCP server configured on port %d (token auth enabled)", port)


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
