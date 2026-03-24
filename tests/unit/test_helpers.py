"""Unit tests for blender_addon.tools._helpers.run_tool."""

from __future__ import annotations

import concurrent.futures
import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def fake_bridge() -> MagicMock:
    fake = MagicMock(name="bridge")

    def run_sync(fn):  # type: ignore[no-untyped-def]
        fut: concurrent.futures.Future = concurrent.futures.Future()
        try:
            fut.set_result(fn())
        except Exception as exc:
            fut.set_exception(exc)
        return fut

    fake.run_on_main_thread = run_sync
    return fake


@pytest.fixture(autouse=True)
def patch_bridge(fake_bridge: MagicMock):  # type: ignore[no-untyped-def]
    with patch("blender_addon.bridge.bridge", fake_bridge):
        yield


async def test_run_tool_success() -> None:
    from blender_addon.tools._helpers import run_tool

    result = await run_tool("test_tool", lambda: {"status": "ok", "value": 42})
    parsed = json.loads(result)
    assert parsed == {"status": "ok", "value": 42}


async def test_run_tool_returns_valid_json_on_success() -> None:
    from blender_addon.tools._helpers import run_tool

    result = await run_tool("test_tool", lambda: [1, 2, 3])
    parsed = json.loads(result)
    assert parsed == [1, 2, 3]


async def test_run_tool_exception_returns_error_json() -> None:
    from blender_addon.tools._helpers import run_tool

    def boom() -> None:
        raise ValueError("something went wrong")

    result = await run_tool("my_tool", boom)
    parsed = json.loads(result)
    assert parsed["error"] == "something went wrong"
    assert parsed["tool"] == "my_tool"


async def test_run_tool_timeout_returns_error_json(fake_bridge: MagicMock) -> None:
    from blender_addon.tools._helpers import run_tool

    # Make run_on_main_thread return a future that immediately raises TimeoutError
    fut: concurrent.futures.Future = concurrent.futures.Future()

    def slow_run(fn):  # type: ignore[no-untyped-def]
        return fut  # never resolved

    fake_bridge.run_on_main_thread = slow_run

    # Patch result() to raise TimeoutError
    with patch.object(fut, "result", side_effect=concurrent.futures.TimeoutError):
        result = await run_tool("slow_tool", lambda: None)

    parsed = json.loads(result)
    assert "timeout" in parsed["error"].lower()
    assert parsed["tool"] == "slow_tool"


async def test_run_tool_always_returns_valid_json() -> None:
    """run_tool must always return parseable JSON, even for unexpected exceptions."""
    from blender_addon.tools._helpers import run_tool

    def raise_runtime() -> None:
        raise RuntimeError("unexpected blender crash")

    result = await run_tool("crash_tool", raise_runtime)
    parsed = json.loads(result)
    assert "error" in parsed
    assert "tool" in parsed
