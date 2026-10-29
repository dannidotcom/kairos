from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain import LEAD_STATUSES
from app.models import Lead
from app.schemas import LeadBrief, LeadRead, SignalRead


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:140] or "workspace"


def unique_slug(base: str) -> str:
    return f"{slugify(base)}-{secrets_token(4)}"


def secrets_token(length: int = 4) -> str:
    import secrets

    return secrets.token_hex(length)


def normalize_lead_url(url: str) -> str:
    cleaned = url.strip().split("?")[0].rstrip("/")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


def quota_date() -> datetime.date:
    return datetime.now(timezone.utc).date()


def ensure_lead_status(value: str) -> str:
    if value not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid lead status")
    return value


def lead_brief(lead: Lead) -> LeadBrief:
    return LeadBrief.model_validate(lead)


def lead_to_read(
    lead: Lead,
    *,
    latest_signal: SignalRead | None = None,
    campaign_names: list[str] | None = None,
    unread_count: int = 0,
    conversation_id: UUID | None = None,
) -> LeadRead:
    payload = {
        "id": lead.id,
        "full_name": lead.full_name,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "headline": lead.headline,
        "company": lead.company,
        "company_size": lead.company_size,
        "industry": lead.industry,
        "location": lead.location,
        "avatar_url": lead.avatar_url,
        "linkedin_url": lead.linkedin_url,
        "status": lead.status,
        "icp_score": lead.icp_score,
        "email": lead.email,
        "owner_user_id": lead.owner_user_id,
        "source": lead.source,
        "tags": lead.tags or [],
        "score_reasons": lead.score_reasons or [],
        "last_signal_at": lead.last_signal_at,
        "last_contacted_at": lead.last_contacted_at,
        "last_replied_at": lead.last_replied_at,
        "created_at": lead.created_at,
        "latest_signal": latest_signal,
        "campaign_names": campaign_names or [],
        "unread_count": unread_count,
        "conversation_id": conversation_id,
    }
    return LeadRead(**payload)


def signal_to_read(signal: Any, lead: Any | None = None) -> SignalRead:
    if lead is None:
        # Relationships eager-loaded with joined/selectin are present in __dict__;
        # avoid triggering a lazy load in async code when they are not.
        lead = getattr(signal, "__dict__", {}).get("lead")
    return SignalRead(
        id=signal.id,
        type=signal.type,
        title=signal.title,
        description=signal.description,
        source_url=signal.source_url,
        source=signal.source,
        strength=signal.strength,
        status=signal.status,
        detected_at=signal.detected_at,
        lead=LeadBrief.model_validate(lead) if lead else None,
    )


def parse_bool(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***@{domain}"


async def get_org_membership(session: AsyncSession, user_id: UUID, organization_id: UUID):
    from app.models import Membership

    result = await session.execute(
        select(Membership)
        .where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


def require_role(role: str, allowed: set[str]) -> None:
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )


def app_url(path: str = "") -> str:
    return f"{settings.frontend_url.rstrip('/')}/{path.lstrip('/')}"
