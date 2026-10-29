from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ICP, Lead, Organization, Signal
from app.security import utcnow
from app.services.campaign import enroll_on_signal
from app.services.scoring import rescore_lead


async def create_signal_for_lead(
    session: AsyncSession,
    org: Organization,
    lead: Lead,
    *,
    type: str,
    title: str,
    description: str | None = None,
    source_url: str | None = None,
    source: str = "manual",
    strength: float = 0.7,
    detected_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> tuple[Signal, int]:
    signal = Signal(
        organization_id=org.id,
        lead_id=lead.id,
        type=type,
        title=title,
        description=description,
        source_url=source_url,
        source=source,
        strength=max(0.0, min(1.0, strength)),
        detected_at=detected_at or utcnow(),
        extra_data=extra_data or {},
    )
    session.add(signal)
    await session.flush()
    signal = await session.get(Signal, signal.id)
    assert signal is not None
    lead.last_signal_at = signal.detected_at
    score, _reasons, icp_id = await rescore_lead(session, lead, locale=org.locale, signal=signal)
    icp = await session.get(ICP, icp_id) if icp_id else None
    if lead.status == "new":
        lead.status = "qualified"
    enrolled = 0
    if icp and score >= icp.min_score:
        enrolled = await enroll_on_signal(session, org, lead, icp, signal=signal)
    return signal, enrolled
