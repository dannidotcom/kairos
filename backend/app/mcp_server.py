from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.db import SessionLocal
from app.models import ApiKey
from app.security import hash_api_key

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("kairos.mcp")
current_api_key: ContextVar[str | None] = ContextVar("current_api_key", default=None)


def _mcp_allowed_origins() -> list[str]:
    configured = [origin.strip() for origin in settings.mcp_allowed_origins.split(",") if origin.strip()]
    if configured:
        return configured
    origins: set[str] = set()
    for url in [*settings.cors_origin_list, settings.frontend_url]:
        if url == "*" or not url:
            continue
        parsed = urlsplit(url)
        if parsed.scheme and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}")
    return sorted(origins)


mcp = FastMCP(
    "Kairos",
    instructions=(
        "Kairos is a signal-led LinkedIn B2B prospecting workspace. Use these tools to inspect buying signals, "
        "qualify and score leads, draft personalised icebreakers, create campaigns and launch or pause outreach. "
        "Every tool is scoped to the organisation that owns the API key. Drafts do not send messages; launching a "
        "campaign authorises the sequence and should only happen after explicit human approval."
    ),
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[host.strip() for host in settings.mcp_allowed_hosts.split(",") if host.strip()],
        allowed_origins=_mcp_allowed_origins(),
    ),
)


class MCPApiKeyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return
        headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
        raw_key = headers.get("x-api-key")
        if not raw_key:
            authorization = headers.get("authorization", "")
            if authorization.lower().startswith("bearer "):
                raw_key = authorization[7:].strip()
        if not raw_key or not raw_key.startswith("kairos_mcp_"):
            await JSONResponse(
                {"detail": "A valid Kairos MCP API key is required (X-API-Key or Authorization: Bearer)."},
                status_code=401,
            )(scope, receive, send)
            return
        async with SessionLocal() as session:
            record = (
                await session.execute(
                    select(ApiKey.id).where(
                        ApiKey.key_hash == hash_api_key(raw_key),
                        ApiKey.revoked_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
        if record is None:
            await JSONResponse({"detail": "Invalid or revoked API key"}, status_code=401)(scope, receive, send)
            return
        token = current_api_key.set(raw_key)
        try:
            await self.app(scope, receive, send)
        finally:
            current_api_key.reset(token)


def _request_key(ctx: Context) -> str:
    request = None
    try:
        request = ctx.request_context.request
    except Exception:  # noqa: BLE001 - context differs across SDK transports
        request = None
    if isinstance(request, Request):
        key = request.headers.get("x-api-key")
        if not key:
            authorization = request.headers.get("authorization", "")
            if authorization.lower().startswith("bearer "):
                key = authorization[7:].strip()
        if key:
            return key
    fallback = current_api_key.get()
    if fallback:
        return fallback
    raise PermissionError("Missing MCP API key context")


async def _call(method: str, path: str, ctx: Context, *, params: dict | None = None, body: dict | None = None) -> Any:
    headers = {"X-API-Key": _request_key(ctx)}
    async with httpx.AsyncClient(base_url=settings.public_api_url, timeout=60.0) as client:
        response = await client.request(method, path, headers=headers, params=params, json=body)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Kairos API {response.status_code}: {detail}")
    if response.status_code == 204:
        return {"ok": True}
    return response.json()


@mcp.tool(
    name="kairos_workspace_summary",
    description="Get the workspace pulse: lead counts, hot leads, recent signals, active campaigns and LinkedIn quota usage.",
)
async def workspace_summary(ctx: Context) -> dict:
    return await _call("GET", "/api/mcp/summary", ctx)


@mcp.tool(
    name="kairos_list_hot_leads",
    description="List the highest-scoring ICP-fit leads, optionally filtered by minimum score or a search query.",
)
async def list_hot_leads(
    ctx: Context,
    min_score: int = 70,
    limit: int = 10,
    query: str | None = None,
) -> list[dict]:
    params: dict[str, Any] = {"min_score": min_score, "limit": min(limit, 50)}
    if query:
        params["query"] = query
    return await _call("GET", "/api/mcp/leads", ctx, params=params)


@mcp.tool(
    name="kairos_search_leads",
    description="Search leads by name, company or headline and return their ICP score and latest buying signal.",
)
async def search_leads(ctx: Context, query: str, min_score: int = 0, limit: int = 10) -> list[dict]:
    return await _call(
        "GET",
        "/api/mcp/leads",
        ctx,
        params={"query": query, "min_score": min_score, "limit": min(limit, 50)},
    )


@mcp.tool(
    name="kairos_get_lead",
    description="Get one lead's full profile, scoring reasons, campaign membership and last ten buying signals.",
)
async def get_lead(ctx: Context, lead_id: str) -> dict:
    return await _call("GET", f"/api/mcp/leads/{lead_id}", ctx)


@mcp.tool(
    name="kairos_list_signals",
    description="List the most recent buying signals across the workspace, newest first.",
)
async def list_signals(ctx: Context, limit: int = 10, signal_type: str | None = None) -> list[dict]:
    params: dict[str, Any] = {"limit": min(limit, 50)}
    if signal_type:
        params["type"] = signal_type
    return await _call("GET", "/api/mcp/signals", ctx, params=params)


@mcp.tool(
    name="kairos_list_icps",
    description="List ideal customer profiles with targeting criteria, scores and automation settings.",
)
async def list_icps(ctx: Context) -> list[dict]:
    return await _call("GET", "/api/mcp/icps", ctx)


@mcp.tool(
    name="kairos_draft_icebreaker",
    description="Draft a personalised icebreaker for a lead based on their latest buying signal. This only returns text; it does not send anything.",
)
async def draft_icebreaker(ctx: Context, lead_id: str, campaign_id: str | None = None) -> dict:
    body: dict[str, Any] = {"lead_id": lead_id}
    if campaign_id:
        body["campaign_id"] = campaign_id
    return await _call("POST", "/api/mcp/draft-icebreaker", ctx, body=body)


@mcp.tool(
    name="kairos_list_campaigns",
    description="List campaigns with status, sequence, enrolled lead counts and reply performance.",
)
async def list_campaigns(ctx: Context) -> list[dict]:
    return await _call("GET", "/api/mcp/campaigns", ctx)


@mcp.tool(
    name="kairos_create_campaign",
    description=(
        "Create a draft LinkedIn campaign. Provide an ICP id and a sequence of steps. A step is "
        "{action_type: connection_request|message|follow_up|inmail, delay_days: int, body_template: str}. "
        "Templates may use {{first_name}}, {{company}}, {{signal}}, {{icebreaker}} and {{value_prop}}. "
        "This does not launch the campaign."
    ),
)
async def create_campaign(
    ctx: Context,
    name: str,
    icp_id: str,
    steps: list[dict],
    description: str | None = None,
    min_score: int = 65,
    auto_launch: bool = True,
    account_id: str | None = None,
) -> dict:
    body = {
        "name": name,
        "icp_id": icp_id,
        "steps": steps,
        "description": description,
        "min_score": min_score,
        "auto_launch": auto_launch,
        "account_id": account_id,
    }
    return await _call("POST", "/api/mcp/campaigns", ctx, body=body)


@mcp.tool(
    name="kairos_launch_campaign",
    description=(
        "Launch an existing draft or paused campaign. This authorises Kairos to send connection requests and messages "
        "within the configured quotas and send window. Use only after explicit human approval."
    ),
)
async def launch_campaign(ctx: Context, campaign_id: str) -> dict:
    return await _call("POST", f"/api/mcp/campaigns/{campaign_id}/launch", ctx)


@mcp.tool(
    name="kairos_pause_campaign",
    description="Pause a campaign so no further connection requests or messages are sent.",
)
async def pause_campaign(ctx: Context, campaign_id: str) -> dict:
    return await _call("POST", f"/api/mcp/campaigns/{campaign_id}/pause", ctx)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "kairos-mcp", "transport": "streamable-http"})


app = mcp.streamable_http_app()
app.router.routes.insert(0, Route("/health", endpoint=health, methods=["GET"]))
app.add_middleware(MCPApiKeyMiddleware)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
