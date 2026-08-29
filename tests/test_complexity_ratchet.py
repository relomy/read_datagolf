"""Tests for the touched-code complexity ratchet (.github/complexity_ratchet.py)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[1] / ".github" / "complexity_ratchet.py"
_spec = importlib.util.spec_from_file_location("complexity_ratchet", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
complexity_ratchet = importlib.util.module_from_spec(_spec)
sys.modules["complexity_ratchet"] = complexity_ratchet
_spec.loader.exec_module(complexity_ratchet)

compare_blocks = complexity_ratchet.compare_blocks
flatten_blocks = complexity_ratchet.flatten_blocks
check = complexity_ratchet.check
NEW_BLOCK_MAX_COMPLEXITY = complexity_ratchet.NEW_BLOCK_MAX_COMPLEXITY


# --- compare_blocks: pure comparison logic -----------------------------------


def test_new_messy_function_above_grade_b_fails():
    base_blocks: dict[str, int] = {}
    head_blocks = {"mod.py:messy": NEW_BLOCK_MAX_COMPLEXITY + 1}

    violations = compare_blocks(base_blocks, head_blocks)

    assert len(violations) == 1
    assert violations[0].qualname == "mod.py:messy"
    assert "new block" in str(violations[0])


def test_new_function_at_or_below_grade_b_passes():
    base_blocks: dict[str, int] = {}
    head_blocks = {"mod.py:clean": NEW_BLOCK_MAX_COMPLEXITY}

    assert compare_blocks(base_blocks, head_blocks) == []


def test_existing_function_complexity_increase_fails():
    base_blocks = {"mod.py:fn": 5}
    head_blocks = {"mod.py:fn": 8}

    violations = compare_blocks(base_blocks, head_blocks)

    assert len(violations) == 1
    assert violations[0].qualname == "mod.py:fn"
    assert "increased" in str(violations[0])


def test_same_letter_grade_but_higher_complexity_still_fails():
    # Both C-grade (11-20), but the increase from C11 to C15 is a regression.
    base_blocks = {"mod.py:fn": 11}
    head_blocks = {"mod.py:fn": 15}

    violations = compare_blocks(base_blocks, head_blocks)

    assert len(violations) == 1
    assert violations[0].qualname == "mod.py:fn"


def test_existing_function_complexity_improved_passes():
    base_blocks = {"mod.py:fn": 10}
    head_blocks = {"mod.py:fn": 5}

    assert compare_blocks(base_blocks, head_blocks) == []


def test_unchanged_block_passes():
    base_blocks = {"mod.py:fn": 7}
    head_blocks = {"mod.py:fn": 7}

    assert compare_blocks(base_blocks, head_blocks) == []


def test_removed_block_does_not_produce_a_violation():
    base_blocks = {"mod.py:fn": 20}
    head_blocks: dict[str, int] = {}

    assert compare_blocks(base_blocks, head_blocks) == []


# --- flatten_blocks: qualified-name matching for methods/nested blocks -------


def test_flatten_blocks_matches_methods_and_nested_closures_by_qualified_name():
    radon_json = [
        {
            "type": "class",
            "name": "Foo",
            "complexity": 4,
            "methods": [
                {
                    "type": "method",
                    "name": "bar",
                    "complexity": 2,
                    "classname": "Foo",
                    "closures": [],
                },
                {
                    "type": "method",
                    "name": "baz",
                    "complexity": 1,
                    "classname": "Foo",
                    "closures": [
                        {
                            "type": "function",
                            "name": "inner",
                            "complexity": 3,
                            "closures": [],
                        }
                    ],
                },
            ],
        },
        {
            "type": "function",
            "name": "top",
            "complexity": 5,
            "closures": [],
        },
    ]

    flattened = flatten_blocks(radon_json, module="mod.py")

    assert flattened == {
        "mod.py:Foo.bar": 2,
        "mod.py:Foo.baz": 1,
        "mod.py:Foo.baz.inner": 3,
        "mod.py:top": 5,
    }
    # The class aggregate itself is not compared directly.
    assert "mod.py:Foo" not in flattened


# --- integration: git materialization in a throwaway repo --------------------


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test"], cwd=repo)


def _commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(textwrap.dedent(content))
    _run(["git", "add", name], cwd=repo)
    _run(["git", "commit", "-m", message], cwd=repo)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _init_repo(repo)
    return repo


def test_check_fails_when_new_function_is_too_complex(git_repo: Path):
    base_rev = _commit_file(git_repo, "mod.py", "def existing():\n    return 1\n", "base")
    head_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        def existing():
            return 1

        def messy(x):
            if x == 1:
                return 1
            elif x == 2:
                return 2
            elif x == 3:
                return 3
            elif x == 4:
                return 4
            elif x == 5:
                return 5
            elif x == 6:
                return 6
            elif x == 7:
                return 7
            elif x == 8:
                return 8
            elif x == 9:
                return 9
            elif x == 10:
                return 10
            elif x == 11:
                return 11
            return 0
        """,
        "add messy function",
    )

    violations = check(base_rev, head_rev, cwd=git_repo)

    assert any(v.qualname == "mod.py:messy" for v in violations)


def test_check_fails_when_existing_function_gets_more_complex(git_repo: Path):
    base_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        def fn(x):
            if x:
                return 1
            return 0
        """,
        "base",
    )
    head_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        def fn(x):
            if x == 1:
                return 1
            elif x == 2:
                return 2
            elif x == 3:
                return 3
            return 0
        """,
        "increase complexity",
    )

    violations = check(base_rev, head_rev, cwd=git_repo)

    assert len(violations) == 1
    assert violations[0].qualname == "mod.py:fn"
    assert "increased" in str(violations[0])


def test_check_passes_when_existing_function_is_simplified(git_repo: Path):
    base_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        def fn(x):
            if x == 1:
                return 1
            elif x == 2:
                return 2
            elif x == 3:
                return 3
            return 0
        """,
        "base",
    )
    head_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        def fn(x):
            if x:
                return 1
            return 0
        """,
        "simplify",
    )

    assert check(base_rev, head_rev, cwd=git_repo) == []


def test_check_passes_when_unrelated_lines_change_but_complexity_is_unchanged(git_repo: Path):
    base_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        def fn(x):
            if x:
                return 1
            return 0
        """,
        "base",
    )
    head_rev = _commit_file(
        git_repo,
        "mod.py",
        """
        # a harmless comment
        def fn(x):
            if x:
                return 1
            return 0
        """,
        "touch unrelated line",
    )

    assert check(base_rev, head_rev, cwd=git_repo) == []


def test_check_passes_with_no_changed_python_files(git_repo: Path):
    base_rev = _commit_file(git_repo, "README.md", "hello\n", "base")
    head_rev = _commit_file(git_repo, "README.md", "hello world\n", "docs")

    assert check(base_rev, head_rev, cwd=git_repo) == []
