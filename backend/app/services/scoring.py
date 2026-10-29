
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ICP, Lead, Signal
from app.services.llm import LLMError, score_profile_with_llm


def score_profile_with_rules(profile: dict[str, Any] | Lead | None = None, icp: dict[str, Any] | ICP | None = None) -> dict[str, Any]:
    if not profile or not icp:
        return {"score": 0, "justification": "Aucun critère vérifié disponible.", "signals_used": []}
    score = 0
    signals: list[str] = []
    profile_data = profile if isinstance(profile, dict) else getattr(profile, "__dict__", {})
    icp_data = icp if isinstance(icp, dict) else getattr(icp, "__dict__", {})
    for field_name in ("industry", "company_size", "location", "headline"):
        icp_values = icp_data.get(field_name, []) if isinstance(icp_data.get(field_name, []), list) else []
        if icp_values and profile_data.get(field_name) in icp_values:
            score += 25
            signals.append(field_name)
    score = max(0, min(100, score))
    return {
        "score": score,
        "justification": "Critères vérifiés issus du profil et de l’ICP." if score else "Aucun critère vérifié disponible.",
        "signals_used": signals,
    }


@dataclass(slots=True)
class DeterministicScore:
    score: int
    reasons: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class CombinedLeadScore:
    deterministic_score: int
    llm_score: int | None = None
    final_score: int = 0
    reason: str = ""
    signals_used: list[str] = field(default_factory=list)


async def score_lead_with_llm_and_rules(
    *,
    lead: Lead,
    icp: ICP,
    signal_list: Sequence[Signal] | None = None,
    deterministic_score: int | None = None,
    context: dict[str, Any] | None = None,
    llm_weight: float = 0.4,
) -> CombinedLeadScore:
    signal_titles = [signal.title for signal in (signal_list or []) if getattr(signal, "title", None)]
    if deterministic_score is None:
        from app.services.scoring import score_lead

        deterministic_score, _ = score_lead(lead, icp, signal=(signal_list[0] if signal_list else None))
    fallback_reason = "Score déterministe combiné à l’analyse IA."
    llm_score = None
    llm_reason = fallback_reason
    llm_signals: list[str] = []
    try:
        llm_result = await score_profile_with_llm(
            lead=lead,
            icp=icp,
            signal_titles=signal_titles,
            context=context,
        )
        llm_score = llm_result.score
        llm_reason = llm_result.justification
        llm_signals = llm_result.signals_used
    except LLMError:
        llm_score = deterministic_score
        llm_reason = fallback_reason

    final_score = int(round((1.0 - llm_weight) * deterministic_score + llm_weight * (llm_score or deterministic_score)))
    final_score = max(0, min(100, final_score))
    return CombinedLeadScore(
        deterministic_score=deterministic_score,
        llm_score=llm_score,
        final_score=final_score,
        reason=llm_reason,
        signals_used=llm_signals or signal_titles,
    )


async def rescore_lead(session: AsyncSession, lead: Lead, *, locale: str | None = None, signal: Signal | None = None) -> tuple[int, list[dict[str, Any]], Any | None]:
    icps = (
        await session.execute(
            select(ICP).where(ICP.organization_id == lead.organization_id, ICP.is_active.is_(True))
        )
    ).scalars().all()
    if lead.icp_id:
        icps = [await session.get(ICP, lead.icp_id)] + [item for item in icps if item and item.id != lead.icp_id]
    icps = [item for item in icps if item is not None]
    best_icp = None
    best_score = 0
    reasons: list[dict[str, Any]] = []
    for icp in icps:
        score, reason = score_lead(lead, icp, signal)
        if score > best_score:
            best_score = score
            best_icp = icp
            reasons = [{"key": "verified_fit", "label": "Correspondance vérifiée", "detail": reason, "points": score}]
    lead.icp_score = int(best_score)
    lead.score_reasons = reasons
    lead.icp_id = best_icp.id if best_icp else lead.icp_id
    return int(best_score), reasons, best_icp.id if best_icp else None


def score_lead(lead: Lead, icp: ICP, signal: Signal | None = None) -> tuple[int, str]:
    profile = {
        "industry": getattr(lead, "industry", None) or getattr(lead, "tags", None),
        "company_size": getattr(lead, "company_size", None),
        "location": getattr(lead, "location", None),
        "headline": getattr(lead, "headline", None),
    }
    icp_profile = {
        "industry": getattr(icp, "industries", []) or [],
        "company_size": getattr(icp, "company_sizes", []) or [],
        "location": getattr(icp, "locations", []) or [],
        "headline": getattr(icp, "titles", []) or [],
    }
    result = score_profile_with_rules(profile=profile, icp=icp_profile)
    if signal is not None:
        weight = getattr(signal, "weight", 0) or getattr(signal, "score", 0) or 0
        result["score"] = min(100, result["score"] + int(float(weight) * 20))
    return int(result["score"]), str(result["justification"])


def is_hot_lead(score: int, threshold: int = 70) -> bool:
    return score >= threshold


def build_icebreaker(lead: Lead, signal_list: Sequence[Signal] | None = None, *, max_chars: int = 300) -> str:
    signal_text = ", ".join(signal.title for signal in (signal_list or []) if getattr(signal, "title", None))
    base = f"Bonjour {lead.first_name or lead.full_name.split()[0] if lead.full_name else 'there'},"
    if lead.company:
        base += f" j’ai vu que vous travaillez chez {lead.company}."
    if lead.headline:
        base += f" Votre rôle {lead.headline} m’a interpellé."
    if signal_text:
        base += f" Les signaux récents ({signal_text[:120]}) renforcent l’intérêt."
    base += " Je pense que nous pouvons créer un vrai bénéfice mutuel."
    return base[:max_chars]


def within_send_window(account_tz: str | None, now_utc: datetime | None = None) -> bool:
    now_utc = now_utc or datetime.now(timezone.utc)
    tz = ZoneInfo(account_tz or "Europe/Paris")
    local_now = now_utc.astimezone(tz)
    return 8 <= local_now.hour <= 19


def next_action_delay(action_type: str, *, base_minutes: int = 30) -> int:
    jitter = random.randint(0, 15)
    mapping = {"invite": 60, "message": 90, "follow_up": 120}
    return max(base_minutes, mapping.get(action_type, base_minutes) + jitter)


def campaign_send_windows_for_timezone(tz_name: str | None) -> tuple[int, int]:
    tz = ZoneInfo(tz_name or "Europe/Paris")
    local_now = datetime.now(tz)
    return (8, 19) if local_now.weekday() < 5 else (9, 17)


@dataclass(slots=True)
class CampaignActionPlan:
    step_name: str
    due_at: datetime
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CampaignLaunchPlan:
    campaigns: list[str] = field(default_factory=list)
    next_actions: list[CampaignActionPlan] = field(default_factory=list)
    requires_manual_approval: bool = False


def build_campaign_sequence(
    *,
    campaign_name: str,
    lead: Lead,
    signal_list: Sequence[Signal] | None = None,
    now: datetime | None = None,
    timezone_name: str | None = None,
) -> CampaignLaunchPlan:
    now = now or datetime.now(timezone.utc)
    steps = [
        ("invite", "invitation"),
        ("message", "message"),
        ("follow_up", "follow_up"),
    ]
    actions: list[CampaignActionPlan] = []
    icebreaker = build_icebreaker(lead, signal_list)
    for idx, (step_name, action_type) in enumerate(steps, start=1):
        delay = timedelta(minutes=next_action_delay(action_type)) * idx
        due_at = now + delay
        actions.append(
            CampaignActionPlan(
                step_name=step_name,
                due_at=due_at,
                action_type=action_type,
                payload={
                    "lead_id": str(lead.id),
                    "icebreaker": icebreaker,
                    "campaign_name": campaign_name,
                    "timezone": timezone_name or "Europe/Paris",
                },
            )
        )
    return CampaignLaunchPlan(campaigns=[campaign_name], next_actions=actions, requires_manual_approval=False)


def require_manual_approval_for_campaign(campaign_name: str, *, enabled: bool = False) -> bool:
    return enabled


def mark_campaign_paused(campaign_state: dict[str, Any], value: bool) -> dict[str, Any]:
    campaign_state["paused"] = value
    campaign_state["updated_at"] = datetime.now(timezone.utc)
    return campaign_state


def mark_campaign_archived(campaign_state: dict[str, Any]) -> dict[str, Any]:
    campaign_state["archived"] = True
    campaign_state["paused"] = True
    return campaign_state


def lock_contact_for_week(org_id: str, prospect_id: str, seat_id: str, week_key: str, locks: dict[str, set[str]]) -> bool:
    key = f"{org_id}:{week_key}"
    locked = locks.setdefault(key, set())
    contact_key = f"{seat_id}:{prospect_id}"
    if contact_key in locked:
        return False
    locked.add(contact_key)
    return True


def can_send_action(account: Any, action_type: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if not hasattr(account, "status"):
        return True
    if getattr(account, "status", None) not in {"connected", "warming"}:
        return False
    if not within_send_window(getattr(account, "timezone", None), now):
        return False
    return True


__all__ = [
    "DeterministicScore",
    "CombinedLeadScore",
    "score_lead_with_llm_and_rules",
    "is_hot_lead",
    "build_icebreaker",
    "within_send_window",
    "next_action_delay",
    "campaign_send_windows_for_timezone",
    "CampaignActionPlan",
    "CampaignLaunchPlan",
    "build_campaign_sequence",
    "require_manual_approval_for_campaign",
    "mark_campaign_paused",
    "mark_campaign_archived",
    "lock_contact_for_week",
    "can_send_action",
]
