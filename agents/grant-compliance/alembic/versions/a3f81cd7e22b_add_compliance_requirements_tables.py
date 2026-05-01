"""add compliance requirements agent tables

Adds the persistence layer for the Compliance Requirements Agent
(Mode A output sets and Mode B Q&A log) per
agents/grant-compliance/docs/compliance_requirements_agent_spec.md.

Three new tables under the grant_compliance schema:
  - compliance_requirements_sets — one row per Mode A generation run
  - compliance_requirements      — child rows, one per generated Requirement
  - compliance_qa_log            — one row per Mode B query

Revision ID: a3f81cd7e22b
Revises: 8d2b4a91c0f7
Create Date: 2026-04-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f81cd7e22b"
down_revision: Union[str, Sequence[str], None] = "8d2b4a91c0f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ----- compliance_requirements_sets -----
    op.create_table(
        "compliance_requirements_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("grant_id", sa.String(length=36), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("regulatory_corpus_version", sa.String(length=100), nullable=False),
        sa.Column("grant_context", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_response_text", sa.Text(), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("superseded_by_id", sa.String(length=36), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["grant_compliance.grants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["grant_compliance.compliance_requirements_sets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_compliance_requirements_sets_grant_id"),
        "compliance_requirements_sets",
        ["grant_id"],
        unique=False,
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_compliance_requirements_sets_generated_at"),
        "compliance_requirements_sets",
        ["generated_at"],
        unique=False,
        schema="grant_compliance",
    )

    # ----- compliance_requirements -----
    op.create_table(
        "compliance_requirements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("set_id", sa.String(length=36), nullable=False),
        sa.Column("requirement_id", sa.String(length=100), nullable=False),
        sa.Column("compliance_area", sa.String(length=50), nullable=False),
        sa.Column("regulatory_citation", sa.String(length=255), nullable=False),
        sa.Column("regulatory_text_excerpt", sa.Text(), nullable=False),
        sa.Column("applicability", sa.JSON(), nullable=False),
        sa.Column("requirement_summary", sa.Text(), nullable=False),
        sa.Column("documentation_artifacts_required", sa.JSON(), nullable=False),
        sa.Column("documentation_form_guidance", sa.Text(), nullable=True),
        sa.Column("cfa_specific_application", sa.Text(), nullable=True),
        sa.Column("severity_if_missing", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["set_id"],
            ["grant_compliance.compliance_requirements_sets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_compliance_requirements_set_id"),
        "compliance_requirements",
        ["set_id"],
        unique=False,
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_compliance_requirements_compliance_area"),
        "compliance_requirements",
        ["compliance_area"],
        unique=False,
        schema="grant_compliance",
    )

    # ----- compliance_qa_log -----
    op.create_table(
        "compliance_qa_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asked_by", sa.String(length=255), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("context_hints", sa.JSON(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("refused", sa.Boolean(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("model_response_text", sa.Text(), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="grant_compliance",
    )
    op.create_index(
        op.f("ix_grant_compliance_compliance_qa_log_asked_at"),
        "compliance_qa_log",
        ["asked_at"],
        unique=False,
        schema="grant_compliance",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_grant_compliance_compliance_qa_log_asked_at"),
        table_name="compliance_qa_log",
        schema="grant_compliance",
    )
    op.drop_table("compliance_qa_log", schema="grant_compliance")

    op.drop_index(
        op.f("ix_grant_compliance_compliance_requirements_compliance_area"),
        table_name="compliance_requirements",
        schema="grant_compliance",
    )
    op.drop_index(
        op.f("ix_grant_compliance_compliance_requirements_set_id"),
        table_name="compliance_requirements",
        schema="grant_compliance",
    )
    op.drop_table("compliance_requirements", schema="grant_compliance")

    op.drop_index(
        op.f("ix_grant_compliance_compliance_requirements_sets_generated_at"),
        table_name="compliance_requirements_sets",
        schema="grant_compliance",
    )
    op.drop_index(
        op.f("ix_grant_compliance_compliance_requirements_sets_grant_id"),
        table_name="compliance_requirements_sets",
        schema="grant_compliance",
    )
    op.drop_table("compliance_requirements_sets", schema="grant_compliance")
