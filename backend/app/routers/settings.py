from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import AuthContext, get_auth_context, require_admin
from app.models import ApiKey, AuditEvent
from app.schemas import ApiKeyCreateRequest, ApiKeyCreated, ApiKeyRead, AuditEventRead, MessageOut
from app.security import generate_api_key
from app.services.audit import audit

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(ApiKey).where(ApiKey.organization_id == ctx.org_id).order_by(ApiKey.created_at.desc())
        )
    ).scalars().all()
    return [ApiKeyRead.model_validate(row) for row in rows]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    raw, prefix, digest = generate_api_key()
    api_key = ApiKey(
        organization_id=ctx.org_id,
        name=payload.name.strip(),
        key_prefix=prefix,
        key_hash=digest,
        created_by_id=ctx.user.id,
    )
    session.add(api_key)
    await session.flush()
    await audit(
        session, ctx.org_id, "api_key.created", actor_id=ctx.user.id, target_type="api_key", target_id=api_key.id
    )
    await session.commit()
    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        last_used_at=None,
        revoked_at=None,
        created_at=api_key.created_at,
        key=raw,
    )


@router.delete("/api-keys/{key_id}", response_model=MessageOut)
async def revoke_api_key(
    key_id: UUID,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    api_key = (
        await session.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    from app.security import utcnow

    api_key.revoked_at = utcnow()
    await audit(
        session, ctx.org_id, "api_key.revoked", actor_id=ctx.user.id, target_type="api_key", target_id=api_key.id
    )
    await session.commit()
    return MessageOut(message="API key revoked")


@router.get("/audit", response_model=list[AuditEventRead])
async def audit_log(
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
):
    rows = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.organization_id == ctx.org_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(min(max(limit, 1), 200))
        )
    ).scalars().all()
    return [AuditEventRead.model_validate(row) for row in rows]
