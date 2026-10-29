from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.domain import LEAD_STATUSES
from app.models import (
    Campaign,
    CampaignLead,
    Conversation,
    Lead,
    LinkedInAccount,
    Message,
    Signal,
)
from app.schemas import (
    ActivityPoint,
    CampaignPerformance,
    DashboardRead,
    FunnelBucket,
    UsageRead,
)
from app.security import utcnow
from app.services.campaign import effective_quotas, reset_daily_usage
from app.utils import signal_to_read

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
async def dashboard(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    org_id = ctx.org_id
    now = utcnow()
    timezone_name = ctx.organization.timezone
    today = now.astimezone(ZoneInfo(timezone_name)).date()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

    total_leads = (await session.execute(select(func.count(Lead.id)).where(Lead.organization_id == org_id))).scalar_one()
    hot_leads = (
        await session.execute(
            select(func.count(Lead.id)).where(Lead.organization_id == org_id, Lead.icp_score >= 70)
        )
    ).scalar_one()
    avg_score = (
        await session.execute(
            select(func.coalesce(func.avg(Lead.icp_score), 0)).where(Lead.organization_id == org_id)
        )
    ).scalar_one()
    signals_today = (
        await session.execute(
            select(func.count(Signal.id)).where(
                Signal.organization_id == org_id,
                func.date(func.timezone(timezone_name, Signal.detected_at)) == today,
            )
        )
    ).scalar_one()
    signals_7d = (
        await session.execute(
            select(func.count(Signal.id)).where(
                Signal.organization_id == org_id, Signal.detected_at >= seven_days_ago
            )
        )
    ).scalar_one()
    active_campaigns = (
        await session.execute(
            select(func.count(Campaign.id)).where(
                Campaign.organization_id == org_id, Campaign.status == "active"
            )
        )
    ).scalar_one()
    replies_7d = (
        await session.execute(
            select(func.count(Lead.id)).where(
                Lead.organization_id == org_id, Lead.last_replied_at >= seven_days_ago
            )
        )
    ).scalar_one()
    meetings = (
        await session.execute(
            select(func.count(Lead.id)).where(Lead.organization_id == org_id, Lead.status == "meeting")
        )
    ).scalar_one()
    contacted = (
        await session.execute(
            select(func.count(Lead.id)).where(
                Lead.organization_id == org_id,
                Lead.status.in_(("contacted", "replied", "meeting", "won", "lost")),
            )
        )
    ).scalar_one()
    replied_total = (
        await session.execute(
            select(func.count(Lead.id)).where(
                Lead.organization_id == org_id, Lead.last_replied_at.is_not(None)
            )
        )
    ).scalar_one()

    funnel_rows = (
        await session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.organization_id == org_id)
            .group_by(Lead.status)
        )
    ).all()
    counts = {status: count for status, count in funnel_rows}
    funnel = [FunnelBucket(status=status, count=counts.get(status, 0)) for status in LEAD_STATUSES]

    signal_activity = {
        str(day): count
        for day, count in (
            await session.execute(
                select(func.date(func.timezone(timezone_name, Signal.detected_at)), func.count(Signal.id))
                .where(Signal.organization_id == org_id, Signal.detected_at >= fourteen_days_ago)
                .group_by(literal_column("1"))
            )
        ).all()
    }
    message_activity = {
        (str(day), direction): count
        for day, direction, count in (
            await session.execute(
                select(func.date(func.timezone(timezone_name, Message.sent_at)), Message.direction, func.count(Message.id))
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(Conversation.organization_id == org_id, Message.sent_at >= fourteen_days_ago)
                .group_by(literal_column("1"), literal_column("2"))
            )
        ).all()
    }
    activity = []
    local_now = now.astimezone(ZoneInfo(timezone_name))
    for offset in range(13, -1, -1):
        day = local_now.date() - timedelta(days=offset)
        key = str(day)
        activity.append(
            ActivityPoint(
                date=key,
                signals=int(signal_activity.get(key, 0)),
                messages=int(message_activity.get((key, "outbound"), 0)),
                replies=int(message_activity.get((key, "inbound"), 0)),
            )
        )

    recent_signals = (
        await session.execute(
            select(Signal)
            .where(Signal.organization_id == org_id)
            .order_by(Signal.detected_at.desc())
            .limit(6)
        )
    ).scalars().all()
    recent_conversations = (
        await session.execute(
            select(Conversation)
            .where(Conversation.organization_id == org_id, Conversation.is_archived.is_(False))
            .order_by(Conversation.last_message_at.desc())
            .limit(5)
        )
    ).scalars().all()
    from app.routers.unibox import _conversation_reads

    campaign_rows = (
        await session.execute(
            select(Campaign).where(Campaign.organization_id == org_id, Campaign.status != "archived")
        )
    ).scalars().all()
    campaign_performance: list[CampaignPerformance] = []
    for campaign in campaign_rows:
        leads_rows = (
            await session.execute(select(CampaignLead).where(CampaignLead.campaign_id == campaign.id))
        ).scalars().all()
        contacted_count = sum(1 for row in leads_rows if row.status not in {"enrolled", "failed"})
        replied_count = sum(1 for row in leads_rows if row.replied_at is not None)
        campaign_performance.append(
            CampaignPerformance(
                id=campaign.id,
                name=campaign.name,
                status=campaign.status,
                leads=len(leads_rows),
                contacted=contacted_count,
                replied=replied_count,
                reply_rate=round((replied_count / contacted_count) * 100, 1) if contacted_count else 0,
            )
        )

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
        reset_daily_usage(account, ctx.organization)
        invite_limit, message_limit = effective_quotas(ctx.organization, account)
        usage = UsageRead(
            invites_used=account.invites_sent_today,
            invites_limit=invite_limit,
            messages_used=account.messages_sent_today,
            messages_limit=message_limit,
            warmup_active=account.status == "warming",
        )

    return DashboardRead(
        total_leads=total_leads,
        hot_leads=hot_leads,
        signals_7d=signals_7d,
        signals_today=signals_today,
        active_campaigns=active_campaigns,
        replies_7d=replies_7d,
        meetings=meetings,
        reply_rate=round((replied_total / contacted) * 100, 1) if contacted else 0,
        avg_icp_score=round(float(avg_score), 1),
        funnel=funnel,
        activity=activity,
        recent_signals=[signal_to_read(signal) for signal in recent_signals],
        recent_conversations=await _conversation_reads(session, list(recent_conversations)),
        campaigns=campaign_performance,
        usage=usage,
    )
