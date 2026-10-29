from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import ApiKeyContext, AuthContext, get_api_key_context, get_auth_context
from app.models import Lead, Signal
from app.schemas import (
    MessageOut,
    SignalCreate,
    SignalCreated,
    SignalIngestRequest,
    SignalListResponse,
    SignalRead,
)
from app.services.audit import audit
from app.services.signals import create_signal_for_lead
from app.utils import normalize_lead_url, signal_to_read

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalListResponse)
async def list_signals(
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
    type_filter: str | None = Query(default=None, alias="type"),
    status_filter: str | None = Query(default=None, alias="status"),
    lead_id: UUID | None = None,
    min_strength: float | None = Query(default=None, ge=0, le=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    conditions = [Signal.organization_id == ctx.org_id]
    if type_filter:
        conditions.append(Signal.type == type_filter)
    if status_filter:
        conditions.append(Signal.status == status_filter)
    if lead_id:
        conditions.append(Signal.lead_id == lead_id)
    if min_strength is not None:
        conditions.append(Signal.strength >= min_strength)
    total = (await session.execute(select(func.count(Signal.id)).where(*conditions))).scalar_one()
    signals = (
        await session.execute(
            select(Signal)
            .where(*conditions)
            .order_by(Signal.detected_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return SignalListResponse(
        items=[signal_to_read(signal) for signal in signals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SignalCreated, status_code=status.HTTP_201_CREATED)
async def create_signal(
    payload: SignalCreate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == payload.lead_id, Lead.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    signal, enrolled = await create_signal_for_lead(
        session,
        ctx.organization,
        lead,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        source_url=payload.source_url,
        source=payload.source,
        strength=payload.strength,
        detected_at=payload.detected_at,
    )
    await audit(
        session, ctx.org_id, "signal.created", actor_id=ctx.user.id, target_type="signal", target_id=signal.id
    )
    await session.commit()
    return SignalCreated(signal=signal_to_read(signal), campaign_enrolled=enrolled)


@router.post("/ingest", response_model=SignalCreated, status_code=201)
async def ingest_signal(
    payload: SignalIngestRequest,
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
):
    org = ctx.organization
    url = normalize_lead_url(payload.lead_linkedin_url)
    lead = (
        await session.execute(
            select(Lead).where(Lead.organization_id == org.id, Lead.linkedin_url == url)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="No lead matches this LinkedIn profile URL")
    signal, enrolled = await create_signal_for_lead(
        session,
        org,
        lead,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        source_url=payload.source_url,
        source=payload.source,
        strength=payload.strength,
        detected_at=payload.detected_at,
    )
    await audit(
        session,
        org.id,
        "signal.ingested",
        actor_type="api_key",
        actor_id=ctx.api_key.id,
        target_type="signal",
        target_id=signal.id,
    )
    await session.commit()
    return SignalCreated(signal=signal_to_read(signal), campaign_enrolled=enrolled)


@router.patch("/{signal_id}/dismiss", response_model=MessageOut)
async def dismiss_signal(
    signal_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    signal = (
        await session.execute(
            select(Signal).where(Signal.id == signal_id, Signal.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    signal.status = "dismissed"
    await session.commit()
    return MessageOut(message="Signal dismissed")
