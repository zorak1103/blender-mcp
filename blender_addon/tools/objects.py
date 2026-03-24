"""
Object CRUD and transform tools: create, delete, transform, duplicate, select, parent.
"""

from __future__ import annotations

import json
import logging

# bpy is imported inside closures to avoid import-time errors in non-Blender environments

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all object tools onto the FastMCP instance."""
    pass  # replaced with actual @mcp.tool() registrations in Phase 2
