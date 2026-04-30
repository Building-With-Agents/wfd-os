"""CLI entrypoint for the contracts bootstrap importer.

Usage:
    python -m grant_compliance.contracts_bootstrap import \\
        --file <path-to-xlsx> \\
        --grant-id <uuid> \\
        --actor <email>

    python -m grant_compliance.contracts_bootstrap import \\
        --file <path-to-xlsx> \\
        --grant-id <uuid> \\
        --actor <email> \\
        --dry-run

    python -m grant_compliance.contracts_bootstrap reconcile \\
        --grant-id <uuid>

The import command:
  1. Reads the Excel file (loader.py)
  2. Reports what would be imported (dry-run shows the parsed bundle)
  3. Asks for confirmation (skipped with --yes)
  4. Performs the import with full audit_log trail (importer.py)
  5. Computes Amendment 1 reconciliation (reconciliation.py) and prints
     drift warnings if any

The reconcile command runs reconciliation only against existing data;
useful after the API has been used to add or update contracts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from grant_compliance.contracts_bootstrap.importer import (
    ImporterError,
    import_bundle,
    write_failure_entry,
)
from grant_compliance.contracts_bootstrap.loader import (
    LoaderError,
    load_workbook_bundle,
)
from grant_compliance.contracts_bootstrap.reconciliation import (
    compute_reconciliation,
)
from grant_compliance.db.session import SessionLocal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m grant_compliance.contracts_bootstrap",
        description="Contracts inventory bootstrap importer.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser(
        "import", help="Import contracts from an Excel workbook."
    )
    p_import.add_argument(
        "--file", required=True, help="Path to the .xlsx workbook to import."
    )
    p_import.add_argument(
        "--grant-id", required=True, help="UUID of the grant to import contracts under."
    )
    p_import.add_argument(
        "--actor",
        required=True,
        help="Email of the staff member running this import (recorded in audit_log).",
    )
    p_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report only; do not write to the database.",
    )
    p_import.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt before persisting.",
    )

    p_reconcile = sub.add_parser(
        "reconcile",
        help="Compute Amendment 1 reconciliation against existing contracts.",
    )
    p_reconcile.add_argument("--grant-id", required=True)

    args = parser.parse_args(argv)

    if args.command == "import":
        return _cmd_import(args)
    if args.command == "reconcile":
        return _cmd_reconcile(args)
    parser.print_help()
    return 2


def _cmd_import(args: argparse.Namespace) -> int:
    file_path = Path(args.file)
    print(f"Loading {file_path} ...")
    try:
        bundle = load_workbook_bundle(file_path)
    except LoaderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"  Loaded: {len(bundle.contracts)} contracts, "
        f"{len(bundle.amendments)} amendments, "
        f"{len(bundle.terminations)} terminations"
    )
    print()
    print("  Contract record_keys:")
    for c in bundle.contracts:
        print(
            f"    - {c.record_key}: {c.vendor_name_display} "
            f"(${c.current_contract_value_cents / 100:,.2f}, "
            f"{c.contract_type.value}, {c.compliance_classification.value}, "
            f"procurement={c.procurement_method.value}, status={c.status.value})"
        )

    if args.dry_run:
        print()
        print("Dry-run: nothing persisted.")
        return 0

    if not args.yes:
        print()
        resp = input("Persist to database? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return 0

    db = SessionLocal()
    try:
        try:
            result = import_bundle(
                db,
                bundle=bundle,
                grant_id=args.grant_id,
                actor=args.actor,
                source_path=str(file_path),
            )
        except ImporterError as exc:
            db.rollback()
            print(f"ERROR: {exc}", file=sys.stderr)
            try:
                write_failure_entry(
                    db,
                    actor=args.actor,
                    source_path=str(file_path),
                    grant_id=args.grant_id,
                    error_message=str(exc),
                )
            except Exception as audit_exc:  # noqa: BLE001
                print(
                    f"  (also failed to write failure audit entry: {audit_exc})",
                    file=sys.stderr,
                )
            return 1
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print(f"ERROR: {exc!r}", file=sys.stderr)
            try:
                write_failure_entry(
                    db,
                    actor=args.actor,
                    source_path=str(file_path),
                    grant_id=args.grant_id,
                    error_message=repr(exc),
                )
            except Exception as audit_exc:  # noqa: BLE001
                print(
                    f"  (also failed to write failure audit entry: {audit_exc})",
                    file=sys.stderr,
                )
            return 1

        db.commit()
        print()
        print(
            f"Imported: {result.contracts_created} contracts, "
            f"{result.amendments_created} amendments, "
            f"{result.terminations_created} terminations."
        )

        # Reconciliation pass (always runs after a successful import)
        report = compute_reconciliation(db, grant_id=args.grant_id)
        _print_reconciliation(report)
        return 0
    finally:
        db.close()


def _cmd_reconcile(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        report = compute_reconciliation(db, grant_id=args.grant_id)
        _print_reconciliation(report)
        return 0 if report.overall_reconciles else 2
    finally:
        db.close()


def _print_reconciliation(report) -> None:  # type: ignore[no-untyped-def]
    print()
    print("Amendment 1 reconciliation:")
    for line in report.lines:
        status = "OK" if line.reconciles else "DRIFT"
        sign = "+" if line.drift_cents > 0 else ""
        print(
            f"  [{status}] {line.budget_line}: "
            f"expected ${line.expected_cents / 100:,.2f}, "
            f"actual ${line.actual_cents / 100:,.2f} "
            f"({line.contract_count} contract"
            f"{'s' if line.contract_count != 1 else ''}, "
            f"drift {sign}${line.drift_cents / 100:,.2f})"
        )
    if report.warnings:
        print()
        print("Drift warnings:")
        for w in report.warnings:
            print(f"  ! {w}")


if __name__ == "__main__":
    raise SystemExit(main())
