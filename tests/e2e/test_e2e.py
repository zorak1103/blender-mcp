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
        "list_scenes",
        "get_scene_info",
        "list_objects",
        "get_object_info",
        "create_object",
        "delete_objects",
        "transform_object",
        "create_material",
        "assign_material",
        "list_materials",
        "render_image",
        "screenshot_viewport",
        "list_shader_nodes",
        "add_shader_node",
        "add_modifier",
        "list_modifiers",
        "apply_modifier",
        "insert_keyframe",
        "delete_keyframe",
        "set_frame_range",
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
