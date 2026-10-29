from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.dependencies import AuthContext, get_auth_context, get_current_user, require_admin, require_owner
from app.models import Membership, Organization, OrganizationInvite, RefreshToken, User
from app.schemas import (
    AcceptInviteRequest,
    AuthResponse,
    InviteRead,
    InviteRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MembershipRead,
    MemberRead,
    MemberUpdateRequest,
    MessageOut,
    OrganizationBrief,
    OrganizationRead,
    OrgCreateRequest,
    OrgUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UpdateMeRequest,
    UserRead,
)
from app.security import (
    decode_token,
    hash_password,
    hash_refresh_token,
    issue_token_pair,
    utcnow,
    verify_password,
)
from app.services.audit import audit
from app.utils import app_url, unique_slug

router = APIRouter(tags=["auth"])


def _membership_read(membership: Membership, organization: Organization) -> MembershipRead:
    return MembershipRead(
        id=membership.id,
        role=membership.role,
        title=membership.title,
        is_active=membership.is_active,
        organization=OrganizationBrief.model_validate(organization),
    )


async def _memberships_for_user(session: AsyncSession, user_id: UUID) -> list[tuple[Membership, Organization]]:
    rows = (
        await session.execute(
            select(Membership, Organization)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(Membership.user_id == user_id, Membership.is_active.is_(True))
            .order_by(Membership.created_at.asc())
        )
    ).all()
    return [(row[0], row[1]) for row in rows]


def _user_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


async def _auth_payload(
    session: AsyncSession,
    user: User,
    pair: TokenPair,
    memberships: list[tuple[Membership, Organization]],
) -> AuthResponse:
    return AuthResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user=_user_read(user),
        organizations=[_membership_read(m, o) for m, o in memberships],
    )


async def _unique_org_slug(session: AsyncSession, name: str) -> str:
    base = unique_slug(name)
    slug = base
    for _ in range(5):
        exists = (await session.execute(select(Organization.id).where(Organization.slug == slug))).scalar_one_or_none()
        if not exists:
            return slug
        slug = unique_slug(name)
    raise HTTPException(status_code=409, detail="Could not create a unique workspace slug")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, session: AsyncSession = Depends(get_session)):
    email = payload.email.lower().strip()
    existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists with this email")
    organization = Organization(
        name=payload.organization_name.strip(),
        slug=await _unique_org_slug(session, payload.organization_name),
        locale=payload.locale,
        timezone=payload.timezone,
        daily_invite_limit=25,
        daily_message_limit=50,
        warmup_enabled=True,
    )
    session.add(organization)
    await session.flush()
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        locale=payload.locale,
        last_login_at=utcnow(),
    )
    session.add(user)
    await session.flush()
    membership = Membership(organization_id=organization.id, user_id=user.id, role="owner", title="Fondateur")
    session.add(membership)
    await session.flush()
    pair = await issue_token_pair(session, user, request.headers.get("user-agent"))
    await audit(session, organization.id, "organization.created", actor_id=user.id, target_type="organization", target_id=organization.id)
    await session.commit()
    memberships = await _memberships_for_user(session, user.id)
    return await _auth_payload(session, user, pair, memberships)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    email = payload.email.lower().strip()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled")
    memberships = await _memberships_for_user(session, user.id)
    if not memberships:
        raise HTTPException(status_code=403, detail="No organization is attached to this account")
    user.last_login_at = utcnow()
    if payload.user_agent:
        pass
    pair = await issue_token_pair(session, user, request.headers.get("user-agent"))
    await session.commit()
    return await _auth_payload(session, user, pair, memberships)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, request: Request, session: AsyncSession = Depends(get_session)):
    token_payload = decode_token(payload.refresh_token, "refresh")
    if not token_payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    digest = hash_refresh_token(payload.refresh_token)
    stored = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == digest).limit(1).with_for_update())
    ).scalar_one_or_none()
    if stored is None or stored.revoked_at is not None or stored.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")
    try:
        user_id = UUID(str(token_payload["sub"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    if stored.user_id != user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    stored.revoked_at = utcnow()
    pair = await issue_token_pair(session, user, request.headers.get("user-agent"))
    await session.commit()
    return pair


@router.post("/logout", response_model=MessageOut)
async def logout(payload: LogoutRequest, session: AsyncSession = Depends(get_session)):
    stored = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(payload.refresh_token))
        )
    ).scalar_one_or_none()
    if stored:
        stored.revoked_at = utcnow()
        await session.commit()
    return MessageOut(message="Signed out")


@router.get("/me", response_model=MeResponse)
async def me(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    memberships = await _memberships_for_user(session, ctx.user.id)
    return MeResponse(
        user=_user_read(ctx.user),
        organizations=[_membership_read(m, o) for m, o in memberships],
        active_organization_id=ctx.org_id,
    )


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UpdateMeRequest,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    user = ctx.user
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.locale is not None:
        user.locale = payload.locale
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    await session.commit()
    return _user_read(user)


@router.get("/organizations", response_model=list[MembershipRead])
async def list_organizations(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    memberships = await _memberships_for_user(session, user.id)
    return [_membership_read(m, o) for m, o in memberships]


@router.post("/organizations", response_model=MembershipRead, status_code=201)
async def create_organization(
    payload: OrgCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    organization = Organization(
        name=payload.name.strip(),
        slug=await _unique_org_slug(session, payload.name),
        locale=payload.locale,
        timezone=payload.timezone,
    )
    session.add(organization)
    await session.flush()
    membership = Membership(organization_id=organization.id, user_id=user.id, role="owner")
    session.add(membership)
    await session.commit()
    return _membership_read(membership, organization)


@router.get("/organizations/current", response_model=OrganizationRead)
async def current_organization(ctx: AuthContext = Depends(get_auth_context)):
    return OrganizationRead.model_validate(ctx.organization)


@router.patch("/organizations/current", response_model=OrganizationRead)
async def update_organization(
    payload: OrgUpdateRequest,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    org = ctx.organization
    for field in (
        "name",
        "locale",
        "timezone",
        "daily_invite_limit",
        "daily_message_limit",
        "warmup_enabled",
        "logo_url",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(org, field, value)
    await audit(session, org.id, "organization.updated", actor_id=ctx.user.id)
    await session.commit()
    return OrganizationRead.model_validate(org)


@router.get("/organizations/members", response_model=list[MemberRead])
async def list_members(ctx: AuthContext = Depends(get_auth_context), session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.organization_id == ctx.org_id)
            .order_by(Membership.created_at.asc())
        )
    ).all()
    return [
        MemberRead(
            membership_id=m.id,
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            avatar_url=u.avatar_url,
            role=m.role,
            title=m.title,
            is_active=m.is_active and u.is_active,
            last_login_at=u.last_login_at,
            created_at=m.created_at,
        )
        for m, u in rows
    ]


@router.patch("/organizations/members/{membership_id}", response_model=MemberRead)
async def update_member(
    membership_id: UUID,
    payload: MemberUpdateRequest,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    membership = (
        await session.execute(
            select(Membership).where(Membership.id == membership_id, Membership.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if payload.role is not None:
        if ctx.membership.role != "owner":
            raise HTTPException(status_code=403, detail="Only the owner can change roles")
        if membership.role == "owner" and payload.role != "owner":
            owners = (
                await session.execute(
                    select(func.count(Membership.id)).where(
                        Membership.organization_id == ctx.org_id,
                        Membership.role == "owner",
                        Membership.is_active.is_(True),
                    )
                )
            ).scalar_one()
            if owners <= 1:
                raise HTTPException(status_code=400, detail="An organization must keep at least one owner")
        membership.role = payload.role
    if payload.title is not None:
        membership.title = payload.title
    if payload.is_active is not None:
        if membership.user_id == ctx.user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own seat")
        if membership.role == "owner" and membership.is_active and not payload.is_active:
            owners = (
                await session.execute(
                    select(func.count(Membership.id)).where(
                        Membership.organization_id == ctx.org_id,
                        Membership.role == "owner",
                        Membership.is_active.is_(True),
                    )
                )
            ).scalar_one()
            if owners <= 1:
                raise HTTPException(status_code=400, detail="An organization must keep at least one active owner")
        membership.is_active = payload.is_active
    user = await session.get(User, membership.user_id)
    await session.commit()
    return MemberRead(
        membership_id=membership.id,
        user_id=membership.user_id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=membership.role,
        title=membership.title,
        is_active=membership.is_active and user.is_active,
        last_login_at=user.last_login_at,
        created_at=membership.created_at,
    )


@router.delete("/organizations/members/{membership_id}", response_model=MessageOut)
async def remove_member(
    membership_id: UUID,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    membership = (
        await session.execute(
            select(Membership).where(Membership.id == membership_id, Membership.organization_id == ctx.org_id)
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if membership.user_id == ctx.user.id:
        raise HTTPException(status_code=400, detail="You cannot remove your own seat")
    if membership.role == "owner":
        owners = (
            await session.execute(
                select(func.count(Membership.id)).where(
                    Membership.organization_id == ctx.org_id,
                    Membership.role == "owner",
                    Membership.is_active.is_(True),
                )
            )
        ).scalar_one()
        if owners <= 1:
            raise HTTPException(status_code=400, detail="An organization must keep at least one owner")
    await session.delete(membership)
    await session.commit()
    return MessageOut(message="Member removed")


@router.get("/organizations/invites", response_model=list[InviteRead])
async def list_invites(ctx: AuthContext = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    invites = (
        await session.execute(
            select(OrganizationInvite)
            .where(OrganizationInvite.organization_id == ctx.org_id)
            .order_by(OrganizationInvite.created_at.desc())
        )
    ).scalars().all()
    return [
        InviteRead(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at,
            created_at=invite.created_at,
        )
        for invite in invites
    ]


@router.post("/organizations/invites", response_model=InviteRead, status_code=201)
async def create_invite(
    payload: InviteRequest,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    existing_member = (
        await session.execute(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(Membership.organization_id == ctx.org_id, User.email == payload.email.lower())
        )
    ).scalar_one_or_none()
    if existing_member:
        raise HTTPException(status_code=409, detail="This person is already a member")
    raw_token = secrets.token_urlsafe(32)
    invite = OrganizationInvite(
        organization_id=ctx.org_id,
        email=payload.email.lower(),
        role=payload.role,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        invited_by_id=ctx.user.id,
        expires_at=utcnow() + timedelta(days=7),
    )
    session.add(invite)
    await audit(session, ctx.org_id, "member.invited", actor_id=ctx.user.id, data={"email": payload.email})
    await session.commit()
    return InviteRead(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        accepted_at=None,
        created_at=invite.created_at,
        invite_url=app_url(f"/invite/{raw_token}"),
    )


@router.delete("/organizations/invites/{invite_id}", response_model=MessageOut)
async def revoke_invite(
    invite_id: UUID,
    ctx: AuthContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    invite = (
        await session.execute(
            select(OrganizationInvite).where(
                OrganizationInvite.id == invite_id, OrganizationInvite.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    await session.delete(invite)
    await session.commit()
    return MessageOut(message="Invite revoked")


@router.post("/accept-invite", response_model=AuthResponse)
async def accept_invite(
    payload: AcceptInviteRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invite = (
        await session.execute(
            select(OrganizationInvite).where(
                OrganizationInvite.token_hash == token_hash,
                OrganizationInvite.accepted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if invite is None or invite.expires_at < utcnow():
        raise HTTPException(status_code=400, detail="This invitation is invalid or has expired")
    user = (await session.execute(select(User).where(User.email == invite.email))).scalar_one_or_none()
    if user:
        if not payload.password or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Sign in with the invited email to accept this invitation")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="This account is disabled")
    else:
        if not payload.password or not payload.full_name:
            raise HTTPException(status_code=400, detail="Full name and password are required for a new account")
        user = User(
            email=invite.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            locale="fr",
            last_login_at=utcnow(),
        )
        session.add(user)
        await session.flush()
    membership = (
        await session.execute(
            select(Membership).where(Membership.organization_id == invite.organization_id, Membership.user_id == user.id)
        )
    ).scalar_one_or_none()
    if membership is None:
        membership = Membership(
            organization_id=invite.organization_id,
            user_id=user.id,
            role=invite.role,
        )
        session.add(membership)
    else:
        membership.is_active = True
        membership.role = invite.role
    invite.accepted_at = utcnow()
    user.last_login_at = utcnow()
    pair = await issue_token_pair(session, user, request.headers.get("user-agent"))
    await session.commit()
    memberships = await _memberships_for_user(session, user.id)
    return await _auth_payload(session, user, pair, memberships)
