"""
Sandbox utilities for the execute_python tool.

Provides a restricted execution namespace that limits code to Blender/math
operations and blocks dangerous standard-library access (filesystem, network,
subprocess, low-level Python internals).

NOTE: This is a *safety net*, not a full security boundary. Python dynamic
nature makes it impossible to guarantee sandbox escape prevention against a
determined attacker. The restricted mode blocks obvious dangerous vectors and
makes accidental damage near-impossible -- it is suitable for AI assistant use
where the risk is accidental rather than adversarial.

The primary defence is an AST pre-flight check (validate_restricted_code) that
rejects dunder-attribute access and other escape patterns before the code is
run. A secondary defence is a reduced SAFE_BUILTINS whitelist that removes
type, object, vars, super, and property. Neither layer alone is sufficient;
the combination stops the known PoC and raises the bar significantly. See
docs/security.md for an explicit list of known limitations.
"""

from __future__ import annotations

import ast
import builtins
from typing import Any

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class RestrictedCodeError(ValueError):
    """Raised when submitted code fails the AST pre-flight check.

    The message contains the line:col and a human-readable description of
    the rejected pattern.
    """


# ---------------------------------------------------------------------------
# AST validator constants
# ---------------------------------------------------------------------------

_FORBIDDEN_DUNDERS: frozenset[str] = frozenset({
    "__class__", "__bases__", "__mro__", "__subclasses__",
    "__subclasshook__", "__init_subclass__", "__base__",
    "__globals__", "__builtins__", "__import__",
    "__code__", "__closure__", "__func__", "__self__",
    "__dict__", "__getattribute__", "__getattr__",
    "__reduce__", "__reduce_ex__",
    "__class_getitem__",
    "__loader__", "__spec__", "__package__",
    "__wrapped__",
    "__objclass__",
    "mro", "__mro_entries__",
})

_FORBIDDEN_NAMES: frozenset[str] = frozenset({
    "__import__", "__builtins__", "__loader__", "__spec__", "__package__",
    'exec', 'eval', "compile",
    "globals", "locals",
    "breakpoint", "open", "input", "help", "exit", "quit", "memoryview",
    "object", "type", "super", "vars", "property",
})

_DUNDER_CALL_GUARDS: frozenset[str] = frozenset({
    "getattr", "setattr", "delattr", "hasattr",
})


# ---------------------------------------------------------------------------
# AST validator
# ---------------------------------------------------------------------------


class _RestrictedCodeValidator(ast.NodeVisitor):
    """Walk an AST and collect violations of the restricted-mode rules."""

    def __init__(self) -> None:
        self._violations: list[tuple[int, int, str]] = []

    def _reject(self, node: ast.AST, msg: str) -> None:
        line = getattr(node, "lineno", 0)
        col = getattr(node, "col_offset", 0)
        self._violations.append((line, col, msg))

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _FORBIDDEN_DUNDERS:
            self._reject(node, f"access to restricted attribute {node.attr!r} is not allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in _FORBIDDEN_NAMES:
            self._reject(node, f"use of restricted name {node.id!r} is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _DUNDER_CALL_GUARDS:
            if len(node.args) >= 2:
                attr_arg = node.args[1]
                if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str):
                    if attr_arg.value.startswith("_"):
                        self._reject(
                            node,
                            f"{node.func.id}() with underscore-prefixed attribute name"
                            f" {attr_arg.value!r} is not allowed",
                        )
        if isinstance(node.func, ast.Name) and node.func.id == "type":
            if len(node.args) == 3:
                self._reject(node, "3-argument type() (class synthesis) is not allowed")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._reject(node, f"class definitions ({node.name!r}) are not allowed in restricted mode")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._reject(node, "async function definitions are not allowed in restricted mode")

    def visit_Await(self, node: ast.Await) -> None:
        self._reject(node, "await expressions are not allowed in restricted mode")
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._reject(node, "async for loops are not allowed in restricted mode")
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._reject(node, "async with statements are not allowed in restricted mode")
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self._reject(node, "global statements are not allowed in restricted mode")

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._reject(node, "nonlocal statements are not allowed in restricted mode")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top not in ALLOWED_MODULES:
                self._reject(node, f"import of {alias.name!r} is not allowed in restricted mode")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        top = module.split(".")[0]
        if top not in ALLOWED_MODULES:
            self._reject(node, f"import from {module!r} is not allowed in restricted mode")
        self.generic_visit(node)

    @property
    def first_violation(self) -> tuple[int, int, str] | None:
        return self._violations[0] if self._violations else None


def validate_restricted_code(code: str) -> None:
    """Pre-flight AST check for restricted mode.

    Raises RestrictedCodeError on the first forbidden pattern found.
    Propagates SyntaxError from ast.parse unchanged.

    Does NOT catch dynamically constructed attribute names such as
    getattr(x, chr(95)*2 + "class" + chr(95)*2).
    """
    tree = ast.parse(code, mode="exec")  # SyntaxError propagates unchanged
    validator = _RestrictedCodeValidator()
    validator.visit(tree)
    violation = validator.first_violation
    if violation:
        line, col, msg = violation
        raise RestrictedCodeError(f"line {line}:{col}: {msg}")


# ---------------------------------------------------------------------------
# Safe built-ins whitelist
# ---------------------------------------------------------------------------

#: Built-in names safe to expose in restricted mode.
#: Excluded: open, compile, globals, locals, breakpoint, exit, quit, input,
#: help, memoryview (direct dangers) and type, object, vars, super, property
#: (defense-in-depth; primary guard is validate_restricted_code).
SAFE_BUILTINS: dict[str, Any] = {
    # Core types
    "bool": bool,
    "bytearray": bytearray,
    "bytes": bytes,
    "complex": complex,
    "dict": dict,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "list": list,
    "set": set,
    "slice": slice,
    "str": str,
    "tuple": tuple,
    # Numeric / math helpers
    "abs": abs,
    "bin": bin,
    "chr": chr,
    "divmod": divmod,
    "hex": hex,
    "max": max,
    "min": min,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "round": round,
    "sum": sum,
    # Iteration / sequences
    "all": all,
    "any": any,
    "enumerate": enumerate,
    "filter": filter,
    "iter": iter,
    "len": len,
    "map": map,
    "next": next,
    "range": range,
    "reversed": reversed,
    "sorted": sorted,
    "zip": zip,
    # Introspection (needed for normal Blender scripting)
    "callable": callable,
    "dir": dir,
    "format": format,
    "getattr": getattr,
    "hasattr": hasattr,
    "hash": hash,
    "id": id,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "repr": repr,
    "setattr": setattr,
    # I/O (print only -- no file access)
    "print": print,
    # Singleton constants
    "True": True,
    "False": False,
    "None": None,
    "NotImplemented": NotImplemented,
    "Ellipsis": Ellipsis,
    # Exception base classes
    "ArithmeticError": ArithmeticError,
    "AttributeError": AttributeError,
    "Exception": Exception,
    "ImportError": ImportError,
    "IndexError": IndexError,
    "KeyError": KeyError,
    "LookupError": LookupError,
    "NameError": NameError,
    "OSError": OSError,
    "OverflowError": OverflowError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,
    "TypeError": TypeError,
    "ValueError": ValueError,
    "ZeroDivisionError": ZeroDivisionError,
}

# ---------------------------------------------------------------------------
# Module import allowlist
# ---------------------------------------------------------------------------

#: Modules that restricted-mode code is allowed to import.
ALLOWED_MODULES: frozenset[str] = frozenset({
    "bpy",
    "mathutils",
    "math",
    "json",
    "re",
    "collections",
    "itertools",
    "functools",
    "copy",
    "random",
    "colorsys",
    "datetime",
    "enum",
    "typing",
    "dataclasses",
})

# ---------------------------------------------------------------------------
# Safe import wrapper
# ---------------------------------------------------------------------------

_real_import = builtins.__import__


def _safe_import(
    name: str,
    globals: dict[str, Any] | None = None,  # noqa: A002
    locals: dict[str, Any] | None = None,  # noqa: A002
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    """Replacement for __import__ that only allows whitelisted modules."""
    top_level = name.split(".")[0]
    if top_level not in ALLOWED_MODULES:
        raise ImportError(
            f"Import of {name!r} is not allowed in restricted mode. "
            f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
        )
    return _real_import(name, globals, locals, fromlist, level)


# ---------------------------------------------------------------------------
# Namespace builders
# ---------------------------------------------------------------------------


def make_restricted_namespace(bpy_mod: Any, mathutils_mod: Any) -> dict[str, Any]:
    """Return a restricted execution namespace for sandboxed code.

    Call validate_restricted_code(code) before running code in this namespace.
    """
    from mathutils import Euler, Matrix, Quaternion, Vector  # noqa: PLC0415

    restricted_builtins = dict(SAFE_BUILTINS)
    restricted_builtins["__import__"] = _safe_import

    return {
        "bpy": bpy_mod,
        "mathutils": mathutils_mod,
        "Vector": Vector,
        "Matrix": Matrix,
        "Euler": Euler,
        "Quaternion": Quaternion,
        "math": _safe_import("math"),
        "json": _safe_import("json"),
        "__builtins__": restricted_builtins,
        "__result__": None,
    }


def make_unrestricted_namespace(bpy_mod: Any, mathutils_mod: Any) -> dict[str, Any]:
    """Return an unrestricted execution namespace (YOLO mode).

    No restrictions applied. Equivalent to Blender built-in Python console.
    """
    from mathutils import Euler, Matrix, Quaternion, Vector  # noqa: PLC0415

    return {
        "bpy": bpy_mod,
        "mathutils": mathutils_mod,
        "Vector": Vector,
        "Matrix": Matrix,
        "Euler": Euler,
        "Quaternion": Quaternion,
        "__builtins__": builtins,
        "__result__": None,
    }
