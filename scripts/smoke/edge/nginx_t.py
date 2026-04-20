"""Validate the committed nginx config syntactically.

Requires nginx installed locally. The committed conf references certbot
TLS paths that likely don't exist on dev machines; this script creates
empty stand-ins in a temp directory so nginx -t can parse the file.

On Windows without WSL + nginx, the script SKIPs (exit 0) rather than
failing — the production validation happens on the VM.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import fail, ok, skip  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]
CONF = _REPO_ROOT / "infra" / "edge" / "nginx" / "wfdos-platform.conf"


def main() -> None:
    if not CONF.exists():
        fail(f"config missing: {CONF}")

    nginx_bin = shutil.which("nginx")
    if nginx_bin is None:
        skip("nginx not installed locally; run this on the VM instead")

    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        # Stub out the TLS files the conf references.
        for f in ("fullchain.pem", "privkey.pem", "options-ssl-nginx.conf", "ssl-dhparams.pem"):
            (tmp / f).touch()

        raw = CONF.read_text(encoding="utf-8")
        patched = raw
        patched = re.sub(
            r"/etc/letsencrypt/live/[^/]+/fullchain\.pem",
            str(tmp / "fullchain.pem"),
            patched,
        )
        patched = re.sub(
            r"/etc/letsencrypt/live/[^/]+/privkey\.pem",
            str(tmp / "privkey.pem"),
            patched,
        )
        patched = patched.replace(
            "/etc/letsencrypt/options-ssl-nginx.conf",
            str(tmp / "options-ssl-nginx.conf"),
        )
        patched = patched.replace(
            "/etc/letsencrypt/ssl-dhparams.pem",
            str(tmp / "ssl-dhparams.pem"),
        )

        # Wrap the conf in an events {} + http { ... } block so nginx -t
        # will accept it standalone.
        wrapper_path = tmp / "nginx.conf"
        wrapper_path.write_text(
            f"events {{}}\nhttp {{\n{patched}\n}}\n", encoding="utf-8"
        )

        result = subprocess.run(
            [nginx_bin, "-t", "-c", str(wrapper_path)],
            capture_output=True,
            text=True,
        )

    combined = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 or "syntax is ok" not in combined:
        fail("nginx -t rejected the config", body=combined)

    ok("nginx -t accepts wfdos-platform.conf")


if __name__ == "__main__":
    main()
