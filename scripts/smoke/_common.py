"""Shared helpers for scripts/smoke/*/*.py — no external deps beyond
httpx (which is a wfdos-common runtime dep, so it's available in any
environment that ran `pip install -e packages/wfdos-common`).

Conventions used by every smoke script:
- Exit 0 on pass, 1 on assertion failure, 2 on misuse (argparse does this).
- Print OK: <what> on success to stdout.
- Print FAIL: <reason> on failure to stderr.
- SKIP: <reason> to stderr + exit 0 when preconditions aren't met
  (e.g. optional binaries missing).

Cross-platform notes:
- Works on macOS, Linux, and Windows PowerShell (the target).
- Uses httpx for HTTP (no curl dependency).
- Uses pathlib for file ops.
- No shell-out unless absolutely necessary (pytest + nginx).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional


def build_parser(description: str) -> argparse.ArgumentParser:
    """Return an argparse parser with --base-url pre-configured. Each
    script adds its own positional/optional args on top."""
    p = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL"),
        help="Override the script's default base URL (also via BASE_URL env).",
    )
    return p


def ok(message: str) -> None:
    """Print the pass marker and exit 0. Last line of stdout is always
    the OK: line so `script.py | tail -n1` is a clean pass/fail signal."""
    print(f"OK: {message}")
    sys.exit(0)


def fail(message: str, *, body: Optional[Any] = None) -> "None":
    """Print the fail marker to stderr and exit 1."""
    print(f"FAIL: {message}", file=sys.stderr)
    if body is not None:
        print(str(body)[:2000], file=sys.stderr)
    sys.exit(1)


def skip(message: str) -> None:
    """Print the skip marker to stderr and exit 0 (smoke didn't fail —
    it just wasn't applicable on this host)."""
    print(f"SKIP: {message}", file=sys.stderr)
    sys.exit(0)


def resolve_base_url(args: argparse.Namespace, default: str) -> str:
    """Argparse default → BASE_URL env → hardcoded default."""
    return args.base_url or default
