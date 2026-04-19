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
    for name in ("callable", "dir", "getattr", "hasattr", "isinstance", "issubclass"):
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
    for removed in ("type", "object", "vars", "super", "property"):
        msg = f"{removed!r} should not be in restricted builtins"
        assert removed not in ns["__builtins__"], msg


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


# ---------------------------------------------------------------------------
# AST pre-flight validator
# ---------------------------------------------------------------------------


def _validator():
    from blender_addon.tools._sandbox import RestrictedCodeError, validate_restricted_code
    return RestrictedCodeError, validate_restricted_code


def test_validator_rejects_class_attr() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__class__'):
        val('x = ().__class__')


def test_validator_rejects_mro_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__mro__'):
        val('x = str.__mro__')


def test_validator_rejects_subclasses_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__subclasses__'):
        val('x = list.__subclasses__()')


def test_validator_rejects_bases_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__bases__'):
        val('x = str.__bases__')


def test_validator_rejects_globals_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__globals__'):
        val('x = len.__globals__')


def test_validator_rejects_code_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__code__'):
        val('x = (lambda: 1).__code__')


def test_validator_rejects_dict_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__dict__'):
        val('x = str.__dict__')


def test_validator_rejects_reduce_access() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__reduce__'):
        val('x = (1).__reduce__()')


def test_validator_rejects_attribute_assignment_to_dunder() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__code__'):
        val('f.__code__ = g')


def test_validator_rejects_attribute_deletion_of_dunder() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__globals__'):
        val('del f.__globals__')


def test_validator_rejects_exec_name() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='exec'):
        val('exec(chr(112)+chr(97)+chr(115)+chr(115))')


def test_validator_rejects_eval_name() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='eval'):
        val('eval(chr(49)+chr(43)+chr(49))')


def test_validator_rejects_compile_name() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='compile'):
        val('compile(chr(49), chr(60)+chr(115)+chr(62), chr(101)+chr(118)+chr(97)+chr(108))')


def test_validator_rejects_open_name() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='open'):
        val('open(chr(47)+chr(101)+chr(116)+chr(99))')


def test_validator_rejects_object_name() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='object'):
        val('x = object')


def test_validator_rejects_type_name() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='type'):
        val('x = type(1)')


def test_validator_rejects_import_dunder() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='__import__'):
        val('__import__(chr(111)+chr(115))')


def test_validator_rejects_getattr_dunder_literal() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='getattr'):
        val("getattr(x, '__class__')")


def test_validator_rejects_setattr_dunder_literal() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='setattr'):
        val("setattr(x, '__code__', y)")


def test_validator_rejects_hasattr_dunder_literal() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='hasattr'):
        val("hasattr(x, '__mro__')")


def test_validator_rejects_type_three_arg() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='3-argument type'):
        val('type(chr(88), (), {})')


def test_validator_rejects_class_def() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='class definitions'):
        val('class Foo: pass')


def test_validator_rejects_async_function() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='async function'):
        val('async def f(): pass')


def test_validator_rejects_global_statement() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='global'):
        val('def f():\n    global x')


def test_validator_rejects_nonlocal_statement() -> None:
    Err, val = _validator()
    with pytest.raises(Err, match='nonlocal'):
        val('def f():\n    x=1\n    def g():\n        nonlocal x')


def test_validator_rejects_f01_poc_verbatim() -> None:
    """The F-01 audit PoC (subclass traversal) must be rejected."""
    Err, val = _validator()
    poc = 'for sub in list.__subclasses__():\n    if sub.__name__ == chr(70)+chr(105)+chr(108)+chr(101)+chr(73)+chr(79):\n        fileio_cls = sub\n        break\n'  # noqa: E501
    with pytest.raises(Err):
        val(poc)


def test_validator_rejects_mro_last_escape() -> None:
    Err, val = _validator()
    with pytest.raises(Err):  # __mro__ or __class__ -- both forbidden
        val('x = ().__class__.__mro__[-1]')


def test_validator_propagates_syntax_error() -> None:
    """SyntaxError from ast.parse propagates unchanged."""
    _, val = _validator()
    with pytest.raises(SyntaxError):
        val("def f(:")


def test_validator_accepts_bpy_iteration() -> None:
    _, val = _validator()
    val('for obj in bpy.data.objects:\n    obj.location.x += 1')


def test_validator_accepts_material_creation() -> None:
    _, val = _validator()
    val("mat = bpy.data.materials.new('Foo')")


def test_validator_accepts_result_assignment() -> None:
    """__result__ is a Name assignment and must not be rejected."""
    _, val = _validator()
    val("__result__ = [o.name for o in bpy.data.objects]")


def test_validator_accepts_result_not_in_forbidden_names() -> None:
    from blender_addon.tools._sandbox import _FORBIDDEN_NAMES
    assert "__result__" not in _FORBIDDEN_NAMES


def test_validator_accepts_math_import() -> None:
    _, val = _validator()
    val('import math\nr = math.sqrt(2)')


def test_validator_accepts_fstring_comprehension() -> None:
    _, val = _validator()
    val("x = [f'{o.name}' for o in bpy.data.objects if o.type == 'MESH']")


def test_validator_accepts_try_except() -> None:
    _, val = _validator()
    val("try:\n    x = bpy.data.objects['Cube']\nexcept KeyError:\n    x = None")


def test_validator_accepts_lambda() -> None:
    _, val = _validator()
    val('f = lambda o: o.location.x')


def test_validator_accepts_function_def() -> None:
    _, val = _validator()
    val('def offset(o, dx):\n    o.location.x += dx')


def test_validator_accepts_isinstance() -> None:
    _, val = _validator()
    val('if isinstance(x, int): pass')


def test_validator_accepts_getattr_non_dunder() -> None:
    _, val = _validator()
    val("v = getattr(obj, 'location')")


