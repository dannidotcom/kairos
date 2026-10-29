from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ICP, Lead, Organization, Signal
from app.security import utcnow
from app.services.campaign import enroll_on_signal
from app.services.scoring import rescore_lead


@dataclass(slots=True)
class SignalCandidate:
    type: str
    title: str
    description: str | None = None
    source_url: str | None = None
    source: str = "detector"
    strength: float = 0.7
    extra_data: dict[str, Any] = field(default_factory=dict)


class SignalDetector(ABC):
    """Base class for purchase signals."""

    name: str = "signal"
    weight: float = 1.0
    enabled: bool = True

    def __init__(self, *, enabled: bool | None = None, weight: float | None = None) -> None:
        if enabled is not None:
            self.enabled = enabled
        if weight is not None:
            self.weight = weight

    def supports_source(self, provider: Any | None) -> bool:
        if provider is None:
            return True
        supports = getattr(provider, "supports_signal", None)
        if callable(supports):
            return bool(supports(self.name))
        return True

    @abstractmethod
    def detect(
        self,
        *,
        organization: Organization,
        lead: Lead,
        provider: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> SignalCandidate | None:
        raise NotImplementedError


SIGNAL_REGISTRY: dict[str, SignalDetector] = {}


def register_signal_detector(detector: SignalDetector) -> None:
    SIGNAL_REGISTRY[detector.name] = detector


def list_signal_detectors() -> list[SignalDetector]:
    return sorted(SIGNAL_REGISTRY.values(), key=lambda item: item.name)


class JobChangeSignalDetector(SignalDetector):
    name = "job_change"
    weight = 0.9

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("job_change")
        if not data:
            return None
        title = data.get("title") or lead.headline or "Changement de poste"
        return SignalCandidate(
            type=self.name,
            title=f"{lead.full_name} a changé de poste",
            description=f"Nouveau poste/role: {title}",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"job_title": title, **(data.get("extra_data") or {})},
        )


class NewRoleAtTargetCompanySignalDetector(SignalDetector):
    name = "new_role_at_target_company"
    weight = 0.8

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("new_role_at_target_company")
        if not data:
            return None
        company = data.get("company") or lead.company or "entreprise cible"
        return SignalCandidate(
            type=self.name,
            title=f"Nouveau poste dans {company}",
            description=data.get("description") or f"Le profil semble avoir intégré une entreprise cible dans un nouveau rôle.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"company": company, **(data.get("extra_data") or {})},
        )


class ContentInteractionSignalDetector(SignalDetector):
    name = "content_interaction"
    weight = 0.9

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("content_interaction")
        if not data:
            return None
        return SignalCandidate(
            type=self.name,
            title="Interaction avec du contenu",
            description=data.get("description") or "Le prospect a interagi avec du contenu de l’entreprise ou de son équipe.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"interaction_type": data.get("interaction_type"), **(data.get("extra_data") or {})},
        )


class CompetitorContentInteractionSignalDetector(SignalDetector):
    name = "competitor_content_interaction"
    weight = 0.7

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("competitor_content_interaction")
        if not data:
            return None
        return SignalCandidate(
            type=self.name,
            title="Interaction avec du contenu concurrent",
            description=data.get("description") or "Le prospect a interagi avec un contenu concurrent.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"competitor": data.get("competitor"), **(data.get("extra_data") or {})},
        )


class ICPLookalikeSignalDetector(SignalDetector):
    name = "icp_lookalike"
    weight = 0.85

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("icp_lookalike")
        if not data:
            return None
        similarity = data.get("similarity") or 0
        return SignalCandidate(
            type=self.name,
            title="Lookalike ICP",
            description=f"Profil très proche d’un client existant (similarité {similarity}).",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", max(self.weight, min(1.0, similarity / 100)))),
            extra_data={"similarity": similarity, **(data.get("extra_data") or {})},
        )


class FundingSignalDetector(SignalDetector):
    name = "funding"
    weight = 0.95

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("funding")
        if not data:
            return None
        round_name = data.get("round") or "levée"
        return SignalCandidate(
            type=self.name,
            title=f"Levée de fonds : {round_name}",
            description=data.get("description") or "L’entreprise a récemment annoncé une levée de fonds.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"round": round_name, **(data.get("extra_data") or {})},
        )


class HiringSignalDetector(SignalDetector):
    name = "hiring"
    weight = 0.75

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("hiring")
        if not data:
            return None
        role = data.get("role") or "poste clé"
        return SignalCandidate(
            type=self.name,
            title="Recrutement sur poste lié à l’offre",
            description=f"L’entreprise recrute sur un poste lié au besoin: {role}.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"role": role, **(data.get("extra_data") or {})},
        )


class TopicPublicationSignalDetector(SignalDetector):
    name = "topic_publication"
    weight = 0.7

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("topic_publication")
        if not data:
            return None
        topic = data.get("topic") or "sujet clé"
        return SignalCandidate(
            type=self.name,
            title=f"Publication sur {topic}",
            description=data.get("description") or f"Le prospect publie ou commente sur un sujet clé: {topic}.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"topic": topic, **(data.get("extra_data") or {})},
        )


class EventParticipationSignalDetector(SignalDetector):
    name = "event_participation"
    weight = 0.65

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("event_participation")
        if not data:
            return None
        event_name = data.get("event_name") or "événement"
        return SignalCandidate(
            type=self.name,
            title=f"Participation à {event_name}",
            description=data.get("description") or f"Le prospect a participé ou interagi avec l’événement {event_name}.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"event_name": event_name, **(data.get("extra_data") or {})},
        )


class HeadcountGrowthSignalDetector(SignalDetector):
    name = "headcount_growth"
    weight = 0.8

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("headcount_growth")
        if not data:
            return None
        delta = data.get("delta") or 0
        return SignalCandidate(
            type=self.name,
            title="Croissance des effectifs",
            description=f"L’entreprise a connu une croissance d’effectifs de {delta}%.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"delta": delta, **(data.get("extra_data") or {})},
        )


class ProfileVisitSignalDetector(SignalDetector):
    name = "profile_visit"
    weight = 0.6

    def detect(self, *, organization: Organization, lead: Lead, provider: Any | None = None, context: dict[str, Any] | None = None) -> SignalCandidate | None:
        data = (context or {}).get("profile_visit")
        if not data:
            return None
        return SignalCandidate(
            type=self.name,
            title="Visite de profil",
            description=data.get("description") or "Le profil utilisateur a été visité / ouvert selon les données disponibles.",
            source_url=data.get("source_url"),
            source=data.get("source", "provider"),
            strength=float(data.get("strength", self.weight)),
            extra_data={"source": data.get("source"), **(data.get("extra_data") or {})},
        )


for detector in (
    JobChangeSignalDetector(),
    NewRoleAtTargetCompanySignalDetector(),
    ContentInteractionSignalDetector(),
    CompetitorContentInteractionSignalDetector(),
    ICPLookalikeSignalDetector(),
    FundingSignalDetector(),
    HiringSignalDetector(),
    TopicPublicationSignalDetector(),
    EventParticipationSignalDetector(),
    HeadcountGrowthSignalDetector(),
    ProfileVisitSignalDetector(),
):
    register_signal_detector(detector)


def collect_signal_candidates(
    *,
    organization: Organization,
    lead: Lead,
    provider: Any | None = None,
    source_data: dict[str, Any] | None = None,
) -> list[SignalCandidate]:
    context = source_data or {}
    candidates: list[SignalCandidate] = []
    for detector in list_signal_detectors():
        if not detector.enabled or not detector.supports_source(provider):
            detector.enabled = False
            continue
        candidate = detector.detect(organization=organization, lead=lead, provider=provider, context=context)
        if candidate is not None:
            candidates.append(candidate)
    deduped: list[SignalCandidate] = []
    seen: set[tuple[str, str | None]] = set()
    for item in candidates:
        key = (item.type, item.source_url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


async def create_signal_for_lead(
    session: AsyncSession,
    org: Organization,
    lead: Lead,
    *,
    type: str,
    title: str,
    description: str | None = None,
    source_url: str | None = None,
    source: str = "manual",
    strength: float = 0.7,
    detected_at: datetime | None = None,
    extra_data: dict[str, Any] | None = None,
) -> tuple[Signal, int]:
    signal = Signal(
        organization_id=org.id,
        lead_id=lead.id,
        type=type,
        title=title,
        description=description,
        source_url=source_url,
        source=source,
        strength=max(0.0, min(1.0, strength)),
        detected_at=detected_at or utcnow(),
        extra_data=extra_data or {},
    )
    session.add(signal)
    await session.flush()
    signal = await session.get(Signal, signal.id)
    assert signal is not None
    lead.last_signal_at = signal.detected_at
    score, _reasons, icp_id = await rescore_lead(session, lead, locale=org.locale, signal=signal)
    icp = await session.get(ICP, icp_id) if icp_id else None
    if lead.status == "new":
        lead.status = "qualified"
    enrolled = 0
    if icp and score >= icp.min_score:
        enrolled = await enroll_on_signal(session, org, lead, icp, signal=signal)
    return signal, enrolled


__all__ = [
    "SignalCandidate",
    "SignalDetector",
    "Signal",
    "SIGNAL_REGISTRY",
    "register_signal_detector",
    "list_signal_detectors",
    "collect_signal_candidates",
    "create_signal_for_lead",
]
