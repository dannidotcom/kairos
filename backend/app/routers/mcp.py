from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import ApiKeyContext, get_api_key_context
from app.models import (
    Campaign,
    CampaignLead,
    ICP,
    Lead,
    LinkedInAccount,
    SequenceStep,
    Signal,
)
from app.routers.campaigns import _campaign_for_org, _to_campaign_read, _validate_relations
from app.routers.leads import _build_lead_reads
from app.schemas import (
    CampaignCreate,
    CampaignRead,
    IcebreakerRequest,
    IcebreakerResponse,
    ICPRead,
    LeadRead,
    SignalRead,
)
from app.security import utcnow
from app.services.audit import audit
from app.services.campaign import effective_quotas, launch_campaign, latest_signal_for_lead, reset_daily_usage, utcnow as service_now
from app.services.llm import draft_icebreaker
from app.utils import signal_to_read

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/summary")
async def workspace_summary(
    ctx: ApiKeyContext = Depends(get_api_key_context), session: AsyncSession = Depends(get_session)
):
    org = ctx.organization
    org_id = org.id
    total_leads = (await session.execute(select(func.count(Lead.id)).where(Lead.organization_id == org_id))).scalar_one()
    hot_leads = (
        await session.execute(
            select(func.count(Lead.id)).where(Lead.organization_id == org_id, Lead.icp_score >= 70)
        )
    ).scalar_one()
    active_campaigns = (
        await session.execute(
            select(func.count(Campaign.id)).where(Campaign.organization_id == org_id, Campaign.status == "active")
        )
    ).scalar_one()
    signals_7d = (
        await session.execute(
            select(func.count(Signal.id)).where(
                Signal.organization_id == org_id, Signal.detected_at >= utcnow() - timedelta(days=7)
            )
        )
    ).scalar_one()
    replies_7d = (
        await session.execute(
            select(func.count(Lead.id)).where(
                Lead.organization_id == org_id, Lead.last_replied_at >= utcnow() - timedelta(days=7)
            )
        )
    ).scalar_one()
    account = (
        await session.execute(
            select(LinkedInAccount)
            .where(
                LinkedInAccount.organization_id == org_id,
                LinkedInAccount.status.in_(("connected", "warming")),
            )
            .order_by(LinkedInAccount.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    usage = None
    if account:
        reset_daily_usage(account, org)
        invite_limit, message_limit = effective_quotas(org, account)
        usage = {
            "invites_used": account.invites_sent_today,
            "invites_limit": invite_limit,
            "messages_used": account.messages_sent_today,
            "messages_limit": message_limit,
        }
    recent_signals = (
        await session.execute(
            select(Signal).where(Signal.organization_id == org_id).order_by(Signal.detected_at.desc()).limit(5)
        )
    ).scalars().all()
    return {
        "workspace": org.name,
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "signals_last_7_days": signals_7d,
        "replies_last_7_days": replies_7d,
        "active_campaigns": active_campaigns,
        "usage": usage,
        "recent_signals": [signal_to_read(signal).model_dump(mode="json") for signal in recent_signals],
        "generated_at": utcnow().isoformat(),
    }


@router.get("/leads", response_model=list[LeadRead])
async def list_hot_leads(
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
    min_score: int = Query(default=0, ge=0, le=100),
    query: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
):
    conditions = [Lead.organization_id == ctx.org_id, Lead.icp_score >= min_score]
    if query:
        pattern = f"%{query.strip()}%"
        from sqlalchemy import or_

        conditions.append(
            or_(Lead.full_name.ilike(pattern), Lead.company.ilike(pattern), Lead.headline.ilike(pattern))
        )
    leads = (
        await session.execute(
            select(Lead).where(*conditions).order_by(Lead.icp_score.desc(), Lead.last_signal_at.desc().nullslast()).limit(limit)
        )
    ).scalars().all()
    return await _build_lead_reads(session, list(leads))


@router.get("/leads/{lead_id}")
async def get_lead_tool(
    lead_id: UUID,
    ctx: ApiKeyContext = Depends(get_api_key_context),
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
    signals = (
        await session.execute(
            select(Signal).where(Signal.lead_id == lead.id).order_by(Signal.detected_at.desc()).limit(10)
        )
    ).scalars().all()
    payload = reads[0].model_dump(mode="json")
    payload["signals"] = [signal_to_read(signal).model_dump(mode="json") for signal in signals]
    payload["about"] = lead.about
    return payload


@router.get("/signals", response_model=list[SignalRead])
async def list_signals_tool(
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=15, ge=1, le=50),
    signal_type: str | None = Query(default=None, alias="type"),
):
    conditions = [Signal.organization_id == ctx.org_id]
    if signal_type:
        conditions.append(Signal.type == signal_type)
    signals = (
        await session.execute(
            select(Signal).where(*conditions).order_by(Signal.detected_at.desc()).limit(limit)
        )
    ).scalars().all()
    return [signal_to_read(signal) for signal in signals]


@router.get("/icps", response_model=list[ICPRead])
async def list_icps_tool(
    ctx: ApiKeyContext = Depends(get_api_key_context), session: AsyncSession = Depends(get_session)
):
    icps = (
        await session.execute(
            select(ICP).where(ICP.organization_id == ctx.org_id).order_by(ICP.created_at.desc())
        )
    ).scalars().all()
    return [ICPRead.model_validate(icp) for icp in icps]


@router.get("/campaigns", response_model=list[CampaignRead])
async def list_campaigns_tool(
    ctx: ApiKeyContext = Depends(get_api_key_context), session: AsyncSession = Depends(get_session)
):
    campaigns = (
        await session.execute(
            select(Campaign)
            .where(Campaign.organization_id == ctx.org_id, Campaign.status != "archived")
            .order_by(Campaign.created_at.desc())
        )
    ).scalars().all()
    return [await _to_campaign_read(session, campaign) for campaign in campaigns]


@router.post("/campaigns", response_model=CampaignRead, status_code=201)
async def create_campaign_tool(
    payload: CampaignCreate,
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
):
    await _validate_relations(session, ctx.org_id, payload.icp_id, payload.account_id)
    campaign = Campaign(
        organization_id=ctx.org_id,
        **payload.model_dump(exclude={"steps"}),
        status="draft",
    )
    session.add(campaign)
    await session.flush()
    for index, step in enumerate(payload.steps):
        session.add(
            SequenceStep(
                campaign_id=campaign.id,
                position=index,
                action_type=step.action_type,
                delay_days=step.delay_days,
                body_template=step.body_template,
                is_active=step.is_active,
            )
        )
    await audit(
        session,
        ctx.org_id,
        "campaign.created.mcp",
        actor_type="api_key",
        actor_id=ctx.api_key.id,
        target_type="campaign",
        target_id=campaign.id,
    )
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return await _to_campaign_read(session, campaign)


@router.post("/campaigns/{campaign_id}/launch")
async def launch_campaign_tool(
    campaign_id: UUID,
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    if not campaign.steps:
        raise HTTPException(status_code=400, detail="Campaign has no sequence steps")
    if not campaign.account_id:
        account = (
            await session.execute(
                select(LinkedInAccount)
                .where(
                    LinkedInAccount.organization_id == ctx.org_id,
                    LinkedInAccount.status.in_(("connected", "warming")),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if account is None:
            raise HTTPException(status_code=400, detail="No connected LinkedIn account")
        campaign.account_id = account.id
    campaign.status = "active"
    try:
        enrolled, skipped = await launch_campaign(session, ctx.organization, campaign)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await audit(
        session,
        ctx.org_id,
        "campaign.launched.mcp",
        actor_type="api_key",
        actor_id=ctx.api_key.id,
        target_type="campaign",
        target_id=campaign.id,
    )
    await session.commit()
    return {"campaign_id": str(campaign.id), "status": "active", "enrolled": enrolled, "skipped": skipped}


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign_tool(
    campaign_id: UUID,
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    if campaign.status == "active":
        campaign.status = "paused"
        campaign.paused_at = service_now()
    await audit(
        session,
        ctx.org_id,
        "campaign.paused.mcp",
        actor_type="api_key",
        actor_id=ctx.api_key.id,
        target_type="campaign",
        target_id=campaign.id,
    )
    await session.commit()
    return {"campaign_id": str(campaign.id), "status": campaign.status}


@router.post("/draft-icebreaker", response_model=IcebreakerResponse)
async def draft_icebreaker_tool(
    payload: IcebreakerRequest,
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: AsyncSession = Depends(get_session),
):
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == payload.lead_id, Lead.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    campaign = await session.get(Campaign, payload.campaign_id) if payload.campaign_id else None
    if campaign and campaign.organization_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    icp = campaign.icp if campaign else (await session.get(ICP, lead.icp_id) if lead.icp_id else None)
    signal = await latest_signal_for_lead(session, lead.id)
    text, generated_by = await draft_icebreaker(
        lead=lead,
        signal=signal,
        icp=icp,
        locale=ctx.organization.locale,
        value_prop=icp.value_prop if icp else None,
    )
    return IcebreakerResponse(text=text, generated_by=generated_by)
