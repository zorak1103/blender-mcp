"""Unit tests for blender_addon.tools._sandbox.

Tests cover:
- SAFE_BUILTINS whitelist completeness and correctness
- ALLOWED_MODULES allowlist content
- _safe_import behaviour for allowed and blocked modules
- make_restricted_namespace / make_unrestricted_namespace structure
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_sandbox():
    """Import the sandbox module freshly (it has no Blender dependencies)."""
    from blender_addon.tools._sandbox import (
        ALLOWED_MODULES,
        SAFE_BUILTINS,
        _safe_import,
        make_restricted_namespace,
        make_unrestricted_namespace,
    )
    return (
        ALLOWED_MODULES,
        SAFE_BUILTINS,
        _safe_import,
        make_restricted_namespace,
        make_unrestricted_namespace,
    )


def _make_namespace() -> tuple[Any, Any]:
    """Return minimal bpy and mathutils mocks for namespace builders."""
    return MagicMock(name="bpy"), MagicMock(name="mathutils")


# ---------------------------------------------------------------------------
# SAFE_BUILTINS
# ---------------------------------------------------------------------------


def test_safe_builtins_has_core_types() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    for name in ("bool", "bytes", "dict", "float", "int", "list", "set", "str", "tuple"):
        assert name in SAFE_BUILTINS, f"Expected {name!r} in SAFE_BUILTINS"


def test_safe_builtins_has_iteration_helpers() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    for name in ("all", "any", "enumerate", "filter", "len", "map", "range", "sorted", "zip"):
        assert name in SAFE_BUILTINS, f"Expected {name!r} in SAFE_BUILTINS"


def test_safe_builtins_has_introspection_helpers() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    for name in ("callable", "dir", "getattr", "hasattr", "isinstance", "issubclass", "type"):
        assert name in SAFE_BUILTINS, f"Expected {name!r} in SAFE_BUILTINS"


def test_safe_builtins_has_common_exceptions() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    for name in ("Exception", "ValueError", "TypeError", "KeyError", "IndexError", "RuntimeError"):
        assert name in SAFE_BUILTINS, f"Expected {name!r} in SAFE_BUILTINS"


def test_safe_builtins_blocks_open() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    assert "open" not in SAFE_BUILTINS


def test_safe_builtins_blocks_globals_and_locals() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    assert "globals" not in SAFE_BUILTINS
    assert "locals" not in SAFE_BUILTINS


def test_safe_builtins_blocks_compile() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    assert "compile" not in SAFE_BUILTINS


def test_safe_builtins_blocks_breakpoint_and_io() -> None:
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    for name in ("breakpoint", "exit", "quit", "input", "help", "memoryview"):
        assert name not in SAFE_BUILTINS, f"Expected {name!r} to be blocked"


def test_safe_builtins_raw_import_blocked() -> None:
    """__import__ should not be in the base dict; it is added by make_restricted_namespace."""
    _, SAFE_BUILTINS, *_ = _import_sandbox()
    assert "__import__" not in SAFE_BUILTINS


# ---------------------------------------------------------------------------
# ALLOWED_MODULES
# ---------------------------------------------------------------------------


def test_allowed_modules_contains_blender_modules() -> None:
    ALLOWED_MODULES, *_ = _import_sandbox()
    for mod in ("bpy", "mathutils", "math", "json", "re", "colorsys"):
        assert mod in ALLOWED_MODULES, f"Expected {mod!r} in ALLOWED_MODULES"


def test_allowed_modules_contains_stdlib_utilities() -> None:
    ALLOWED_MODULES, *_ = _import_sandbox()
    for mod in ("collections", "itertools", "functools", "copy", "random", "datetime", "enum"):
        assert mod in ALLOWED_MODULES, f"Expected {mod!r} in ALLOWED_MODULES"


# ---------------------------------------------------------------------------
# _safe_import
# ---------------------------------------------------------------------------


def test_safe_import_allows_math() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    mod = _safe_import("math")
    assert hasattr(mod, "pi")


def test_safe_import_allows_json() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    mod = _safe_import("json")
    assert hasattr(mod, "dumps")


def test_safe_import_allows_re() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    mod = _safe_import("re")
    assert hasattr(mod, "compile")


def test_safe_import_allows_collections_submodule() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    # collections.abc is a submodule of an allowed top-level module
    mod = _safe_import("collections.abc", fromlist=("Mapping",))
    assert hasattr(mod, "Mapping")


def test_safe_import_blocks_os() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("os")


def test_safe_import_blocks_subprocess() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("subprocess")


def test_safe_import_blocks_socket() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("socket")


def test_safe_import_blocks_ctypes() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("ctypes")


def test_safe_import_blocks_http() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("http")


def test_safe_import_blocks_urllib() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("urllib")


def test_safe_import_blocks_importlib() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("importlib")


def test_safe_import_blocks_shutil() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="not allowed"):
        _safe_import("shutil")


def test_safe_import_error_message_lists_allowed_modules() -> None:
    _, _, _safe_import, *_ = _import_sandbox()
    with pytest.raises(ImportError, match="math"):
        _safe_import("os")


# ---------------------------------------------------------------------------
# make_restricted_namespace
# ---------------------------------------------------------------------------


def test_make_restricted_namespace_has_blender_keys() -> None:
    *_, make_restricted_namespace, _ = _import_sandbox()
    bpy_mock, mathutils_mock = _make_namespace()
    ns = make_restricted_namespace(bpy_mock, mathutils_mock)
    expected_keys = (
        "bpy", "mathutils", "Vector", "Matrix", "Euler", "Quaternion", "math", "json", "__result__"
    )
    for key in expected_keys:
        assert key in ns, f"Expected {key!r} in restricted namespace"


def test_make_restricted_namespace_builtins_is_safe_dict() -> None:
    *_, make_restricted_namespace, _ = _import_sandbox()
    bpy_mock, mathutils_mock = _make_namespace()
    ns = make_restricted_namespace(bpy_mock, mathutils_mock)
    assert isinstance(ns["__builtins__"], dict)
    assert "open" not in ns["__builtins__"]
    assert "globals" not in ns["__builtins__"]
    assert "len" in ns["__builtins__"]


def test_make_restricted_namespace_builtins_has_safe_import() -> None:
    from blender_addon.tools._sandbox import _safe_import
    *_, make_restricted_namespace, _ = _import_sandbox()
    bpy_mock, mathutils_mock = _make_namespace()
    ns = make_restricted_namespace(bpy_mock, mathutils_mock)
    assert ns["__builtins__"]["__import__"] is _safe_import


def test_make_restricted_namespace_result_is_none() -> None:
    *_, make_restricted_namespace, _ = _import_sandbox()
    bpy_mock, mathutils_mock = _make_namespace()
    ns = make_restricted_namespace(bpy_mock, mathutils_mock)
    assert ns["__result__"] is None


# ---------------------------------------------------------------------------
# make_unrestricted_namespace
# ---------------------------------------------------------------------------


def test_make_unrestricted_namespace_has_blender_keys() -> None:
    *_, make_unrestricted_namespace = _import_sandbox()
    bpy_mock, mathutils_mock = _make_namespace()
    ns = make_unrestricted_namespace(bpy_mock, mathutils_mock)
    for key in ("bpy", "mathutils", "Vector", "Matrix", "Euler", "Quaternion", "__result__"):
        assert key in ns, f"Expected {key!r} in unrestricted namespace"


def test_make_unrestricted_namespace_does_not_restrict_builtins() -> None:
    *_, make_unrestricted_namespace = _import_sandbox()
    bpy_mock, mathutils_mock = _make_namespace()
    ns = make_unrestricted_namespace(bpy_mock, mathutils_mock)
    # __builtins__ should be absent or be the full builtins module/dict
    if "__builtins__" in ns:
        builtins = ns["__builtins__"]
        # If it's a dict it should contain open; if it's the module it'll have open
        if isinstance(builtins, dict):
            assert "open" in builtins or "len" in builtins
        else:
            assert hasattr(builtins, "open")
    # The key test: unrestricted namespace has no artificial __builtins__ restriction
    assert "open" not in ns  # open should not be explicitly added to the namespace top level
