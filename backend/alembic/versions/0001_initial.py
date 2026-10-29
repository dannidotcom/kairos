"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("plan", sa.String(40), nullable=False),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("daily_invite_limit", sa.Integer(), nullable=False),
        sa.Column("daily_message_limit", sa.Integer(), nullable=False),
        sa.Column("warmup_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("data_retention_days", sa.Integer(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", TS),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "memberships",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("title", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"], unique=False)
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], unique=False)

    op.create_table(
        "organization_invites",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("invited_by_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("accepted_at", TS),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_organization_invites_token_hash"),
    )
    op.create_index("ix_organization_invites_organization_id", "organization_invites", ["organization_id"])
    op.create_index("ix_organization_invites_email", "organization_invites", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("revoked_at", TS),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "linkedin_accounts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("account_urn", sa.String(255)),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_account_id", sa.String(255)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("daily_invite_limit", sa.Integer(), nullable=False),
        sa.Column("daily_message_limit", sa.Integer(), nullable=False),
        sa.Column("invites_sent_today", sa.Integer(), nullable=False),
        sa.Column("messages_sent_today", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date()),
        sa.Column("warmup_started_at", TS),
        sa.Column("last_sync_at", TS),
        sa.Column("connected_at", TS, server_default=sa.text("now()")),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_linkedin_accounts_organization_id", "linkedin_accounts", ["organization_id"])
    op.create_index("ix_linkedin_accounts_user_id", "linkedin_accounts", ["user_id"])

    op.create_table(
        "icps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value_prop", sa.Text()),
        sa.Column("keywords", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("titles", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("industries", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("company_sizes", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("locations", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("seniorities", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("pain_points", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("signal_types", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("auto_launch", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("generated_by", sa.String(40), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_icps_organization_id", "icps", ["organization_id"])

    op.create_table(
        "leads",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icp_id", UUID, sa.ForeignKey("icps.id", ondelete="SET NULL")),
        sa.Column("owner_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("linkedin_url", sa.String(600), nullable=False),
        sa.Column("linkedin_urn", sa.String(255)),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("full_name", sa.String(250), nullable=False),
        sa.Column("headline", sa.String(500)),
        sa.Column("about", sa.Text()),
        sa.Column("company", sa.String(250)),
        sa.Column("company_size", sa.String(80)),
        sa.Column("industry", sa.String(160)),
        sa.Column("location", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(80)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("icp_score", sa.Integer(), nullable=False),
        sa.Column("score_reasons", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("tags", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("extra_data", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_signal_at", TS),
        sa.Column("last_contacted_at", TS),
        sa.Column("last_replied_at", TS),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "linkedin_url", name="uq_lead_org_linkedin"),
    )
    op.create_index("ix_leads_organization_id", "leads", ["organization_id"])
    op.create_index("ix_leads_icp_id", "leads", ["icp_id"])
    op.create_index("ix_leads_owner_user_id", "leads", ["owner_user_id"])
    op.create_index("ix_leads_org_score", "leads", ["organization_id", "icp_score"])

    op.create_table(
        "signals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(400), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source_url", sa.String(800)),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("detected_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("extra_data", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_signals_organization_id", "signals", ["organization_id"])
    op.create_index("ix_signals_lead_id", "signals", ["lead_id"])
    op.create_index("ix_signals_org_detected", "signals", ["organization_id", "detected_at"])

    op.create_table(
        "campaigns",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icp_id", UUID, sa.ForeignKey("icps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID, sa.ForeignKey("linkedin_accounts.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("auto_launch", sa.Boolean(), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("daily_invite_limit", sa.Integer(), nullable=False),
        sa.Column("daily_message_limit", sa.Integer(), nullable=False),
        sa.Column("launched_at", TS),
        sa.Column("paused_at", TS),
        sa.Column("completed_at", TS),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_campaigns_organization_id", "campaigns", ["organization_id"])
    op.create_index("ix_campaigns_icp_id", "campaigns", ["icp_id"])
    op.create_index("ix_campaigns_account_id", "campaigns", ["account_id"])

    op.create_table(
        "sequence_steps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("campaign_id", UUID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("campaign_id", "position", name="uq_step_campaign_position"),
    )
    op.create_index("ix_sequence_steps_campaign_id", "sequence_steps", ["campaign_id"])

    op.create_table(
        "campaign_leads",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("campaign_id", UUID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("next_action_at", TS),
        sa.Column("last_action_at", TS),
        sa.Column("replied_at", TS),
        sa.Column("stopped_reason", sa.String(250)),
        sa.Column("extra_data", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),
    )
    op.create_index("ix_campaign_leads_campaign_id", "campaign_leads", ["campaign_id"])
    op.create_index("ix_campaign_leads_lead_id", "campaign_leads", ["lead_id"])

    op.create_table(
        "outbound_actions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", UUID, sa.ForeignKey("campaigns.id", ondelete="CASCADE")),
        sa.Column("campaign_lead_id", UUID, sa.ForeignKey("campaign_leads.id", ondelete="CASCADE")),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID, sa.ForeignKey("linkedin_accounts.id", ondelete="SET NULL")),
        sa.Column("step_id", UUID, sa.ForeignKey("sequence_steps.id", ondelete="SET NULL")),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("scheduled_at", TS, nullable=False),
        sa.Column("executed_at", TS),
        sa.Column("content", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("external_id", sa.String(255)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outbound_actions_organization_id", "outbound_actions", ["organization_id"])
    op.create_index("ix_outbound_actions_campaign_id", "outbound_actions", ["campaign_id"])
    op.create_index("ix_outbound_actions_campaign_lead_id", "outbound_actions", ["campaign_lead_id"])
    op.create_index("ix_outbound_actions_lead_id", "outbound_actions", ["lead_id"])
    op.create_index("ix_outbound_actions_account_id", "outbound_actions", ["account_id"])
    op.create_index("ix_actions_status_due", "outbound_actions", ["status", "scheduled_at"])

    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID, sa.ForeignKey("linkedin_accounts.id", ondelete="SET NULL")),
        sa.Column("campaign_id", UUID, sa.ForeignKey("campaigns.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("unread_count", sa.Integer(), nullable=False),
        sa.Column("last_message_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("last_message_preview", sa.String(500)),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("assigned_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
    op.create_index("ix_conversations_lead_id", "conversations", ["lead_id"])
    op.create_index("ix_conversations_campaign_id", "conversations", ["campaign_id"])
    op.create_index("ix_conversations_org_last", "conversations", ["organization_id", "last_message_at"])

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sender_name", sa.String(200)),
        sa.Column("sent_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_conversation_sent", "messages", ["conversation_id", "sent_at"])

    op.create_table(
        "api_keys",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("key_prefix", sa.String(40), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("last_used_at", TS),
        sa.Column("revoked_at", TS),
        sa.Column("created_by_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_type", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.String(80)),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.String(80)),
        sa.Column("extra_data", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_org_created", "audit_events", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("api_keys")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("outbound_actions")
    op.drop_table("campaign_leads")
    op.drop_table("sequence_steps")
    op.drop_table("campaigns")
    op.drop_table("signals")
    op.drop_table("leads")
    op.drop_table("icps")
    op.drop_table("linkedin_accounts")
    op.drop_table("refresh_tokens")
    op.drop_table("organization_invites")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")
