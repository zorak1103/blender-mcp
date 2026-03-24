"""Unit tests for blender_addon.server and blender_addon.__init__."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# server.py
# ---------------------------------------------------------------------------


def test_setup_creates_fastmcp_instance() -> None:
    from blender_addon import server as server_mod

    mock_mcp = MagicMock()
    with patch("blender_addon.server.FastMCP", return_value=mock_mcp) as mock_cls:
        server_mod.setup(port=8400)
        mock_cls.assert_called_once_with("blender-mcp", host="127.0.0.1", port=8400)
    assert server_mod.mcp is mock_mcp


def test_setup_calls_register_all() -> None:
    from blender_addon import server as server_mod

    mock_mcp = MagicMock()
    with patch("blender_addon.server.FastMCP", return_value=mock_mcp):
        with patch("blender_addon.server.register_all") as mock_reg:
            server_mod.setup(port=9000)
            mock_reg.assert_called_once_with(mock_mcp, allow_execute_python=False)


def test_start_raises_if_setup_not_called() -> None:
    from blender_addon import server as server_mod

    server_mod.mcp = None
    with pytest.raises(RuntimeError, match="setup"):
        server_mod.start()


def test_start_launches_daemon_thread() -> None:
    from blender_addon import server as server_mod

    mock_mcp = MagicMock()
    server_mod.mcp = mock_mcp

    started: list[bool] = []

    def fake_run(**kwargs: object) -> None:
        started.append(True)

    mock_mcp.run = fake_run

    with patch("blender_addon.server.threading.Thread") as mock_thread_cls:
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread
        server_mod.start()
        mock_thread_cls.assert_called_once()
        assert mock_thread_cls.call_args.kwargs.get("daemon") is True
        mock_thread.start.assert_called_once()


def test_stop_joins_thread() -> None:
    from blender_addon import server as server_mod

    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    server_mod._server_thread = mock_thread

    server_mod.stop()
    mock_thread.join.assert_called_once_with(timeout=5)

    # Cleanup
    server_mod._server_thread = None


def test_stop_does_nothing_if_no_thread() -> None:
    from blender_addon import server as server_mod

    server_mod._server_thread = None
    server_mod.stop()  # should not raise


# ---------------------------------------------------------------------------
# __init__.py register / unregister
# ---------------------------------------------------------------------------


def test_register_initialises_bridge_and_starts_server(mock_bpy: MagicMock) -> None:
    import blender_addon
    from blender_addon import bridge as bridge_mod
    from blender_addon import server as server_mod

    mock_bridge_inst = MagicMock()
    prefs = MagicMock()
    prefs.port = 8400
    prefs.allow_execute_python = False
    mock_bpy.context.preferences.addons.__getitem__.return_value.preferences = prefs

    with patch.object(bridge_mod, "MainThreadBridge", return_value=mock_bridge_inst):
        with patch.object(server_mod, "setup") as mock_setup:
            with patch.object(server_mod, "start") as mock_start:
                blender_addon.register()

    mock_bridge_inst.start.assert_called_once()
    mock_setup.assert_called_once_with(port=8400, allow_execute_python=False)
    mock_start.assert_called_once()
    assert bridge_mod.bridge is mock_bridge_inst


def test_unregister_stops_server_and_bridge(mock_bpy: MagicMock) -> None:
    import blender_addon
    from blender_addon import bridge as bridge_mod
    from blender_addon import server as server_mod

    mock_bridge_inst = MagicMock()
    bridge_mod.bridge = mock_bridge_inst

    with patch.object(server_mod, "stop") as mock_stop:
        blender_addon.unregister()

    mock_stop.assert_called_once()
    mock_bridge_inst.stop.assert_called_once()
    assert bridge_mod.bridge is None


def test_tools_register_all(mock_bpy: MagicMock) -> None:
    from blender_addon.tools import register_all

    mcp = MagicMock()
    # register_all should call each module's register(mcp) without raising
    register_all(mcp)
