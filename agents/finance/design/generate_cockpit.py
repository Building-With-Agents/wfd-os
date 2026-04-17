"""
CFA Cockpit — Generator

Reads the four K8341 spreadsheets, computes derived figures, renders the
Jinja2 template, and writes the final HTML.

Usage:
    python3 generate_cockpit.py
    python3 generate_cockpit.py --project-dir /path/to/spreadsheets --out /path/to/output.html

In production (wfd-os Finance portal), this becomes a server-side render where
the data dict comes from grant-compliance API endpoints instead of openpyxl.
"""

import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from cockpit_data import extract_all


def render_cockpit(project_dir: Path, template_path: Path, out_path: Path) -> None:
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

    out_path.write_text(rendered)
    print(f"✓ Rendered cockpit to {out_path}")
    print(f"  Backbone runway: ${data['summary']['backbone_runway_combined']:,.0f}")
    print(f"  GJC remaining: ${data['summary']['gjc_remaining']:,.0f}")
    print(f"  Action items: {len(data['action_items'])} ({high_priority_count} high)")
    print(f"  Providers loaded: {sum(len(v) for v in data['providers'].values())}")
    print(f"  Trailing Q1 invoices: ${trailing_q1_total:,.0f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default="/mnt/project", type=Path)
    parser.add_argument("--template", default="/home/claude/cockpit_template.html", type=Path)
    parser.add_argument("--out", default="/mnt/user-data/outputs/CFA_Cockpit.html", type=Path)
    args = parser.parse_args()

    render_cockpit(args.project_dir, args.template, args.out)
