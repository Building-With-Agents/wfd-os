"""
Finance cockpit DataSource abstraction.

The cockpit reads from different sources depending on deployment phase:
* Phase 2B (today):    ExcelDataSource — reads local xlsx fixtures
* Phase 2B + 1 (soon): QBDataSource    — reads QuickBooks sandbox once
                                         Ritu's sandbox approval lands

The abstraction lets cockpit_api.py hold a single reference without caring
which source is behind it. Swapping to QB is a one-line constructor change
when the time comes. Recruiting uses a parallel pattern in agents/job-board/.

Implementation notes
* ExcelDataSource wraps design/cockpit_data.py::extract_all() — does NOT
  reimplement. cockpit_data.py stays the single source of truth for how
  the raw sheets turn into the cockpit data dict.
* Results are memoized until refresh() is called. The Excel reads take ~1s
  on a warm cache; without memoization every endpoint call would re-parse.
* COCKPIT_DATA_DIR env var path already plumbed through cockpit_data.py
  (resolve_data_dir helper). ExcelDataSource honors the same contract.
"""

from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Make design/ importable without requiring the package to be installed.
_HERE = Path(__file__).resolve().parent
_DESIGN = _HERE / "design"
if str(_DESIGN) not in sys.path:
    sys.path.insert(0, str(_DESIGN))

from cockpit_data import extract_all, resolve_data_dir  # noqa: E402


class DataSource(ABC):
    """Shared interface: cockpit_api.py only talks through this."""

    @abstractmethod
    def extract(self) -> dict:
        """Return the full cockpit data dict — same shape extract_all() emits."""

    @abstractmethod
    def refresh(self) -> dict:
        """Force re-read from source. Returns the new data."""

    @abstractmethod
    def info(self) -> dict:
        """Describe the source — type, path/endpoint, file list, liveness."""


class ExcelDataSource(DataSource):
    """Reads cockpit data from K8341 source spreadsheets in fixtures/."""

    def __init__(self, project_dir: Optional[Path | str] = None):
        self.project_dir = project_dir
        self._cache: Optional[dict] = None
        self._loaded_at: Optional[datetime] = None

    # --- DataSource interface ---

    def extract(self) -> dict:
        if self._cache is None:
            self._load()
        return self._cache  # type: ignore[return-value]

    def refresh(self) -> dict:
        self._load()
        return self._cache  # type: ignore[return-value]

    def info(self) -> dict:
        path = resolve_data_dir(self.project_dir)
        files = sorted(p.name for p in path.glob("*.xlsx")) if path.exists() else []
        return {
            "type": "excel",
            "path": str(path),
            "files": files,
            "available": path.exists() and bool(files),
            "loaded_at": self._loaded_at.isoformat() if self._loaded_at else None,
        }

    # --- internals ---

    def _load(self) -> None:
        self._cache = extract_all(self.project_dir)
        self._loaded_at = datetime.now(timezone.utc)


class QBDataSource(DataSource):
    """Placeholder for the live QuickBooks pull.

    The swap happens once Ritu's QB sandbox approval lands and the
    mapping from QB transactions → cockpit data dict is implemented.
    Until then this class exists to document the eventual shape and to
    fail loudly if it's accidentally instantiated.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "QBDataSource is not implemented yet. Ritu's QB sandbox approval "
            "is still pending. Use ExcelDataSource in the meantime."
        )

    def extract(self) -> dict:  # pragma: no cover
        raise NotImplementedError

    def refresh(self) -> dict:  # pragma: no cover
        raise NotImplementedError

    def info(self) -> dict:  # pragma: no cover
        return {"type": "qb", "available": False, "status": "not_implemented"}


def default_source() -> DataSource:
    """Resolve the DataSource a fresh cockpit_api should use.

    Precedence:
      COCKPIT_SOURCE=qb       → QBDataSource (currently raises)
      COCKPIT_SOURCE=excel    → ExcelDataSource (default)
      unset                   → ExcelDataSource
    """
    src = os.environ.get("COCKPIT_SOURCE", "excel").lower()
    if src == "qb":
        return QBDataSource()
    return ExcelDataSource()
