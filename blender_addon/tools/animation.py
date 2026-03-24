"""
Animation tools: insert/delete keyframes, set frame range, set current frame, set FPS.
"""

from __future__ import annotations

import logging

# bpy is imported inside closures to avoid import-time errors in non-Blender environments

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all animation tools onto the FastMCP instance."""
    pass  # replaced with actual @mcp.tool() registrations in Phase 4
