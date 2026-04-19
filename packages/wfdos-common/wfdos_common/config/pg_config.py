"""Compat shim for the `scripts/pgconfig.py` `PG_CONFIG` dict.

Pre-#27, every service did::

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
    from pgconfig import PG_CONFIG

That `sys.path.insert` is what #27 eliminates. Services now import::

    from wfdos_common.config import PG_CONFIG

PG_CONFIG is a lazy-loaded dict that pulls values from
`wfdos_common.config.settings.pg`. Same shape + same keys as the old
file so existing call sites (`psycopg2.connect(**PG_CONFIG)`) don't
change.

`scripts/pgconfig.py` itself is kept as a one-line re-export for any
CLI script that still imports it by filename path.
"""

from __future__ import annotations

from typing import Any


class _PgConfigDict(dict):
    """Lazy-filled dict — resolves to settings values on first access.

    Acts as a normal dict afterward, so `psycopg2.connect(**PG_CONFIG)`
    unpacks correctly.
    """

    _loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        from wfdos_common.config import settings

        self.update({
            "host": settings.pg.host,
            "database": settings.pg.database,
            "user": settings.pg.user,
            "password": settings.pg.password or "",
            "port": settings.pg.port,
        })
        self._loaded = True

    def __getitem__(self, key: str) -> Any:
        self._ensure_loaded()
        return super().__getitem__(key)

    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def items(self):
        self._ensure_loaded()
        return super().items()

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def __len__(self):
        self._ensure_loaded()
        return super().__len__()

    def __repr__(self):
        self._ensure_loaded()
        # Mask password in repr for safety
        masked = {k: ("***" if k == "password" and v else v) for k, v in super().items()}
        return f"PG_CONFIG({masked})"


PG_CONFIG: dict = _PgConfigDict()
