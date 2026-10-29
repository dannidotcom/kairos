from __future__ import annotations

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx

from app.config import settings
from app.models import LinkedInAccount, Lead

logger = logging.getLogger("kairos.linkedin")


@dataclass(slots=True)
class ProviderResult:
    success: bool
    external_id: str | None = None
    error: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class LinkedInProvider(ABC):
    """Abstract provider contract for LinkedIn operations."""

    name = "base"

    @abstractmethod
    async def connect_account(self, user: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def search_profiles(self, account_id: str, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_profile(self, account_id: str, profile_ref: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def send_invitation(self, account_id: str, profile_ref: str, note: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, account_id: str, chat_ref_or_profile_ref: str, text: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def list_chats(self, account_id: str, cursor: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def list_messages(self, account_id: str, chat_ref: str, cursor: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_profile_posts(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_profile_reactions(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return ProviderResult(success=False, error="Legacy send_connection_request is not implemented for this provider")

    async def send_message_legacy(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return ProviderResult(success=False, error="Legacy send_message_legacy is not implemented for this provider")


class DemoLinkedInProvider(LinkedInProvider):
    name = "demo"

    async def connect_account(self, user: Any) -> dict[str, Any]:
        user_id = str(getattr(user, "id", user.get("id", "demo-user")) if hasattr(user, "get") else user)
        account_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"demo-linkedin:{user_id}"))
        return {
            "account_id": account_id,
            "status": "connected",
            "provider": "demo",
            "mode": "demo",
            "connected": True,
            "metadata": {"demo": True},
        }

    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        return {"account_id": account_id, "status": "connected", "provider": "demo"}

    async def search_profiles(self, account_id: str, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        filters = filters or {}
        keyword = str(filters.get("keyword") or "").strip()
        profiles = [
            {
                "ref": "demo-profile-1",
                "full_name": "Ariana Dubois",
                "headline": "VP Growth",
                "company": "Northstar Labs",
                "location": "Paris, France",
            },
            {
                "ref": "demo-profile-2",
                "full_name": "Lucas Martin",
                "headline": "Head of Sales",
                "company": "Signal Forge",
                "location": "Lyon, France",
            },
        ]
        if keyword:
            profiles = [p for p in profiles if keyword.lower() in (p["full_name"] + " " + p["company"]).lower()]
        return {"items": profiles, "cursor": None, "total": len(profiles)}

    async def get_profile(self, account_id: str, profile_ref: str) -> dict[str, Any]:
        return {
            "ref": profile_ref,
            "full_name": "Demo Profile",
            "headline": "Building customer momentum",
            "company": "Demo Company",
            "location": "France",
            "url": f"https://linkedin.com/in/{profile_ref}",
            "raw": {"profile_ref": profile_ref},
        }

    async def send_invitation(self, account_id: str, profile_ref: str, note: str | None = None) -> dict[str, Any]:
        return {
            "account_id": account_id,
            "profile_ref": profile_ref,
            "status": "sent",
            "invitation_id": f"demo_invite_{profile_ref}",
            "note": note,
        }

    async def send_message(self, account_id: str, chat_ref_or_profile_ref: str, text: str) -> dict[str, Any]:
        return {
            "account_id": account_id,
            "chat_ref": chat_ref_or_profile_ref,
            "status": "sent",
            "message_id": f"demo_message_{uuid.uuid5(uuid.NAMESPACE_URL, f'{account_id}:{chat_ref_or_profile_ref}:{text}')}",
            "text": text,
        }

    async def list_chats(self, account_id: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": None}

    async def list_messages(self, account_id: str, chat_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": None, "chat_ref": chat_ref}

    async def get_profile_posts(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": None, "profile_ref": profile_ref}

    async def get_profile_reactions(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": None, "profile_ref": profile_ref}

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return ProviderResult(success=True, external_id=f"demo_invite_{action_id.hex[:16]}")

    async def send_message_legacy(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return ProviderResult(success=True, external_id=f"demo_message_{action_id.hex[:16]}")


class UnipileProvider(LinkedInProvider):
    name = "unipile"

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        raw_base = (base_url or settings.unipile_base_url or settings.unipile_dsn or "").rstrip("/")
        self.base_url = raw_base
        self.api_key = api_key or settings.unipile_api_key
        self.timeout = float(settings.unipile_timeout_seconds or 20.0)
        self.max_retries = max(1, int(settings.unipile_max_retries or 5))
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def _request(self, method: str, path: str, *, params: Mapping[str, Any] | None = None, json_body: Any = None) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("UNIPILE_BASE_URL/UNIPILE_DSN is not configured")
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, params=params, json=json_body, headers=self.headers)
                if response.status_code == 429:
                    wait = min(2 ** attempt, 30)
                    logger.warning("Unipile rate limited on %s %s, retry in %s sec (attempt %s/%s)", method, path, wait, attempt, self.max_retries)
                    if attempt == self.max_retries:
                        raise httpx.HTTPStatusError(f"Unipile rate limit exceeded: {response.text[:250]}", request=response.request, response=response)
                    await asyncio.sleep(wait)
                    continue
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"Unipile error {response.status_code}: {response.text[:250]}",
                        request=response.request,
                        response=response,
                    )
                try:
                    return response.json()
                except ValueError:
                    return {"ok": True, "raw": response.text}
            except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(min(2 ** attempt, 30))
        if last_error is not None:
            raise last_error
        return {}

    async def connect_account(self, user: Any) -> dict[str, Any]:
        payload = {
            "user": getattr(user, "email", None) or user.get("email") if isinstance(user, Mapping) else str(user),
            "mode": "hosted",
            "provider": "linkedin",
        }
        return await self._request("POST", "/accounts/connect", json_body=payload)

    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/accounts/{account_id}")

    async def search_profiles(self, account_id: str, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", f"/accounts/{account_id}/profiles", params=dict(filters or {}))

    async def get_profile(self, account_id: str, profile_ref: str) -> dict[str, Any]:
        return await self._request("GET", f"/accounts/{account_id}/profiles/{profile_ref}")

    async def send_invitation(self, account_id: str, profile_ref: str, note: str | None = None) -> dict[str, Any]:
        payload = {"profile_ref": profile_ref, "note": note}
        return await self._request("POST", f"/accounts/{account_id}/invitations", json_body=payload)

    async def send_message(self, account_id: str, chat_ref_or_profile_ref: str, text: str) -> dict[str, Any]:
        payload = {"chat_ref_or_profile_ref": chat_ref_or_profile_ref, "text": text}
        return await self._request("POST", f"/accounts/{account_id}/messages", json_body=payload)

    async def list_chats(self, account_id: str, cursor: str | None = None) -> dict[str, Any]:
        params = {"cursor": cursor} if cursor else {}
        return await self._request("GET", f"/accounts/{account_id}/chats", params=params)

    async def list_messages(self, account_id: str, chat_ref: str, cursor: str | None = None) -> dict[str, Any]:
        params = {"cursor": cursor} if cursor else {}
        return await self._request("GET", f"/accounts/{account_id}/chats/{chat_ref}/messages", params=params)

    async def get_profile_posts(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        params = {"cursor": cursor} if cursor else {}
        return await self._request("GET", f"/accounts/{account_id}/profiles/{profile_ref}/posts", params=params)

    async def get_profile_reactions(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        params = {"cursor": cursor} if cursor else {}
        return await self._request("GET", f"/accounts/{account_id}/profiles/{profile_ref}/reactions", params=params)

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        try:
            payload = {
                "account_id": str(account.provider_account_id or account.id),
                "profile_ref": str(lead.linkedin_urn or lead.linkedin_url),
                "note": message,
            }
            data = await self._request("POST", "/actions/invitations", json_body=payload)
            return ProviderResult(success=True, external_id=str(data.get("id") or data.get("invitation_id") or action_id), payload=data)
        except Exception as exc:  # pragma: no cover - boundary protection
            logger.exception("LinkedIn invitation failed via Unipile")
            return ProviderResult(success=False, error=str(exc))

    async def send_message_legacy(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        try:
            payload = {
                "account_id": str(account.provider_account_id or account.id),
                "profile_ref": str(lead.linkedin_urn or lead.linkedin_url),
                "text": message,
            }
            data = await self._request("POST", "/actions/messages", json_body=payload)
            return ProviderResult(success=True, external_id=str(data.get("id") or data.get("message_id") or action_id), payload=data)
        except Exception as exc:  # pragma: no cover - boundary protection
            logger.exception("LinkedIn message failed via Unipile")
            return ProviderResult(success=False, error=str(exc))


class MockProvider(LinkedInProvider):
    """Deterministic in-memory provider used for local dev and tests."""

    _profiles: dict[str, dict[str, Any]] = {
        "demo-profile-1": {
            "ref": "demo-profile-1",
            "full_name": "Ariana Dubois",
            "headline": "VP Growth",
            "company": "Northstar Labs",
            "location": "Paris, France",
            "url": "https://www.linkedin.com/in/demo-profile-1",
        },
        "demo-profile-2": {
            "ref": "demo-profile-2",
            "full_name": "Lucas Martin",
            "headline": "Head of Sales",
            "company": "Signal Forge",
            "location": "Lyon, France",
            "url": "https://www.linkedin.com/in/demo-profile-2",
        },
    }

    async def connect_account(self, user: Any) -> dict[str, Any]:
        user_id = str(user.get("id") if isinstance(user, Mapping) else getattr(user, "id", "mock-user"))
        account_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"mock:linkedin:{user_id}"))
        return {"account_id": account_id, "status": "connected", "provider": "mock", "connected": True}

    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        return {"account_id": account_id, "status": "connected", "provider": "mock"}

    async def search_profiles(self, account_id: str, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        items = list(self._profiles.values())
        if filters:
            keyword = str(filters.get("keyword") or "").lower()
            if keyword:
                items = [item for item in items if keyword in (item["full_name"] + " " + item["company"]).lower()]
        return {"items": items, "cursor": None, "total": len(items)}

    async def get_profile(self, account_id: str, profile_ref: str) -> dict[str, Any]:
        return dict(self._profiles.get(profile_ref, {"ref": profile_ref, "full_name": "Mock profile"}))

    async def send_invitation(self, account_id: str, profile_ref: str, note: str | None = None) -> dict[str, Any]:
        return {"account_id": account_id, "profile_ref": profile_ref, "status": "sent", "note": note, "invitation_id": f"mock-invite-{profile_ref}"}

    async def send_message(self, account_id: str, chat_ref_or_profile_ref: str, text: str) -> dict[str, Any]:
        return {"account_id": account_id, "chat_ref": chat_ref_or_profile_ref, "status": "sent", "message_id": f"mock-msg-{chat_ref_or_profile_ref}", "text": text}

    async def list_chats(self, account_id: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": None}

    async def list_messages(self, account_id: str, chat_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor, "chat_ref": chat_ref}

    async def get_profile_posts(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor, "profile_ref": profile_ref}

    async def get_profile_reactions(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor, "profile_ref": profile_ref}


class ConnectorLinkedInProvider(LinkedInProvider):
    """Talks to a customer-hosted LinkedIn connector, never to LinkedIn directly."""

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
        return ProviderResult(success=True, external_id=data.get("external_id") or action_id.hex, payload=data)

    async def connect_account(self, user: Any) -> dict[str, Any]:
        return {"status": "pending", "provider": "connector", "user": str(user)}

    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        return {"account_id": account_id, "status": "connected", "provider": "connector"}

    async def search_profiles(self, account_id: str, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": None, "total": 0}

    async def get_profile(self, account_id: str, profile_ref: str) -> dict[str, Any]:
        return {"ref": profile_ref, "account_id": account_id}

    async def send_invitation(self, account_id: str, profile_ref: str, note: str | None = None) -> dict[str, Any]:
        return {"account_id": account_id, "profile_ref": profile_ref, "status": "sent", "note": note}

    async def send_message(self, account_id: str, chat_ref_or_profile_ref: str, text: str) -> dict[str, Any]:
        return {"account_id": account_id, "chat_ref": chat_ref_or_profile_ref, "status": "sent", "text": text}

    async def list_chats(self, account_id: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor}

    async def list_messages(self, account_id: str, chat_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor, "chat_ref": chat_ref}

    async def get_profile_posts(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor, "profile_ref": profile_ref}

    async def get_profile_reactions(self, account_id: str, profile_ref: str, cursor: str | None = None) -> dict[str, Any]:
        return {"items": [], "cursor": cursor, "profile_ref": profile_ref}

    async def send_connection_request(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return await self._post("connection_request", account, lead, message, action_id)

    async def send_message_legacy(
        self, account: LinkedInAccount, lead: Lead, message: str, action_id: uuid.UUID
    ) -> ProviderResult:
        return await self._post("message", account, lead, message, action_id)


def provider_for_account(account: LinkedInAccount) -> LinkedInProvider:
    provider_name = (account.provider or "demo").lower()
    if provider_name == "demo":
        return DemoLinkedInProvider()
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "connector":
        return ConnectorLinkedInProvider()
    if provider_name == "unipile":
        return UnipileProvider()
    return DemoLinkedInProvider()


__all__ = [
    "LinkedInProvider",
    "ProviderResult",
    "DemoLinkedInProvider",
    "UnipileProvider",
    "MockProvider",
    "ConnectorLinkedInProvider",
    "provider_for_account",
]
