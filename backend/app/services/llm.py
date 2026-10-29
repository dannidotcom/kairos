
from __future__ import annotations

import json
import re
from typing import Any, Sequence

from pydantic import BaseModel, Field, field_validator

from app.services.llm import LLMError, get_llm_client


class StrictJsonLLMScore(BaseModel):
    score: int = Field(ge=0, le=100)
    justification: str = Field(min_length=1, max_length=200)
    signals_used: list[str] = Field(default_factory=list)

    @field_validator("justification")
    @classmethod
    def ensure_two_sentences_max(cls, value: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", value.strip())
        if len(sentences) > 2:
            value = " ".join(sentences[:2])
        return value


async def extract_structured_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if not cleaned:
        raise LLMError("Empty LLM output")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(cleaned[start : end + 1])
            else:
                raise
        except Exception as exc:  # pragma: no cover - validation path
            raise LLMError(f"LLM returned invalid JSON: {cleaned[:300]}") from exc
    if not isinstance(data, dict):
        raise LLMError("LLM response was not a JSON object")
    return data


async def score_profile_with_llm(
    *,
    lead: Any,
    icp: Any,
    signal_titles: Sequence[str] | None = None,
    context: dict[str, Any] | None = None,
    max_retries: int = 3,
) -> StrictJsonLLMScore:
    signal_titles = signal_titles or []
    context = context or {}
    prompt = (
        "You must answer strictly in JSON with keys: score, justification, signals_used. "
        "score is an integer from 0 to 100. justification is a maximum of two sentences. "
        "signals_used is a list of signal names referenced in the score.\n\n"
        f"ICP profile:\n{json.dumps({
            'name': getattr(icp, 'name', None),
            'titles': list(getattr(icp, 'titles', []) or []),
            'industries': list(getattr(icp, 'industries', []) or []),
            'keywords': list(getattr(icp, 'keywords', []) or []),
            'locations': list(getattr(icp, 'locations', []) or []),
            'company_sizes': list(getattr(icp, 'company_sizes', []) or []),
            'seniorities': list(getattr(icp, 'seniorities', []) or []),
            'description': getattr(icp, 'description', None),
        }, ensure_ascii=False)}\n\n"
        f"Lead profile:\n{json.dumps({
            'full_name': getattr(lead, 'full_name', None),
            'headline': getattr(lead, 'headline', None),
            'company': getattr(lead, 'company', None),
            'industry': getattr(lead, 'industry', None),
            'location': getattr(lead, 'location', None),
            'company_size': getattr(lead, 'company_size', None),
            'about': getattr(lead, 'about', None),
            'tags': list(getattr(lead, 'tags', []) or []),
            'signals': list(signal_titles),
            'extra_data': context,
        }, ensure_ascii=False)}\n\n"
        "Return only valid JSON; do not include markdown fences."
    )
    client = get_llm_client()
    for attempt in range(max_retries):
        try:
            raw = await client.complete(system="You are a B2B sales scoring assistant.", prompt=prompt)
            data = await extract_structured_json(raw)
            validated = StrictJsonLLMScore.model_validate(data)
            return validated
        except (LLMError, ValueError, TypeError):
            if attempt == max_retries - 1:
                raise
    raise LLMError("Failed to score lead with LLM after retries")
