"""
CFA Cockpit — Generator

Reads the K8341 source spreadsheets, computes derived figures, renders the
Jinja2 template, and writes the final HTML.

Usage:
    python generate_cockpit.py
    python generate_cockpit.py --project-dir /path/to/spreadsheets --out /path/to/output.html
    COCKPIT_DATA_DIR=/path/to/spreadsheets python generate_cockpit.py

By default, reads from agents/finance/design/fixtures/ (gitignored local
copies of the source spreadsheets) and writes to agents/finance/design/
CFA_Cockpit.html alongside the template.

In production (wfd-os Finance portal), this becomes a server-side render where
the data dict comes from grant-compliance API endpoints instead of openpyxl.
"""

import argparse
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from cockpit_data import DEFAULT_DATA_DIR, canonical_provider, extract_all, resolve_data_dir


HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE / "cockpit_template.html"
DEFAULT_OUT = HERE / "CFA_Cockpit.html"


def render_cockpit(project_dir, template_path: Path, out_path: Path) -> None:
    # 1. Extract data from spreadsheets
    data = extract_all(project_dir)

    # 2. Compute additional derived values the template expects
    trailing_q1_total = sum(
        row["invoice"] for row in data["placements"]["q1_provider_actuals_breakdown"]
        if row["invoice"] is not None
    )
    high_priority_count = sum(
        1 for item in data["action_items"] if item["priority"] == "HIGH"
    )

    # 3. Set up Jinja2 with template directory
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["canonical_provider"] = canonical_provider
    template = env.get_template(template_path.name)

    # 4. Render
    rendered = template.render(
        summary=data["summary"],
        providers=data["providers"],
        action_items=data["action_items"],
        placements=data["placements"],
        cost_per_placement=data["cost_per_placement"],
        budget=data["budget"],
        recovered=data["recovered"],
        financial_performance=data["financial_performance"],
        charts=data["charts"],
        drills=data["drills"],
        trailing_q1_total=trailing_q1_total,
        high_priority_count=high_priority_count,
    )

    out_path.write_text(rendered, encoding="utf-8")
    print(f"Rendered cockpit to {out_path}")
    print(f"  Data dir:           {resolve_data_dir(project_dir)}")
    print(f"  Backbone runway:    ${data['summary']['backbone_runway_combined']:,.0f}")
    print(f"  GJC remaining:      ${data['summary']['gjc_remaining']:,.0f}")
    print(f"  Action items:       {len(data['action_items'])} ({high_priority_count} high)")
    print(f"  Providers loaded:   {sum(len(v) for v in data['providers'].values())}")
    print(f"  Trailing Q1 invoices: ${trailing_q1_total:,.0f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=None, type=Path,
                        help="Directory of source spreadsheets. Defaults to "
                             "COCKPIT_DATA_DIR env var, else "
                             f"{DEFAULT_DATA_DIR}")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()

    render_cockpit(args.project_dir, args.template, args.out)
