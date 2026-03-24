"""End-to-end tests for the Blender MCP server.

These tests POST JSON-RPC requests directly to the HTTP endpoint at
localhost:8400 and require a running Blender instance with the add-on enabled.

Run with:
    pytest tests/e2e/ -v -m e2e

Skip if Blender is not running:
    pytest tests/ -v -m "not e2e"

Protocol notes:
  - FastMCP Streamable HTTP returns SSE-formatted responses (event: message / data: {...}).
  - All requests after initialization must include the mcp-session-id header.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

BASE_URL = "http://localhost:8400/mcp"
E2E_PREFIX = "E2E_"

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


# ---------------------------------------------------------------------------
# SSE / protocol helpers
# ---------------------------------------------------------------------------


def _parse_sse(response: httpx.Response) -> dict[str, Any]:
    """Extract the first JSON payload from an SSE-formatted response body."""
    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])  # type: ignore[no-any-return]
    raise ValueError(f"No 'data:' line found in SSE response: {response.text[:300]}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mcp_client() -> httpx.Client:
    """httpx client with an established MCP session (initialize handshake complete)."""
    client = httpx.Client(headers=MCP_HEADERS, timeout=30.0)

    # Step 1: initialize
    init_payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 0,
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "blender-mcp-e2e", "version": "0"},
        },
    }
    resp = client.post(BASE_URL, json=init_payload)
    session_id = resp.headers.get("mcp-session-id", "")
    assert session_id, f"No mcp-session-id in initialize response. Status: {resp.status_code}"

    # Step 2: pin session ID on the client for all subsequent requests
    client.headers["mcp-session-id"] = session_id

    # Step 3: send initialized notification (fire-and-forget, server may return 202)
    client.post(BASE_URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    return client


def call_tool(
    client: httpx.Client, tool_name: str, arguments: dict[str, Any] | None = None
) -> Any:
    """Call a Blender MCP tool and return the parsed result dict."""
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 1,
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }
    response = client.post(BASE_URL, json=payload)
    data = _parse_sse(response)
    # tools/call result shape: {"result": {"content": [{"type": "text", "text": "<json>"}]}}
    content = data.get("result", {}).get("content", [{}])
    if content and isinstance(content, list):
        text = content[0].get("text", "{}")
        return json.loads(text)
    return data


def send_rpc(client: httpx.Client, method: str, params: dict[str, Any] | None = None) -> Any:
    """Send a raw JSON-RPC request and return the parsed result."""
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1,
        "params": params or {},
    }
    response = client.post(BASE_URL, json=payload)
    return _parse_sse(response)


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_tools_list(mcp_client: httpx.Client) -> None:
    """The server must expose all expected tools."""
    data = send_rpc(mcp_client, "tools/list")
    tools = data.get("result", {}).get("tools", [])
    tool_names = {t["name"] for t in tools}

    expected = {
        # scene
        "list_scenes", "get_scene_info", "list_objects", "get_object_info",
        # objects
        "create_object", "delete_objects", "transform_object",
        "duplicate_object", "select_objects", "parent_objects",
        # materials
        "create_material", "assign_material", "list_materials", "set_material_property",
        # render
        "set_render_settings", "render_image", "screenshot_viewport",
        # shader nodes
        "list_shader_nodes", "add_shader_node", "connect_nodes", "remove_node", "set_node_value",
        # modifiers
        "list_modifiers", "add_modifier", "remove_modifier", "configure_modifier", "apply_modifier",
        # animation
        "set_frame_range", "set_current_frame", "set_fps", "insert_keyframe", "delete_keyframe",
        # lighting
        "configure_light",
        # camera
        "set_active_camera", "look_at",
        # world
        "set_world_settings",
        # scripting (opt-in, requires allow_execute_python=True in preferences)
        "execute_python",
    }
    missing = expected - tool_names
    assert not missing, f"Missing tools: {missing}"


@pytest.mark.e2e
def test_create_and_delete_object(mcp_client: httpx.Client) -> None:
    """Create a cube, verify it exists, then delete it."""
    cube_name = f"{E2E_PREFIX}TestCube"

    try:
        result = call_tool(mcp_client, "create_object", {
            "type": "MESH_CUBE",
            "name": cube_name,
            "location": [5.0, 5.0, 5.0],
        })
        assert "error" not in result, f"create_object failed: {result}"
        assert result.get("name") == cube_name

        objects = call_tool(mcp_client, "list_objects")
        assert "error" not in objects
        names = [o["name"] for o in objects]
        assert cube_name in names

        deleted = call_tool(mcp_client, "delete_objects", {"names": [cube_name]})
        assert "error" not in deleted
        assert cube_name in deleted.get("deleted", [])

        objects_after = call_tool(mcp_client, "list_objects")
        names_after = [o["name"] for o in objects_after]
        assert cube_name not in names_after

    except Exception:
        call_tool(mcp_client, "delete_objects", {"names": [cube_name]})
        raise


@pytest.mark.e2e
def test_material_workflow(mcp_client: httpx.Client) -> None:
    """Create a material, assign it to an object, verify the assignment."""
    mat_name = f"{E2E_PREFIX}TestMat"
    cube_name = f"{E2E_PREFIX}MatCube"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": cube_name})
        mat_result = call_tool(mcp_client, "create_material", {
            "name": mat_name,
            "color": [0.0, 0.0, 1.0, 1.0],
        })
        assert "error" not in mat_result

        assign_result = call_tool(mcp_client, "assign_material", {
            "object_name": cube_name,
            "material_name": mat_name,
        })
        assert "error" not in assign_result

        info = call_tool(mcp_client, "get_object_info", {"name": cube_name})
        assert "error" not in info
        assert mat_name in info.get("materials", [])

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [cube_name]})


@pytest.mark.e2e
def test_modifier_stack(mcp_client: httpx.Client) -> None:
    """Add a Subdivision Surface modifier, verify it, then remove it."""
    cube_name = f"{E2E_PREFIX}ModCube"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": cube_name})

        add_result = call_tool(mcp_client, "add_modifier", {
            "object_name": cube_name,
            "modifier_type": "SUBSURF",
            "settings": {"levels": 2},
        })
        assert "error" not in add_result
        mod_name = add_result.get("name", "Subsurf")

        mods = call_tool(mcp_client, "list_modifiers", {"object_name": cube_name})
        assert "error" not in mods
        assert mod_name in [m["name"] for m in mods]

        remove_result = call_tool(mcp_client, "remove_modifier", {
            "object_name": cube_name,
            "modifier_name": mod_name,
        })
        assert "error" not in remove_result

        mods_after = call_tool(mcp_client, "list_modifiers", {"object_name": cube_name})
        assert mod_name not in [m["name"] for m in mods_after]

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [cube_name]})


@pytest.mark.e2e
def test_animation_keyframes(mcp_client: httpx.Client) -> None:
    """Insert a keyframe, delete it, verify timeline operations."""
    cube_name = f"{E2E_PREFIX}AnimCube"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": cube_name})

        fr = call_tool(mcp_client, "set_frame_range", {"start": 1, "end": 100})
        assert "error" not in fr
        assert fr.get("frame_start") == 1
        assert fr.get("frame_end") == 100

        kf_insert = call_tool(mcp_client, "insert_keyframe", {
            "object_name": cube_name,
            "data_path": "location",
            "frame": 1,
        })
        assert "error" not in kf_insert

        kf_delete = call_tool(mcp_client, "delete_keyframe", {
            "object_name": cube_name,
            "data_path": "location",
            "frame": 1,
        })
        assert "error" not in kf_delete

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [cube_name]})


@pytest.mark.e2e
def test_screenshot_viewport(mcp_client: httpx.Client) -> None:
    """Capture the viewport; verify the response contains a filepath."""
    # Use a Windows temp path accessible from Blender's process
    filepath = "C:/Windows/Temp/e2e_blender_mcp_screenshot.png"

    result = call_tool(mcp_client, "screenshot_viewport", {"filepath": filepath})
    assert "error" not in result, f"screenshot_viewport failed: {result}"
    assert result.get("filepath") == filepath
    assert result.get("area_type") == "VIEW_3D"


@pytest.mark.e2e
def test_scene_inspection(mcp_client: httpx.Client) -> None:
    """list_scenes and get_scene_info return valid data for the active scene."""
    scenes = call_tool(mcp_client, "list_scenes")
    assert isinstance(scenes, list), f"Expected list, got: {scenes}"
    assert len(scenes) >= 1
    first = scenes[0]
    assert "name" in first
    assert "object_count" in first
    assert "frame_start" in first

    info = call_tool(mcp_client, "get_scene_info", {"scene_name": first["name"]})
    assert "error" not in info, f"get_scene_info failed: {info}"
    assert info.get("name") == first["name"]
    assert "objects" in info
    assert "fps" in info
    assert "frame_start" in info


@pytest.mark.e2e
def test_object_transform(mcp_client: httpx.Client) -> None:
    """transform_object updates location, rotation, and scale."""
    obj_name = f"{E2E_PREFIX}TransformCube"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": obj_name})

        result = call_tool(mcp_client, "transform_object", {
            "name": obj_name,
            "location": [1.0, 2.0, 3.0],
            "rotation": [0.1, 0.2, 0.3],
            "scale": [2.0, 2.0, 2.0],
        })
        assert "error" not in result, f"transform_object failed: {result}"
        assert result.get("location") == [1.0, 2.0, 3.0]
        assert result.get("scale") == [2.0, 2.0, 2.0]

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [obj_name]})


@pytest.mark.e2e
def test_object_duplicate_and_select(mcp_client: httpx.Client) -> None:
    """duplicate_object creates a copy; select_objects selects by name."""
    obj_name = f"{E2E_PREFIX}DupSource"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": obj_name})

        dup = call_tool(mcp_client, "duplicate_object", {"name": obj_name})
        assert "error" not in dup, f"duplicate_object failed: {dup}"
        dup_name = dup.get("duplicate")
        assert dup_name and dup_name != obj_name

        sel = call_tool(mcp_client, "select_objects", {"names": [obj_name]})
        assert "error" not in sel, f"select_objects failed: {sel}"
        assert obj_name in sel.get("selected", [])
        assert sel.get("not_found") == []

    finally:
        objects = call_tool(mcp_client, "list_objects")
        names = [o["name"] for o in objects] if isinstance(objects, list) else []
        to_delete = [n for n in [obj_name, dup.get("duplicate")] if n and n in names]
        if to_delete:
            call_tool(mcp_client, "delete_objects", {"names": to_delete})


@pytest.mark.e2e
def test_object_parent(mcp_client: httpx.Client) -> None:
    """parent_objects sets parent/child relationship."""
    parent_name = f"{E2E_PREFIX}Parent"
    child_name = f"{E2E_PREFIX}Child"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": parent_name})
        call_tool(mcp_client, "create_object", {
            "type": "MESH_SPHERE", "name": child_name, "location": [3.0, 0.0, 0.0],
        })

        result = call_tool(mcp_client, "parent_objects", {
            "child_name": child_name,
            "parent_name": parent_name,
        })
        assert "error" not in result, f"parent_objects failed: {result}"
        assert result.get("child") == child_name
        assert result.get("parent") == parent_name

        info = call_tool(mcp_client, "get_object_info", {"name": child_name})
        assert info.get("parent") == parent_name

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [child_name, parent_name]})


@pytest.mark.e2e
def test_material_list_and_property(mcp_client: httpx.Client) -> None:
    """list_materials enumerates materials; set_material_property updates BSDF inputs."""
    mat_name = f"{E2E_PREFIX}PropMat"

    try:
        call_tool(mcp_client, "create_material", {"name": mat_name, "color": [1.0, 0.0, 0.0, 1.0]})

        materials = call_tool(mcp_client, "list_materials")
        assert isinstance(materials, list), f"Expected list, got: {materials}"
        mat_names = [m["name"] for m in materials]
        assert mat_name in mat_names

        result = call_tool(mcp_client, "set_material_property", {
            "material_name": mat_name,
            "prop": "roughness",
            "value": 0.2,
        })
        assert "error" not in result, f"set_material_property failed: {result}"
        assert result.get("property") == "roughness"
        assert result.get("value") == 0.2

    finally:
        # Materials must be removed via bpy; delete the test object is not applicable here.
        # Leftover test materials are harmless — blend file is not persisted between sessions.
        pass


@pytest.mark.e2e
def test_render_settings(mcp_client: httpx.Client) -> None:
    """set_render_settings updates engine and resolution without rendering."""
    result = call_tool(mcp_client, "set_render_settings", {
        "engine": "BLENDER_WORKBENCH",
        "resolution_x": 320,
        "resolution_y": 240,
    })
    assert "error" not in result, f"set_render_settings failed: {result}"
    assert result.get("engine") == "BLENDER_WORKBENCH"
    assert result.get("resolution") == [320, 240]


@pytest.mark.e2e
def test_render_image(mcp_client: httpx.Client) -> None:
    """render_image produces a file at the given path (WORKBENCH, low resolution)."""
    filepath = "C:/Windows/Temp/e2e_blender_mcp_render.png"

    # Use Workbench at minimal resolution so the render completes quickly.
    call_tool(mcp_client, "set_render_settings", {
        "engine": "BLENDER_WORKBENCH",
        "resolution_x": 64,
        "resolution_y": 64,
    })

    result = call_tool(mcp_client, "render_image", {"filepath": filepath})
    assert "error" not in result, f"render_image failed: {result}"
    assert result.get("filepath") == filepath
    assert result.get("format") == "PNG"
    assert result.get("resolution") == [64, 64]


@pytest.mark.e2e
def test_shader_node_workflow(mcp_client: httpx.Client) -> None:
    """Full shader node round-trip: list, add, set_value, connect, remove."""
    mat_name = f"{E2E_PREFIX}NodeMat"

    try:
        call_tool(mcp_client, "create_material", {"name": mat_name})

        nodes = call_tool(mcp_client, "list_shader_nodes", {"material_name": mat_name})
        assert isinstance(nodes, list), f"Expected list, got: {nodes}"
        node_names = [n["name"] for n in nodes]
        assert "Principled BSDF" in node_names

        # Add a Mix Shader node
        added = call_tool(mcp_client, "add_shader_node", {
            "material_name": mat_name,
            "node_type": "ShaderNodeMixShader",
            "location": [-200.0, 0.0],
        })
        assert "error" not in added, f"add_shader_node failed: {added}"
        mix_name = added.get("name")
        assert mix_name

        # Set Fac input on the Mix Shader to 0.5
        set_val = call_tool(mcp_client, "set_node_value", {
            "material_name": mat_name,
            "node_name": mix_name,
            "input_name": "Fac",
            "value": 0.5,
        })
        assert "error" not in set_val, f"set_node_value failed: {set_val}"
        assert set_val.get("value") == 0.5

        # Connect Principled BSDF output (index 0) to Mix Shader input (index 1)
        conn = call_tool(mcp_client, "connect_nodes", {
            "material_name": mat_name,
            "from_node": "Principled BSDF",
            "from_output": "0",
            "to_node": mix_name,
            "to_input": "1",
        })
        assert "error" not in conn, f"connect_nodes failed: {conn}"

        # Remove the Mix Shader node
        removed = call_tool(mcp_client, "remove_node", {
            "material_name": mat_name,
            "node_name": mix_name,
        })
        assert "error" not in removed, f"remove_node failed: {removed}"
        assert removed.get("removed") == mix_name

    finally:
        pass  # Materials are ephemeral; no persistent cleanup needed.


@pytest.mark.e2e
def test_modifier_configure_and_apply(mcp_client: httpx.Client) -> None:
    """configure_modifier updates modifier settings; apply_modifier bakes it."""
    obj_name = f"{E2E_PREFIX}ConfigMod"

    try:
        call_tool(mcp_client, "create_object", {"type": "MESH_CUBE", "name": obj_name})

        added = call_tool(mcp_client, "add_modifier", {
            "object_name": obj_name,
            "modifier_type": "SUBSURF",
        })
        assert "error" not in added, f"add_modifier failed: {added}"
        mod_name = added.get("name")

        configured = call_tool(mcp_client, "configure_modifier", {
            "object_name": obj_name,
            "modifier_name": mod_name,
            "settings": {"levels": 1},
        })
        assert "error" not in configured, f"configure_modifier failed: {configured}"
        assert "levels" in configured.get("updated", {})

        applied = call_tool(mcp_client, "apply_modifier", {
            "object_name": obj_name,
            "modifier_name": mod_name,
        })
        assert "error" not in applied, f"apply_modifier failed: {applied}"
        assert applied.get("applied") == mod_name

        # Modifier must be gone after apply
        mods = call_tool(mcp_client, "list_modifiers", {"object_name": obj_name})
        assert mod_name not in [m["name"] for m in mods]

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [obj_name]})


@pytest.mark.e2e
def test_animation_frame_and_fps(mcp_client: httpx.Client) -> None:
    """set_current_frame moves the playhead; set_fps updates the scene rate."""
    frame_result = call_tool(mcp_client, "set_current_frame", {"frame": 42})
    assert "error" not in frame_result, f"set_current_frame failed: {frame_result}"
    assert frame_result.get("current_frame") == 42

    fps_result = call_tool(mcp_client, "set_fps", {"fps": 30})
    assert "error" not in fps_result, f"set_fps failed: {fps_result}"
    assert fps_result.get("fps") == 30


@pytest.mark.e2e
def test_configure_light(mcp_client: httpx.Client) -> None:
    """configure_light sets energy and color on an existing light object."""
    light_name = f"{E2E_PREFIX}TestLight"

    try:
        call_tool(mcp_client, "create_object", {
            "type": "LIGHT",
            "name": light_name,
            "location": [0.0, 0.0, 5.0],
        })

        result = call_tool(mcp_client, "configure_light", {
            "name": light_name,
            "energy": 500.0,
            "color": [1.0, 0.9, 0.8],
        })
        assert "error" not in result, f"configure_light failed: {result}"
        assert result.get("name") == light_name
        assert result.get("energy") == 500.0
        assert result.get("color") == pytest.approx([1.0, 0.9, 0.8], abs=1e-5)

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [light_name]})


@pytest.mark.e2e
def test_camera_look_at_and_active(mcp_client: httpx.Client) -> None:
    """set_active_camera sets the scene camera; look_at orients it toward a target."""
    cam_name = f"{E2E_PREFIX}TestCamera"

    try:
        call_tool(mcp_client, "create_object", {
            "type": "CAMERA",
            "name": cam_name,
            "location": [5.0, -5.0, 5.0],
        })

        active_result = call_tool(mcp_client, "set_active_camera", {"name": cam_name})
        assert "error" not in active_result, f"set_active_camera failed: {active_result}"
        assert active_result.get("active_camera") == cam_name

        look_result = call_tool(mcp_client, "look_at", {
            "name": cam_name,
            "target": [0.0, 0.0, 0.0],
        })
        assert "error" not in look_result, f"look_at failed: {look_result}"
        assert look_result.get("name") == cam_name
        assert look_result.get("target") == [0.0, 0.0, 0.0]
        assert "rotation_euler" in look_result

    finally:
        call_tool(mcp_client, "delete_objects", {"names": [cam_name]})


@pytest.mark.e2e
def test_world_settings(mcp_client: httpx.Client) -> None:
    """set_world_settings updates background color and strength."""
    result = call_tool(mcp_client, "set_world_settings", {
        "background_color": [0.1, 0.1, 0.1, 1.0],
        "strength": 0.8,
    })
    assert "error" not in result, f"set_world_settings failed: {result}"
    assert "background_color" in result
    assert "strength" in result
    assert result.get("strength") == pytest.approx(0.8)


@pytest.mark.e2e
def test_execute_python(mcp_client: httpx.Client) -> None:
    """execute_python runs arbitrary bpy code and returns __result__."""
    result = call_tool(mcp_client, "execute_python", {
        "code": "__result__ = [obj.name for obj in bpy.data.objects]",
    })
    assert "error" not in result, f"execute_python failed: {result}"
    assert result.get("status") == "ok"
    assert isinstance(result.get("result"), list)
