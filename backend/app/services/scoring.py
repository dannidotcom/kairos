from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ICP, Lead, Signal

TITLE_POINTS = 28
INDUSTRY_POINTS = 15
KEYWORD_POINTS = 17
LOCATION_POINTS = 10
SIZE_POINTS = 10
SENIORITY_POINTS = 10
SIGNAL_POINTS = 10

SENIORITY_TERMS = {
    "c-level": ["ceo", "cto", "cfo", "cmo", "coo", "cro", "chief", "founder", "président", "directeur général"],
    "vp": ["vp", "vice president", "vice-président"],
    "head": ["head of", "head ", "responsable"],
    "director": ["director", "directeur", "directrice"],
    "manager": ["manager", "responsable"],
    "founder": ["founder", "co-founder", "cofondateur", "fondateur"],
}


def _contains_any(haystack: str, needles: list[str] | None) -> tuple[bool, str | None]:
    if not haystack or not needles:
        return False, None
    for needle in needles:
        cleaned = str(needle).strip().lower()
        if cleaned and cleaned in haystack:
            return True, needle
    return False, None


def _parse_range(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    numbers = re.findall(r"\d+", value.replace(" ", ""))
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    if len(numbers) == 1:
        return int(numbers[0]), int(numbers[0])
    labels = {
        "startup": (1, 50),
        "scale-up": (51, 500),
        "scaleup": (51, 500),
        "pme": (11, 250),
        "sme": (11, 250),
        "eti": (250, 5000),
        "enterprise": (1000, 100000),
        "grand groupe": (1000, 100000),
    }
    lower = value.lower()
    for label, bounds in labels.items():
        if label in lower:
            return bounds
    return None


def _size_matches(icp_sizes: list[str] | None, lead_size: str | None) -> bool:
    if not icp_sizes:
        return False
    lead_range = _parse_range(lead_size)
    if lead_range is None:
        return False
    for size in icp_sizes:
        target = _parse_range(size)
        if target and not (lead_range[1] < target[0] or lead_range[0] > target[1]):
            return True
        if size.lower() in (lead_size or "").lower():
            return True
    return False


def _seniority_matches(icp_seniorities: list[str] | None, headline: str) -> str | None:
    if not icp_seniorities:
        return None
    for seniority in icp_seniorities:
        terms = SENIORITY_TERMS.get(seniority.strip().lower(), [seniority.lower()])
        if any(term in headline for term in terms):
            return seniority
    return None


def score_lead(lead: Lead, icp: ICP, signal: Signal | None = None, locale: str = "fr") -> tuple[int, list[dict[str, Any]]]:
    reasons: list[dict[str, Any]] = []
    score = 0
    headline = (lead.headline or "").lower()
    company = (lead.company or "").lower()
    industry = (lead.industry or "").lower()
    location = (lead.location or "").lower()
    profile_text = " ".join(
        [
            lead.headline or "",
            lead.about or "",
            lead.company or "",
            lead.industry or "",
            " ".join(lead.tags or []),
        ]
    ).lower()

    title_hit, title_value = _contains_any(headline, icp.titles)
    if title_hit:
        score += TITLE_POINTS
        reasons.append(
            {
                "key": "title",
                "label": "Fonction cible" if locale == "fr" else "Target role",
                "detail": title_value,
                "points": TITLE_POINTS,
            }
        )

    industry_hit, industry_value = _contains_any(f"{industry} {company}", icp.industries)
    if industry_hit:
        score += INDUSTRY_POINTS
        reasons.append(
            {
                "key": "industry",
                "label": "Secteur aligné" if locale == "fr" else "Industry match",
                "detail": industry_value,
                "points": INDUSTRY_POINTS,
            }
        )

    matched_keywords: list[str] = []
    for keyword in icp.keywords or []:
        if str(keyword).lower() in profile_text:
            matched_keywords.append(keyword)
    if matched_keywords:
        points = min(KEYWORD_POINTS, 4 + (len(matched_keywords) - 1) * 4)
        score += points
        reasons.append(
            {
                "key": "keywords",
                "label": "Mots-clés présents" if locale == "fr" else "Keywords found",
                "detail": ", ".join(matched_keywords[:3]),
                "points": points,
            }
        )

    location_hit, location_value = _contains_any(location, icp.locations)
    if location_hit:
        score += LOCATION_POINTS
        reasons.append(
            {
                "key": "location",
                "label": "Zone géographique" if locale == "fr" else "Location",
                "detail": location_value,
                "points": LOCATION_POINTS,
            }
        )

    if _size_matches(icp.company_sizes, lead.company_size):
        score += SIZE_POINTS
        reasons.append(
            {
                "key": "company_size",
                "label": "Taille d'entreprise" if locale == "fr" else "Company size",
                "detail": lead.company_size,
                "points": SIZE_POINTS,
            }
        )

    seniority_hit = _seniority_matches(icp.seniorities, headline)
    if seniority_hit:
        score += SENIORITY_POINTS
        reasons.append(
            {
                "key": "seniority",
                "label": "Niveau de décision" if locale == "fr" else "Seniority",
                "detail": seniority_hit,
                "points": SENIORITY_POINTS,
            }
        )

    if signal and signal.strength > 0:
        points = max(2, round(SIGNAL_POINTS * float(signal.strength)))
        score += points
        reasons.append(
            {
                "key": "signal",
                "label": "Signal d'achat" if locale == "fr" else "Buying signal",
                "detail": signal.title,
                "points": points,
            }
        )

    return max(0, min(100, score)), sorted(reasons, key=lambda item: item["points"], reverse=True)


async def rescore_lead(
    session: AsyncSession,
    lead: Lead,
    locale: str = "fr",
    signal: Signal | None = None,
    *,
    commit: bool = False,
) -> tuple[int, list[dict[str, Any]], UUID | None]:
    icps = (
        await session.execute(select(ICP).where(ICP.organization_id == lead.organization_id, ICP.is_active.is_(True)))
    ).scalars().all()
    if not icps:
        lead.icp_score = 0
        lead.score_reasons = []
        if commit:
            await session.commit()
        return 0, [], None
    if signal is None:
        signal = (
            await session.execute(
                select(Signal)
                .where(Signal.lead_id == lead.id)
                .order_by(Signal.detected_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    best_score = -1
    best_reasons: list[dict[str, Any]] = []
    best_icp_id: UUID | None = None
    for icp in icps:
        score, reasons = score_lead(lead, icp, signal, locale=locale)
        if score > best_score:
            best_score = score
            best_reasons = reasons
            best_icp_id = icp.id
    lead.icp_score = max(0, best_score)
    lead.score_reasons = best_reasons
    lead.icp_id = best_icp_id
    if signal is not None:
        lead.last_signal_at = signal.detected_at
    if commit:
        await session.commit()
    return lead.icp_score, lead.score_reasons, lead.icp_id


async def icp_match_for_lead(session: AsyncSession, lead: Lead) -> ICP | None:
    if lead.icp_id:
        return await session.get(ICP, lead.icp_id)
    return (
        await session.execute(
            select(ICP)
            .where(ICP.organization_id == lead.organization_id, ICP.is_active.is_(True))
            .order_by(ICP.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
