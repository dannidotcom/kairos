from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.models import CampaignLead, ICP, Lead, Organization, Signal, User
from app.schemas import AuthResponse, DemoSignalResponse
from app.routers.auth import _auth_payload, _memberships_for_user
from app.security import issue_token_pair, utcnow
from app.services.signals import create_signal_for_lead
from app.utils import signal_to_read

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_SIGNALS = [
    (
        "funding",
        "Nouvelle levée de fonds",
        "{company} vient d'annoncer une levée de fonds pour accélérer son déploiement commercial.",
        0.92,
    ),
    (
        "hiring",
        "Recrutement d'une équipe revenue",
        "{company} recrute activement sur les fonctions commerciales et marketing.",
        0.78,
    ),
    (
        "job_change",
        "Prise de poste récente",
        "{name} vient de prendre un nouveau poste chez {company}.",
        0.85,
    ),
    (
        "linkedin_post",
        "Publication sur un enjeu de croissance",
        "{name} a partagé un point de vue sur les défis d'acquisition de {company}.",
        0.7,
    ),
    (
        "company_growth",
        "Expansion internationale",
        "{company} accélère son expansion et structure ses opérations.",
        0.82,
    ),
]


@router.get("/enabled")
async def demo_enabled():
    return {"enabled": settings.demo_mode}


@router.post("/login", response_model=AuthResponse)
async def demo_login(request: Request, session: AsyncSession = Depends(get_session)):
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Demo mode is disabled")
    user = (
        await session.execute(select(User).where(User.email == settings.demo_user_email.lower()))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="The demo workspace is not seeded yet")
    memberships = await _memberships_for_user(session, user.id)
    if not memberships:
        raise HTTPException(status_code=404, detail="The demo workspace is not available")
    user.last_login_at = utcnow()
    pair = await issue_token_pair(session, user, request.headers.get("user-agent"))
    await session.commit()
    return await _auth_payload(session, user, pair, memberships)


@router.post("/signal", response_model=DemoSignalResponse)
async def demo_signal(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Demo mode is disabled")
    if not ctx.organization.is_demo:
        raise HTTPException(status_code=403, detail="This endpoint is only available in the demo workspace")
    icp = (
        await session.execute(
            select(ICP)
            .where(ICP.organization_id == ctx.org_id, ICP.is_active.is_(True))
            .order_by(ICP.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    lead = (
        await session.execute(
            select(Lead)
            .where(Lead.organization_id == ctx.org_id, Lead.status.in_(("new", "qualified", "contacted")))
            .order_by(Lead.icp_score.desc(), Lead.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if lead is None or icp is None:
        raise HTTPException(status_code=400, detail="No demo lead is available")
    count = (
        await session.execute(
            select(Signal).where(Signal.organization_id == ctx.org_id, Signal.lead_id == lead.id).limit(1)
        )
    ).scalar_one_or_none()
    signal_type, title, description, strength = DEMO_SIGNALS[
        int(datetime.now().timestamp()) % len(DEMO_SIGNALS)
    ]
    signal, enrolled = await create_signal_for_lead(
        session,
        ctx.organization,
        lead,
        type=signal_type,
        title=title.format(company=lead.company or "l'entreprise", name=lead.first_name),
        description=description.format(company=lead.company or "l'entreprise", name=lead.full_name),
        source="Kairos demo feed",
        strength=strength,
        extra_data={"demo": True, "previous_signal": bool(count)},
    )
    await session.commit()
    return DemoSignalResponse(
        created=1,
        signal=signal_to_read(signal, lead=lead),
        campaign_enrolled=enrolled,
    )
