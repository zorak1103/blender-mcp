"""Shared async helpers for MCP tool modules."""

from __future__ import annotations

import concurrent.futures
import json
import logging
from collections.abc import Callable
from typing import Any

from .. import bridge as _bridge_module

logger = logging.getLogger(__name__)

TOOL_TIMEOUT = 30  # seconds


async def run_tool(tool_name: str, fn: Callable[[], Any]) -> str:
    """Run fn on Blender's main thread and return a JSON string.

    On success returns json.dumps(result). On timeout or any exception returns
    a JSON error object: {"error": "<message>", "tool": "<tool_name>"}.
    """
    try:
        fut = _bridge_module.bridge.run_on_main_thread(fn)  # type: ignore[union-attr]
        result = fut.result(timeout=TOOL_TIMEOUT)
        return json.dumps(result)
    except concurrent.futures.TimeoutError:
        msg = f"Main thread timeout after {TOOL_TIMEOUT}s"
        return json.dumps({"error": msg, "tool": tool_name})
    except Exception as exc:
        logger.exception("Tool %s failed", tool_name)
        return json.dumps({"error": str(exc), "tool": tool_name})
