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
