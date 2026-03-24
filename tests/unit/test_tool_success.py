"""Happy-path unit tests for all tool modules.

Each test exercises the actual bpy logic inside _do() closures by providing
a configured mock_bpy. This brings tool module coverage from ~30% to ~80%+.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Reset shared bpy mock state before each test to prevent bleed-over
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_bpy(mock_bpy: MagicMock) -> None:
    """Replace data collection mocks with fresh instances before each test."""
    mock_bpy.data.objects = MagicMock()
    mock_bpy.data.objects.get.return_value = None
    mock_bpy.data.materials = MagicMock()
    mock_bpy.data.materials.get.return_value = None
    mock_bpy.data.materials.new = MagicMock()
    mock_bpy.data.materials.__iter__ = MagicMock(return_value=iter([]))
    mock_bpy.data.scenes = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mcp() -> MagicMock:
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


# ---------------------------------------------------------------------------
# scene tools — success paths
# ---------------------------------------------------------------------------


async def test_list_scenes_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    scene = MagicMock()
    scene.name = "Scene"
    scene.frame_start = 1
    scene.frame_end = 250
    scene.objects = [MagicMock(), MagicMock()]
    mock_bpy.data.scenes = [scene]

    from blender_addon.tools import scene as scene_mod

    mcp = make_mcp()
    scene_mod.register(mcp)
    result = await call(mcp, "list_scenes")
    assert isinstance(result, list)
    assert result[0]["name"] == "Scene"
    assert result[0]["object_count"] == 2


async def test_get_scene_info_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.name = "Cube"
    obj.type = "MESH"
    child_col = MagicMock()
    child_col.name = "Collection"
    scene = MagicMock()
    scene.name = "Scene"
    scene.objects = [obj]
    scene.collection.children_recursive = [child_col]
    scene.frame_start = 1
    scene.frame_end = 250
    scene.render.fps = 24
    mock_bpy.context.scene = scene

    from blender_addon.tools import scene as scene_mod

    mcp = make_mcp()
    scene_mod.register(mcp)
    result = await call(mcp, "get_scene_info")
    assert result["name"] == "Scene"
    assert result["fps"] == 24
    assert result["objects"][0]["name"] == "Cube"


async def test_list_objects_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.name = "Cube"
    obj.type = "MESH"
    obj.location = [0.0, 0.0, 0.0]
    obj.hide_viewport = False
    scene = MagicMock()
    scene.objects = [obj]
    mock_bpy.context.scene = scene

    from blender_addon.tools import scene as scene_mod

    mcp = make_mcp()
    scene_mod.register(mcp)
    result = await call(mcp, "list_objects")
    assert result[0]["name"] == "Cube"
    assert result[0]["visible"] is True


async def test_get_object_info_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mat = MagicMock()
    mat.name = "Material"
    obj = MagicMock()
    obj.name = "Cube"
    obj.type = "MESH"
    obj.location = [1.0, 2.0, 3.0]
    obj.rotation_euler = [0.0, 0.0, 0.0]
    obj.scale = [1.0, 1.0, 1.0]
    obj.dimensions = [2.0, 2.0, 2.0]
    obj.data.materials = [mat]
    obj.modifiers = []
    obj.parent = None
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import scene as scene_mod

    mcp = make_mcp()
    scene_mod.register(mcp)
    result = await call(mcp, "get_object_info", name="Cube")
    assert result["name"] == "Cube"
    assert result["materials"] == ["Material"]
    assert result["parent"] is None


# ---------------------------------------------------------------------------
# objects tools — success paths
# ---------------------------------------------------------------------------


async def test_create_object_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    active = MagicMock()
    active.name = "MyCube"
    active.type = "MESH"
    active.location = [1.0, 2.0, 3.0]
    mock_bpy.context.active_object = active

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object", type="MESH_CUBE", name="MyCube",
                        location=[1.0, 2.0, 3.0])
    assert result["name"] == "MyCube"


async def test_delete_objects_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.name = "Cube"
    mock_bpy.data.objects.get.side_effect = lambda n: obj if n == "Cube" else None

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "delete_objects", names=["Cube", "Ghost"])
    assert "Cube" in result["deleted"]
    assert "Ghost" in result["not_found"]


async def test_transform_object_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.name = "Cube"
    obj.location = [0.0, 0.0, 5.0]
    obj.rotation_euler = [0.0, 0.0, 0.0]
    obj.scale = [1.0, 1.0, 1.0]
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "transform_object", name="Cube", location=[0.0, 0.0, 5.0])
    assert result["name"] == "Cube"


async def test_duplicate_object_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.name = "Cube"
    new_obj = MagicMock()
    new_obj.name = "Cube.001"
    mock_bpy.data.objects.get.return_value = obj
    mock_bpy.context.active_object = new_obj

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "duplicate_object", name="Cube")
    assert result["original"] == "Cube"
    assert result["duplicate"] == "Cube.001"


async def test_select_objects_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    mock_bpy.data.objects.get.side_effect = lambda n: obj if n == "Cube" else None

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "select_objects", names=["Cube", "Missing"])
    assert "Cube" in result["selected"]
    assert "Missing" in result["not_found"]


async def test_parent_objects_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    child = MagicMock()
    parent = MagicMock()
    parent.matrix_world.inverted.return_value = MagicMock()
    mock_bpy.data.objects.get.side_effect = (
        lambda n: child if n == "Child" else parent if n == "Parent" else None
    )

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "parent_objects", child_name="Child", parent_name="Parent")
    assert result["child"] == "Child"
    assert result["parent"] == "Parent"


async def test_transform_object_with_rotation_scale(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    obj = MagicMock()
    obj.name = "Cube"
    obj.location = [0.0, 0.0, 0.0]
    obj.rotation_euler = [0.0, 0.0, 0.0]
    obj.scale = [1.0, 1.0, 1.0]
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "transform_object", name="Cube",
                        rotation=[0.1, 0.2, 0.3], scale=[2.0, 2.0, 2.0])
    assert "name" in result
    assert "rotation_euler" in result
    assert "scale" in result


async def test_create_object_grid_success(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    active_obj = MagicMock()
    active_obj.name = ""
    mock_bpy.context.active_object = active_obj

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_object_grid",
                        type="MESH_CUBE", name_prefix="G", count=[2, 2, 1])
    assert result["count"] == 4
    assert result["grid"] == [2, 2, 1]
    assert len(result["created"]) == 4


async def test_create_objects_batch_success(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    active_obj = MagicMock()
    active_obj.name = ""
    mock_bpy.context.active_object = active_obj

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_objects_batch", objects=[
        {"type": "MESH_CUBE", "name": "A"},
        {"type": "MESH_SPHERE", "name": "B"},
    ])
    assert result["count"] == 2
    assert result["errors"] == []


async def test_create_objects_batch_partial_failure(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    active_obj = MagicMock()
    active_obj.name = ""
    mock_bpy.context.active_object = active_obj

    from blender_addon.tools import objects

    mcp = make_mcp()
    objects.register(mcp)
    result = await call(mcp, "create_objects_batch", objects=[
        {"type": "INVALID", "name": "Bad"},
        {"type": "MESH_CUBE", "name": "Good"},
    ])
    assert result["count"] == 1
    assert len(result["errors"]) == 1


# ---------------------------------------------------------------------------
# materials tools — success paths
# ---------------------------------------------------------------------------


async def test_create_material_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mat = MagicMock()
    mat.name = "RedMat"
    mock_bpy.data.materials.new.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "create_material", name="RedMat", color=[1.0, 0.0, 0.0, 1.0])
    assert result["name"] == "RedMat"


async def test_assign_material_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mat = MagicMock()
    obj = MagicMock()
    obj.data.materials = []
    mock_bpy.data.objects.get.return_value = obj
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material",
                        object_name="Cube", material_name="RedMat")
    assert result["object"] == "Cube"
    assert result["material"] == "RedMat"


async def test_list_materials_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mat = MagicMock()
    mat.name = "Material"
    mat.use_nodes = True
    mock_bpy.data.materials = [mat]

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "list_materials")
    assert result[0]["name"] == "Material"
    assert result[0]["use_nodes"] is True


async def test_set_material_property_roughness(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    socket = MagicMock()
    bsdf = MagicMock()
    bsdf.inputs.get.return_value = socket
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = bsdf
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="roughness", value=0.5)
    assert result["property"] == "roughness"
    assert result["value"] == 0.5


async def test_set_material_property_color(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    socket = MagicMock()
    bsdf = MagicMock()
    bsdf.inputs.get.return_value = socket
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = bsdf
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "set_material_property",
                        material_name="Mat", prop="base_color", value=[1.0, 0.0, 0.0, 1.0])
    assert result["property"] == "base_color"


async def test_assign_material_replace_slot(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mat = MagicMock()
    obj = MagicMock()
    obj.data.materials = [MagicMock()]  # existing slot → triggers replace path
    mock_bpy.data.objects.get.return_value = obj
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_material",
                        object_name="Cube", material_name="RedMat")
    assert result["object"] == "Cube"
    assert result["material"] == "RedMat"


async def test_assign_materials_batch_success(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mat = MagicMock()
    obj = MagicMock()
    obj.data.materials = []
    mock_bpy.data.objects.get.return_value = obj
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_materials_batch", assignments=[
        {"object_name": "Cube", "material_name": "Mat"},
        {"object_name": "Sphere", "material_name": "Mat"},
    ])
    assert result["count"] == 2
    assert result["errors"] == []


async def test_assign_materials_batch_partial_failure(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mat = MagicMock()
    obj = MagicMock()
    obj.data.materials = []
    mock_bpy.data.objects.get.side_effect = (
        lambda n: obj if n == "Cube" else None
    )
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "assign_materials_batch", assignments=[
        {"object_name": "Missing", "material_name": "Mat"},
        {"object_name": "Cube", "material_name": "Mat"},
    ])
    assert result["count"] == 1
    assert len(result["errors"]) == 1


async def test_create_material_with_properties(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    input_metallic = MagicMock()
    input_roughness = MagicMock()
    bsdf = MagicMock()
    bsdf.inputs.__getitem__ = lambda self, k: (
        input_metallic if k == "Metallic" else input_roughness
    )
    mat = MagicMock()
    mat.name = "MetalMat"
    mat.node_tree.nodes.get.return_value = bsdf
    mock_bpy.data.materials.new.return_value = mat

    from blender_addon.tools import materials

    mcp = make_mcp()
    materials.register(mcp)
    result = await call(mcp, "create_material", name="MetalMat",
                        properties={"metallic": 0.9, "roughness": 0.1})
    assert result["name"] == "MetalMat"


# ---------------------------------------------------------------------------
# render tools — success paths
# ---------------------------------------------------------------------------


async def test_set_render_settings_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    scene = MagicMock()
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = "/tmp/out"
    mock_bpy.context.scene = scene

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "set_render_settings",
                        engine="CYCLES", resolution_x=1280, resolution_y=720)
    assert result["engine"] == "CYCLES"
    assert result["resolution"] == [1280, 720]


async def test_render_image_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    scene = MagicMock()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    mock_bpy.context.scene = scene

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "render_image", filepath="/tmp/test.png")
    assert result["filepath"] == "/tmp/test.png"
    assert result["format"] == "PNG"


async def test_screenshot_viewport_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    area = MagicMock()
    area.type = "VIEW_3D"
    mock_bpy.context.screen.areas = [area]
    mock_bpy.context.temp_override.return_value.__enter__ = MagicMock(return_value=None)
    mock_bpy.context.temp_override.return_value.__exit__ = MagicMock(return_value=False)

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "screenshot_viewport", filepath="/tmp/viewport.png")
    assert result["filepath"] == "/tmp/viewport.png"
    assert result["area_type"] == "VIEW_3D"


async def test_screenshot_viewport_no_view3d(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mock_bpy.context.screen.areas = []

    from blender_addon.tools import render

    mcp = make_mcp()
    render.register(mcp)
    result = await call(mcp, "screenshot_viewport", filepath="/tmp/viewport.png")
    assert "error" in result


# ---------------------------------------------------------------------------
# nodes tools — success paths
# ---------------------------------------------------------------------------


async def test_list_shader_nodes_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    inp = MagicMock()
    inp.name = "Base Color"
    inp.type = "RGBA"
    out = MagicMock()
    out.name = "BSDF"
    out.type = "SHADER"
    node = MagicMock()
    node.name = "Principled BSDF"
    node.type = "BSDF_PRINCIPLED"
    # location must return plain floats so json.dumps succeeds
    node.location = MagicMock()
    node.location.x = 0.0
    node.location.y = 0.0
    node.inputs = [inp]
    node.outputs = [out]
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes = [node]
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "list_shader_nodes", material_name="Mat")
    assert isinstance(result, list)
    assert result[0]["name"] == "Principled BSDF"


async def test_add_shader_node_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    new_node = MagicMock()
    new_node.name = "Checker Texture"
    new_node.type = "TEX_CHECKER"
    # add_shader_node does list(node.location) — needs an iterable of floats
    new_node.location = [0.0, 0.0]
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.new.return_value = new_node
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "add_shader_node",
                        material_name="Mat", node_type="ShaderNodeTexChecker")
    assert result["name"] == "Checker Texture"


async def test_connect_nodes_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    out_socket = MagicMock()
    in_socket = MagicMock()
    src = MagicMock()
    src.outputs.get.return_value = out_socket
    dst = MagicMock()
    dst.inputs.get.return_value = in_socket
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "Checker" else dst
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="Checker", from_output="Color",
                        to_node="BSDF", to_input="Base Color")
    assert "from" in result
    assert "to" in result


async def test_connect_nodes_by_index(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    out_socket = MagicMock()
    in_socket = MagicMock()
    src = MagicMock()
    src.outputs = [out_socket]
    dst = MagicMock()
    dst.inputs = [in_socket]
    nt = MagicMock()
    nt.nodes.get.side_effect = lambda n: src if n == "A" else dst
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree = nt
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "connect_nodes",
                        material_name="Mat", from_node="A", from_output="0",
                        to_node="B", to_input="0")
    assert "from" in result


async def test_remove_node_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    node = MagicMock()
    node.name = "Checker Texture"
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = node
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "remove_node", material_name="Mat", node_name="Checker Texture")
    assert result["removed"] == "Checker Texture"


async def test_set_node_value_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    socket = MagicMock()
    node = MagicMock()
    node.inputs.get.return_value = socket
    mat = MagicMock()
    mat.use_nodes = True
    mat.node_tree.nodes.get.return_value = node
    mock_bpy.data.materials.get.return_value = mat

    from blender_addon.tools import nodes

    mcp = make_mcp()
    nodes.register(mcp)
    result = await call(mcp, "set_node_value",
                        material_name="Mat", node_name="BSDF",
                        input_name="Roughness", value=0.3)
    assert result["value"] == 0.3


# ---------------------------------------------------------------------------
# modifiers tools — success paths
# ---------------------------------------------------------------------------


async def test_list_modifiers_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mod = MagicMock()
    mod.name = "Subsurf"
    mod.type = "SUBSURF"
    mod.show_viewport = True
    mod.show_render = True
    obj = MagicMock()
    obj.modifiers = [mod]
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "list_modifiers", object_name="Cube")
    assert result[0]["name"] == "Subsurf"
    assert result[0]["type"] == "SUBSURF"


async def test_add_modifier_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mod = MagicMock()
    mod.name = "Subsurf"
    mod.type = "SUBSURF"
    obj = MagicMock()
    obj.modifiers.new.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "add_modifier",
                        object_name="Cube", modifier_type="SUBSURF", settings={"levels": 2})
    assert result["name"] == "Subsurf"
    assert result["type"] == "SUBSURF"


async def test_remove_modifier_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mod = MagicMock()
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "remove_modifier",
                        object_name="Cube", modifier_name="Subsurf")
    assert result["removed"] == "Subsurf"
    assert result["object"] == "Cube"


async def test_configure_modifier_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mod = MagicMock(spec=["levels", "render_levels"])
    mod.levels = 1
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "configure_modifier",
                        object_name="Cube", modifier_name="Subsurf", settings={"levels": 3})
    assert result["modifier"] == "Subsurf"
    assert result["updated"]["levels"] == 3


async def test_apply_modifier_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mod = MagicMock()
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "apply_modifier",
                        object_name="Cube", modifier_name="Subsurf")
    assert result["applied"] == "Subsurf"
    assert result["object"] == "Cube"


async def test_add_modifiers_batch_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    mod = MagicMock()
    mod.name = "Subsurf"
    mod.type = "SUBSURF"
    obj = MagicMock()
    obj.modifiers.new.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "add_modifiers_batch",
                        object_names=["Cube", "Sphere"], modifier_type="SUBSURF",
                        settings={"levels": 2})
    assert result["count"] == 2
    assert result["errors"] == []
    assert len(result["added"]) == 2
    assert result["added"][0]["object"] == "Cube"
    assert result["added"][0]["modifier"] == "Subsurf"


async def test_add_modifiers_batch_partial_failure(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mod = MagicMock()
    mod.name = "Subsurf"
    mod.type = "SUBSURF"
    obj = MagicMock()
    obj.modifiers.new.return_value = mod
    mock_bpy.data.objects.get.side_effect = lambda n: obj if n == "Cube" else None

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "add_modifiers_batch",
                        object_names=["Missing", "Cube"], modifier_type="SUBSURF")
    assert result["count"] == 1
    assert len(result["errors"]) == 1
    assert result["errors"][0]["object"] == "Missing"


async def test_apply_modifiers_batch_success(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mod = MagicMock()
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "apply_modifiers_batch",
                        object_names=["Cube", "Sphere"], modifier_name="Subsurf")
    assert result["count"] == 2
    assert result["errors"] == []
    assert len(result["applied"]) == 2


async def test_apply_modifiers_batch_partial_failure(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mod = MagicMock()
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.side_effect = lambda n: obj if n == "Cube" else None

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "apply_modifiers_batch",
                        object_names=["Missing", "Cube"], modifier_name="Subsurf")
    assert result["count"] == 1
    assert len(result["errors"]) == 1
    assert result["errors"][0]["object"] == "Missing"


async def test_remove_modifiers_batch_success(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mod = MagicMock()
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "remove_modifiers_batch",
                        object_names=["Cube", "Sphere"], modifier_name="Subsurf")
    assert result["count"] == 2
    assert result["errors"] == []
    assert obj.modifiers.remove.call_count == 2


async def test_remove_modifiers_batch_partial_failure(
    mock_bridge: MagicMock, mock_bpy: MagicMock
) -> None:
    mod = MagicMock()
    obj = MagicMock()
    obj.modifiers.get.return_value = mod
    mock_bpy.data.objects.get.side_effect = lambda n: obj if n == "Cube" else None

    from blender_addon.tools import modifiers

    mcp = make_mcp()
    modifiers.register(mcp)
    result = await call(mcp, "remove_modifiers_batch",
                        object_names=["Missing", "Cube"], modifier_name="Subsurf")
    assert result["count"] == 1
    assert len(result["errors"]) == 1
    assert result["errors"][0]["object"] == "Missing"


# ---------------------------------------------------------------------------
# animation tools — success paths
# ---------------------------------------------------------------------------


async def test_set_frame_range_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    scene = MagicMock()
    scene.frame_start = 1
    scene.frame_end = 100
    mock_bpy.context.scene = scene

    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "set_frame_range", start=1, end=100)
    assert result["frame_start"] == 1
    assert result["frame_end"] == 100


async def test_set_current_frame_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    scene = MagicMock()
    scene.frame_current = 42
    mock_bpy.context.scene = scene

    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "set_current_frame", frame=42)
    assert result["current_frame"] == 42


async def test_set_fps_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    scene = MagicMock()
    scene.render.fps = 30
    mock_bpy.context.scene = scene

    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "set_fps", fps=30)
    assert result["fps"] == 30


async def test_insert_keyframe_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    mock_bpy.data.objects.get.return_value = obj
    scene = MagicMock()
    mock_bpy.context.scene = scene

    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "insert_keyframe",
                        object_name="Cube", data_path="location", frame=1)
    assert result["object"] == "Cube"
    assert result["frame"] == 1


async def test_delete_keyframe_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.keyframe_delete.return_value = True
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import animation

    mcp = make_mcp()
    animation.register(mcp)
    result = await call(mcp, "delete_keyframe",
                        object_name="Cube", data_path="location", frame=1)
    assert result["success"] is True


# ---------------------------------------------------------------------------
# lighting tools
# ---------------------------------------------------------------------------


async def test_configure_light_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.type = "LIGHT"
    obj.data.type = "POINT"
    obj.data.energy = 1000.0
    obj.data.color = [1.0, 0.8, 0.6]
    obj.data.shadow_soft_size = 0.25
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import lighting

    mcp = make_mcp()
    lighting.register(mcp)
    result = await call(mcp, "configure_light",
                        name="Sun", energy=1000.0, color=[1.0, 0.8, 0.6])
    assert result["name"] == "Sun"
    assert result["energy"] == 1000.0
    assert result["color"] == [1.0, 0.8, 0.6]


# ---------------------------------------------------------------------------
# camera tools — success paths
# ---------------------------------------------------------------------------


async def test_set_active_camera_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    obj = MagicMock()
    obj.type = "CAMERA"
    obj.name = "Camera"
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import camera

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "set_active_camera", name="Camera")
    assert result["active_camera"] == "Camera"
    assert mock_bpy.context.scene.camera == obj


async def test_look_at_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    euler = MagicMock()
    euler.__iter__ = MagicMock(return_value=iter([0.0, 0.0, 0.0]))
    obj = MagicMock()
    obj.name = "Camera"
    obj.location = MagicMock()
    obj.location.__sub__ = MagicMock(return_value=MagicMock())
    obj.rotation_euler = euler
    mock_bpy.data.objects.get.return_value = obj

    from blender_addon.tools import camera

    mcp = make_mcp()
    camera.register(mcp)
    result = await call(mcp, "look_at", name="Camera", target=[0.0, 0.0, 0.0])
    assert result["name"] == "Camera"
    assert result["target"] == [0.0, 0.0, 0.0]
    assert "rotation_euler" in result


# ---------------------------------------------------------------------------
# world tools — success paths
# ---------------------------------------------------------------------------


async def test_set_world_settings_success(mock_bridge: MagicMock, mock_bpy: MagicMock) -> None:
    color_input = MagicMock()
    color_input.default_value = [0.05, 0.05, 0.05, 1.0]
    strength_input = MagicMock()
    strength_input.default_value = 1.0
    bg_node = MagicMock()
    bg_node.inputs = {"Color": color_input, "Strength": strength_input}
    node_tree = MagicMock()
    node_tree.nodes.get.return_value = bg_node
    world_mock = MagicMock()
    world_mock.node_tree = node_tree
    mock_bpy.context.scene.world = world_mock

    from blender_addon.tools import world

    mcp = make_mcp()
    world.register(mcp)
    result = await call(mcp, "set_world_settings",
                        background_color=[0.1, 0.1, 0.1, 1.0], strength=0.8)
    assert "background_color" in result
    assert "strength" in result


# ---------------------------------------------------------------------------
# scripting tools — success paths
# ---------------------------------------------------------------------------


async def test_execute_python_success(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import scripting

    mcp = make_mcp()
    scripting.register(mcp)
    result = await call(mcp, "execute_python", code="__result__ = 42")
    assert result.get("status") == "ok"
    assert result.get("result") == 42


async def test_execute_python_no_result(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import scripting

    mcp = make_mcp()
    scripting.register(mcp)
    result = await call(mcp, "execute_python", code="x = 1 + 1")
    assert result.get("status") == "ok"
    assert result.get("result") is None


async def test_execute_python_runtime_error(mock_bridge: MagicMock) -> None:
    from blender_addon.tools import scripting

    mcp = make_mcp()
    scripting.register(mcp)
    result = await call(mcp, "execute_python", code="raise ValueError('oops')")
    assert "error" in result
    assert "oops" in result["error"]
    assert "traceback" in result
