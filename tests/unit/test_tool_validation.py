"""Unit tests for input validation in all tool modules.

Tools are tested by calling their registered functions via a minimal FastMCP instance.
The mock_bridge fixture makes run_on_main_thread execute _do() synchronously,
so validation errors are returned as JSON {"error": "...", "tool": "..."}.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mcp() -> MagicMock:
    """Return a MagicMock that captures @mcp.tool() decorated functions."""
    registered: dict[str, object] = {}
    mcp = MagicMock()

    def tool_decorator():  # type: ignore[no-untyped-def]
        def capture(fn):  # type: ignore[no-untyped-def]
            registered[fn.__name__] = fn
            return fn

        return capture

    mcp.tool = tool_decorator
    mcp._registered = registered
    return mcp


async def call(mcp: MagicMock, tool: str, **kwargs: object) -> dict:  # type: ignore[type-arg]
    fn = mcp._registered[tool]
    raw = await fn(**kwargs)  # type: ignore[operator]
    return json.loads(raw)  # type: ignore[arg-type]


def is_error(result: dict) -> bool:  # type: ignore[type-arg]
    return "error" in result


# ---------------------------------------------------------------------------
# scene tools
# ---------------------------------------------------------------------------


async def test_get_object_info_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import scene

    mcp = make_mcp()
    scene.register(mcp)
    result = await call(mcp, "get_object_info", name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_get_scene_info_nonexistent_scene(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import scene

    mock_bpy.data.scenes.__contains__ = MagicMock(return_value=False)
    mock_bpy.data.scenes.__getitem__ = MagicMock(side_effect=KeyError("No Scene"))

    mcp = make_mcp()
    scene.register(mcp)
    result = await call(mcp, "get_scene_info", scene_name="NonExistentScene")
    assert is_error(result)


# ---------------------------------------------------------------------------
# objects tools
# ---------------------------------------------------------------------------


async def test_create_object_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object", type="MESH_CUBE", name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_create_object_invalid_type(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object", type="INVALID_TYPE", name="x")
    assert is_error(result)
    assert "unknown type" in result["error"].lower()


async def test_create_object_wrong_location_length(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object", type="MESH_CUBE", name="x", location=[1.0, 2.0])
    assert is_error(result)
    assert "3" in result["error"]


# ---------------------------------------------------------------------------
# materials tools
# ---------------------------------------------------------------------------


async def test_create_material_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "create_material", name="", color=[1.0, 0.0, 0.0, 1.0])
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_create_material_wrong_color_length(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "create_material", name="Mat", color=[1.0, 0.0, 0.0])
    assert is_error(result)
    assert "4" in result["error"]


# ---------------------------------------------------------------------------
# render tools
# ---------------------------------------------------------------------------


async def test_render_image_empty_filepath(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "render_image", filepath="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_render_image_path_traversal(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "render_image", filepath="../../etc/passwd")
    assert is_error(result)
    assert ".." in result["error"]


async def test_set_render_settings_invalid_engine(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import render

    mock_bpy.context.scene.render.engine = "CYCLES"
    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "set_render_settings", engine="INVALID_ENGINE")
    assert is_error(result)
    assert "unknown engine" in result["error"].lower()


# ---------------------------------------------------------------------------
# animation tools
# ---------------------------------------------------------------------------


async def test_set_frame_range_end_before_start(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "set_frame_range", start=100, end=50)
    assert is_error(result)
    assert "end frame" in result["error"].lower()


async def test_set_fps_zero(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "set_fps", fps=0)
    assert is_error(result)
    assert "positive" in result["error"].lower()


async def test_insert_keyframe_empty_object_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "insert_keyframe", object_name="", data_path="location", frame=1)
    assert is_error(result)
    assert "empty" in result["error"].lower()


# ---------------------------------------------------------------------------
# modifiers tools
# ---------------------------------------------------------------------------


async def test_add_modifier_empty_object_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "add_modifier", object_name="", modifier_type="SUBSURF")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_remove_modifier_empty_modifier_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "remove_modifier", object_name="Cube", modifier_name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()
