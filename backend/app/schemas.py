from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    message: str


# ── Auth & organizations ─────────────────────────────────────────────────────


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    locale: str
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class OrganizationBrief(ORMModel):
    id: UUID
    name: str
    slug: str
    plan: str
    locale: str
    timezone: str
    is_demo: bool
    daily_invite_limit: int
    daily_message_limit: int
    warmup_enabled: bool


class OrganizationRead(OrganizationBrief):
    logo_url: str | None = None
    data_retention_days: int = 365
    created_at: datetime


class MembershipRead(ORMModel):
    id: UUID
    role: str
    title: str | None = None
    is_active: bool
    organization: OrganizationBrief


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
    organizations: list[MembershipRead]


class MeResponse(BaseModel):
    user: UserRead
    organizations: list[MembershipRead]
    active_organization_id: UUID


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    locale: Literal["fr", "en"] = "fr"
    timezone: str = "Europe/Paris"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    user_agent: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str


class UpdateMeRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    locale: Literal["fr", "en"] | None = None
    avatar_url: str | None = None


class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    locale: Literal["fr", "en"] = "fr"
    timezone: str = "Europe/Paris"


class OrgUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    locale: Literal["fr", "en"] | None = None
    timezone: str | None = None
    daily_invite_limit: int | None = Field(default=None, ge=1, le=100)
    daily_message_limit: int | None = Field(default=None, ge=1, le=200)
    warmup_enabled: bool | None = None
    logo_url: str | None = None


class MemberRead(BaseModel):
    membership_id: UUID
    user_id: UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None
    role: str
    title: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class MemberUpdateRequest(BaseModel):
    role: Literal["owner", "admin", "member"] | None = None
    title: str | None = None
    is_active: bool | None = None


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "member"] = "member"


class InviteRead(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    invite_url: str | None = None


class AcceptInviteRequest(BaseModel):
    token: str
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=10, max_length=200)


# ── LinkedIn ─────────────────────────────────────────────────────────────────


class AccountRead(ORMModel):
    id: UUID
    display_name: str
    account_urn: str | None
    provider: str
    status: str
    avatar_url: str | None
    daily_invite_limit: int
    daily_message_limit: int
    invites_sent_today: int
    messages_sent_today: int
    warmup_started_at: datetime | None
    last_sync_at: datetime | None
    connected_at: datetime | None
    last_error: str | None


class AccountConnectRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    mode: Literal["demo", "connector"] = "demo"
    provider_account_id: str | None = None
    daily_invite_limit: int = Field(default=20, ge=1, le=100)
    daily_message_limit: int = Field(default=40, ge=1, le=200)


class AccountUpdateRequest(BaseModel):
    status: Literal["connected", "paused"] | None = None
    daily_invite_limit: int | None = Field(default=None, ge=1, le=100)
    daily_message_limit: int | None = Field(default=None, ge=1, le=200)


class UsageRead(BaseModel):
    invites_used: int
    invites_limit: int
    messages_used: int
    messages_limit: int
    warmup_active: bool


# ── ICP & scoring ────────────────────────────────────────────────────────────


class ICPBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10)
    value_prop: str | None = None
    keywords: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    seniorities: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    signal_types: list[str] = Field(default_factory=list)
    min_score: int = Field(default=65, ge=0, le=100)
    auto_launch: bool = False
    is_active: bool = True


class ICPCreate(ICPBase):
    pass


class ICPUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    value_prop: str | None = None
    keywords: list[str] | None = None
    titles: list[str] | None = None
    industries: list[str] | None = None
    company_sizes: list[str] | None = None
    locations: list[str] | None = None
    seniorities: list[str] | None = None
    pain_points: list[str] | None = None
    signal_types: list[str] | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    auto_launch: bool | None = None
    is_active: bool | None = None


class ICPRead(ICPBase, ORMModel):
    id: UUID
    generated_by: str
    created_at: datetime
    updated_at: datetime


class ICPGenerateRequest(BaseModel):
    description: str = Field(min_length=20, max_length=4000)
    value_prop: str | None = Field(default=None, max_length=1200)
    locale: Literal["fr", "en"] = "fr"


class ICPSuggestion(BaseModel):
    name: str
    description: str
    value_prop: str
    keywords: list[str]
    titles: list[str]
    industries: list[str]
    company_sizes: list[str]
    locations: list[str]
    seniorities: list[str]
    pain_points: list[str]
    signal_types: list[str]
    min_score: int = 65
    auto_launch: bool = False
    generated_by: str = "heuristic"


# ── Leads & signals ──────────────────────────────────────────────────────────


class LeadBrief(ORMModel):
    id: UUID
    full_name: str
    first_name: str
    last_name: str
    headline: str | None
    company: str | None
    company_size: str | None
    industry: str | None
    location: str | None
    avatar_url: str | None
    linkedin_url: str
    status: str
    icp_score: int


class SignalRead(ORMModel):
    id: UUID
    type: str
    title: str
    description: str | None
    source_url: str | None
    source: str
    strength: float
    status: str
    detected_at: datetime
    lead: LeadBrief | None = None


class LatestSignalsMixin(BaseModel):
    latest_signal: SignalRead | None = None


class LeadRead(LeadBrief, LatestSignalsMixin):
    email: EmailStr | None = None
    owner_user_id: UUID | None = None
    source: str
    tags: list[str]
    score_reasons: list[dict[str, Any]]
    last_signal_at: datetime | None
    last_contacted_at: datetime | None
    last_replied_at: datetime | None
    created_at: datetime
    campaign_names: list[str] = Field(default_factory=list)
    unread_count: int = 0
    conversation_id: UUID | None = None


class LeadDetail(LeadRead):
    about: str | None = None
    phone: str | None = None
    linkedin_urn: str | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)
    signals: list[SignalRead] = Field(default_factory=list)
    conversations: list[dict[str, Any]] = Field(default_factory=list)


class LeadCreate(BaseModel):
    linkedin_url: str = Field(min_length=8, max_length=600)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(default="", max_length=80)
    headline: str | None = None
    company: str | None = None
    company_size: str | None = None
    industry: str | None = None
    location: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    about: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin(cls, value: str) -> str:
        url = value.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        if "linkedin.com/" not in url:
            raise ValueError("A LinkedIn profile URL is required")
        return url


class LeadUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = None
    headline: str | None = None
    company: str | None = None
    company_size: str | None = None
    industry: str | None = None
    location: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: Literal["new", "qualified", "contacted", "replied", "meeting", "won", "lost", "disqualified"] | None = None
    tags: list[str] | None = None
    owner_user_id: UUID | None = None


class LeadListResponse(BaseModel):
    items: list[LeadRead]
    total: int
    page: int
    page_size: int


class LeadImportResult(BaseModel):
    created: int
    skipped: int
    leads: list[LeadRead]


class SignalCreate(BaseModel):
    lead_id: UUID
    type: str = "manual"
    title: str = Field(min_length=2, max_length=300)
    description: str | None = None
    source_url: str | None = None
    source: str = "manual"
    strength: float = Field(default=0.7, ge=0, le=1)
    detected_at: datetime | None = None


class SignalIngestRequest(BaseModel):
    lead_linkedin_url: str
    type: str = "manual"
    title: str = Field(min_length=2, max_length=300)
    description: str | None = None
    source_url: str | None = None
    source: str = "api"
    strength: float = Field(default=0.75, ge=0, le=1)
    detected_at: datetime | None = None


class SignalListResponse(BaseModel):
    items: list[SignalRead]
    total: int
    page: int
    page_size: int


class SignalCreated(BaseModel):
    signal: SignalRead
    campaign_enrolled: int = 0


class LeadScoreRead(BaseModel):
    score: int
    reasons: list[dict[str, Any]]
    icp_id: UUID | None = None


class IcebreakerRequest(BaseModel):
    lead_id: UUID
    campaign_id: UUID | None = None


class IcebreakerResponse(BaseModel):
    text: str
    generated_by: str


# ── Campaigns ────────────────────────────────────────────────────────────────


class SequenceStepInput(BaseModel):
    action_type: Literal["connection_request", "message", "follow_up", "inmail"] = "message"
    delay_days: int = Field(default=0, ge=0, le=60)
    body_template: str = Field(default="", max_length=4000)
    is_active: bool = True


class SequenceStepRead(SequenceStepInput, ORMModel):
    id: UUID
    position: int


class CampaignBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    icp_id: UUID
    account_id: UUID | None = None
    auto_launch: bool = True
    min_score: int = Field(default=65, ge=0, le=100)
    daily_invite_limit: int = Field(default=20, ge=1, le=100)
    daily_message_limit: int = Field(default=40, ge=1, le=200)


class CampaignCreate(CampaignBase):
    steps: list[SequenceStepInput] = Field(min_length=1, max_length=10)


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icp_id: UUID | None = None
    account_id: UUID | None = None
    auto_launch: bool | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    daily_invite_limit: int | None = Field(default=None, ge=1, le=100)
    daily_message_limit: int | None = Field(default=None, ge=1, le=200)
    steps: list[SequenceStepInput] | None = None


class CampaignStats(BaseModel):
    total_leads: int = 0
    contacted: int = 0
    replied: int = 0
    meetings: int = 0
    reply_rate: float = 0


class CampaignRead(CampaignBase, ORMModel):
    id: UUID
    status: str
    launched_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    steps: list[SequenceStepRead]
    icp_name: str | None = None
    account_name: str | None = None
    stats: CampaignStats = Field(default_factory=CampaignStats)


class CampaignLeadRead(BaseModel):
    id: UUID
    status: str
    current_step: int
    next_action_at: datetime | None
    last_action_at: datetime | None
    replied_at: datetime | None
    lead: LeadBrief


class CampaignDetail(CampaignRead):
    leads: list[CampaignLeadRead] = Field(default_factory=list)


class CampaignAddLeadsRequest(BaseModel):
    lead_ids: list[UUID] = Field(min_length=1, max_length=500)


class CampaignListResponse(BaseModel):
    items: list[CampaignRead]
    total: int


class CampaignRunResponse(BaseModel):
    campaign: CampaignRead
    enrolled: int
    skipped: int


# ── Inbox ────────────────────────────────────────────────────────────────────


class MessageRead(ORMModel):
    id: UUID
    direction: str
    body: str
    sender_name: str | None
    sent_at: datetime
    is_read: bool
    ai_generated: bool


class ConversationRead(ORMModel):
    id: UUID
    status: str
    unread_count: int
    last_message_at: datetime
    last_message_preview: str | None
    is_archived: bool
    lead: LeadBrief
    campaign_name: str | None = None
    last_message: MessageRead | None = None


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    items: list[ConversationRead]
    total: int


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    ai_generated: bool = False


class SuggestReplyResponse(BaseModel):
    suggestion: str
    generated_by: str


class ConversationUpdateRequest(BaseModel):
    status: Literal["open", "waiting", "meeting", "closed"] | None = None
    is_archived: bool | None = None


# ── Dashboard ────────────────────────────────────────────────────────────────


class FunnelBucket(BaseModel):
    status: str
    count: int


class ActivityPoint(BaseModel):
    date: str
    signals: int
    messages: int
    replies: int


class CampaignPerformance(BaseModel):
    id: UUID
    name: str
    status: str
    leads: int
    contacted: int
    replied: int
    reply_rate: float


class DashboardRead(BaseModel):
    total_leads: int
    hot_leads: int
    signals_7d: int
    signals_today: int
    active_campaigns: int
    replies_7d: int
    meetings: int
    reply_rate: float
    avg_icp_score: float
    funnel: list[FunnelBucket]
    activity: list[ActivityPoint]
    recent_signals: list[SignalRead]
    recent_conversations: list[ConversationRead]
    campaigns: list[CampaignPerformance]
    usage: UsageRead | None = None


# ── API keys & audit ─────────────────────────────────────────────────────────


class ApiKeyRead(ORMModel):
    id: UUID
    name: str
    key_prefix: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class ApiKeyCreated(ApiKeyRead):
    key: str


class AuditEventRead(ORMModel):
    id: UUID
    actor_type: str
    action: str
    target_type: str | None
    target_id: str | None
    extra_data: dict[str, Any]
    created_at: datetime


# ── Demo ─────────────────────────────────────────────────────────────────────


class DemoSignalResponse(BaseModel):
    created: int
    signal: SignalRead
    campaign_enrolled: int
