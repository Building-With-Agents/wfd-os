"""Instantiate the EchoAgent reference implementation of the Agent ABC
and assert INTAKE_COMPLETE signal detection works end-to-end (#26).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import fail, ok  # noqa: E402

from wfdos_common.agent import EchoAgent


def main() -> None:
    a = EchoAgent()
    r = a.process(
        "intake complete, ready to scope",
        metadata={"tenant_id": "waifinder-flagship"},
    )
    if r.response != "echo: intake complete, ready to scope":
        fail(f"unexpected response: {r.response!r}")
    if r.action != "intake_complete":
        fail(f"expected action=intake_complete, got {r.action!r}")
    if r.metadata.get("tenant_id") != "waifinder-flagship":
        fail(f"metadata.tenant_id missing or wrong: {r.metadata!r}")

    ok(f"EchoAgent -- action={r.action}, latency_ms={r.metadata['latency_ms']}")


if __name__ == "__main__":
    main()
