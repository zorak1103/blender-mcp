"""
Thread-safe bridge between the MCP background thread and Blender's main thread.

The MCP server runs in a daemon thread, but all bpy.* calls must happen on Blender's
main thread. This module provides a queue-based dispatch mechanism using bpy.app.timers
to execute callables on the main thread and return results via concurrent.futures.Future.
"""

from __future__ import annotations

import concurrent.futures
import logging
import queue
from collections.abc import Callable
from typing import Any

import bpy

logger = logging.getLogger(__name__)


class MainThreadBridge:
    """Singleton bridge that dispatches callables from background threads to Blender's main thread.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[Callable[[], Any], concurrent.futures.Future[Any]]] = (
            queue.Queue()
        )
        self._running: bool = False

    def start(self) -> None:
        """Initialize the queue and register the timer callback on the main thread."""
        self._running = True
        bpy.app.timers.register(self._timer_callback, persistent=True)
        logger.info("MainThreadBridge started")

    def stop(self) -> None:
        """Stop the bridge, unregister the timer, and cancel pending futures."""
        self._running = False
        if bpy.app.timers.is_registered(self._timer_callback):
            bpy.app.timers.unregister(self._timer_callback)
        # Drain and cancel any remaining queued work
        while True:
            try:
                _, future = self._queue.get_nowait()
                if not future.done():
                    future.cancel()
            except queue.Empty:
                break
        logger.info("MainThreadBridge stopped")

    def run_on_main_thread(self, fn: Callable[[], Any]) -> concurrent.futures.Future[Any]:
        """
        Submit a callable for execution on Blender's main thread.

        The caller (background thread) should block on the returned Future:
            result = future.result(timeout=30)
        """
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()
        self._queue.put((fn, future))
        return future

    def _timer_callback(self) -> float | None:
        """
        Called by bpy.app.timers on the main thread every ~10 ms.

        Processes one queued callable per invocation to keep the main thread responsive.
        Returns None to unregister the timer, or 0.01 to reschedule.
        """
        if not self._running:
            return None  # unregister timer

        try:
            fn, future = self._queue.get_nowait()
            try:
                result = fn()
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)
        except queue.Empty:
            pass

        return 0.01  # reschedule in 10 ms


# Module-level singleton — set by blender_addon/__init__.py during register()
bridge: MainThreadBridge | None = None
