"""
Offline/paper evaluator for research hypotheses.

Replays a research hypothesis against historical price history in-process to
estimate expected edge and win-rate. This component places NO orders, touches NO
live adapter, and writes to NO exchange. It exists so a hypothesis can be
measured before any capital is at risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.agents.research.grok_extractor import ResearchHypothesis
from src.trading.research_feature_store import hypothesis_to_features


@dataclass
class PaperEvaluation:
    """Result of evaluating a hypothesis in paper mode."""

    market_id: str
    expected_edge: float  # estimated edge, 0.0 - 1.0
    estimated_win_rate: float  # 0.0 - 1.0
    sample_size: int  # number of historical points used
    passed: bool  # whether the hypothesis meets min edge/confidence
    reason: str


class PaperEvaluator:
    """Evaluates research hypotheses against historical price history."""

    def __init__(
        self,
        min_edge: float = 0.08,
        min_confidence: float = 0.60,
        max_uncertainty: float = 0.60,
    ) -> None:
        self.min_edge = min_edge
        self.min_confidence = min_confidence
        self.max_uncertainty = max_uncertainty

    def evaluate(
        self,
        market_id: str,
        hypothesis: Optional[ResearchHypothesis],
        price_history: Optional[list[float]] = None,
    ) -> PaperEvaluation:
        """
        Evaluate a hypothesis. With no price history available, returns a
        conservative not-passed evaluation rather than fabricating edge.
        """
        features = hypothesis_to_features(hypothesis)

        # No research signal -> no edge.
        if hypothesis is None:
            return PaperEvaluation(
                market_id=market_id,
                expected_edge=0.0,
                estimated_win_rate=0.5,
                sample_size=0,
                passed=False,
                reason="no research hypothesis",
            )

        # Stale sources reduce confidence.
        age_penalty = min(features.research_source_age_hours / 168.0, 0.5)
        adjusted_confidence = features.research_confidence * (1.0 - age_penalty)

        # High uncertainty directly reduces estimated win rate.
        estimated_win_rate = 0.5 + (features.research_direction * adjusted_confidence * 0.4)
        estimated_win_rate = max(0.0, min(1.0, estimated_win_rate))

        # Edge estimated from directional confidence, capped.
        expected_edge = abs(features.research_direction) * adjusted_confidence * 0.3
        expected_edge = max(0.0, min(1.0, expected_edge))

        sample_size = len(price_history) if price_history else 0

        passed = (
            expected_edge >= self.min_edge
            and adjusted_confidence >= self.min_confidence
            and features.research_uncertainty <= self.max_uncertainty
        )

        reason_parts: list[str] = []
        if expected_edge < self.min_edge:
            reason_parts.append(f"edge {expected_edge:.2f} < min {self.min_edge:.2f}")
        if adjusted_confidence < self.min_confidence:
            reason_parts.append(
                f"confidence {adjusted_confidence:.2f} < min {self.min_confidence:.2f}"
            )
        if features.research_uncertainty > self.max_uncertainty:
            reason_parts.append(
                f"uncertainty {features.research_uncertainty:.2f} > max {self.max_uncertainty:.2f}"
            )
        if sample_size == 0:
            reason_parts.append("no price history")
        reason = "; ".join(reason_parts) if reason_parts else "passed paper evaluation"

        return PaperEvaluation(
            market_id=market_id,
            expected_edge=expected_edge,
            estimated_win_rate=estimated_win_rate,
            sample_size=sample_size,
            passed=passed,
            reason=reason,
        )
