"""Unit tests for input validation in all tool modules.

Tools are tested by calling their registered functions via a minimal FastMCP instance.
The mock_bridge fixture makes run_on_main_thread execute _do() synchronously,
so validation errors are returned as JSON {"error": "...", "tool": "..."}.
"""

from __future__ import annotations

import json
import os
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

    # Use a MagicMock for scenes so we can control __contains__
    scenes_mock = MagicMock()
    scenes_mock.__contains__ = MagicMock(return_value=False)
    mock_bpy.data.scenes = scenes_mock

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


async def test_transform_object_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "transform_object", name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_transform_object_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import objects

    mock_bpy.data.objects.get.return_value = None
    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "transform_object", name="Missing")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_duplicate_object_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "duplicate_object", name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_duplicate_object_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import objects

    mock_bpy.data.objects.get.return_value = None
    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "duplicate_object", name="Missing")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_parent_objects_empty_names(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "parent_objects", child_name="", parent_name="Parent")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_parent_objects_child_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import objects

    mock_bpy.data.objects.get.return_value = None
    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "parent_objects", child_name="Child", parent_name="Parent")
    assert is_error(result)
    assert "child" in result["error"].lower()


async def test_parent_objects_parent_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import objects

    child = MagicMock()
    mock_bpy.data.objects.get.side_effect = (
        lambda n: child if n == "Child" else None
    )
    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "parent_objects", child_name="Child", parent_name="Missing")
    mock_bpy.data.objects.get.side_effect = None  # prevent leak to subsequent tests
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_create_object_grid_invalid_type(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object_grid",
                        type="INVALID", name_prefix="Grid", count=[2, 2, 1])
    assert is_error(result)
    assert "unknown type" in result["error"].lower()


async def test_create_object_grid_empty_prefix(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object_grid",
                        type="MESH_CUBE", name_prefix="", count=[2, 2, 1])
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_create_object_grid_invalid_count(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object_grid",
                        type="MESH_CUBE", name_prefix="G", count=[2, 2])
    assert is_error(result)
    assert "count" in result["error"].lower()


async def test_create_object_grid_count_zero(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object_grid",
                        type="MESH_CUBE", name_prefix="G", count=[2, 0, 1])
    assert is_error(result)
    assert "count" in result["error"].lower()


async def test_create_objects_batch_empty_list(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_objects_batch", objects=[])
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_create_objects_batch_missing_type(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_objects_batch",
                        objects=[{"name": "Obj", "type": "INVALID_TYPE"}])
    # batch records errors per-entry, does not raise globally
    assert result.get("count") == 0
    assert len(result.get("errors", [])) == 1


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
    # Construct a path that is always outside ~ regardless of CWD or home location.
    # dirname(realpath(~)) is the parent of the home directory (e.g. /home on Linux,
    # C:\Users on Windows), so any path there is guaranteed outside _ALLOWED_OUTPUT_BASE.
    outside_home = os.path.join(
        os.path.dirname(os.path.realpath(os.path.expanduser("~"))),
        "etc",
        "outside.txt",
    )
    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "render_image", filepath=outside_home)
    assert is_error(result)
    assert "outside" in result["error"].lower() or "allowed" in result["error"].lower()


async def test_render_image_absolute_path_outside_home(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "render_image", filepath="/etc/passwd")
    assert is_error(result)
    assert "outside" in result["error"].lower()


async def test_render_image_blender_relative_path_accepted(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    scene = MagicMock()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    mock_bpy.context.scene = scene

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "render_image", filepath="//output.png")
    assert "error" not in result


async def test_render_image_home_subdir_accepted(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    scene = MagicMock()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    mock_bpy.context.scene = scene

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    home_path = os.path.join(os.path.expanduser("~"), "renders", "output.png")
    result = await call(mcp, "render_image", filepath=home_path)
    assert "error" not in result


async def test_screenshot_viewport_absolute_path_outside_home(
    mock_bridge: MagicMock,
) -> None:
    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "screenshot_viewport", filepath="/tmp/vuln.png")
    assert is_error(result)
    assert "outside" in result["error"].lower()


async def test_set_render_settings_absolute_path_outside_home(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mock_bpy.context.scene.render.engine = "CYCLES"

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "set_render_settings", output_path="/etc/cron.d/evil")
    assert is_error(result)
    assert "outside" in result["error"].lower()


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


async def test_add_modifiers_batch_empty_list(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "add_modifiers_batch", object_names=[], modifier_type="SUBSURF")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_add_modifiers_batch_empty_modifier_type(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "add_modifiers_batch", object_names=["Cube"], modifier_type="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_apply_modifiers_batch_empty_list(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "apply_modifiers_batch", object_names=[], modifier_name="Subsurf")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_apply_modifiers_batch_empty_modifier_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "apply_modifiers_batch", object_names=["Cube"], modifier_name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_remove_modifiers_batch_empty_list(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "remove_modifiers_batch", object_names=[], modifier_name="Subsurf")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_remove_modifiers_batch_empty_modifier_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "remove_modifiers_batch", object_names=["Cube"], modifier_name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


# ---------------------------------------------------------------------------
# nodes tools — validation and error branches
# ---------------------------------------------------------------------------


async def test_list_shader_nodes_not_using_nodes(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import nodes

    mat = MagicMock()
    mat.use_nodes = False
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "list_shader_nodes", material_name="Mat")
    assert is_error(result)


async def test_connect_nodes_output_index_out_of_range(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import nodes

    src = MagicMock()
    src.outputs = []  # empty — index 0 is out of range
    dst = MagicMock()
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "A" else dst
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="A", from_output="0",
                        to_node="B", to_input="Color")
    assert is_error(result)
    assert "out of range" in result["error"].lower()


async def test_connect_nodes_input_index_out_of_range(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import nodes

    out_socket = MagicMock()
    src = MagicMock()
    src.outputs = [out_socket]
    dst = MagicMock()
    dst.inputs = []  # empty — index 0 is out of range
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "A" else dst
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="A", from_output="0",
                        to_node="B", to_input="0")
    assert is_error(result)
    assert "out of range" in result["error"].lower()


async def test_connect_nodes_named_socket_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import nodes

    src = MagicMock()
    src.outputs.get.return_value = None  # named socket not found
    dst = MagicMock()
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "A" else dst
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="A", from_output="NoSuchOutput",
                        to_node="B", to_input="Color")
    assert is_error(result)


async def test_connect_nodes_named_input_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import nodes

    out_socket = MagicMock()
    src = MagicMock()
    src.outputs.get.return_value = out_socket
    dst = MagicMock()
    dst.inputs.get.return_value = None  # named input not found
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "A" else dst
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="A", from_output="Color",
                        to_node="B", to_input="NoSuchInput")
    assert is_error(result)


async def test_add_shader_node_empty_material(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "add_shader_node", material_name="", node_type="ShaderNodeTexChecker")
    assert is_error(result)


async def test_add_shader_node_empty_node_type(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import nodes

    mock_bpy.data.materials.get.return_value = MagicMock()
    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "add_shader_node", material_name="Mat", node_type="")
    assert is_error(result)


async def test_connect_nodes_src_not_found(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    from blender_addon.tools import nodes

    nt = MagicMock()
    nt.nodes.get.return_value = None  # neither src nor dst found
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="NoSrc", from_output="Color",
                        to_node="BSDF", to_input="Base Color")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_connect_nodes_dst_not_found(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    from blender_addon.tools import nodes

    src = MagicMock()
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "Src" else None
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="Src", from_output="Color",
                        to_node="NoDst", to_input="Base Color")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_set_material_property_invalid_prop(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    bsdf = MagicMock()
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = bsdf
    mock_bpy.data.materials.get.return_value = mat

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="nonexistent", value=0.5)
    assert is_error(result)
    assert "unknown property" in result["error"].lower()


async def test_assign_material_object_no_material_support(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    obj = MagicMock()
    obj.type = "CAMERA"
    obj.data = None  # cameras have no material slots
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material",
                        object_name="Camera", material_name="Mat")
    assert is_error(result)


async def test_assign_material_empty_object_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material", object_name="", material_name="Mat")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_assign_material_empty_material_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material", object_name="Cube", material_name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_assign_material_object_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    mock_bpy.data.objects.get.return_value = None
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material",
                        object_name="Missing", material_name="Mat")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_assign_material_material_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    obj = MagicMock()
    mock_bpy.data.objects.get.return_value = obj
    mock_bpy.data.materials.get.return_value = None
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material",
                        object_name="Cube", material_name="Missing")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_assign_materials_batch_empty(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_materials_batch", assignments=[])
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_create_material_invalid_property(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    mat = MagicMock()
    mat.name = "Mat"
    mock_bpy.data.materials.new.return_value = mat
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "create_material", name="Mat",
                        properties={"unknown_prop": 0.5})
    assert is_error(result)
    assert "unknown property" in result["error"].lower()


async def test_set_material_property_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="", prop="roughness", value=0.5)
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_set_material_property_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    mock_bpy.data.materials.get.return_value = None
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Missing", prop="roughness", value=0.5)
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_set_material_property_no_nodes(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    mat = MagicMock()
    mat.use_nodes = False
    mock_bpy.data.materials.get.return_value = mat
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="roughness", value=0.5)
    assert is_error(result)
    assert "nodes" in result["error"].lower()


async def test_set_material_property_no_bsdf(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = None
    mock_bpy.data.materials.get.return_value = mat
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="roughness", value=0.5)
    assert is_error(result)
    assert "bsdf" in result["error"].lower()


async def test_set_material_property_socket_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    bsdf = MagicMock()
    bsdf.inputs.get.return_value = None
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = bsdf
    mock_bpy.data.materials.get.return_value = mat
    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="roughness", value=0.5)
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_set_material_property_color_bad_value(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import materials

    bsdf = MagicMock()
    bsdf.inputs.get.return_value = MagicMock()
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = bsdf
    mock_bpy.data.materials.get.return_value = mat
    mcp = make_mcp()
    materials.register(mcp)
    # base_color is a color prop — must be 4-component
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="base_color", value=[1.0, 0.0, 0.0])
    assert is_error(result)
    assert "4-component" in result["error"].lower()


# ---------------------------------------------------------------------------
# lighting tools
# ---------------------------------------------------------------------------


async def test_configure_light_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import lighting

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light", name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_configure_light_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import lighting

    mock_bpy.data.objects.get.return_value = None

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light", name="NoSuchLight")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_configure_light_not_light(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import lighting

    obj = MagicMock()
    obj.type = "MESH"
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light", name="Cube")
    assert is_error(result)
    assert "not a light" in result["error"].lower()


async def test_configure_light_invalid_type(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import lighting

    obj = MagicMock()
    obj.type = "LIGHT"
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light", name="Light", light_type="LASER")
    assert is_error(result)
    assert "invalid light_type" in result["error"].lower()


async def test_configure_light_invalid_color(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import lighting

    obj = MagicMock()
    obj.type = "LIGHT"
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light", name="Light", color=[1.0, 0.0])
    assert is_error(result)
    assert "3 components" in result["error"].lower()


async def test_configure_light_spot_on_non_spot(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import lighting

    obj = MagicMock()
    obj.type = "LIGHT"
    obj.data.type = "POINT"
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light", name="Light", spot_size=1.0)
    assert is_error(result)
    assert "spot" in result["error"].lower()


# ---------------------------------------------------------------------------
# camera tools
# ---------------------------------------------------------------------------


async def test_set_active_camera_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import camera

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "set_active_camera", name="")
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_set_active_camera_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import camera

    mock_bpy.data.objects.get.return_value = None

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "set_active_camera", name="NoSuchCam")
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_set_active_camera_not_camera(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import camera

    obj = MagicMock()
    obj.type = "MESH"
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "set_active_camera", name="Cube")
    assert is_error(result)
    assert "not a camera" in result["error"].lower()


async def test_look_at_empty_name(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import camera

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "look_at", name="", target=[0.0, 0.0, 0.0])
    assert is_error(result)
    assert "empty" in result["error"].lower()


async def test_look_at_not_found(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import camera

    mock_bpy.data.objects.get.return_value = None

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "look_at", name="NoSuchObj", target=[0.0, 0.0, 0.0])
    assert is_error(result)
    assert "not found" in result["error"].lower()


async def test_look_at_invalid_target(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import camera

    obj = MagicMock()
    mock_bpy.data.objects.get.return_value = obj

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "look_at", name="Camera", target=[0.0, 0.0])
    assert is_error(result)
    assert "3 components" in result["error"].lower()


# ---------------------------------------------------------------------------
# world tools
# ---------------------------------------------------------------------------


async def test_set_world_settings_no_params(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import world

    mcp = make_mcp()
    world.register(mcp)
    result = await call(mcp, "set_world_settings")
    assert is_error(result)
    assert "at least one" in result["error"].lower()


async def test_set_world_settings_invalid_color(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    from blender_addon.tools import world

    mcp = make_mcp()
    world.register(mcp)
    result = await call(mcp, "set_world_settings", background_color=[1.0, 0.0, 0.0])
    assert is_error(result)
    assert "4 components" in result["error"].lower()


# ---------------------------------------------------------------------------
# scripting tools
# ---------------------------------------------------------------------------


async def test_execute_python_empty_code(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import scripting

    mcp = make_mcp()
    scripting.register(mcp)
    result = await call(mcp, "execute_python", code="")
    assert is_error(result)
    assert "non-empty" in result["error"].lower()


# ---------------------------------------------------------------------------
# execute_python — restricted mode blocking tests
# ---------------------------------------------------------------------------


async def _call_restricted(code: str, mock_bridge: MagicMock) -> dict:  # type: ignore[type-arg]
    """Helper: call execute_python in restricted mode and return parsed result."""
    from blender_addon import server as server_mod
    from blender_addon.tools import scripting

    original = server_mod.execute_python_unrestricted
    server_mod.execute_python_unrestricted = False
    try:
        mcp = make_mcp()
        scripting.register(mcp)
        return await call(mcp, "execute_python", code=code)
    finally:
        server_mod.execute_python_unrestricted = original


async def test_execute_python_restricted_blocks_os_import(mock_bridge: MagicMock) -> None:
    result = await _call_restricted("import os", mock_bridge)
    assert is_error(result)
    assert "not allowed" in result["error"].lower()


async def test_execute_python_restricted_blocks_subprocess(mock_bridge: MagicMock) -> None:
    result = await _call_restricted("import subprocess", mock_bridge)
    assert is_error(result)
    assert "not allowed" in result["error"].lower()


async def test_execute_python_restricted_blocks_socket(mock_bridge: MagicMock) -> None:
    result = await _call_restricted("import socket", mock_bridge)
    assert is_error(result)
    assert "not allowed" in result["error"].lower()


async def test_execute_python_restricted_blocks_open(mock_bridge: MagicMock) -> None:
    # open() is not in SAFE_BUILTINS, so it raises NameError
    result = await _call_restricted("open('/tmp/x', 'r')", mock_bridge)
    assert is_error(result)


async def test_execute_python_restricted_blocks_dunder_import(mock_bridge: MagicMock) -> None:
    # __import__ in restricted mode is the safe wrapper; importing os must fail
    result = await _call_restricted("__import__('os')", mock_bridge)
    assert is_error(result)
    assert "not allowed" in result["error"].lower()


async def test_execute_python_restricted_reports_mode(mock_bridge: MagicMock) -> None:
    result = await _call_restricted("__result__ = 42", mock_bridge)
    assert result.get("mode") == "restricted"


# ---------------------------------------------------------------------------
# modifier settings guards (_apply_modifier_settings)
# ---------------------------------------------------------------------------


def test_apply_modifier_settings_rejects_dunder_keys() -> None:
    from blender_addon.tools.modifiers import _apply_modifier_settings

    # Use a real object so we can confirm __class__ was NOT overwritten
    class FakeMod:
        type = "SUBSURF"
        levels = 1

    mod = FakeMod()
    original_class = mod.__class__
    _apply_modifier_settings(mod, {"__class__": int, "__dict__": {}})
    assert mod.__class__ is original_class  # dunder write was blocked


def test_apply_modifier_settings_clamps_large_int() -> None:
    from blender_addon.tools.modifiers import _MAX_NUMERIC_VALUE, _apply_modifier_settings

    class FakeMod:
        type = "SUBSURF"
        levels = 1

    mod = FakeMod()
    _apply_modifier_settings(mod, {"levels": 2_000_000_000})
    assert mod.levels == _MAX_NUMERIC_VALUE


def test_apply_modifier_settings_clamps_large_float() -> None:
    from blender_addon.tools.modifiers import _MAX_NUMERIC_VALUE, _apply_modifier_settings

    class FakeMod:
        type = "SUBSURF"
        width = 0.5

    mod = FakeMod()
    _apply_modifier_settings(mod, {"width": 1e12})
    assert mod.width == _MAX_NUMERIC_VALUE


def test_apply_modifier_settings_allows_normal_int() -> None:
    from blender_addon.tools.modifiers import _apply_modifier_settings

    class FakeMod:
        type = "SUBSURF"
        levels = 1

    mod = FakeMod()
    _apply_modifier_settings(mod, {"levels": 3})
    assert mod.levels == 3


def test_apply_modifier_settings_allows_bool_unchanged() -> None:
    from blender_addon.tools.modifiers import _apply_modifier_settings

    class FakeMod:
        type = "SUBSURF"
        use_custom_normals = False

    mod = FakeMod()
    _apply_modifier_settings(mod, {"use_custom_normals": True})
    assert mod.use_custom_normals is True  # bool not clamped


def test_apply_modifier_settings_skips_unknown_keys() -> None:
    from blender_addon.tools.modifiers import _apply_modifier_settings

    class FakeMod:
        type = "SUBSURF"

    mod = FakeMod()
    _apply_modifier_settings(mod, {"nonexistent_key": 42})
    assert not hasattr(mod, "nonexistent_key")


async def test_add_modifier_dunder_key_rejected(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mod = MagicMock()
    mod.name = 'Subsurf'
    mod.type = 'SUBSURF'
    obj = MagicMock()
    obj.modifiers.new.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    # Dunder key should not reach setattr
    result = await call(mcp, 'add_modifier',
                        object_name='Cube', modifier_type='SUBSURF',
                        settings={'__class__': 'evil'})
    assert 'error' not in result
    # The mock should not have had __class__ set via setattr
    # (MagicMock does not record dunder setattr by default, so we just check no exception)


async def test_add_modifier_extreme_levels_clamped(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:

    mod = MagicMock()
    mod.name = 'Subsurf'
    mod.type = 'SUBSURF'
    mod.levels = 1
    obj = MagicMock()
    obj.modifiers.new.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    # levels=2000000000 should be clamped to _MAX_NUMERIC_VALUE, not raise
    result = await call(mcp, 'add_modifier',
                        object_name='Cube', modifier_type='SUBSURF',
                        settings={'levels': 2_000_000_000})
    assert 'error' not in result
