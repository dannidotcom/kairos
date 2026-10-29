
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import ICP, Lead, Signal


@dataclass(slots=True)
class LeadScoreDecision:
    deterministic_score: int
    llm_score: int | None = None
    final_score: int = 0
    threshold: int = 70
    is_hot: bool = False
    justification: str = ""
    signals_used: list[str] = field(default_factory=list)


async def score_lead_with_threshold(
    *,
    lead: Lead,
    icp: ICP,
    signal: Signal | None = None,
    threshold: int = 70,
    locale: str = "fr",
    context: dict[str, Any] | None = None,
) -> LeadScoreDecision:
    from app.services.scoring import score_lead
    from app.services.llm import score_profile_with_llm

    deterministic_score, _ = score_lead(lead, icp, signal=signal, locale=locale)
    try:
        llm_result = await score_profile_with_llm(
            lead=lead,
            icp=icp,
            signal_titles=[signal.title for signal in [signal] if signal and getattr(signal, "title", None)],
            context=context or {},
        )
        llm_score = llm_result.score
        justification = llm_result.justification
        signals_used = llm_result.signals_used
    except Exception:
        llm_score = deterministic_score
        justification = "Score déterministe conservateur appliqué en raison d’un refus IA."
        signals_used = []

    final_score = int(round((deterministic_score * 0.6) + (llm_score * 0.4)))
    final_score = max(0, min(100, final_score))
    decision = LeadScoreDecision(
        deterministic_score=deterministic_score,
        llm_score=llm_score,
        final_score=final_score,
        threshold=threshold,
        is_hot=final_score >= threshold,
        justification=justification,
        signals_used=signals_used,
    )
    return decision


__all__ = ["LeadScoreDecision", "score_lead_with_threshold"]
