from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Organization(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(40), default="growth", nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="fr", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Paris", nullable=False)
    daily_invite_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    daily_message_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    warmup_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    data_retention_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="fr", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class Membership(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    title: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="memberships", lazy="joined")
    user: Mapped[User] = relationship(back_populates="memberships", lazy="joined")


class OrganizationInvite(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "organization_invites"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(lazy="joined")


class RefreshToken(UUIDPrimaryKey, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LinkedInAccount(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "linkedin_accounts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_urn: Mapped[str | None] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(40), default="demo", nullable=False)
    provider_account_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="connected", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    daily_invite_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    daily_message_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    invites_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_date: Mapped[date | None] = mapped_column(Date)
    warmup_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_error: Mapped[str | None] = mapped_column(Text)


class ICP(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "icps"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    value_prop: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    titles: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    industries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    company_sizes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    locations: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    seniorities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    pain_points: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    signal_types: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    min_score: Mapped[int] = mapped_column(Integer, default=65, nullable=False)
    auto_launch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(40), default="heuristic", nullable=False)


class Lead(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("organization_id", "linkedin_url", name="uq_lead_org_linkedin"),
        Index("ix_leads_org_score", "organization_id", "icp_score"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    icp_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("icps.id", ondelete="SET NULL"), index=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    linkedin_url: Mapped[str] = mapped_column(String(600), nullable=False)
    linkedin_urn: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    full_name: Mapped[str] = mapped_column(String(250), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(500))
    about: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(String(250))
    company_size: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(160))
    location: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(80))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    icp_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    signals: Mapped[list[Signal]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", lazy="select"
    )


class Signal(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "signals"
    __table_args__ = (Index("ix_signals_org_detected", "organization_id", "detected_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(800))
    source: Mapped[str] = mapped_column(String(80), default="manual", nullable=False)
    strength: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    lead: Mapped[Lead] = relationship(back_populates="signals", lazy="joined")


class Campaign(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "campaigns"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    icp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("icps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("linkedin_accounts.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    auto_launch: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_score: Mapped[int] = mapped_column(Integer, default=65, nullable=False)
    daily_invite_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    daily_message_limit: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    icp: Mapped[ICP] = relationship(lazy="joined")
    account: Mapped[LinkedInAccount | None] = relationship(lazy="joined")
    steps: Mapped[list[SequenceStep]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SequenceStep.position",
    )


class SequenceStep(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "sequence_steps"
    __table_args__ = (UniqueConstraint("campaign_id", "position", name="uq_step_campaign_position"),)

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(40), default="message", nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    campaign: Mapped[Campaign] = relationship(back_populates="steps")


class CampaignLead(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "campaign_leads"
    __table_args__ = (UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),)

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="enrolled", nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_reason: Mapped[str | None] = mapped_column(String(250))
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    campaign: Mapped[Campaign] = relationship(lazy="joined")
    lead: Mapped[Lead] = relationship(lazy="joined")


class OutboundAction(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "outbound_actions"
    __table_args__ = (Index("ix_actions_status_due", "status", "scheduled_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    campaign_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_leads.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("linkedin_accounts.id", ondelete="SET NULL"), index=True
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequence_steps.id", ondelete="SET NULL")
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    lead: Mapped[Lead] = relationship(lazy="joined")


class Conversation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_org_last", "organization_id", "last_message_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("linkedin_accounts.id", ondelete="SET NULL")
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_message_preview: Mapped[str | None] = mapped_column(String(500))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    lead: Mapped[Lead] = relationship(lazy="joined")
    campaign: Mapped[Campaign | None] = relationship(lazy="joined")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Message.sent_at",
    )


class Message(UUIDPrimaryKey, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_sent", "conversation_id", "sent_at"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(20), default="outbound", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ApiKey(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "api_keys"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(40), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    organization: Mapped[Organization] = relationship(lazy="joined")


class AuditEvent(UUIDPrimaryKey, Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_org_created", "organization_id", "created_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(30), default="user", nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(80))
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
