from __future__ import annotations

import hmac
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.models import Lead, LinkedInAccount, LinkedInWebhookEvent
from app.schemas import (
    AccountConnectRequest,
    AccountRead,
    AccountUpdateRequest,
    MessageOut,
    UsageRead,
)
from app.services.audit import audit
from app.services.campaign import effective_quotas, reset_daily_usage
from app.services.linkedin import provider_for_account
from app.utils import normalize_lead_url

router = APIRouter(prefix="/linkedin", tags=["linkedin"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/accounts", response_model=list[AccountRead])
async def list_accounts(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    accounts = (
        await session.execute(
            select(LinkedInAccount)
            .where(LinkedInAccount.organization_id == ctx.org_id)
            .order_by(LinkedInAccount.created_at.asc())
        )
    ).scalars().all()
    return [AccountRead.model_validate(account) for account in accounts]


@router.post("/accounts", response_model=AccountRead, status_code=201)
async def connect_account(
    payload: AccountConnectRequest,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    if payload.mode == "demo" and not settings.demo_mode:
        raise HTTPException(status_code=400, detail="Demo LinkedIn accounts are disabled in this environment")
    if payload.mode == "connector":
        if not settings.linkedin_connector_url:
            raise HTTPException(
                status_code=400,
                detail="The secure connector is not configured. Set LINKEDIN_CONNECTOR_URL on the API.",
            )
        if not payload.provider_account_id:
            raise HTTPException(status_code=400, detail="The connector account identifier is required")
    account = LinkedInAccount(
        organization_id=ctx.org_id,
        user_id=ctx.user.id,
        display_name=payload.display_name.strip(),
        provider=payload.mode,
        provider_account_id=payload.provider_account_id,
        status="warming" if ctx.organization.warmup_enabled else "connected",
        warmup_started_at=datetime.now(timezone.utc) if ctx.organization.warmup_enabled else None,
        daily_invite_limit=payload.daily_invite_limit,
        daily_message_limit=payload.daily_message_limit,
        usage_date=datetime.now(timezone.utc).date(),
    )
    session.add(account)
    await session.flush()
    await audit(
        session,
        ctx.org_id,
        "linkedin.connected",
        actor_id=ctx.user.id,
        target_type="linkedin_account",
        target_id=account.id,
        data={"provider": payload.mode},
    )
    await session.commit()
    return AccountRead.model_validate(account)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: UUID,
    payload: AccountUpdateRequest,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    account = (
        await session.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == account_id, LinkedInAccount.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="LinkedIn account not found")
    if payload.status is not None:
        account.status = payload.status
    if payload.daily_invite_limit is not None:
        account.daily_invite_limit = payload.daily_invite_limit
    if payload.daily_message_limit is not None:
        account.daily_message_limit = payload.daily_message_limit
    await session.commit()
    return AccountRead.model_validate(account)


@router.post("/accounts/{account_id}/sync", response_model=AccountRead)
async def sync_account(
    account_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    account = (
        await session.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == account_id, LinkedInAccount.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="LinkedIn account not found")
    account.last_sync_at = datetime.now(timezone.utc)
    account.last_error = None
    await session.commit()
    return AccountRead.model_validate(account)


@router.delete("/accounts/{account_id}", response_model=MessageOut)
async def disconnect_account(
    account_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    account = (
        await session.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == account_id, LinkedInAccount.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="LinkedIn account not found")
    account.status = "disconnected"
    await audit(
        session, ctx.org_id, "linkedin.disconnected", actor_id=ctx.user.id, target_type="linkedin_account", target_id=account.id
    )
    await session.commit()
    return MessageOut(message="LinkedIn account disconnected")


@router.get("/usage", response_model=UsageRead)
async def usage(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    account = (
        await session.execute(
            select(LinkedInAccount)
            .where(
                LinkedInAccount.organization_id == ctx.org_id,
                LinkedInAccount.status.in_("connected", "warming"),
            )
            .order_by(LinkedInAccount.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if account is None:
        return UsageRead(invites_used=0, invites_limit=0, messages_used=0, messages_limit=0, warmup_active=False)
    reset_daily_usage(account, ctx.organization)
    invite_limit, message_limit = effective_quotas(ctx.organization, account)
    return UsageRead(
        invites_used=account.invites_sent_today,
        invites_limit=invite_limit,
        messages_used=account.messages_sent_today,
        messages_limit=message_limit,
        warmup_active=account.status == "warming",
    )


@webhook_router.post("/linkedin")
async def linkedin_webhook(
    payload: dict,
    x_kairos_webhook_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not x_kairos_webhook_secret or not hmac.compare_digest(
        x_kairos_webhook_secret, settings.linkedin_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = payload.get("event") or payload.get("type")
    if not event:
        raise HTTPException(status_code=422, detail="event is required")
    try:
        account_id = UUID(str(payload["account_id"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=422, detail="account_id is required") from None
    account = await session.get(LinkedInAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="LinkedIn account not found")

    event_id = str(payload.get("event_id") or payload.get("id") or payload.get("webhook_id") or f"{account_id}:{event}:{datetime.now(timezone.utc).isoformat()}")
    existing = (
        await session.execute(
            select(LinkedInWebhookEvent).where(
                LinkedInWebhookEvent.organization_id == account.organization_id,
                LinkedInWebhookEvent.event_id == event_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"ok": True, "duplicate": True, "event_id": event_id}

    webhook_record = LinkedInWebhookEvent(
        organization_id=account.organization_id,
        account_id=account.id,
        event_id=event_id,
        event_type=str(event),
        payload=payload,
    )
    session.add(webhook_record)
    await session.flush()

    provider = provider_for_account(account)
    profile_url = normalize_lead_url(str(payload.get("profile_url", "")))
    lead = (
        await session.execute(
            select(Lead).where(
                Lead.organization_id == account.organization_id,
                Lead.linkedin_url == profile_url,
            )
        )
    ).scalar_one_or_none()
    if lead is None and profile_url:
        raise HTTPException(status_code=404, detail="Lead not found for this profile")

    from app.services.campaign import mark_connection_accepted, record_inbound_reply

    if event == "connection_accepted":
        accepted = await mark_connection_accepted(session, account=account, lead=lead)
        await session.commit()
        return {"ok": True, "scheduled_next_step": accepted}
    if event == "message_received":
        message = payload.get("message") or {}
        body = str(message.get("text", "")).strip()
        if not body:
            raise HTTPException(status_code=422, detail="message.text is required")
        conversation = await record_inbound_reply(
            session,
            account=account,
            lead=lead,
            body=body,
            sender_name=message.get("sender_name") or (lead.full_name if lead else account.display_name),
            external_id=message.get("id"),
        )
        await session.commit()
        return {"ok": True, "conversation_id": str(conversation.id)}
    if event in {"account_connected", "account_disconnected", "credentials_expired", "invitation_accepted", "new_message_received"}:
        await session.commit()
        return {"ok": True, "processed": True, "event": event, "provider": provider.name}
    raise HTTPException(status_code=422, detail="Unsupported event")
