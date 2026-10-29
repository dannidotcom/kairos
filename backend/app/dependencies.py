from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import ApiKey, Membership, Organization, User
from app.security import decode_token, hash_api_key
from app.utils import require_role

bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthContext:
    user: User
    organization: Organization
    membership: Membership

    @property
    def org_id(self) -> UUID:
        return self.organization.id

    def require_role(self, *roles: str) -> None:
        require_role(self.membership.role, set(roles))


@dataclass(slots=True)
class ApiKeyContext:
    organization: Organization
    api_key: ApiKey

    @property
    def org_id(self) -> UUID:
        return self.organization.id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid access token") from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def get_auth_context(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    org_header = request.headers.get("x-organization-id")
    query = select(Membership).where(
        Membership.user_id == user.id,
        Membership.is_active.is_(True),
    )
    if org_header:
        try:
            org_id = UUID(org_header)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization header") from None
        query = query.where(Membership.organization_id == org_id)
    else:
        query = query.order_by(Membership.created_at.asc())
    membership = (await session.execute(query.limit(1))).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="No active organization for this account")
    organization = await session.get(Organization, membership.organization_id)
    if organization is None:
        raise HTTPException(status_code=403, detail="Organization not found")
    return AuthContext(user=user, organization=organization, membership=membership)


async def get_org_context(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return ctx


async def require_owner(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    ctx.require_role("owner")
    return ctx


async def require_admin(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    ctx.require_role("owner", "admin")
    return ctx


async def get_api_key_context(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyContext:
    if not x_api_key or not x_api_key.startswith("kairos_mcp_"):
        raise HTTPException(status_code=401, detail="A valid Kairos MCP API key is required")
    digest = hash_api_key(x_api_key)
    api_key = (
        await session.execute(
            select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.revoked_at.is_(None)).limit(1)
        )
    ).scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    organization = await session.get(Organization, api_key.organization_id)
    if organization is None:
        raise HTTPException(status_code=401, detail="API key organization not found")
    await session.execute(
        update(ApiKey).where(ApiKey.id == api_key.id).values(last_used_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return ApiKeyContext(organization=organization, api_key=api_key)
