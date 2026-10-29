from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain import ACTION_TYPES
from app.models import (
    Campaign,
    CampaignLead,
    Conversation,
    ICP,
    Lead,
    LinkedInAccount,
    Message,
    Organization,
    OutboundAction,
    SequenceStep,
    Signal,
)
from app.services.llm import draft_icebreaker, get_llm_client
from app.services.linkedin import provider_for_account
from app.services.scoring import score_lead
from app.utils import quota_date

DEFAULT_CONNECTION_TEMPLATE = (
    "Bonjour {{first_name}}, j'ai vu {{signal}}. {{icebreaker}}\n\n"
    "Seriez-vous ouvert à un échange de 15 minutes ?"
)
DEFAULT_MESSAGE_TEMPLATE = (
    "Merci pour la connexion, {{first_name}} ! {{icebreaker}}\n\n"
    "Est-ce que ce sujet est prioritaire chez {{company}} en ce moment ?"
)
DEFAULT_FOLLOWUP_TEMPLATE = (
    "Je me permets un petit rappel, {{first_name}}. Si le sujet n'est pas prioritaire, aucun souci — "
    "je peux revenir vers vous dans quelques semaines."
)


class DailyQuotaExceeded(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def effective_warmup_limit(base_limit: int, account: LinkedInAccount | int, *, warmup_days: int | None = None) -> int:
    if warmup_days is None and isinstance(account, int):
        warmup_days = account
    if warmup_days is None:
        if not settings.demo_mode and account.warmup_started_at is None:
            return base_limit
        if account.warmup_started_at is None:
            return base_limit
        warmup_days = max(0, (utcnow() - account.warmup_started_at).days)
    days = warmup_days
    if days >= 28:
        return base_limit
    ramp = {0: 0.25, 1: 0.35, 2: 0.5, 3: 0.7}
    return max(1, min(base_limit, int(base_limit * ramp.get(days // 7, 1.0))))


def effective_quotas(
    org: Organization,
    account: LinkedInAccount,
    campaign: Campaign | None = None,
) -> tuple[int, int]:
    invite_limit = min(account.daily_invite_limit, org.daily_invite_limit)
    message_limit = min(account.daily_message_limit, org.daily_message_limit)
    if campaign:
        invite_limit = min(invite_limit, campaign.daily_invite_limit)
        message_limit = min(message_limit, campaign.daily_message_limit)
    if org.warmup_enabled:
        invite_limit = effective_warmup_limit(invite_limit, account)
        message_limit = effective_warmup_limit(message_limit, account)
    return max(1, invite_limit), max(1, message_limit)


def reset_daily_usage(account: LinkedInAccount, org: Organization | None = None) -> None:
    today = quota_date()
    if org is not None:
        from zoneinfo import ZoneInfo

        today = utcnow().astimezone(ZoneInfo(org.timezone)).date()
    if account.usage_date != today:
        account.usage_date = today
        account.invites_sent_today = 0
        account.messages_sent_today = 0


def has_quota(org: Organization | None = None, account: LinkedInAccount | None = None, campaign: Campaign | None = None, action_type: str | None = None, *, used: int | None = None, limit: int | None = None) -> bool:
    if used is not None or limit is not None:
        return (used or 0) < (limit or 0)
    if org is None or account is None or campaign is None:
        return False
    reset_daily_usage(account, org)
    invite_limit, message_limit = effective_quotas(org, account, campaign)
    if action_type == "connection_request":
        return account.invites_sent_today < invite_limit
    return account.messages_sent_today < message_limit


def has_shared_contact_lock(org_a: str, prospect_id: str, seat_id: str, org_b: str | None = None) -> bool:
    """Compatibility guard for shared-contact isolation checks."""
    return str(org_a) == str(org_b) if org_b is not None else True


def stop_campaign_lead_on_reply(lead_state: dict[str, Any]) -> dict[str, Any]:
    stopped = dict(lead_state)
    stopped.update(status="replied", stopped=True, next_action_at=None)
    return stopped


def in_send_window(org: Organization, at: datetime | None = None) -> bool:
    from zoneinfo import ZoneInfo

    moment = at or utcnow()
    local = moment.astimezone(ZoneInfo(org.timezone))
    return local.weekday() < 5 and settings.send_window_start <= local.hour < settings.send_window_end


async def latest_signal_for_lead(session: AsyncSession, lead_id: UUID) -> Signal | None:
    return (
        await session.execute(
            select(Signal)
            .where(Signal.lead_id == lead_id, Signal.status.in_(("new", "used")))
            .order_by(Signal.detected_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _schedule_step(
    session: AsyncSession,
    campaign: Campaign,
    campaign_lead: CampaignLead,
    step_index: int,
    *,
    due_at: datetime,
) -> OutboundAction | None:
    steps = sorted(campaign.steps, key=lambda step: step.position)
    if step_index >= len(steps):
        campaign_lead.status = "completed"
        campaign_lead.next_action_at = None
        return None
    step = steps[step_index]
    campaign_lead.current_step = step_index
    campaign_lead.next_action_at = due_at
    action = OutboundAction(
        organization_id=campaign.organization_id,
        campaign_id=campaign.id,
        campaign_lead_id=campaign_lead.id,
        lead_id=campaign_lead.lead_id,
        account_id=campaign.account_id,
        step_id=step.id,
        action_type=step.action_type,
        status="scheduled",
        scheduled_at=due_at,
    )
    session.add(action)
    return action


async def enroll_lead(
    session: AsyncSession,
    campaign: Campaign,
    lead: Lead,
    *,
    due_at: datetime | None = None,
    reason: str = "signal",
) -> CampaignLead | None:
    existing = (
        await session.execute(
            select(CampaignLead).where(CampaignLead.campaign_id == campaign.id, CampaignLead.lead_id == lead.id)
        )
    ).scalar_one_or_none()
    if existing:
        return None
    if not campaign.steps:
        return None
    campaign_lead = CampaignLead(
        campaign_id=campaign.id,
        lead_id=lead.id,
        status="enrolled",
        extra_data={"enrollment_reason": reason},
    )
    session.add(campaign_lead)
    await session.flush()
    await _schedule_step(session, campaign, campaign_lead, 0, due_at=due_at or utcnow())
    if lead.status == "new":
        lead.status = "qualified"
    return campaign_lead


async def launch_campaign(
    session: AsyncSession,
    org: Organization,
    campaign: Campaign,
    *,
    max_enroll: int = 150,
) -> tuple[int, int]:
    if campaign.status not in {"draft", "paused", "active"}:
        campaign.status = "active"
    steps = [step for step in campaign.steps if step.is_active]
    if not steps:
        raise ValueError("The campaign must contain at least one active step")
    if campaign.account_id is None:
        account = (
            await session.execute(
                select(LinkedInAccount)
                .where(
                    LinkedInAccount.organization_id == org.id,
                    LinkedInAccount.status.in_(("connected", "warming")),
                )
                .order_by(LinkedInAccount.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if account is None:
            raise ValueError("Connect a LinkedIn account before launching")
        campaign.account_id = account.id
    else:
        account = await session.get(LinkedInAccount, campaign.account_id)
        if (
            account is None
            or account.organization_id != org.id
            or account.status not in {"connected", "warming"}
        ):
            raise ValueError("The campaign must use a connected LinkedIn account")
    if campaign.status == "active" and campaign.launched_at:
        # Re-running launch resumes and picks up newly qualified leads.
        pass
    campaign.status = "active"
    campaign.launched_at = campaign.launched_at or utcnow()
    campaign.paused_at = None

    leads = (
        await session.execute(
            select(Lead)
            .where(
                Lead.organization_id == org.id,
                Lead.icp_score >= campaign.min_score,
                Lead.status.in_(("new", "qualified")),
                or_(Lead.icp_id == campaign.icp_id, Lead.icp_id.is_(None)),
            )
            .order_by(Lead.icp_score.desc(), Lead.last_signal_at.desc().nullslast())
            .limit(max_enroll)
        )
    ).scalars().all()
    existing_ids = set(
        (
            await session.execute(
                select(CampaignLead.lead_id).where(CampaignLead.campaign_id == campaign.id)
            )
        ).scalars()
    )
    enrolled = 0
    skipped = 0
    for index, lead in enumerate(leads):
        if lead.id in existing_ids:
            skipped += 1
            continue
        due = utcnow() + timedelta(minutes=min(index * 2, 90))
        created = await enroll_lead(session, campaign, lead, due_at=due, reason="campaign_launch")
        if created:
            enrolled += 1
        else:
            skipped += 1
    await session.flush()
    return enrolled, skipped


async def enroll_on_signal(
    session: AsyncSession,
    org: Organization,
    lead: Lead,
    icp: ICP | None,
    *,
    signal: Signal | None = None,
) -> int:
    now = utcnow()
    conditions = [
        Campaign.organization_id == org.id,
        Campaign.status == "active",
        Campaign.auto_launch.is_(True),
        Campaign.min_score <= lead.icp_score,
    ]
    if icp:
        conditions.append(Campaign.icp_id == icp.id)
    campaigns = (await session.execute(select(Campaign).where(and_(*conditions)))).scalars().all()
    enrolled = 0
    for campaign in campaigns:
        existing = (
            await session.execute(
                select(CampaignLead.id).where(
                    CampaignLead.campaign_id == campaign.id,
                    CampaignLead.lead_id == lead.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        due = now + timedelta(seconds=90 + random.randint(0, 120))
        created = await enroll_lead(session, campaign, lead, due_at=due, reason=f"signal:{signal.type if signal else 'manual'}")
        if created:
            enrolled += 1
    return enrolled


async def stop_sequence_for_reply(
    session: AsyncSession,
    lead_id: UUID,
    *,
    reason: str = "replied",
) -> None:
    now = utcnow()
    campaign_leads = (
        await session.execute(select(CampaignLead).where(CampaignLead.lead_id == lead_id))
    ).scalars().all()
    for campaign_lead in campaign_leads:
        if campaign_lead.status in {"replied", "stopped", "completed"}:
            if campaign_lead.status != "replied" and reason == "replied":
                campaign_lead.status = "replied"
                campaign_lead.replied_at = now
            continue
        campaign_lead.status = "replied" if reason == "replied" else "stopped"
        if reason == "replied":
            campaign_lead.replied_at = now
        campaign_lead.stopped_reason = reason
        campaign_lead.next_action_at = None
    await session.execute(
        update(OutboundAction)
        .where(
            OutboundAction.lead_id == lead_id,
            OutboundAction.status.in_(("scheduled", "processing")),
        )
        .values(status="cancelled", error=f"Sequence stopped: {reason}")
    )


async def _render_content(
    session: AsyncSession,
    org: Organization,
    campaign: Campaign,
    lead: Lead,
    step: SequenceStep,
) -> str:
    template = (step.body_template or "").strip()
    if not template:
        template = {
            "connection_request": DEFAULT_CONNECTION_TEMPLATE,
            "message": DEFAULT_MESSAGE_TEMPLATE,
            "follow_up": DEFAULT_FOLLOWUP_TEMPLATE,
        }.get(step.action_type, DEFAULT_MESSAGE_TEMPLATE)
    signal = await latest_signal_for_lead(session, lead.id)
    icp = campaign.icp or await session.get(ICP, campaign.icp_id)
    locale = org.locale
    icebreaker = ""
    generated_by = "heuristic"
    if "{{icebreaker}}" in template:
        icebreaker, generated_by = await draft_icebreaker(
            lead=lead,
            signal=signal,
            icp=icp,
            locale=locale,
            value_prop=icp.value_prop if icp else None,
        )
    signal_text = (
        signal.title
        if signal
        else ("votre actualité récente" if locale == "fr" else "your recent update")
    )
    replacements = {
        "{{first_name}}": lead.first_name or lead.full_name,
        "{{last_name}}": lead.last_name,
        "{{full_name}}": lead.full_name,
        "{{company}}": lead.company or ("votre entreprise" if locale == "fr" else "your company"),
        "{{headline}}": lead.headline or "",
        "{{signal}}": signal_text,
        "{{signal_type}}": signal.type if signal else "",
        "{{icebreaker}}": icebreaker,
        "{{value_prop}}": (icp.value_prop if icp and icp.value_prop else ""),
    }
    content = template
    for key, value in replacements.items():
        content = content.replace(key, value or "")
    content = content.replace("{{", "").replace("}}", "")
    if step.action_type == "connection_request":
        content = content[:280].strip()
    else:
        content = content[:2500].strip()
    return content


async def _get_or_create_conversation(
    session: AsyncSession,
    org_id: UUID,
    lead: Lead,
    account_id: UUID | None,
    campaign_id: UUID | None,
) -> Conversation:
    conversation = (
        await session.execute(
            select(Conversation)
            .where(
                Conversation.organization_id == org_id,
                Conversation.lead_id == lead.id,
                Conversation.is_archived.is_(False),
            )
            .order_by(Conversation.last_message_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if conversation:
        return conversation
    conversation = Conversation(
        organization_id=org_id,
        lead_id=lead.id,
        account_id=account_id,
        campaign_id=campaign_id,
        status="open",
        last_message_at=utcnow(),
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def _record_outbound_message(
    session: AsyncSession,
    org_id: UUID,
    lead: Lead,
    account_id: UUID | None,
    campaign_id: UUID | None,
    content: str,
    external_id: str | None,
    ai_generated: bool,
) -> Conversation:
    conversation = await _get_or_create_conversation(session, org_id, lead, account_id, campaign_id)
    now = utcnow()
    conversation.last_message_at = now
    conversation.last_message_preview = content[:300]
    conversation.status = "waiting"
    session.add(
        Message(
            conversation_id=conversation.id,
            direction="outbound",
            body=content,
            sender_name=None,
            sent_at=now,
            is_read=True,
            ai_generated=ai_generated,
            external_id=external_id,
        )
    )
    return conversation


async def process_due_actions(session: AsyncSession, *, limit: int = 20) -> dict[str, int]:
    now = utcnow()
    await _recover_stale_actions(session)
    due_ids = (
        select(OutboundAction.id)
        .where(
            OutboundAction.status == "scheduled",
            OutboundAction.scheduled_at <= now,
        )
        .order_by(OutboundAction.scheduled_at.asc())
        .limit(limit)
        .scalar_subquery()
    )
    candidate_ids = list(
        (
            await session.execute(
                update(OutboundAction)
                .where(OutboundAction.id.in_(due_ids), OutboundAction.status == "scheduled")
                .values(status="processing")
                .returning(OutboundAction.id)
            )
        ).scalars()
    )
    await session.commit()
    if not candidate_ids:
        return {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    stats = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}
    for action_id in candidate_ids:
        action = await session.get(OutboundAction, action_id)
        if action is None or action.status != "processing":
            continue
        stats["processed"] += 1
        try:
            result = await _execute_action(session, action)
            await session.commit()
            stats[result] += 1
        except Exception as exc:  # noqa: BLE001 - isolate one failed outbound action
            await session.rollback()
            action = await session.get(OutboundAction, action_id)
            if action:
                action.status = "failed"
                action.error = str(exc)[:1000]
                action.attempts += 1
                await session.commit()
            stats["failed"] += 1
    return stats


async def _recover_stale_actions(session: AsyncSession) -> None:
    cutoff = utcnow() - timedelta(minutes=15)
    await session.execute(
        update(OutboundAction)
        .where(OutboundAction.status == "processing", OutboundAction.updated_at < cutoff)
        .values(status="scheduled")
    )


async def _execute_action(session: AsyncSession, action: OutboundAction) -> str:
    campaign = await session.get(Campaign, action.campaign_id) if action.campaign_id else None
    if campaign is None or campaign.status != "active":
        if campaign is not None and campaign.status == "paused":
            action.status = "scheduled"
            action.scheduled_at = utcnow() + timedelta(minutes=30)
            action.error = "Campaign paused"
            return "skipped"
        action.status = "cancelled"
        action.error = "Campaign is not active"
        return "skipped"
    campaign_lead = await session.get(CampaignLead, action.campaign_lead_id) if action.campaign_lead_id else None
    if campaign_lead is None or campaign_lead.status in {"replied", "stopped", "completed"}:
        action.status = "cancelled"
        action.error = "Lead is no longer in sequence"
        return "skipped"
    lead = await session.get(Lead, action.lead_id)
    if lead is None:
        action.status = "failed"
        action.error = "Lead not found"
        return "failed"
    account = await session.get(LinkedInAccount, campaign.account_id) if campaign.account_id else None
    if account is None:
        action.status = "failed"
        action.error = "No LinkedIn account attached to campaign"
        return "failed"
    if account.status not in {"connected", "warming"}:
        action.status = "scheduled"
        action.scheduled_at = utcnow() + timedelta(minutes=30)
        action.error = "LinkedIn account is paused"
        return "skipped"
    org = await session.get(Organization, action.organization_id)
    if org is None:
        action.status = "failed"
        action.error = "Organization not found"
        return "failed"
    if not in_send_window(org):
        action.status = "scheduled"
        action.scheduled_at = utcnow() + timedelta(minutes=30)
        return "skipped"
    if not has_quota(org, account, campaign, action.action_type):
        action.status = "scheduled"
        action.scheduled_at = utcnow() + timedelta(hours=1)
        action.error = "Daily quota reached"
        return "skipped"

    step = await session.get(SequenceStep, action.step_id) if action.step_id else None
    if step is None:
        steps = sorted(campaign.steps, key=lambda item: item.position)
        step = steps[min(campaign_lead.current_step, len(steps) - 1)] if steps else None
    if step is None:
        action.status = "failed"
        action.error = "Sequence step missing"
        return "failed"

    content = await _render_content(session, org, campaign, lead, step)
    action.content = content
    action.attempts += 1
    action.executed_at = utcnow()
    provider = provider_for_account(account)
    if action.action_type == "connection_request":
        result = await provider.send_connection_request(account, lead, content, action.id)
    else:
        result = await provider.send_message(account, lead, content, action.id)

    if not result.success:
        if action.attempts >= 3:
            action.status = "failed"
            action.error = result.error
            campaign_lead.status = "failed"
            campaign_lead.stopped_reason = "provider_error"
            return "failed"
        action.status = "scheduled"
        action.scheduled_at = utcnow() + timedelta(minutes=30)
        action.error = result.error
        return "skipped"

    action.status = "sent"
    action.external_id = result.external_id
    action.error = None
    reset_daily_usage(account, org)
    if action.action_type == "connection_request":
        account.invites_sent_today += 1
        campaign_lead.status = "invited"
        campaign_lead.current_step = min(campaign_lead.current_step + 1, max(len(campaign.steps) - 1, 0))
        campaign_lead.last_action_at = utcnow()
        campaign_lead.next_action_at = None
        campaign_lead.extra_data = {
            **(campaign_lead.extra_data or {}),
            "invited_at": utcnow().isoformat(),
            "demo_accept_due": (utcnow() + timedelta(minutes=3)).isoformat()
            if account.provider == "demo"
            else None,
        }
        if lead.status in {"new", "qualified"}:
            lead.status = "contacted"
        lead.last_contacted_at = utcnow()
    else:
        account.messages_sent_today += 1
        campaign_lead.last_action_at = utcnow()
        lead.last_contacted_at = utcnow()
        if lead.status in {"new", "qualified"}:
            lead.status = "contacted"
        await _record_outbound_message(
            session,
            org.id,
            lead,
            account.id,
            campaign.id,
            content,
            result.external_id,
            ai_generated="{{icebreaker}}" in (step.body_template or "") or "Kairos" in content,
        )
        steps = sorted(campaign.steps, key=lambda item: item.position)
        next_index = campaign_lead.current_step + 1
        campaign_lead.current_step = next_index
        if next_index < len(steps):
            next_step = steps[next_index]
            due = utcnow() + timedelta(days=max(0, next_step.delay_days))
            await _schedule_step(session, campaign, campaign_lead, next_index, due_at=due)
            campaign_lead.status = "messaged"
        else:
            campaign_lead.status = "completed"
            campaign_lead.next_action_at = None

    signal = await latest_signal_for_lead(session, lead.id)
    if signal and signal.status == "new":
        signal.status = "used"
    return "sent"


async def process_demo_acceptances(session: AsyncSession) -> int:
    if not settings.demo_mode and settings.environment != "test":
        return 0
    now = utcnow()
    campaign_leads = (
        await session.execute(
            select(CampaignLead).where(CampaignLead.status == "invited")
        )
    ).scalars().all()
    accepted = 0
    for campaign_lead in campaign_leads:
        campaign = await session.get(Campaign, campaign_lead.campaign_id)
        if not campaign:
            continue
        account = await session.get(LinkedInAccount, campaign.account_id) if campaign.account_id else None
        if not account or account.provider != "demo":
            continue
        due_raw = (campaign_lead.extra_data or {}).get("demo_accept_due")
        if not due_raw:
            continue
        try:
            due = datetime.fromisoformat(due_raw)
        except ValueError:
            continue
        if due > now:
            continue
        campaign_lead.status = "connected"
        campaign_lead.extra_data = {**(campaign_lead.extra_data or {}), "connected_at": now.isoformat()}
        lead = await session.get(Lead, campaign_lead.lead_id)
        if lead and lead.status == "contacted":
            pass
        steps = sorted(campaign.steps, key=lambda item: item.position)
        if campaign_lead.current_step < len(steps):
            step = steps[campaign_lead.current_step]
            due_at = now + timedelta(days=max(0, step.delay_days))
            await _schedule_step(session, campaign, campaign_lead, campaign_lead.current_step, due_at=due_at)
        else:
            campaign_lead.status = "completed"
        accepted += 1
    return accepted


async def process_auto_enrollment(session: AsyncSession, *, limit: int = 100) -> int:
    orgs = (await session.execute(select(Organization))).scalars().all()
    enrolled_total = 0
    for org in orgs:
        leads = (
            await session.execute(
                select(Lead)
                .where(
                    Lead.organization_id == org.id,
                    Lead.status.in_(("new", "qualified")),
                    Lead.last_signal_at.is_not(None),
                )
                .order_by(Lead.last_signal_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        for lead in leads:
            icp = await session.get(ICP, lead.icp_id) if lead.icp_id else None
            if icp is None:
                continue
            count = await enroll_on_signal(session, org, lead, icp)
            enrolled_total += count
    return enrolled_total


async def process_pending_invitations(session: AsyncSession) -> int:
    return await process_demo_acceptances(session)


async def record_inbound_reply(
    session: AsyncSession,
    *,
    account: LinkedInAccount,
    lead: Lead,
    body: str,
    sender_name: str | None = None,
    external_id: str | None = None,
    received_at: datetime | None = None,
) -> Conversation:
    conversation = await _get_or_create_conversation(
        session, account.organization_id, lead, account.id, None
    )
    now = received_at or utcnow()
    session.add(
        Message(
            conversation_id=conversation.id,
            direction="inbound",
            body=body,
            sender_name=sender_name or lead.full_name,
            sent_at=now,
            is_read=False,
            ai_generated=False,
            external_id=external_id,
        )
    )
    conversation.last_message_at = now
    conversation.last_message_preview = body[:300]
    conversation.unread_count += 1
    conversation.status = "open"
    lead.last_replied_at = now
    lead.status = "replied"
    await stop_sequence_for_reply(session, lead.id, reason="replied")
    return conversation


async def mark_connection_accepted(
    session: AsyncSession,
    *,
    account: LinkedInAccount,
    lead: Lead,
) -> bool:
    campaign_leads = (
        await session.execute(
            select(CampaignLead)
            .join(Campaign, Campaign.id == CampaignLead.campaign_id)
            .where(
                CampaignLead.lead_id == lead.id,
                CampaignLead.status == "invited",
                Campaign.account_id == account.id,
            )
        )
    ).scalars().all()
    if not campaign_leads:
        return False
    now = utcnow()
    for campaign_lead in campaign_leads:
        campaign = await session.get(Campaign, campaign_lead.campaign_id)
        if not campaign:
            continue
        if campaign.status != "active":
            continue
        campaign_lead.status = "connected"
        campaign_lead.extra_data = {**(campaign_lead.extra_data or {}), "connected_at": now.isoformat()}
        steps = sorted(campaign.steps, key=lambda item: item.position)
        if campaign_lead.current_step < len(steps):
            step = steps[campaign_lead.current_step]
            await _schedule_step(
                session,
                campaign,
                campaign_lead,
                campaign_lead.current_step,
                due_at=now + timedelta(days=max(0, step.delay_days)),
            )
    return True


async def send_manual_message(
    session: AsyncSession,
    *,
    org: Organization,
    account: LinkedInAccount,
    conversation: Conversation,
    lead: Lead,
    body: str,
    actor_id: UUID | None = None,
    ai_generated: bool = False,
) -> tuple[bool, str | None]:
    reset_daily_usage(account, org)
    _invite_limit, message_limit = effective_quotas(org, account)
    if account.messages_sent_today >= message_limit:
        raise DailyQuotaExceeded("Daily message quota reached")
    provider = provider_for_account(account)
    action_id = UUID(int=random.getrandbits(128))
    result = await provider.send_message(account, lead, body, action_id)
    if not result.success:
        return False, result.error
    now = utcnow()
    session.add(
        Message(
            conversation_id=conversation.id,
            direction="outbound",
            body=body,
            sent_at=now,
            is_read=True,
            ai_generated=ai_generated,
            external_id=result.external_id,
        )
    )
    conversation.last_message_at = now
    conversation.last_message_preview = body[:300]
    conversation.status = "waiting"
    conversation.unread_count = 0
    account.messages_sent_today += 1
    await stop_sequence_for_reply(session, lead.id, reason="human_takeover")
    if lead.status not in {"meeting", "won", "lost"}:
        lead.status = "contacted"
    return True, None


def campaign_stats(campaign_lead_rows: list[CampaignLead]) -> dict[str, Any]:
    total = len(campaign_lead_rows)
    contacted = sum(1 for row in campaign_lead_rows if row.status not in {"enrolled", "failed"})
    replied = sum(1 for row in campaign_lead_rows if row.status in {"replied", "meeting", "completed"} and row.replied_at)
    meetings = sum(1 for row in campaign_lead_rows if row.status == "meeting")
    return {
        "total_leads": total,
        "contacted": contacted,
        "replied": replied,
        "meetings": meetings,
        "reply_rate": round((replied / contacted) * 100, 1) if contacted else 0.0,
    }
