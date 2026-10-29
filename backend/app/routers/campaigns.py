from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.models import Campaign, CampaignLead, ICP, Lead, LinkedInAccount, OutboundAction, SequenceStep
from app.schemas import (
    CampaignAddLeadsRequest,
    CampaignCreate,
    CampaignDetail,
    CampaignLeadRead,
    CampaignListResponse,
    CampaignRead,
    CampaignRunResponse,
    CampaignStats,
    CampaignUpdate,
    LeadBrief,
    MessageOut,
    SequenceStepRead,
)
from app.services.audit import audit
from app.services.campaign import enroll_lead, launch_campaign, utcnow
from app.security import utcnow as now_utc

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


async def _stats_for(session: AsyncSession, campaign_id: UUID) -> CampaignStats:
    rows = (
        await session.execute(select(CampaignLead).where(CampaignLead.campaign_id == campaign_id))
    ).scalars().all()
    total = len(rows)
    contacted = sum(1 for row in rows if row.status not in {"enrolled", "failed"})
    replied = sum(1 for row in rows if row.replied_at is not None)
    meetings = sum(1 for row in rows if row.status == "meeting")
    return CampaignStats(
        total_leads=total,
        contacted=contacted,
        replied=replied,
        meetings=meetings,
        reply_rate=round((replied / contacted) * 100, 1) if contacted else 0,
    )


async def _to_campaign_read(session: AsyncSession, campaign: Campaign) -> CampaignRead:
    steps = sorted(campaign.steps, key=lambda item: item.position)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        icp_id=campaign.icp_id,
        account_id=campaign.account_id,
        auto_launch=campaign.auto_launch,
        min_score=campaign.min_score,
        daily_invite_limit=campaign.daily_invite_limit,
        daily_message_limit=campaign.daily_message_limit,
        status=campaign.status,
        launched_at=campaign.launched_at,
        paused_at=campaign.paused_at,
        completed_at=campaign.completed_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        steps=[
            SequenceStepRead(
                id=step.id,
                position=step.position,
                action_type=step.action_type,  # type: ignore[arg-type]
                delay_days=step.delay_days,
                body_template=step.body_template,
                is_active=step.is_active,
            )
            for step in steps
        ],
        icp_name=campaign.icp.name if campaign.icp else None,
        account_name=campaign.account.display_name if campaign.account else None,
        stats=await _stats_for(session, campaign.id),
    )


async def _campaign_for_org(session: AsyncSession, org_id: UUID, campaign_id: UUID) -> Campaign:
    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
        )
    ).scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


async def _validate_relations(
    session: AsyncSession,
    org_id: UUID,
    icp_id: UUID,
    account_id: UUID | None,
) -> None:
    icp = await session.get(ICP, icp_id)
    if icp is None or icp.organization_id != org_id:
        raise HTTPException(status_code=400, detail="The selected ICP does not belong to this workspace")
    if account_id:
        account = await session.get(LinkedInAccount, account_id)
        if account is None or account.organization_id != org_id:
            raise HTTPException(status_code=400, detail="The selected LinkedIn account is invalid")


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
    status_filter: str | None = Query(default=None, alias="status"),
    include_archived: bool = False,
):
    conditions = [Campaign.organization_id == ctx.org_id]
    if status_filter:
        conditions.append(Campaign.status == status_filter)
    elif not include_archived:
        conditions.append(Campaign.status != "archived")
    campaigns = (
        await session.execute(select(Campaign).where(*conditions).order_by(Campaign.created_at.desc()))
    ).scalars().all()
    items = [await _to_campaign_read(session, campaign) for campaign in campaigns]
    return CampaignListResponse(items=items, total=len(items))


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    await _validate_relations(session, ctx.org_id, payload.icp_id, payload.account_id)
    data = payload.model_dump(exclude={"steps"})
    campaign = Campaign(
        organization_id=ctx.org_id,
        **data,
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
    await session.flush()
    await session.refresh(campaign)
    await audit(
        session, ctx.org_id, "campaign.created", actor_id=ctx.user.id, target_type="campaign", target_id=campaign.id
    )
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return await _to_campaign_read(session, campaign)


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    base = (await _to_campaign_read(session, campaign)).model_dump()
    rows = (
        await session.execute(
            select(CampaignLead)
            .where(CampaignLead.campaign_id == campaign.id)
            .order_by(CampaignLead.created_at.desc())
        )
    ).scalars().all()
    leads = [
        CampaignLeadRead(
            id=row.id,
            status=row.status,
            current_step=row.current_step,
            next_action_at=row.next_action_at,
            last_action_at=row.last_action_at,
            replied_at=row.replied_at,
            lead=LeadBrief.model_validate(row.lead),
        )
        for row in rows
        if row.lead
    ]
    base["leads"] = leads
    return CampaignDetail(**base)


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    data = payload.model_dump(exclude_unset=True, exclude={"steps"})
    if "icp_id" in data or "account_id" in data:
        await _validate_relations(
            session,
            ctx.org_id,
            data.get("icp_id", campaign.icp_id),
            data.get("account_id", campaign.account_id),
        )
    for field, value in data.items():
        setattr(campaign, field, value)
    if payload.steps is not None:
        if campaign.status == "active":
            raise HTTPException(status_code=409, detail="Pause the campaign before editing its sequence")
        current_steps = (
            await session.execute(select(SequenceStep).where(SequenceStep.campaign_id == campaign.id))
        ).scalars().all()
        for step in current_steps:
            await session.delete(step)
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
        session, ctx.org_id, "campaign.updated", actor_id=ctx.user.id, target_type="campaign", target_id=campaign.id
    )
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return await _to_campaign_read(session, campaign)


@router.post("/{campaign_id}/launch", response_model=CampaignRunResponse)
async def launch(
    campaign_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    if not campaign.steps:
        raise HTTPException(status_code=400, detail="Add at least one sequence step before launching")
    if campaign.status == "active":
        pass
    else:
        account = await session.get(LinkedInAccount, campaign.account_id) if campaign.account_id else None
        if account is None:
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
                raise HTTPException(status_code=400, detail="Connect a LinkedIn account before launching")
            campaign.account_id = account.id
        campaign.status = "active"
    try:
        enrolled, skipped = await launch_campaign(session, ctx.organization, campaign)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await audit(
        session, ctx.org_id, "campaign.launched", actor_id=ctx.user.id, target_type="campaign", target_id=campaign.id
    )
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return CampaignRunResponse(
        campaign=await _to_campaign_read(session, campaign),
        enrolled=enrolled,
        skipped=skipped,
    )


@router.post("/{campaign_id}/pause", response_model=CampaignRead)
async def pause(
    campaign_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    if campaign.status == "active":
        campaign.status = "paused"
        campaign.paused_at = utcnow()
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return await _to_campaign_read(session, campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignRunResponse)
async def resume(
    campaign_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    if campaign.status != "paused":
        raise HTTPException(status_code=400, detail="Only a paused campaign can be resumed")
    campaign.status = "active"
    campaign.paused_at = None
    try:
        enrolled, skipped = await launch_campaign(session, ctx.organization, campaign)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return CampaignRunResponse(
        campaign=await _to_campaign_read(session, campaign),
        enrolled=enrolled,
        skipped=skipped,
    )


@router.post("/{campaign_id}/leads", response_model=CampaignRunResponse)
async def add_campaign_leads(
    campaign_id: UUID,
    payload: CampaignAddLeadsRequest,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    if campaign.status not in {"draft", "active", "paused"}:
        raise HTTPException(status_code=400, detail="This campaign cannot receive new leads")
    enrolled = 0
    skipped = 0
    for offset, lead_id in enumerate(payload.lead_ids):
        lead = (
            await session.execute(
                select(Lead).where(Lead.id == lead_id, Lead.organization_id == ctx.org_id)
            )
        ).scalar_one_or_none()
        if lead is None:
            skipped += 1
            continue
        created = await enroll_lead(
            session,
            campaign,
            lead,
            due_at=utcnow() + timedelta(minutes=offset * 2),
            reason="manual_add",
        )
        if created:
            enrolled += 1
        else:
            skipped += 1
    await session.commit()
    campaign = await _campaign_for_org(session, ctx.org_id, campaign.id)
    return CampaignRunResponse(
        campaign=await _to_campaign_read(session, campaign),
        enrolled=enrolled,
        skipped=skipped,
    )


@router.delete("/{campaign_id}/leads/{campaign_lead_id}", response_model=MessageOut)
async def remove_campaign_lead(
    campaign_id: UUID,
    campaign_lead_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    await _campaign_for_org(session, ctx.org_id, campaign_id)
    campaign_lead = (
        await session.execute(
            select(CampaignLead).where(
                CampaignLead.id == campaign_lead_id, CampaignLead.campaign_id == campaign_id
            )
        )
    ).scalar_one_or_none()
    if campaign_lead is None:
        raise HTTPException(status_code=404, detail="Campaign lead not found")
    campaign_lead.status = "stopped"
    campaign_lead.stopped_reason = "removed_by_user"
    campaign_lead.next_action_at = None
    await session.execute(
        update(OutboundAction)
        .where(
            OutboundAction.campaign_lead_id == campaign_lead.id,
            OutboundAction.status.in_(("scheduled", "processing")),
        )
        .values(status="cancelled")
    )
    await session.commit()
    return MessageOut(message="Lead removed from campaign")


@router.delete("/{campaign_id}", response_model=MessageOut)
async def archive_campaign(
    campaign_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    campaign = await _campaign_for_org(session, ctx.org_id, campaign_id)
    campaign.status = "archived"
    await session.execute(
        update(OutboundAction)
        .where(OutboundAction.campaign_id == campaign.id, OutboundAction.status == "scheduled")
        .values(status="cancelled", error="Campaign archived")
    )
    await audit(
        session, ctx.org_id, "campaign.archived", actor_id=ctx.user.id, target_type="campaign", target_id=campaign.id
    )
    await session.commit()
    return MessageOut(message="Campaign archived")
