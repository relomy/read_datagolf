from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if SRC_PATH.is_dir():
    src_str = str(SRC_PATH)
    if not sys.path or sys.path[0] != src_str:
        if src_str in sys.path:
            sys.path.remove(src_str)
        sys.path.insert(0, src_str)


def _run() -> None:
    from read_datagolf.cli.read_datagolf import run_cli

    run_cli()


if __name__ == "__main__":
    _run()
