from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas import ICPSuggestion


class LLMError(RuntimeError):
    pass


class LLMClient(ABC):
    name = "base"

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 900,
        temperature: float = 0.4,
    ) -> str:
        raise NotImplementedError

    async def complete_json(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 900,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        text = await self.complete(
            system=system,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return extract_json_object(text)


class AnthropicLLMClient(LLMClient):
    name = "anthropic"

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 900,
        temperature: float = 0.4,
    ) -> str:
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.anthropic_model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if response.status_code >= 400:
            raise LLMError(f"Anthropic returned {response.status_code}: {response.text[:300]}")
        payload = response.json()
        blocks = payload.get("content", [])
        text = "\n".join(block.get("text", "") for block in blocks if block.get("type") == "text").strip()
        if not text:
            raise LLMError("Anthropic returned an empty response")
        return text


class OpenAICompatibleLLMClient(LLMClient):
    name = "openai_compatible"

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 900,
        temperature: float = 0.4,
    ) -> str:
        base_url = settings.openai_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        if response.status_code >= 400:
            raise LLMError(f"OpenAI-compatible endpoint returned {response.status_code}: {response.text[:300]}")
        payload = response.json()
        text = (
            payload.get("choices", [{}])[0].get("message", {}).get("content", "") if payload.get("choices") else ""
        ).strip()
        if not text:
            raise LLMError("OpenAI-compatible endpoint returned an empty response")
        return text


class HeuristicLLMClient(LLMClient):
    """Offline-safe writer used when no model endpoint is configured."""

    name = "heuristic"

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 900,
        temperature: float = 0.4,
    ) -> str:
        raise LLMError("Heuristic mode does not call a language model")


@lru_cache
def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.strip().lower()
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicLLMClient()
    if provider in {"openai_compatible", "openai", "vllm", "ollama"}:
        return OpenAICompatibleLLMClient()
    return HeuristicLLMClient()


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    raise LLMError("The model did not return valid JSON")


TITLE_CATALOG = [
    "head of growth",
    "vp sales",
    "head of sales",
    "chief revenue officer",
    "cro",
    "cto",
    "vp engineering",
    "head of engineering",
    "head of data",
    "head of marketing",
    "cmo",
    "founder",
    "co-founder",
    "ceo",
    "directeur général",
    "directrice générale",
    "directeur marketing",
    "directrice marketing",
    "responsable marketing",
    "responsable croissance",
    "directeur commercial",
    "directrice commerciale",
    "head of product",
    "vp product",
    "head of talent",
    "head of hr",
    "drh",
    "operations director",
    "directeur des opérations",
]

INDUSTRY_CATALOG = [
    "saas",
    "fintech",
    "healthtech",
    "legaltech",
    "hrtech",
    "edtech",
    "e-commerce",
    "marketplace",
    "cybersecurity",
    "cybersécurité",
    "artificial intelligence",
    "intelligence artificielle",
    "developer tools",
    "data",
    "logistics",
    "logistique",
    "retail",
    "industriel",
    "manufacturing",
    "media",
    "média",
    "travel",
    "voyage",
    "insurance",
    "assurance",
    "real estate",
    "immobilier",
]

LOCATION_CATALOG = [
    "paris",
    "lyon",
    "bordeaux",
    "toulouse",
    "lille",
    "nantes",
    "marseille",
    "london",
    "berlin",
    "madrid",
    "new york",
    "san francisco",
    "france",
    "europe",
    "benelux",
    "dach",
    "uk",
    "usa",
]

SIGNAL_CATALOG = {
    "job_change": ["nouveau poste", "nouvelle fonction", "nomination", "promotion", "a rejoint", "appointed"],
    "funding": ["levée", "leve", "funding", "series a", "series b", "série a", "série b", "amorçage", "investment"],
    "hiring": ["recrute", "recrutement", "hiring", "offre d'emploi", "job opening", "talent"],
    "linkedin_post": ["post linkedin", "publication", "partagé", "posted", "a publié"],
    "company_growth": ["croissance", "growth", "expansion", "ouverture", "international"],
    "product_launch": ["lancement", "launch", "nouveau produit", "nouvelle version"],
    "website_visit": ["visite", "trafic", "site web"],
    "engagement": ["engagement", "commentaire", "réaction"],
}

STOPWORDS = {
    "the",
    "and",
    "with",
    "that",
    "this",
    "from",
    "their",
    "pour",
    "dans",
    "avec",
    "nous",
    "vous",
    "sont",
    "plus",
    "sans",
    "être",
    "avoir",
    "sur",
    "les",
    "des",
    "une",
    "qui",
    "que",
    "aux",
    "par",
    "est",
    "leur",
    "dont",
    "comme",
    "they",
    "have",
    "will",
    "your",
    "our",
    "are",
    "for",
}


def _dedupe(values: list[str], limit: int = 12) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value.strip())
        if len(result) >= limit:
            break
    return result


def _extract_keywords(description: str, locale: str) -> list[str]:
    text = description.lower()
    found = [value for value in INDUSTRY_CATALOG if value in text]
    tokens = re.findall(r"[a-zàâçéèêëîïôûùüÿœæ0-9][a-zàâçéèêëîïôûùüÿœæ0-9+-]{3,}", text)
    tokens = [token for token in tokens if token not in STOPWORDS and not token.isdigit()]
    return _dedupe(found + tokens, 10)


def heuristic_icp(description: str, value_prop: str | None, locale: str) -> ICPSuggestion:
    text = description.lower()
    titles = [title for title in TITLE_CATALOG if title in text]
    if not titles:
        if "marketing" in text:
            titles = ["head of marketing", "cmo", "responsable marketing"]
        elif "vente" in text or "sales" in text or "revenu" in text:
            titles = ["vp sales", "head of sales", "chief revenue officer"]
        elif "technique" in text or "tech" in text or "engineering" in text:
            titles = ["cto", "vp engineering", "head of engineering"]
        else:
            titles = ["founder", "ceo", "head of growth"]
    industries = [industry for industry in INDUSTRY_CATALOG if industry in text]
    if not industries:
        industries = ["B2B SaaS"] if "saas" in text or "logiciel" in text else ["B2B services"]
    locations = [location for location in LOCATION_CATALOG if location in text]
    if not locations:
        locations = ["France"] if locale == "fr" else ["Europe"]
    sizes = re.findall(r"(\d{1,5}\s*(?:-|–|à|to)\s*\d{1,5})\s*(?:salariés|employés|employees|people|personnes)?", text)
    sizes = [re.sub(r"\s*(à|to)\s*", "-", size.replace("–", "-")) for size in sizes]
    if not sizes:
        if "startup" in text:
            sizes = ["11-50"]
        elif "scale-up" in text or "scaleup" in text:
            sizes = ["51-200"]
        elif "pme" in text or "sme" in text:
            sizes = ["11-250"]
        elif "eti" in text or "enterprise" in text:
            sizes = ["250-5000"]
        else:
            sizes = ["11-200"] if locale == "fr" else ["11-200"]
    signals = [signal for signal, clues in SIGNAL_CATALOG.items() if any(clue in text for clue in clues)]
    if not signals:
        signals = ["job_change", "funding", "hiring", "linkedin_post"]
    seniorities = ["C-Level", "VP", "Head", "Director"] if locale == "en" else ["C-Level", "VP", "Head", "Directeur"]
    keywords = _extract_keywords(description, locale)
    if locale == "fr":
        name = f"{industries[0].title()} · {titles[0].title()}"
        pain_points = [
            "Trop de temps passé à qualifier des prospects froids",
            "Des signaux d'achat détectés trop tard",
            "Une prospection difficile à personnaliser à l'échelle",
        ]
        generated_value_prop = value_prop or (
            f"Kairos aide les équipes de {titles[0]} dans le {industries[0]} à contacter les bons comptes "
            "au moment exact où un signal d'achat apparaît."
        )
        signal_types = signals
    else:
        name = f"{industries[0].title()} · {titles[0].title()}"
        pain_points = [
            "Too much time spent qualifying cold prospects",
            "Buying signals discovered too late",
            "Personalised outreach is hard to scale",
        ]
        generated_value_prop = value_prop or (
            f"Kairos helps {titles[0]} teams in {industries[0]} reach the right accounts "
            "at the exact moment a buying signal appears."
        )
        signal_types = signals
    return ICPSuggestion(
        name=name[:160],
        description=description.strip(),
        value_prop=generated_value_prop,
        keywords=keywords,
        titles=_dedupe(titles, 8),
        industries=_dedupe(industries, 8),
        company_sizes=_dedupe(sizes, 5),
        locations=_dedupe(locations, 8),
        seniorities=seniorities,
        pain_points=pain_points,
        signal_types=_dedupe(signal_types, 8),
        min_score=65,
        auto_launch=False,
        generated_by="heuristic",
    )


async def generate_icp(description: str, value_prop: str | None, locale: str) -> ICPSuggestion:
    fallback = heuristic_icp(description, value_prop, locale)
    client = get_llm_client()
    if client.name == "heuristic":
        return fallback
    language = "French" if locale == "fr" else "English"
    system = (
        "You are a senior B2B go-to-market strategist. You turn ideal customer profile descriptions into "
        "precise, ethical, actionable targeting criteria. Never target people on sensitive attributes "
        "(age, gender, ethnicity, health, religion, sexual orientation). Return strict JSON only."
    )
    prompt = f"""Build an ICP from the description below.
Language: {language}.
Description: {description}
Value proposition: {value_prop or "(not supplied)"}

Return a JSON object with exactly these keys:
- name: short segment name (max 8 words)
- description: concise restatement
- value_prop: one sentence
- keywords: 5-10 short search keywords
- titles: 4-8 job titles to target
- industries: 2-6 industries
- company_sizes: 1-4 ranges (for example "51-200")
- locations: 1-6 geographic zones
- seniorities: 2-5 seniority labels
- pain_points: 2-5 concrete pains
- signal_types: subset of ["job_change","funding","hiring","linkedin_post","website_visit","company_growth","product_launch","engagement"]
- min_score: integer between 55 and 85
- auto_launch: boolean (default false)

No markdown, no commentary."""
    try:
        payload = await client.complete_json(
            system=system,
            prompt=prompt,
            max_tokens=1100,
            temperature=0.25,
        )
        payload["generated_by"] = client.name
        payload.setdefault("description", description)
        payload.setdefault("value_prop", value_prop or fallback.value_prop)
        return ICPSuggestion.model_validate(payload)
    except (LLMError, ValidationError, httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError):
        return fallback


def _clean_generated_text(text: str, max_chars: int = 420) -> str:
    cleaned = text.strip().strip('"').strip("'").replace("\n\n", "\n")
    cleaned = re.sub(r"^(objet|subject)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return cleaned


def heuristic_icebreaker(lead: Any, signal: Any | None, locale: str, value_prop: str | None = None) -> str:
    company = lead.company or ("votre entreprise" if locale == "fr" else "your company")
    signal_title = (signal.title if signal else "").strip().rstrip(".")
    signal_type = signal.type if signal else "manual"
    if locale == "fr":
        if signal_type == "job_change" and signal_title:
            opening = f"Félicitations pour votre nouveau poste chez {company} — j'ai vu « {signal_title} »."
        elif signal_type == "funding" and signal_title:
            opening = f"J'ai vu que {company} accélère : « {signal_title} ». Félicitations."
        elif signal_type == "hiring" and signal_title:
            opening = f"J'ai remarqué que {company} recrute en ce moment — « {signal_title} »."
        elif signal_title:
            opening = f"Votre actualité chez {company} a retenu mon attention : « {signal_title} »."
        else:
            opening = f"J'ai suivi la trajectoire de {company} et votre travail sur {lead.headline or 'votre marché'}."
        value = value_prop or "J'aide les équipes commerciales à transformer les signaux d'achat en conversations utiles."
        return _clean_generated_text(f"{opening} {value}")
    if signal_type == "job_change" and signal_title:
        opening = f"Congrats on the new role at {company} — I saw “{signal_title}”."
    elif signal_type == "funding" and signal_title:
        opening = f"Looks like {company} is accelerating — I saw “{signal_title}”. Congratulations."
    elif signal_type == "hiring" and signal_title:
        opening = f"I noticed {company} is hiring right now — “{signal_title}”."
    elif signal_title:
        opening = f"Your recent news at {company} caught my eye: “{signal_title}”."
    else:
        opening = f"I've been following {company} and your work around {lead.headline or 'your market'}."
    value = value_prop or "I help teams turn buying signals into useful conversations."
    return _clean_generated_text(f"{opening} {value}")


async def draft_icebreaker(
    *,
    lead: Any,
    signal: Any | None,
    icp: Any | None,
    locale: str,
    value_prop: str | None = None,
) -> tuple[str, str]:
    client = get_llm_client()
    if client.name == "heuristic":
        return heuristic_icebreaker(lead, signal, locale, value_prop or (icp.value_prop if icp else None)), "heuristic"
    language = "French" if locale == "fr" else "English"
    signal_text = (
        f"{signal.type}: {signal.title}. {signal.description or ''}" if signal else "No specific signal; use the profile only."
    )
    system = (
        "You write short, specific, non-creepy B2B LinkedIn icebreakers. No flattery, no clichés, no emojis, "
        "no invented facts. Follow the language instruction. Return only the message, no quotation marks."
    )
    prompt = f"""Write one icebreaker in {language}, maximum 45 words.
Lead: {lead.full_name}, {lead.headline or ''} at {lead.company or ''} ({lead.industry or ''}, {lead.location or ''}).
Signal: {signal_text}
Our value proposition: {value_prop or (icp.value_prop if icp else '')}
Rules: mention one concrete detail from the signal, connect it naturally to the value proposition, and ask nothing
in this sentence. Avoid "I hope this message finds you well". No links."""
    try:
        text = await client.complete(system=system, prompt=prompt, max_tokens=180, temperature=0.65)
        return _clean_generated_text(text, 320), client.name
    except (LLMError, httpx.HTTPError):
        return heuristic_icebreaker(lead, signal, locale, value_prop), "heuristic"


async def draft_reply(
    *,
    lead: Any,
    incoming: str,
    history: list[str],
    locale: str,
    org_name: str,
) -> tuple[str, str]:
    client = get_llm_client()
    if client.name == "heuristic":
        fallback = (
            f"Merci pour votre retour, {lead.first_name}. Je vous propose un échange de 15 minutes pour creuser — "
            "je peux vous montrer concrètement comment nous travaillons."
            if locale == "fr"
            else f"Thanks for getting back to me, {lead.first_name}. Happy to find 15 minutes to explore — "
            "I can show you concretely how we work."
        )
        return fallback, "heuristic"
    language = "French" if locale == "fr" else "English"
    system = (
        f"You are a helpful sales assistant for {org_name}. Write concise, human replies. "
        "Do not invent pricing, commitments, or facts. Return only the reply."
    )
    prompt = f"""Reply in {language} to this LinkedIn conversation.
Lead: {lead.full_name}, {lead.headline or ''} at {lead.company or ''}.
Earlier messages: {history[-4:]}
Latest inbound message: {incoming}
Goal: move toward a short discovery call, answer the question directly, ask one clear next-step question.
Maximum 90 words."""
    try:
        text = await client.complete(system=system, prompt=prompt, max_tokens=300, temperature=0.55)
        return _clean_generated_text(text, 900), client.name
    except (LLMError, httpx.HTTPError):
        fallback = (
            "Merci pour votre message. Je serais ravi d'en discuter : avez-vous 15 minutes cette semaine ?"
            if locale == "fr"
            else "Thanks for your message. I'd be glad to discuss — do you have 15 minutes this week?"
        )
        return fallback, "heuristic"
