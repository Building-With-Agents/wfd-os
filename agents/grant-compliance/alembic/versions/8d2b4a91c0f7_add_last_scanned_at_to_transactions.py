"""add last_scanned_at to transactions

Adds the scan-freshness signal described in step 2 of
agents/grant-compliance/docs/audit_readiness_tab_spec.md. Stamped by
ComplianceMonitor.scan_transaction on every evaluation. Drives the
denominator for the Audit Readiness tab's allowable_costs percentage —
only transactions scanned within the freshness window count.

Revision ID: 8d2b4a91c0f7
Revises: 7c1fa8b3d2e4
Create Date: 2026-04-23 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d2b4a91c0f7'
down_revision: Union[str, Sequence[str], None] = '7c1fa8b3d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add nullable last_scanned_at column."""
    op.add_column(
        'transactions',
        sa.Column(
            'last_scanned_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema='grant_compliance',
    )


def downgrade() -> None:
    """Downgrade schema — drop the last_scanned_at column."""
    op.drop_column('transactions', 'last_scanned_at', schema='grant_compliance')
