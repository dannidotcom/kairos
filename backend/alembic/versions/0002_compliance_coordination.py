"""Add seats, companies, scoring, lists, history, opt-outs, webhooks and quota tables.

Revision ID: 0002_compliance_coordination
Revises: 0001_initial
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_compliance_coordination"
down_revision = "0001_initial"
branch_labels = None
depends_on = None
UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table("seats", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("linkedin_account_id", UUID, sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("agent_name", sa.String(160)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", TS, nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("organization_id", "user_id", name="uq_seat_org_user"))
    op.create_table("companies", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(250), nullable=False), sa.Column("domain", sa.String(255)), sa.Column("size", sa.String(80)), sa.Column("industry", sa.String(160)), sa.Column("country", sa.String(100)), sa.Column("extra_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", TS, nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("organization_id", "name", name="uq_company_org_name"))
    op.create_table("prospect_scores", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("prospect_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False), sa.Column("icp_id", UUID, sa.ForeignKey("icps.id", ondelete="CASCADE"), nullable=False), sa.Column("score", sa.Integer(), nullable=False), sa.Column("justification", sa.String(500), nullable=False), sa.Column("model_version", sa.String(80), nullable=False, server_default="kairos-1"), sa.Column("signals_used", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_prospect_scores_lookup", "prospect_scores", ["organization_id", "prospect_id", "icp_id", "created_at"])
    op.create_table("lists", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("filters", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("is_smart", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", TS, nullable=False, server_default=sa.text("now()")))
    op.create_table("list_members", sa.Column("id", UUID, primary_key=True), sa.Column("list_id", UUID, sa.ForeignKey("lists.id", ondelete="CASCADE"), nullable=False), sa.Column("prospect_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("list_id", "prospect_id", name="uq_list_member"))
    op.create_table("org_contact_history", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("prospect_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False), sa.Column("seat_id", UUID, sa.ForeignKey("seats.id", ondelete="SET NULL")), sa.Column("campaign_id", UUID, sa.ForeignKey("campaigns.id", ondelete="SET NULL")), sa.Column("contacted_at", TS, nullable=False, server_default=sa.text("now()")), sa.Column("extra_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.create_index("ix_org_contact_history_lock", "org_contact_history", ["organization_id", "prospect_id", "contacted_at"])
    op.create_table("opt_outs", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("linkedin_url", sa.String(600), nullable=False), sa.Column("email", sa.String(320)), sa.Column("reason", sa.String(250)), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("organization_id", "linkedin_url", name="uq_optout_org_url"))
    op.create_table("webhook_events", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE")), sa.Column("account_id", UUID, sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE")), sa.Column("event_id", sa.String(255), nullable=False, unique=True), sa.Column("provider", sa.String(40), nullable=False, server_default="linkedin"), sa.Column("event_type", sa.String(80), nullable=False), sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("processed_at", TS), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")))
    op.create_table("send_quota_usage", sa.Column("id", UUID, primary_key=True), sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("account_id", UUID, sa.ForeignKey("linkedin_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("period_start", TS, nullable=False), sa.Column("action_type", sa.String(40), nullable=False), sa.Column("count", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", TS, nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", TS, nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("account_id", "period_start", "action_type", name="uq_quota_account_period_action"))


def downgrade() -> None:
    for table in ("send_quota_usage", "webhook_events", "opt_outs", "org_contact_history", "list_members", "lists", "prospect_scores", "companies", "seats"):
        op.drop_table(table)
