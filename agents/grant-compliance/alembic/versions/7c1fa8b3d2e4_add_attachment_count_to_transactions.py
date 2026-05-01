"""add attachment_count to transactions

Adds the documentation-linkage signal described in step 1.5 of
agents/grant-compliance/docs/audit_readiness_tab_spec.md. Populated by
quickbooks.sync.sync_attachables from QB's Attachable entity.

Revision ID: 7c1fa8b3d2e4
Revises: 52e509f9e39a
Create Date: 2026-04-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1fa8b3d2e4'
down_revision: Union[str, Sequence[str], None] = '52e509f9e39a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add attachment_count column with server default 0."""
    op.add_column(
        'transactions',
        sa.Column(
            'attachment_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
        schema='grant_compliance',
    )


def downgrade() -> None:
    """Downgrade schema — drop the attachment_count column."""
    op.drop_column('transactions', 'attachment_count', schema='grant_compliance')
