"""add contracts inventory tables

Adds the persistence layer for the Contracts Inventory feature per
agents/grant-compliance/docs/contracts_inventory_spec.md. Three new
tables under the grant_compliance schema:
  - contracts                       — primary entity, one row per K8341 contract
  - contract_amendments             — one row per amendment, FK contracts
  - contract_termination_details    — one row per terminated contract, FK contracts

Includes the procurement_method enum field on contracts (promoted from v1.1
to v1 per the 2026-04-30 spec amendment — see contracts_inventory_spec.md).

Revision ID: b51e9d3a8c14
Revises: a3f81cd7e22b
Create Date: 2026-04-30 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b51e9d3a8c14"
down_revision: Union[str, Sequence[str], None] = "a3f81cd7e22b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum value lists. Kept in sync with db.models.py — if you change either,
# change both. Values are also reflected in the spec document.
_CONTRACT_TYPE_VALUES = (
    "training_provider",
    "strategic_partner_subrecipient",
    "cfa_contractor",
    "subrecipient_other",
    "other",
)
_COMPLIANCE_CLASSIFICATION_VALUES = (
    "contractor_200_331b",
    "subrecipient_200_331a",
    "unclassified",
)
_CONTRACT_STATUS_VALUES = (
    "active",
    "closed_normally",
    "closed_with_findings",
    "terminated_by_cfa",
    "terminated_by_funder",
)
_PAYMENT_BASIS_VALUES = (
    "per_placement",
    "fixed_fee",
    "time_and_materials",
    "milestone",
    "cost_reimbursement",
    "other",
)
# procurement_method — promoted to v1 per 2026-04-30 amendment.
_PROCUREMENT_METHOD_VALUES = (
    "competitive_rfp",
    "competitive_proposals",
    "small_purchase",
    "micro_purchase",
    "sole_source",
    "informal",
    "unknown",
    "not_applicable_subaward",
)
_AMENDMENT_TYPE_VALUES = (
    "value_change",
    "period_extension",
    "scope_change",
    "termination",
    "other",
)
_TERMINATED_BY_VALUES = ("cfa", "funder", "mutual")


def upgrade() -> None:
    """Upgrade schema."""
    # ----- contracts -----
    op.create_table(
        "contracts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("grant_id", sa.String(length=36), nullable=False),
        sa.Column("vendor_party_id", sa.String(length=36), nullable=True),
        sa.Column("vendor_name_display", sa.String(length=255), nullable=False),
        sa.Column("vendor_legal_entity", sa.String(length=255), nullable=False),
        sa.Column("vendor_qb_names", sa.JSON(), nullable=False),
        sa.Column(
            "contract_type",
            sa.Enum(*_CONTRACT_TYPE_VALUES, name="contracttype"),
            nullable=False,
        ),
        sa.Column(
            "compliance_classification",
            sa.Enum(*_COMPLIANCE_CLASSIFICATION_VALUES, name="complianceclassification"),
            nullable=False,
        ),
        sa.Column("classification_rationale", sa.Text(), nullable=True),
        sa.Column(
            "procurement_method",
            sa.Enum(*_PROCUREMENT_METHOD_VALUES, name="procurementmethod"),
            nullable=False,
        ),
        sa.Column("original_executed_date", sa.Date(), nullable=True),
        sa.Column("original_effective_date", sa.Date(), nullable=True),
        sa.Column("current_end_date", sa.Date(), nullable=True),
        sa.Column("original_contract_value_cents", sa.BigInteger(), nullable=False),
        sa.Column("current_contract_value_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*_CONTRACT_STATUS_VALUES, name="contractstatus"),
            nullable=False,
        ),
        sa.Column(
            "payment_basis",
            sa.Enum(*_PAYMENT_BASIS_VALUES, name="paymentbasis"),
            nullable=False,
        ),
        sa.Column("payment_basis_detail", sa.Text(), nullable=True),
        sa.Column("executed_contract_link", sa.String(length=1024), nullable=True),
        sa.Column("scope_of_work_summary", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("record_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_updated_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["grant_compliance.grants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_contracts_grant_id"),
        "contracts",
        ["grant_id"],
        unique=False,
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_contracts_contract_type"),
        "contracts",
        ["contract_type"],
        unique=False,
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_contracts_compliance_classification"),
        "contracts",
        ["compliance_classification"],
        unique=False,
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_contracts_procurement_method"),
        "contracts",
        ["procurement_method"],
        unique=False,
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_contracts_status"),
        "contracts",
        ["status"],
        unique=False,
        schema="grant_compliance",
    )

    # ----- contract_amendments -----
    op.create_table(
        "contract_amendments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("amendment_number", sa.Integer(), nullable=False),
        sa.Column(
            "amendment_type",
            sa.Enum(*_AMENDMENT_TYPE_VALUES, name="amendmenttype"),
            nullable=False,
        ),
        sa.Column("executed_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("previous_value_cents", sa.BigInteger(), nullable=True),
        sa.Column("new_value_cents", sa.BigInteger(), nullable=True),
        sa.Column("previous_end_date", sa.Date(), nullable=True),
        sa.Column("new_end_date", sa.Date(), nullable=True),
        sa.Column("summary_of_changes", sa.Text(), nullable=True),
        sa.Column("document_link", sa.String(length=1024), nullable=True),
        sa.Column("record_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["grant_compliance.contracts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_contract_amendments_contract_id"),
        "contract_amendments",
        ["contract_id"],
        unique=False,
        schema="grant_compliance",
    )

    # ----- contract_termination_details -----
    op.create_table(
        "contract_termination_details",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column(
            "terminated_by",
            sa.Enum(*_TERMINATED_BY_VALUES, name="terminatedby"),
            nullable=False,
        ),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("termination_correspondence_link", sa.String(length=1024), nullable=True),
        sa.Column("final_reconciliation_link", sa.String(length=1024), nullable=True),
        sa.Column("closeout_findings", sa.Text(), nullable=True),
        sa.Column("record_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["grant_compliance.contracts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="grant_compliance",
    )
    # Unique index on contract_id enforces the one-termination-per-contract
    # constraint declared by `unique=True` on the model's contract_id column.
    op.create_index(
        op.f("ix_grant_compliance_contract_termination_details_contract_id"),
        "contract_termination_details",
        ["contract_id"],
        unique=True,
        schema="grant_compliance",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_grant_compliance_contract_termination_details_contract_id"),
        table_name="contract_termination_details",
        schema="grant_compliance",
    )
    op.drop_table("contract_termination_details", schema="grant_compliance")

    op.drop_index(
        op.f("ix_grant_compliance_contract_amendments_contract_id"),
        table_name="contract_amendments",
        schema="grant_compliance",
    )
    op.drop_table("contract_amendments", schema="grant_compliance")

    op.drop_index(
        op.f("ix_grant_compliance_contracts_status"),
        table_name="contracts",
        schema="grant_compliance",
    )
    op.drop_index(
        op.f("ix_grant_compliance_contracts_procurement_method"),
        table_name="contracts",
        schema="grant_compliance",
    )
    op.drop_index(
        op.f("ix_grant_compliance_contracts_compliance_classification"),
        table_name="contracts",
        schema="grant_compliance",
    )
    op.drop_index(
        op.f("ix_grant_compliance_contracts_contract_type"),
        table_name="contracts",
        schema="grant_compliance",
    )
    op.drop_index(
        op.f("ix_grant_compliance_contracts_grant_id"),
        table_name="contracts",
        schema="grant_compliance",
    )
    op.drop_table("contracts", schema="grant_compliance")
