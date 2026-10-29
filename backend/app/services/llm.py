
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Sequence

import httpx
from pydantic import BaseModel, Field, field_validator

from app.config import settings


class LLMError(RuntimeError):
    pass


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, *, system: str, prompt: str, temperature: float = 0.2) -> str:
        raise NotImplementedError


class HeuristicLLMClient(LLMClient):
    async def complete(self, *, system: str, prompt: str, temperature: float = 0.2) -> str:
        if "score, justification, signals_used" in prompt:
            return '{"score":65,"justification":"Profil compatible avec les informations disponibles.","signals_used":[]}'
        return "Une accroche personnalisée basée uniquement sur les informations vérifiées du prospect."


class AnthropicLLMClient(LLMClient):
    async def complete(self, *, system: str, prompt: str, temperature: float = 0.2) -> str:
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": settings.anthropic_model, "max_tokens": 800, "temperature": temperature, "system": system, "messages": [{"role": "user", "content": prompt}]},
            )
            if response.status_code >= 400:
                raise LLMError(f"Anthropic API error {response.status_code}")
            content = response.json().get("content", [])
            return "".join(part.get("text", "") for part in content if part.get("type") == "text")


class OpenAICompatibleLLMClient(LLMClient):
    async def complete(self, *, system: str, prompt: str, temperature: float = 0.2) -> str:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "content-type": "application/json"},
                json={"model": settings.openai_model, "temperature": temperature, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
            )
            if response.status_code >= 400:
                raise LLMError(f"OpenAI-compatible API error {response.status_code}")
            choices = response.json().get("choices", [])
            return choices[0].get("message", {}).get("content", "") if choices else ""


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleLLMClient()
    return HeuristicLLMClient()


class StrictJsonLLMScore(BaseModel):
    score: int = Field(ge=0, le=100)
    justification: str = Field(min_length=1, max_length=200)
    signals_used: list[str] = Field(default_factory=list)

    @field_validator("justification")
    @classmethod
    def ensure_two_sentences_max(cls, value: str) -> str:
        return " ".join(re.split(r"(?<=[.!?])\s+", value.strip())[:2])


async def extract_structured_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if not cleaned:
        raise LLMError("Empty LLM output")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise LLMError("LLM returned invalid JSON")


async def score_profile_with_llm(*, lead: Any, icp: Any, signal_titles: Sequence[str] | None = None, context: dict[str, Any] | None = None, max_retries: int = 3) -> StrictJsonLLMScore:
    profile = {
        "name": getattr(lead, "full_name", None), "headline": getattr(lead, "headline", None),
        "company": getattr(lead, "company", None), "industry": getattr(lead, "industry", None),
        "location": getattr(lead, "location", None), "company_size": getattr(lead, "company_size", None),
        "about": getattr(lead, "about", None), "tags": list(getattr(lead, "tags", []) or []),
        "signals": list(signal_titles or []), "context": context or {},
    }
    icp_profile = {"name": getattr(icp, "name", None), "description": getattr(icp, "description", None), "titles": getattr(icp, "titles", []), "industries": getattr(icp, "industries", []), "locations": getattr(icp, "locations", [])}
    prompt = "Return only valid JSON with keys score, justification, signals_used. " + json.dumps({"lead": profile, "icp": icp_profile}, ensure_ascii=False)
    client = get_llm_client()
    for attempt in range(max_retries):
        try:
            return StrictJsonLLMScore.model_validate(await extract_structured_json(await client.complete(system="You are a conservative B2B scoring assistant.", prompt=prompt)))
        except (LLMError, ValueError, TypeError):
            if attempt == max_retries - 1:
                raise
    raise LLMError("Failed to validate LLM score")


async def generate_icp(description: str, value_prop: str | None = None, locale: str = "fr") -> Any:
    from app.schemas import ICPSuggestion

    prompt = (
        "Return only verified targeting fields derived from this ICP description. "
        + json.dumps({"description": description, "value_prop": value_prop or "", "locale": locale}, ensure_ascii=False)
    )
    text = await get_llm_client().complete(
        system="You extract a conservative B2B ICP. Do not invent sectors, countries or job titles.",
        prompt=prompt,
    )
    data: dict[str, Any] = {}
    try:
        data = await extract_structured_json(text)
    except LLMError:
        data = {}
    first_line = description.strip().splitlines()[0][:160] or "ICP cible"
    return ICPSuggestion(
        name=str(data.get("name") or first_line),
        description=description,
        value_prop=str(data.get("value_prop") or value_prop or "Valeur proposée à définir"),
        keywords=list(data.get("keywords") or []),
        titles=list(data.get("titles") or []),
        industries=list(data.get("industries") or []),
        company_sizes=list(data.get("company_sizes") or []),
        locations=list(data.get("locations") or []),
        seniorities=list(data.get("seniorities") or []),
        pain_points=list(data.get("pain_points") or []),
        signal_types=list(data.get("signal_types") or []),
        min_score=max(0, min(100, int(data.get("min_score", 65)))),
        auto_launch=bool(data.get("auto_launch", False)),
        generated_by=settings.llm_provider,
    )


async def draft_reply(*, lead: Any, incoming: Any, history: Sequence[str] | None = None, locale: str = "fr", org_name: str | None = None) -> tuple[str, str]:
    name = getattr(lead, "first_name", None) or getattr(lead, "full_name", "") .split()[0] if getattr(lead, "full_name", "") else ""
    greeting = f"Bonjour {name}" if name else ("Bonjour" if locale == "fr" else "Hello")
    body = getattr(incoming, "body", "") or ""
    if locale == "fr":
        reply = f"{greeting}, merci pour votre retour. Pouvez-vous préciser vos priorités actuelles concernant ce sujet ?"
    else:
        reply = f"{greeting}, thank you for your reply. Could you clarify your current priorities on this topic?"
    if org_name:
        reply += ""
    return reply[:2000], settings.llm_provider


async def draft_icebreaker(*, lead: Any, signal: Any | None = None, tone: str = "professionnel", max_chars: int = 300) -> str:
    facts = {
        "first_name": getattr(lead, "first_name", None) or getattr(lead, "full_name", "").split()[0] if getattr(lead, "full_name", None) else None,
        "company": getattr(lead, "company", None), "headline": getattr(lead, "headline", None),
        "signal_title": getattr(signal, "title", None),
    }
    facts = {key: value for key, value in facts.items() if value}
    prompt = (
        "Rédigez une accroche LinkedIn b2B vérifiable en français ou anglais selon le contexte. "
        "N'inventez aucun fait. Si une donnée manque, omettez-la. Ne prétendez aucun contact antérieur ni familiarité. "
        "Maximum 300 caractères. Reflétez ce ton: " + tone + ". Facts vérifiés JSON: " + json.dumps(facts, ensure_ascii=False)
    )
    text = await get_llm_client().complete(system="You create non-deceptive sales messages from verified facts only.", prompt=prompt)
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:max_chars]
