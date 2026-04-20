"""Run the full wfdos-common test suite with the >=50% coverage floor.

Mirrors what CI runs. Exits 0 on pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "smoke"))

from _common import fail, ok  # noqa: E402


def main() -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "packages/wfdos-common/tests",
            "-q",
            "--cov=wfdos_common",
            "--cov-report=term",
            "--cov-fail-under=50",
        ],
        cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        fail(f"pytest exited {result.returncode}")
    ok("wfdos-common test suite green + coverage floor met")


if __name__ == "__main__":
    main()
