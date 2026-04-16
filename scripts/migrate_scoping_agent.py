"""One-off migration script: copies Scoping/Grant agent code into wfd-os
and rewrites imports to use the new package structure.

Idempotent — safe to re-run. Writes to agents/graph/, agents/scoping/,
agents/grant/. Does not delete the source projects.
"""
import os
import re
import shutil
from pathlib import Path

SRC_SCOPING = Path("C:/Users/ritub/projects/cfa-scoping-agent")
SRC_GRANT = Path("C:/Users/ritub/projects/cfa-grant-agent")
DST_ROOT = Path("C:/Users/ritub/projects/wfd-os/agents")


# Import rewrites: (old pattern, new pattern)
# Applied in order, first match wins per line
SCOPING_REWRITES = [
    # config
    (r"^import config$", "from agents.graph import config"),
    # graph package
    (r"^from graph\.auth import", "from agents.graph.auth import"),
    (r"^from graph\.sharepoint import", "from agents.graph.sharepoint import"),
    (r"^from graph\.teams import", "from agents.graph.teams import"),
    (r"^from graph\.transcript import", "from agents.graph.transcript import"),
    # scoping package
    (r"^from scoping\.models import", "from wfdos_common.models.scoping import"),
    (r"^from scoping\.pipeline import", "from agents.scoping.pipeline import"),
    (r"^from scoping\.postcall import", "from agents.scoping.postcall import"),
    (r"^from scoping\.webhook import", "from agents.scoping.webhook import"),
    # research -> scoping.research / transcript_analysis
    (r"^from research\.prospect import", "from agents.scoping.research import"),
    (r"^from research\.transcript_analysis import", "from agents.scoping.transcript_analysis import"),
    (r"^import research\.prospect as", "import agents.scoping.research as"),
    (r"^import research\.transcript_analysis as", "import agents.scoping.transcript_analysis as"),
    # inline imports (not at start of line)
    (r"\bfrom research\.transcript_analysis import", "from agents.scoping.transcript_analysis import"),
    (r"\bfrom research\.prospect import", "from agents.scoping.research import"),
    # docs -> scoping
    (r"^from docs\.briefing import", "from agents.scoping.briefing import"),
    (r"^from docs\.proposal import", "from agents.scoping.proposal import"),
]


def rewrite_content(content: str, rewrites: list) -> str:
    """Apply import rewrites line by line using multiline regex."""
    new_content = content
    for old_pat, new_pat in rewrites:
        new_content = re.sub(old_pat, new_pat, new_content, flags=re.MULTILINE)
    return new_content


def copy_and_rewrite(src: Path, dst: Path, rewrites: list) -> None:
    """Copy a .py file and rewrite its imports."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8")
    new_content = rewrite_content(content, rewrites)
    dst.write_text(new_content, encoding="utf-8")
    print(f"  {src.name} -> {dst.relative_to(DST_ROOT.parent)}")


def write_init(path: Path, comment: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'"""{comment}"""\n', encoding="utf-8")


def migrate_graph():
    print("\n[1] Graph API client -> agents/graph/")
    graph_src = SRC_SCOPING / "graph"
    graph_dst = DST_ROOT / "graph"
    for name in ["auth.py", "sharepoint.py", "teams.py", "transcript.py"]:
        copy_and_rewrite(graph_src / name, graph_dst / name, SCOPING_REWRITES)
    write_init(
        graph_dst / "__init__.py",
        "Microsoft Graph API client for WFD OS — shared across Scoping/Grant agents",
    )


def migrate_scoping():
    print("\n[2] Scoping Agent -> agents/scoping/")
    scoping_dst = DST_ROOT / "scoping"

    # scoping/* files (keep the same names)
    scoping_src = SRC_SCOPING / "scoping"
    for name in ["models.py", "pipeline.py", "postcall.py", "webhook.py"]:
        copy_and_rewrite(scoping_src / name, scoping_dst / name, SCOPING_REWRITES)

    # research/prospect.py -> scoping/research.py (renamed)
    copy_and_rewrite(
        SRC_SCOPING / "research" / "prospect.py",
        scoping_dst / "research.py",
        SCOPING_REWRITES,
    )

    # research/transcript_analysis.py -> scoping/transcript_analysis.py
    copy_and_rewrite(
        SRC_SCOPING / "research" / "transcript_analysis.py",
        scoping_dst / "transcript_analysis.py",
        SCOPING_REWRITES,
    )

    # docs/briefing.py -> scoping/briefing.py
    copy_and_rewrite(
        SRC_SCOPING / "docs" / "briefing.py",
        scoping_dst / "briefing.py",
        SCOPING_REWRITES,
    )
    copy_and_rewrite(
        SRC_SCOPING / "docs" / "proposal.py",
        scoping_dst / "proposal.py",
        SCOPING_REWRITES,
    )

    # run_phase1_live.py -> scoping/runner.py
    copy_and_rewrite(
        SRC_SCOPING / "run_phase1_live.py",
        scoping_dst / "runner.py",
        SCOPING_REWRITES,
    )

    # app.py -> scoping/api.py
    copy_and_rewrite(
        SRC_SCOPING / "app.py",
        scoping_dst / "api.py",
        SCOPING_REWRITES,
    )

    write_init(scoping_dst / "__init__.py", "Scoping Agent for WFD OS")


def migrate_grant():
    print("\n[3] Grant Agent -> agents/grant/")
    grant_dst = DST_ROOT / "grant"
    grant_dst.mkdir(parents=True, exist_ok=True)

    # Copy reconciliation, ingestion, queries folders if they exist
    for folder in ["reconciliation", "ingestion", "queries", "database"]:
        src = SRC_GRANT / folder
        if src.exists() and src.is_dir():
            dst = grant_dst / folder
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            print(f"  {folder}/ -> agents/grant/{folder}/")

    # Copy main app.py if it exists
    if (SRC_GRANT / "app.py").exists():
        shutil.copy2(SRC_GRANT / "app.py", grant_dst / "api.py")
        print(f"  app.py -> agents/grant/api.py")

    write_init(grant_dst / "__init__.py", "Grant Agent for WFD OS (WJI dashboard)")


if __name__ == "__main__":
    print("=" * 60)
    print("WFD OS Migration: Scoping + Grant Agents")
    print("=" * 60)

    migrate_graph()
    migrate_scoping()
    migrate_grant()

    print("\n" + "=" * 60)
    print("Migration complete. Next: run test_migration.py to verify.")
    print("=" * 60)
