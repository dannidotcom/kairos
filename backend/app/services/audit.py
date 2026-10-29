from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


async def audit(
    session: AsyncSession,
    organization_id: UUID,
    action: str,
    *,
    actor_type: str = "user",
    actor_id: str | UUID | None = None,
    target_type: str | None = None,
    target_id: str | UUID | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_type=actor_type,
            actor_id=str(actor_id) if actor_id else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            extra_data=data or {},
        )
    )
