"""Unit tests for blender_addon.bridge.MainThreadBridge."""

from __future__ import annotations

import concurrent.futures

import pytest

# bpy mock is injected globally by conftest.inject_bpy_mock
from blender_addon.bridge import MainThreadBridge


@pytest.fixture
def bridge() -> MainThreadBridge:
    return MainThreadBridge()


def test_run_on_main_thread_returns_future(bridge: MainThreadBridge) -> None:
    fut = bridge.run_on_main_thread(lambda: 42)
    assert isinstance(fut, concurrent.futures.Future)


def test_timer_callback_executes_fn_and_sets_result(bridge: MainThreadBridge) -> None:
    fut = bridge.run_on_main_thread(lambda: {"answer": 99})
    bridge._running = True
    bridge._timer_callback()
    assert fut.result(timeout=1) == {"answer": 99}


def test_timer_callback_on_empty_queue_returns_reschedule(bridge: MainThreadBridge) -> None:
    bridge._running = True
    result = bridge._timer_callback()
    assert result == pytest.approx(0.01)


def test_timer_callback_fn_exception_sets_future_exception(bridge: MainThreadBridge) -> None:
    def boom() -> None:
        raise ValueError("oops")

    fut = bridge.run_on_main_thread(boom)
    bridge._running = True
    bridge._timer_callback()
    with pytest.raises(ValueError, match="oops"):
        fut.result(timeout=1)


def test_timer_callback_not_running_returns_none(bridge: MainThreadBridge) -> None:
    bridge._running = False
    result = bridge._timer_callback()
    assert result is None


def test_stop_cancels_pending_futures(bridge: MainThreadBridge, mock_bpy) -> None:  # type: ignore[no-untyped-def]
    # Queue some work without running the timer
    fut1 = bridge.run_on_main_thread(lambda: 1)
    fut2 = bridge.run_on_main_thread(lambda: 2)
    bridge._running = True
    bridge.stop()
    # Futures should be cancelled or done after stop
    assert fut1.cancelled() or fut1.done()
    assert fut2.cancelled() or fut2.done()


def test_stop_calls_unregister_timer(bridge: MainThreadBridge, mock_bpy) -> None:  # type: ignore[no-untyped-def]
    mock_bpy.app.timers.unregister.reset_mock()
    bridge._running = True
    bridge.stop()
    mock_bpy.app.timers.unregister.assert_called_once_with(bridge._timer_callback)


def test_multiple_tasks_processed_sequentially(bridge: MainThreadBridge) -> None:
    results = []
    bridge._running = True

    for i in range(3):
        bridge.run_on_main_thread(lambda v=i: results.append(v))

    for _ in range(3):
        bridge._timer_callback()

    assert results == [0, 1, 2]
