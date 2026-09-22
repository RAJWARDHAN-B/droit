"""add legal drafting tables

Revision ID: a1d4e6f7b8c9
Revises: 9b2f7c1d4e30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1d4e6f7b8c9"
down_revision: Union[str, Sequence[str], None] = "9b2f7c1d4e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "draft_templates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("clause_outline", sa.JSON(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug"),
    )
    op.create_index("ix_draft_templates_organization_id", "draft_templates", ["organization_id"])
    op.create_table(
        "drafts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "FINAL", name="draft_status", native_enum=False), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("risk_breakdown", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["draft_templates.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "user_id", "template_id"):
        op.create_index(f"ix_drafts_{column}", "drafts", [column])
    op.create_table(
        "draft_clauses",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("risk_notes", sa.JSON(), nullable=False),
        sa.Column("source", sa.Enum("GENERATED", "EDITED", "TEMPLATE", name="draft_clause_source", native_enum=False), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "ordinal"),
    )
    op.create_index("ix_draft_clauses_draft_id", "draft_clauses", ["draft_id"])
    op.create_index("ix_draft_clauses_organization_id", "draft_clauses", ["organization_id"])
    op.create_table(
        "draft_versions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "version"),
    )
    op.create_index("ix_draft_versions_draft_id", "draft_versions", ["draft_id"])
    op.create_index("ix_draft_versions_organization_id", "draft_versions", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_draft_versions_organization_id", table_name="draft_versions")
    op.drop_index("ix_draft_versions_draft_id", table_name="draft_versions")
    op.drop_table("draft_versions")
    op.drop_index("ix_draft_clauses_organization_id", table_name="draft_clauses")
    op.drop_index("ix_draft_clauses_draft_id", table_name="draft_clauses")
    op.drop_table("draft_clauses")
    for column in ("template_id", "user_id", "organization_id"):
        op.drop_index(f"ix_drafts_{column}", table_name="drafts")
    op.drop_table("drafts")
    op.drop_index("ix_draft_templates_organization_id", table_name="draft_templates")
    op.drop_table("draft_templates")