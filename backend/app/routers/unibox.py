from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import AuthContext, get_auth_context
from app.models import Conversation, Lead, LinkedInAccount, Message
from app.schemas import (
    ConversationDetail,
    ConversationListResponse,
    ConversationRead,
    ConversationUpdateRequest,
    LeadBrief,
    MessageOut,
    MessageRead,
    ReplyRequest,
    SuggestReplyResponse,
)
from app.services.campaign import DailyQuotaExceeded, send_manual_message
from app.services.llm import draft_reply

router = APIRouter(prefix="/conversations", tags=["unibox"])


async def _conversation_reads(session: AsyncSession, conversations: list[Conversation]) -> list[ConversationRead]:
    if not conversations:
        return []
    ids = [conversation.id for conversation in conversations]
    message_rows = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id.in_(ids))
            .order_by(Message.sent_at.desc())
        )
    ).scalars().all()
    last_messages: dict[UUID, Message] = {}
    for message in message_rows:
        last_messages.setdefault(message.conversation_id, message)
    return [
        ConversationRead(
            id=conversation.id,
            status=conversation.status,
            unread_count=conversation.unread_count,
            last_message_at=conversation.last_message_at,
            last_message_preview=conversation.last_message_preview,
            is_archived=conversation.is_archived,
            lead=LeadBrief.model_validate(conversation.lead),
            campaign_name=conversation.campaign.name if conversation.campaign else None,
            last_message=MessageRead.model_validate(last_messages[conversation.id])
            if conversation.id in last_messages
            else None,
        )
        for conversation in conversations
        if conversation.lead
    ]


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    conditions = [Conversation.organization_id == ctx.org_id, Conversation.is_archived.is_(archived)]
    if status_filter:
        conditions.append(Conversation.status == status_filter)
    if q:
        pattern = f"%{q.strip()}%"
        lead_ids = select(Lead.id).where(
            Lead.organization_id == ctx.org_id,
            or_(Lead.full_name.ilike(pattern), Lead.company.ilike(pattern), Lead.headline.ilike(pattern)),
        )
        conditions.append(or_(Conversation.lead_id.in_(lead_ids), Conversation.last_message_preview.ilike(pattern)))
    total = (await session.execute(select(func.count(Conversation.id)).where(*conditions))).scalar_one()
    conversations = (
        await session.execute(
            select(Conversation)
            .where(*conditions)
            .order_by(Conversation.last_message_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ConversationListResponse(
        items=await _conversation_reads(session, list(conversations)),
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    conversation = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    base = (await _conversation_reads(session, [conversation]))[0].model_dump()
    messages = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.sent_at.asc())
        )
    ).scalars().all()
    base["messages"] = [MessageRead.model_validate(message) for message in messages]
    return ConversationDetail(**base)


@router.post("/{conversation_id}/read", response_model=MessageOut)
async def mark_read(
    conversation_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    conversation = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation.unread_count = 0
    await session.execute(
        update(Message)
        .where(Message.conversation_id == conversation.id, Message.direction == "inbound")
        .values(is_read=True)
    )
    await session.commit()
    return MessageOut(message="Marked as read")


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdateRequest,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    conversation = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if payload.status is not None:
        conversation.status = payload.status
    if payload.is_archived is not None:
        conversation.is_archived = payload.is_archived
    await session.commit()
    return (await _conversation_reads(session, [conversation]))[0]


@router.post("/{conversation_id}/reply", response_model=ConversationDetail)
async def reply_to_conversation(
    conversation_id: UUID,
    payload: ReplyRequest,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    conversation = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    lead = await session.get(Lead, conversation.lead_id)
    account = await session.get(LinkedInAccount, conversation.account_id) if conversation.account_id else None
    if account is None:
        account = (
            await session.execute(
                select(LinkedInAccount)
                .where(
                    LinkedInAccount.organization_id == ctx.org_id,
                    LinkedInAccount.status.in_(("connected", "warming")),
                )
                .order_by(LinkedInAccount.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if lead is None or account is None:
        raise HTTPException(status_code=400, detail="No connected LinkedIn account is available")
    try:
        success, error = await send_manual_message(
            session,
            org=ctx.organization,
            account=account,
            conversation=conversation,
            lead=lead,
            body=payload.body.strip(),
            actor_id=ctx.user.id,
            ai_generated=payload.ai_generated,
        )
    except DailyQuotaExceeded as exc:
        await session.rollback()
        raise HTTPException(status_code=429, detail=str(exc)) from None
    if not success:
        await session.rollback()
        raise HTTPException(status_code=502, detail=error or "LinkedIn provider rejected the message")
    await session.commit()
    return await get_conversation(conversation_id, ctx, session)


@router.post("/{conversation_id}/suggest", response_model=SuggestReplyResponse)
async def suggest_reply(
    conversation_id: UUID,
    ctx: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    conversation = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.sent_at.asc())
        )
    ).scalars().all()
    inbound = [message.body for message in messages if message.direction == "inbound"]
    if not inbound:
        raise HTTPException(status_code=400, detail="This conversation has no inbound message to answer")
    lead = conversation.lead
    suggestion, generated_by = await draft_reply(
        lead=lead,
        incoming=inbound[-1],
        history=[message.body for message in messages],
        locale=ctx.organization.locale,
        org_name=ctx.organization.name,
    )
    return SuggestReplyResponse(suggestion=suggestion, generated_by=generated_by)
