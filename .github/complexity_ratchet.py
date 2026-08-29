#!/usr/bin/env python3
"""Touched-code Radon complexity ratchet.

Compares the Radon cyclomatic complexity of Python blocks (functions,
methods, and nested closures) in changed files between a base revision and
a head revision. Fails when:

  * a block that exists only at head is worse than Radon grade B
    (complexity > 10), or
  * a block present at both revisions has higher complexity at head than
    at base (even if the letter grade is unchanged, e.g. C11 -> C15).

Existing code that is not touched, and touched blocks whose complexity is
unchanged or improved, always pass. This is intentionally additive to (and
does not replace) the whole-codebase D/E/F floor enforced separately with
``radon cc -n D``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

NEW_BLOCK_MAX_COMPLEXITY = 10  # Radon grade B ceiling; grade C+ fails.
DEFAULT_BASE_BRANCH = "origin/main"


@dataclass(frozen=True)
class Violation:
    qualname: str
    message: str

    def __str__(self) -> str:
        return f"{self.qualname}: {self.message}"


def run_git(args: list[str], cwd: str | Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def find_merge_base(base_ref: str, head_ref: str, cwd: str | Path | None = None) -> str:
    return run_git(["merge-base", base_ref, head_ref], cwd=cwd).strip()


def changed_python_files(base_rev: str, head_rev: str, cwd: str | Path | None = None) -> list[str]:
    output = run_git(["diff", "--name-only", "--diff-filter=d", base_rev, head_rev], cwd=cwd)
    return sorted(line for line in output.splitlines() if line.endswith(".py"))


def read_file_at_revision(revision: str, path: str, cwd: str | Path | None = None) -> str | None:
    """Return the file's contents at `revision`, or None if it didn't exist."""
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def radon_blocks_for_sources(sources: dict[str, str]) -> dict[str, list[dict]]:
    """Run `radon cc --json` over materialized copies of `sources`.

    `sources` maps a logical path (used as the module key in the result) to
    file content. Each source is written to its own temp file (basename
    preserved so radon's block names/types stay unaffected) and radon is
    invoked once across all of them.
    """
    if not sources:
        return {}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_to_logical: dict[str, str] = {}
        tmp_paths: list[str] = []
        for index, (logical_path, content) in enumerate(sources.items()):
            tmp_dir = tmp_root / str(index)
            tmp_dir.mkdir()
            tmp_path = tmp_dir / Path(logical_path).name
            tmp_path.write_text(content)
            tmp_to_logical[str(tmp_path)] = logical_path
            tmp_paths.append(str(tmp_path))

        result = subprocess.run(
            [sys.executable, "-m", "radon", "cc", "--json", *tmp_paths],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"radon cc failed: {result.stderr.strip()}")

        raw = json.loads(result.stdout or "{}")
        return {tmp_to_logical[tmp_path]: blocks for tmp_path, blocks in raw.items()}


def flatten_blocks(blocks: list[dict], module: str, prefix: tuple[str, ...] = ()) -> dict[str, int]:
    """Flatten radon's nested JSON blocks into {qualname: complexity}.

    Qualified names are `module:Class.method.<closure>` style, built from the
    enclosing class/function names so methods and nested closures can be
    matched by identity across revisions.
    """
    result: dict[str, int] = {}
    for block in blocks:
        name_parts = prefix + (block["name"],)
        qualname = f"{module}:{'.'.join(name_parts)}"
        block_type = block.get("type")
        if block_type != "class":
            result[qualname] = block["complexity"]
        nested = block.get("methods") or block.get("closures") or []
        result.update(flatten_blocks(nested, module, name_parts))
    return result


def collect_complexity(
    base_rev: str, head_rev: str, files: list[str], cwd: str | Path | None = None
):
    """Return (base_blocks, head_blocks): {path: {qualname: complexity}}."""
    base_sources: dict[str, str] = {}
    head_sources: dict[str, str] = {}
    for path in files:
        base_content = read_file_at_revision(base_rev, path, cwd=cwd)
        if base_content is not None:
            base_sources[path] = base_content
        head_content = read_file_at_revision(head_rev, path, cwd=cwd)
        if head_content is not None:
            head_sources[path] = head_content

    base_raw = radon_blocks_for_sources(base_sources)
    head_raw = radon_blocks_for_sources(head_sources)

    base_blocks = {path: flatten_blocks(blocks, path) for path, blocks in base_raw.items()}
    head_blocks = {path: flatten_blocks(blocks, path) for path, blocks in head_raw.items()}
    return base_blocks, head_blocks


def compare_blocks(base_blocks: dict[str, int], head_blocks: dict[str, int]) -> list[Violation]:
    """Compare two flattened {qualname: complexity} maps for a single file."""
    violations: list[Violation] = []
    for qualname, head_complexity in head_blocks.items():
        base_complexity = base_blocks.get(qualname)
        if base_complexity is None:
            if head_complexity > NEW_BLOCK_MAX_COMPLEXITY:
                violations.append(
                    Violation(
                        qualname,
                        f"new block has complexity {head_complexity} "
                        f"({_grade(head_complexity)}); must be grade B or better "
                        f"(complexity <= {NEW_BLOCK_MAX_COMPLEXITY})",
                    )
                )
        elif head_complexity > base_complexity:
            violations.append(
                Violation(
                    qualname,
                    f"complexity increased from {base_complexity} "
                    f"({_grade(base_complexity)}) to {head_complexity} "
                    f"({_grade(head_complexity)})",
                )
            )
    return violations


def _grade(complexity: int) -> str:
    from radon.complexity import cc_rank

    return f"grade {cc_rank(complexity)}"


def check(base_rev: str, head_rev: str, cwd: str | Path | None = None) -> list[Violation]:
    files = changed_python_files(base_rev, head_rev, cwd=cwd)
    if not files:
        return []

    base_blocks, head_blocks = collect_complexity(base_rev, head_rev, files, cwd=cwd)

    violations: list[Violation] = []
    for path in files:
        violations.extend(compare_blocks(base_blocks.get(path, {}), head_blocks.get(path, {})))
    return violations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=None,
        help=f"Base revision (default: merge-base of {DEFAULT_BASE_BRANCH} and --head)",
    )
    parser.add_argument("--head", default="HEAD", help="Head revision (default: HEAD)")
    parser.add_argument(
        "--base-branch",
        default=DEFAULT_BASE_BRANCH,
        help=f"Branch to diff against when --base is not given (default: {DEFAULT_BASE_BRANCH})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_rev = args.base or find_merge_base(args.base_branch, args.head)

    violations = check(base_rev, args.head)

    if violations:
        for violation in violations:
            print(violation)
        print(
            "::error::complexity ratchet found regressions in touched code; simplify before merging"
        )
        return 1

    print("Complexity ratchet passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
