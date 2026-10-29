from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.models import LinkedInAccount, Lead


@dataclass(slots=True)
class ProviderResult:
    success: bool
    external_id: str | None = None
    error: str | None = None


class LinkedInProvider:
    name = "base"

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        raise NotImplementedError

    async def send_message(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        raise NotImplementedError


class DemoLinkedInProvider(LinkedInProvider):
    name = "demo"

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return ProviderResult(success=True, external_id=f"demo_invite_{action_id.hex[:16]}")

    async def send_message(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return ProviderResult(success=True, external_id=f"demo_message_{action_id.hex[:16]}")


class ConnectorLinkedInProvider(LinkedInProvider):
    """Talks to a customer-hosted LinkedIn connector, never to LinkedIn directly.

    The connector owns the authenticated browser session and is responsible for
    respecting LinkedIn's terms of service and local law. Kairos stores no cookie.
    """

    name = "connector"

    def __init__(self) -> None:
        self.base_url = settings.linkedin_connector_url.rstrip("/")

    async def _post(self, action_type: str, account, lead, message, action_id) -> ProviderResult:
        if not self.base_url:
            return ProviderResult(success=False, error="LINKEDIN_CONNECTOR_URL is not configured")
        payload: dict[str, Any] = {
            "action_id": str(action_id),
            "action_type": action_type,
            "account_id": account.provider_account_id,
            "profile_url": lead.linkedin_url,
            "message": message,
        }
        headers = {
            "Authorization": f"Bearer {settings.linkedin_connector_token}",
            "Idempotency-Key": str(action_id),
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/actions", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return ProviderResult(success=False, error=f"Connector unavailable: {exc}")
        if response.status_code >= 400:
            return ProviderResult(
                success=False,
                error=f"Connector returned {response.status_code}: {response.text[:250]}",
            )
        try:
            data = response.json()
        except ValueError:
            data = {}
        return ProviderResult(success=True, external_id=data.get("external_id") or action_id.hex)

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return await self._post("connection_request", account, lead, message, action_id)

    async def send_message(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return await self._post("message", account, lead, message, action_id)


def provider_for_account(account: LinkedInAccount) -> LinkedInProvider:
    if account.provider == "demo":
        return DemoLinkedInProvider()
    if account.provider == "connector":
        return ConnectorLinkedInProvider()
    return DemoLinkedInProvider()
