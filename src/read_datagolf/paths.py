"""Repository path helpers for read_datagolf."""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Return repository root by walking up to pyproject.toml or .git."""
    current = (start or Path(__file__).resolve()).parent
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return Path(__file__).resolve().parents[2]


def repo_file(*parts: str) -> Path:
    """Return a path under repo root."""
    return repo_root() / Path(*parts)

