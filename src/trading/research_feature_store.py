"""
Deterministic feature store for research signals.

Converts sanitized research hypotheses into whitelisted numeric features only.
Read-only with respect to execution: never computes position sizes, never
touches the order manager or live adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.agents.research.grok_extractor import ResearchHypothesis

FEATURE_NAMES = (
    "research_direction",
    "research_confidence",
    "research_uncertainty",
    "research_source_age_hours",
)


@dataclass
class ResearchFeatures:
    research_direction: float  # 1.0 long, -1.0 short, 0.0 neutral
    research_confidence: float  # 0.0 - 1.0
    research_uncertainty: float  # 0.0 - 1.0
    research_source_age_hours: float  # age of newest source, capped at 168h

    def as_dict(self) -> dict:
        return {
            "research_direction": self.research_direction,
            "research_confidence": self.research_confidence,
            "research_uncertainty": self.research_uncertainty,
            "research_source_age_hours": self.research_source_age_hours,
        }

    def as_vector(self) -> list[float]:
        return [
            self.research_direction,
            self.research_confidence,
            self.research_uncertainty,
            self.research_source_age_hours,
        ]


def direction_to_float(direction: str) -> float:
    d = str(direction or "neutral").strip().lower()
    if d in ("long", "buy", "yes"):
        return 1.0
    if d in ("short", "sell", "no"):
        return -1.0
    return 0.0


def hypothesis_to_features(
    hypothesis: Optional[ResearchHypothesis],
    source_age_hours: float = 24.0,
) -> ResearchFeatures:
    if hypothesis is None:
        return ResearchFeatures(
            research_direction=0.0,
            research_confidence=0.0,
            research_uncertainty=1.0,
            research_source_age_hours=min(source_age_hours, 168.0),
        )

    effective_confidence = max(
        0.0, min(1.0, hypothesis.confidence * (1.0 - hypothesis.uncertainty))
    )

    return ResearchFeatures(
        research_direction=direction_to_float(hypothesis.direction),
        research_confidence=effective_confidence,
        research_uncertainty=max(0.0, min(1.0, hypothesis.uncertainty)),
        research_source_age_hours=min(max(source_age_hours, 0.0), 168.0),
    )
