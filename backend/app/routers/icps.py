from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.models import Campaign, ICP, Lead
from app.schemas import (
    ICPCreate,
    ICPGenerateRequest,
    ICPRead,
    ICPSuggestion,
    ICPUpdate,
    LeadScoreRead,
    MessageOut,
)
from app.services.audit import audit
from app.services.llm import generate_icp
from app.services.scoring import rescore_lead

router = APIRouter(prefix="/icps", tags=["icps"])


async def _icp_for_org(session: AsyncSession, org_id: UUID, icp_id: UUID) -> ICP:
    icp = (
        await session.execute(select(ICP).where(ICP.id == icp_id, ICP.organization_id == org_id))
    ).scalar_one_or_none()
    if icp is None:
        raise HTTPException(status_code=404, detail="ICP not found")
    return icp


@router.get("", response_model=list[ICPRead])
async def list_icps(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    icps = (
        await session.execute(
            select(ICP).where(ICP.organization_id == ctx.org_id).order_by(ICP.created_at.desc())
        )
    ).scalars().all()
    return [ICPRead.model_validate(icp) for icp in icps]


@router.post("", response_model=ICPRead, status_code=status.HTTP_201_CREATED)
async def create_icp(
    payload: ICPCreate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    icp = ICP(organization_id=ctx.org_id, **payload.model_dump(), generated_by="manual")
    session.add(icp)
    await session.flush()
    await audit(session, ctx.org_id, "icp.created", actor_id=ctx.user.id, target_type="icp", target_id=icp.id)
    await session.commit()
    return ICPRead.model_validate(icp)


@router.post("/generate", response_model=ICPSuggestion)
async def generate_icp_suggestion(
    payload: ICPGenerateRequest,
    ctx: AuthContext = Depends(get_auth_context),
):
    suggestion = await generate_icp(payload.description, payload.value_prop, payload.locale)
    if not suggestion.auto_launch:
        suggestion.auto_launch = False
    return suggestion


@router.get("/{icp_id}", response_model=ICPRead)
async def get_icp(
    icp_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    return ICPRead.model_validate(await _icp_for_org(session, ctx.org_id, icp_id))


@router.patch("/{icp_id}", response_model=ICPRead)
async def update_icp(
    icp_id: UUID,
    payload: ICPUpdate,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    icp = await _icp_for_org(session, ctx.org_id, icp_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(icp, field, value)
    await audit(session, ctx.org_id, "icp.updated", actor_id=ctx.user.id, target_type="icp", target_id=icp.id)
    await session.commit()
    return ICPRead.model_validate(icp)


@router.delete("/{icp_id}", response_model=MessageOut)
async def delete_icp(
    icp_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    icp = await _icp_for_org(session, ctx.org_id, icp_id)
    campaigns = (
        await session.execute(select(Campaign.id).where(Campaign.icp_id == icp.id).limit(1))
    ).scalar_one_or_none()
    if campaigns:
        raise HTTPException(status_code=409, detail="Archive campaigns linked to this ICP before deleting it")
    await session.delete(icp)
    await session.commit()
    return MessageOut(message="ICP deleted")


@router.post("/{icp_id}/rescore", response_model=list[LeadScoreRead])
async def rescore_icp_leads(
    icp_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    await _icp_for_org(session, ctx.org_id, icp_id)
    leads = (
        await session.execute(select(Lead).where(Lead.organization_id == ctx.org_id).limit(500))
    ).scalars().all()
    results: list[LeadScoreRead] = []
    for lead in leads:
        score, reasons, best_icp = await rescore_lead(session, lead, locale=ctx.organization.locale)
        results.append(LeadScoreRead(score=score, reasons=reasons, icp_id=best_icp))
    await session.commit()
    return results
