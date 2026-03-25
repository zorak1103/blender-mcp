"""Patch version strings from a git tag.

Usage:
    python scripts/patch_version.py v0.2.0

Updates:
- blender_addon/__init__.py  → bl_info["version"] = (major, minor, patch)
- pyproject.toml             → version = "major.minor.patch"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def parse_tag(tag: str) -> tuple[int, int, int]:
    """Parse a git tag like 'v0.2.0' into a (major, minor, patch) tuple."""
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        sys.exit(f"ERROR: Tag '{tag}' does not match 'vMAJOR.MINOR.PATCH' format.")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def patch_init(major: int, minor: int, patch: int) -> None:
    """Replace 'version' tuple in bl_info inside blender_addon/__init__.py."""
    path = REPO_ROOT / "blender_addon" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'"version":\s*\(\d+,\s*\d+,\s*\d+\)',
        f'"version": ({major}, {minor}, {patch})',
        text,
    )
    if count == 0:
        sys.exit(f"ERROR: Could not find 'version' tuple in {path}")
    path.write_text(new_text, encoding="utf-8")
    print(f"Patched {path.relative_to(REPO_ROOT)}: version = ({major}, {minor}, {patch})")


def patch_pyproject(major: int, minor: int, patch: int) -> None:
    """Replace version string in pyproject.toml."""
    path = REPO_ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'^(version\s*=\s*")[^"]+"',
        rf'\g<1>{major}.{minor}.{patch}"',
        text,
        flags=re.MULTILINE,
    )
    if count == 0:
        sys.exit(f"ERROR: Could not find 'version' field in {path}")
    path.write_text(new_text, encoding="utf-8")
    print(f"Patched {path.relative_to(REPO_ROOT)}: version = {major}.{minor}.{patch}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <tag>  (e.g. v0.2.0)")

    tag = sys.argv[1]
    major, minor, patch = parse_tag(tag)
    patch_init(major, minor, patch)
    patch_pyproject(major, minor, patch)
    print(f"Version patched to {major}.{minor}.{patch}")
