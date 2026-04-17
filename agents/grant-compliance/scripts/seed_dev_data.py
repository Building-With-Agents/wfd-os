"""Seed the dev database with realistic example data.

Creates:
  - 1 federal funder + 1 federal grant (HRSA-style, ending Sept 2026)
  - 1 foundation funder + 1 foundation grant
  - QB account/class mirror + sample transactions via fixture
  - 2 employees, one assigned to both grants

Run after init_db.py. Idempotent: re-running won't duplicate.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from grant_compliance.db.models import (
    BudgetLine,
    Employee,
    Funder,
    FunderType,
    Grant,
)
from grant_compliance.db.session import SessionLocal, init_db
from grant_compliance.quickbooks.sync import seed_from_fixture

FIXTURE = Path(__file__).parent / "fixtures" / "qb_sandbox.json"


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Funders ----------------------------------------------------------
        federal = db.query(Funder).filter(Funder.name == "HRSA (example)").first()
        if not federal:
            federal = Funder(
                name="HRSA (example)",
                funder_type=FunderType.federal,
                cfda_number="93.243",
            )
            db.add(federal)
            db.flush()

        foundation = db.query(Funder).filter(Funder.name == "Example Foundation").first()
        if not foundation:
            foundation = Funder(name="Example Foundation", funder_type=FunderType.foundation)
            db.add(foundation)
            db.flush()

        # Grants -----------------------------------------------------------
        federal_grant = db.query(Grant).filter(Grant.name == "Community Health Initiative").first()
        if not federal_grant:
            federal_grant = Grant(
                funder_id=federal.id,
                name="Community Health Initiative",
                award_number="H79TI000000",
                qb_class_name="Federal:CHI",
                period_start=date(2024, 4, 1),
                period_end=date(2026, 9, 30),
                total_award_cents=75_000_000,  # $750k
                indirect_rate_pct=10.0,
                indirect_rate_basis="MTDC",
                scope_of_work=(
                    "Provide outpatient mental health services to underserved adults; "
                    "training of peer support specialists; data collection and reporting."
                ),
            )
            db.add(federal_grant)
            db.flush()
            db.add_all(
                [
                    BudgetLine(
                        grant_id=federal_grant.id,
                        category="Personnel",
                        budgeted_cents=45_000_000,
                        effective_from=date(2024, 4, 1),
                    ),
                    BudgetLine(
                        grant_id=federal_grant.id,
                        category="Fringe Benefits",
                        budgeted_cents=12_000_000,
                        effective_from=date(2024, 4, 1),
                    ),
                    BudgetLine(
                        grant_id=federal_grant.id,
                        category="Supplies",
                        budgeted_cents=4_000_000,
                        effective_from=date(2024, 4, 1),
                    ),
                    BudgetLine(
                        grant_id=federal_grant.id,
                        category="Travel",
                        budgeted_cents=2_500_000,
                        effective_from=date(2024, 4, 1),
                    ),
                    BudgetLine(
                        grant_id=federal_grant.id,
                        category="Indirect",
                        budgeted_cents=6_500_000,
                        effective_from=date(2024, 4, 1),
                    ),
                    BudgetLine(
                        grant_id=federal_grant.id,
                        category="Other",
                        budgeted_cents=5_000_000,
                        effective_from=date(2024, 4, 1),
                    ),
                ]
            )

        foundation_grant = db.query(Grant).filter(Grant.name == "Peer Training Pilot").first()
        if not foundation_grant:
            foundation_grant = Grant(
                funder_id=foundation.id,
                name="Peer Training Pilot",
                award_number="EF-2025-1234",
                qb_class_name="Foundation:Peer",
                period_start=date(2025, 1, 1),
                period_end=date(2026, 12, 31),
                total_award_cents=15_000_000,  # $150k
                scope_of_work="Pilot peer support specialist training curriculum.",
            )
            db.add(foundation_grant)

        # Employees --------------------------------------------------------
        for name, email in [("Alex Rivera", "alex@example.org"), ("Sam Chen", "sam@example.org")]:
            if not db.query(Employee).filter(Employee.name == name).first():
                db.add(Employee(name=name, email=email))

        # QB mirror + transactions from fixture ----------------------------
        if FIXTURE.exists():
            counts = seed_from_fixture(db, FIXTURE)
            print(f"Loaded from fixture: {counts}")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
