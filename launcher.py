"""
Thin stdio-to-HTTP proxy for Claude Code integration.

Claude Code launches MCP servers via stdio. Blender pollutes stdout on startup,
so this launcher runs as a clean separate process, forwarding JSON-RPC messages
from stdin to the Blender MCP HTTP server and writing responses back to stdout.

IMPORTANT: This process must NEVER write anything to stdout except MCP JSON responses.
All logging goes to stderr.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import httpx

# All log output goes to stderr — stdout must carry only MCP JSON
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [launcher] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

BLENDER_MCP_URL = "http://localhost:8400/mcp"
RETRY_INTERVAL = 1.0   # seconds between connection attempts
RETRY_TIMEOUT = 60.0   # total seconds to wait for Blender to become ready


async def wait_for_blender() -> None:
    """Poll the Blender MCP endpoint until it responds or the timeout is exceeded."""
    elapsed = 0.0
    async with httpx.AsyncClient() as client:
        while elapsed < RETRY_TIMEOUT:
            try:
                response = await client.get(BLENDER_MCP_URL, timeout=5.0)
                if response.status_code < 500:
                    logger.info("Blender MCP server is ready (status %d)", response.status_code)
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            logger.info("Waiting for Blender MCP server... (%.0fs elapsed)", elapsed)
            await asyncio.sleep(RETRY_INTERVAL)
            elapsed += RETRY_INTERVAL
    raise RuntimeError(
        f"Blender MCP server not reachable after {RETRY_TIMEOUT:.0f}s. "
        "Make sure Blender is running with the add-on enabled."
    )


async def proxy_request(client: httpx.AsyncClient, line: bytes) -> bytes:
    """POST a raw JSON-RPC line to the Blender MCP server and return the response body."""
    try:
        response = await client.post(
            BLENDER_MCP_URL,
            content=line,
            headers={"Content-Type": "application/json"},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.content
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error from Blender MCP: %s", exc)
        error = {"error": {"code": exc.response.status_code, "message": str(exc)}}
        return json.dumps(error).encode()
    except Exception as exc:
        logger.error("Proxy error: %s", exc)
        error = {"error": {"code": -32000, "message": str(exc)}}
        return json.dumps(error).encode()


async def main() -> None:
    """Main event loop: wait for Blender, then proxy stdin → HTTP → stdout."""
    await wait_for_blender()

    loop = asyncio.get_event_loop()
    async with httpx.AsyncClient() as client:
        while True:
            line = await loop.run_in_executor(None, sys.stdin.buffer.readline)
            if not line:
                break  # EOF — Claude Code closed the pipe
            line = line.rstrip(b"\n")
            if not line:
                continue
            response = await proxy_request(client, line)
            sys.stdout.buffer.write(response + b"\n")
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    asyncio.run(main())
