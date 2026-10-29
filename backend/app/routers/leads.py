from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.models import Campaign, CampaignLead, Conversation, Lead, Membership, Signal
from app.schemas import (
    LeadCreate,
    LeadDetail,
    LeadImportResult,
    LeadListResponse,
    LeadRead,
    LeadScoreRead,
    LeadUpdate,
    MessageOut,
    SignalRead,
)
from app.services.audit import audit
from app.services.campaign import stop_sequence_for_reply
from app.services.scoring import rescore_lead
from app.utils import ensure_lead_status, lead_to_read, normalize_lead_url

router = APIRouter(prefix="/leads", tags=["leads"])


def _signal_read(signal: Signal, include_lead: bool = False) -> SignalRead:
    payload = {
        "id": signal.id,
        "type": signal.type,
        "title": signal.title,
        "description": signal.description,
        "source_url": signal.source_url,
        "source": signal.source,
        "strength": signal.strength,
        "status": signal.status,
        "detected_at": signal.detected_at,
        "lead": None,
    }
    if include_lead:
        from app.schemas import LeadBrief

        payload["lead"] = LeadBrief.model_validate(signal.lead)
    return SignalRead(**payload)


async def _build_lead_reads(session: AsyncSession, leads: list[Lead]) -> list[LeadRead]:
    if not leads:
        return []
    ids = [lead.id for lead in leads]
    signal_rows = (
        await session.execute(
            select(Signal).where(Signal.lead_id.in_(ids)).order_by(Signal.detected_at.desc())
        )
    ).scalars().all()
    latest_signals: dict[UUID, Signal] = {}
    for signal in signal_rows:
        latest_signals.setdefault(signal.lead_id, signal)
    campaign_rows = (
        await session.execute(
            select(CampaignLead.lead_id, Campaign.name)
            .join(Campaign, Campaign.id == CampaignLead.campaign_id)
            .where(CampaignLead.lead_id.in_(ids))
            .order_by(Campaign.created_at.desc())
        )
    ).all()
    campaign_names: dict[UUID, list[str]] = {}
    for lead_id, name in campaign_rows:
        campaign_names.setdefault(lead_id, []).append(name)
    conversation_rows = (
        await session.execute(
            select(Conversation).where(Conversation.lead_id.in_(ids)).order_by(Conversation.last_message_at.desc())
        )
    ).scalars().all()
    conversations: dict[UUID, Conversation] = {}
    unread: dict[UUID, int] = {}
    for conversation in conversation_rows:
        conversations.setdefault(conversation.lead_id, conversation)
        unread[conversation.lead_id] = unread.get(conversation.lead_id, 0) + conversation.unread_count
    return [
        lead_to_read(
            lead,
            latest_signal=_signal_read(latest_signals[lead.id]) if lead.id in latest_signals else None,
            campaign_names=campaign_names.get(lead.id, []),
            unread_count=unread.get(lead.id, 0),
            conversation_id=conversations[lead.id].id if lead.id in conversations else None,
        )
        for lead in leads
    ]


@router.get("", response_model=LeadListResponse)
async def list_leads(
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
    q: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    min_score: int | None = Query(default=None, ge=0, le=100),
    campaign_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    sort: str = Query(default="recent", pattern="^(recent|score|name|signal)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    conditions = [Lead.organization_id == ctx.org_id]
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                Lead.full_name.ilike(pattern),
                Lead.company.ilike(pattern),
                Lead.headline.ilike(pattern),
                Lead.location.ilike(pattern),
            )
        )
    if status_filter:
        statuses = [value.strip() for value in status_filter.split(",") if value.strip()]
        if statuses:
            for value in statuses:
                ensure_lead_status(value)
            conditions.append(Lead.status.in_(statuses))
    if min_score is not None:
        conditions.append(Lead.icp_score >= min_score)
    if campaign_id:
        conditions.append(
            Lead.id.in_(select(CampaignLead.lead_id).where(CampaignLead.campaign_id == campaign_id))
        )
    if owner_user_id:
        conditions.append(Lead.owner_user_id == owner_user_id)

    total = (
        await session.execute(select(func.count(Lead.id)).where(*conditions))
    ).scalar_one()
    ordering = {
        "recent": Lead.created_at.desc(),
        "score": Lead.icp_score.desc(),
        "name": Lead.full_name.asc(),
        "signal": Lead.last_signal_at.desc().nullslast(),
    }[sort]
    leads = (
        await session.execute(
            select(Lead)
            .where(*conditions)
            .order_by(ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return LeadListResponse(
        items=await _build_lead_reads(session, list(leads)),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(
    lead_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == lead_id, Lead.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    reads = await _build_lead_reads(session, [lead])
    base = reads[0].model_dump()
    signals = (
        await session.execute(
            select(Signal).where(Signal.lead_id == lead.id).order_by(Signal.detected_at.desc())
        )
    ).scalars().all()
    conversation_rows = (
        await session.execute(
            select(Conversation).where(Conversation.lead_id == lead.id).order_by(Conversation.last_message_at.desc())
        )
    ).scalars().all()
    base.update(
        {
            "about": lead.about,
            "phone": lead.phone,
            "linkedin_urn": lead.linkedin_urn,
            "extra_data": lead.extra_data or {},
            "signals": [_signal_read(signal) for signal in signals],
            "conversations": [
                {
                    "id": str(conversation.id),
                    "status": conversation.status,
                    "unread_count": conversation.unread_count,
                    "last_message_at": conversation.last_message_at.isoformat(),
                    "last_message_preview": conversation.last_message_preview,
                }
                for conversation in conversation_rows
            ],
        }
    )
    return LeadDetail(**base)


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    url = normalize_lead_url(payload.linkedin_url)
    existing = (
        await session.execute(
            select(Lead.id).where(Lead.organization_id == ctx.org_id, Lead.linkedin_url == url)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="This LinkedIn profile is already in your workspace")
    lead = Lead(
        organization_id=ctx.org_id,
        linkedin_url=url,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        full_name=f"{payload.first_name.strip()} {payload.last_name.strip()}".strip(),
        headline=payload.headline,
        company=payload.company,
        company_size=payload.company_size,
        industry=payload.industry,
        location=payload.location,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        avatar_url=payload.avatar_url,
        about=payload.about,
        tags=payload.tags,
        source=payload.source,
        status="new",
    )
    session.add(lead)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="This lead already exists") from None
    await rescore_lead(session, lead, locale=ctx.organization.locale)
    await audit(session, ctx.org_id, "lead.created", actor_id=ctx.user.id, target_type="lead", target_id=lead.id)
    await session.commit()
    return (await _build_lead_reads(session, [lead]))[0]


@router.post("/import", response_model=LeadImportResult)
async def import_leads(
    payload: list[LeadCreate],
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    if len(payload) > 500:
        raise HTTPException(status_code=400, detail="Import at most 500 leads at a time")
    created: list[Lead] = []
    skipped = 0
    for item in payload:
        url = normalize_lead_url(item.linkedin_url)
        existing = (
            await session.execute(
                select(Lead.id).where(Lead.organization_id == ctx.org_id, Lead.linkedin_url == url)
            )
        ).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        lead = Lead(
            organization_id=ctx.org_id,
            linkedin_url=url,
            first_name=item.first_name.strip(),
            last_name=item.last_name.strip(),
            full_name=f"{item.first_name.strip()} {item.last_name.strip()}".strip(),
            headline=item.headline,
            company=item.company,
            company_size=item.company_size,
            industry=item.industry,
            location=item.location,
            email=str(item.email) if item.email else None,
            phone=item.phone,
            avatar_url=item.avatar_url,
            about=item.about,
            tags=item.tags,
            source=item.source,
        )
        session.add(lead)
        await session.flush()
        await rescore_lead(session, lead, locale=ctx.organization.locale)
        created.append(lead)
    await session.commit()
    return LeadImportResult(
        created=len(created),
        skipped=skipped,
        leads=await _build_lead_reads(session, created),
    )


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == lead_id, Lead.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"]:
        ensure_lead_status(updates["status"])
    if updates.get("owner_user_id") is not None:
        owner_membership = (
            await session.execute(
                select(Membership.id).where(
                    Membership.organization_id == ctx.org_id,
                    Membership.user_id == updates["owner_user_id"],
                    Membership.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if owner_membership is None:
            raise HTTPException(status_code=400, detail="The lead owner must be an active workspace member")
    for field, value in updates.items():
        if field == "email" and value is not None:
            value = str(value)
        setattr(lead, field, value)
    lead.full_name = f"{lead.first_name} {lead.last_name}".strip()
    if updates.get("status") in {"lost", "disqualified"}:
        await stop_sequence_for_reply(session, lead.id, reason="manually_stopped")
    await audit(session, ctx.org_id, "lead.updated", actor_id=ctx.user.id, target_type="lead", target_id=lead.id)
    await session.commit()
    return (await _build_lead_reads(session, [lead]))[0]


@router.post("/{lead_id}/score", response_model=LeadScoreRead)
async def score_lead_endpoint(
    lead_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == lead_id, Lead.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    score, reasons, icp_id = await rescore_lead(session, lead, locale=ctx.organization.locale)
    await session.commit()
    return LeadScoreRead(score=score, reasons=reasons, icp_id=icp_id)


@router.delete("/{lead_id}", response_model=MessageOut)
async def delete_lead(
    lead_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    ctx.require_role("owner", "admin")
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == lead_id, Lead.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    await session.delete(lead)
    await audit(session, ctx.org_id, "lead.deleted", actor_id=ctx.user.id, target_type="lead", target_id=lead_id)
    await session.commit()
    return MessageOut(message="Lead deleted")
