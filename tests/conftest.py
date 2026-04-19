"""Shared test fixtures for blender-mcp unit and E2E tests.

IMPORTANT: bpy is injected into sys.modules at module load time (not in a fixture)
so that add-on modules can be imported during pytest collection without a Blender
runtime. All test modules that import blender_addon.* will pick up this mock.
"""

from __future__ import annotations

import concurrent.futures
import sys
from unittest.mock import MagicMock

import pytest


def _make_bpy_mock() -> MagicMock:
    """Create a MagicMock satisfying bpy attribute patterns used by the add-on."""
    bpy = MagicMock(name="bpy")

    # bpy.data collections
    bpy.data.objects.get.return_value = None
    bpy.data.scenes.__iter__ = MagicMock(return_value=iter([]))
    bpy.data.materials.get.return_value = None
    bpy.data.materials.__iter__ = MagicMock(return_value=iter([]))

    # bpy.context
    bpy.context.scene = MagicMock()
    bpy.context.scene.frame_current = 1
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 250
    bpy.context.scene.render.fps = 24
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.filepath = ""
    bpy.context.active_object = MagicMock()
    bpy.context.view_layer.objects.active = None
    bpy.context.screen.areas = []

    # bpy.app.timers
    bpy.app.timers.register = MagicMock()
    bpy.app.timers.unregister = MagicMock()
    bpy.app.timers.is_registered = MagicMock(return_value=True)

    return bpy


# ---------------------------------------------------------------------------
# Inject stubs at module load so blender_addon.* can be imported during
# pytest collection without a Blender or mcp runtime.
# ---------------------------------------------------------------------------

if "bpy" not in sys.modules:
    sys.modules["bpy"] = _make_bpy_mock()  # type: ignore[assignment]

# mathutils is Blender-only; stub it so camera.py can be imported and tested.
if "mathutils" not in sys.modules:
    _mathutils_mock = MagicMock(name="mathutils")

    class _Vector:
        """Minimal Vector stub for unit tests."""

        def __init__(self, coords):  # type: ignore[no-untyped-def]
            self._coords = tuple(coords)

        def __sub__(self, other):  # type: ignore[no-untyped-def]
            return _Vector(a - b for a, b in zip(self._coords, other._coords))

        def to_track_quat(self, track, up):  # type: ignore[no-untyped-def]
            _euler = MagicMock()
            _euler.__iter__ = MagicMock(return_value=iter([0.0, 0.0, 0.0]))
            quat = MagicMock()
            quat.to_euler.return_value = _euler
            return quat

    _mathutils_mock.Vector = _Vector
    sys.modules["mathutils"] = _mathutils_mock  # type: ignore[assignment]

# mcp is a Blender-side dependency; stub it so server.py can be imported.
# Include auth submodules needed by blender_addon.server's top-level imports.
for _mod in (
    "mcp",
    "mcp.server",
    "mcp.server.fastmcp",
    "mcp.server.auth",
    "mcp.server.auth.middleware",
    "mcp.server.auth.middleware.bearer_auth",
    "mcp.server.auth.settings",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock(name=_mod)  # type: ignore[assignment]


@pytest.fixture
def mock_bpy() -> MagicMock:
    """Return the bpy mock currently in sys.modules."""
    return sys.modules["bpy"]  # type: ignore[return-value]


@pytest.fixture
def mock_bridge(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the bridge singleton so run_on_main_thread executes fn() directly.

    This lets tool functions be tested without a running Blender instance.
    """
    fake = MagicMock(name="bridge")

    def run_sync(fn):  # type: ignore[no-untyped-def]
        fut: concurrent.futures.Future = concurrent.futures.Future()
        try:
            result = fn()
            fut.set_result(result)
        except Exception as exc:
            fut.set_exception(exc)
        return fut

    fake.run_on_main_thread = run_sync

    monkeypatch.setattr("blender_addon.bridge.bridge", fake)
    yield fake
