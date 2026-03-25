"""
Sandbox utilities for the execute_python tool.

Provides a restricted execution namespace that limits code to Blender/math
operations and blocks dangerous standard-library access (filesystem, network,
subprocess, low-level Python internals).

NOTE: This is a *safety net*, not a full security boundary. Python's dynamic
nature makes it impossible to guarantee sandbox escape prevention against a
determined attacker. The restricted mode blocks obvious dangerous vectors and
makes accidental damage near-impossible — it is suitable for AI assistant use
where the risk is accidental rather than adversarial.
"""

from __future__ import annotations

import builtins
from typing import Any

# ---------------------------------------------------------------------------
# Safe built-ins whitelist
# ---------------------------------------------------------------------------

#: Built-in names that are safe to expose in restricted mode.
#: Dangerous builtins (open, compile, globals, locals, breakpoint,
#: exit, quit, input, help, memoryview) are intentionally excluded.
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
    "object": object,
    "property": property,
    "set": set,
    "slice": slice,
    "str": str,
    "tuple": tuple,
    "type": type,
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
    "super": super,
    "vars": vars,
    # I/O (print only — no file access)
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
            f"Import of '{name}' is not allowed in restricted mode. "
            f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
        )
    return _real_import(name, globals, locals, fromlist, level)


# ---------------------------------------------------------------------------
# Namespace builders
# ---------------------------------------------------------------------------


def make_restricted_namespace(bpy_mod: Any, mathutils_mod: Any) -> dict[str, Any]:
    """Return a restricted execution namespace for sandboxed code execution.

    The namespace exposes bpy, mathutils convenience types, math, and json.
    The __builtins__ dict only contains safe built-ins; dangerous functions
    (open, globals, compile, etc.) and unrestricted __import__ are excluded.
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

    No restrictions are applied. The code has full access to the Python
    standard library and bpy. This is equivalent to running code directly
    in Blender's built-in Python console.
    """
    from mathutils import Euler, Matrix, Quaternion, Vector  # noqa: PLC0415

    return {
        "bpy": bpy_mod,
        "mathutils": mathutils_mod,
        "Vector": Vector,
        "Matrix": Matrix,
        "Euler": Euler,
        "Quaternion": Quaternion,
        "__result__": None,
    }
