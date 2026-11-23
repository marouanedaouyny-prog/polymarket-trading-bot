"""
Grok/X research extractor — signal-only component.

Calls the xAI Grok API (X Search, web search, structured outputs) and returns a
structured hypothesis with uncertainty and sources. This component has NO access
to credentials beyond XAI_API_KEY (passed by the caller), NO access to order
placement, and NO authority to size or authorize any trade. All output is treated
as untrusted and must pass through the sanitizer and research feature store
before reaching the risk path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - openai is optional at import time
    OpenAI = None  # type: ignore[assignment]
    _OPENAI_AVAILABLE = False

GROK_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.7"


@dataclass
class ResearchHypothesis:
    """Structured output from Grok: a trading hypothesis, never an order."""

    market_id: str
    question: str
    direction: str  # "long" | "short" | "neutral"
    confidence: float  # 0.0 - 1.0
    uncertainty: float  # 0.0 - 1.0; higher = less reliable
    sources: List[str] = field(default_factory=list)
    reasoning: str = ""
    fetched_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    model: str = DEFAULT_MODEL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_id": self.market_id,
            "question": self.question,
            "direction": self.direction,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "sources": self.sources,
            "reasoning": self.reasoning,
            "fetched_at": self.fetched_at,
            "model": self.model,
        }


class GrokExtractor:
    """Extracts structured research hypotheses from X/web content via Grok."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.model = model
        self.client = None
        if self.api_key and _OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=GROK_BASE_URL)
            except Exception:
                # Client init failure is safe: extractor simply reports unavailable.
                self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None

    def extract_hypothesis(
        self,
        market_id: str,
        question: str,
        context: Optional[str] = None,
    ) -> Optional[ResearchHypothesis]:
        """
        Ask Grok to analyze a market question using X/web search and return a
        structured hypothesis. Returns None when the client is unavailable or
        the response cannot be parsed.
        """
        if not self.available:
            return None

        prompt = (
            "You are a research assistant for a prediction-market trading system. "
            "Analyze the following market question using X and web search. "
            "Return a structured JSON object only, with these fields: "
            "direction ('long'|'short'|'neutral'), confidence (0-1), "
            "uncertainty (0-1), sources (list of URLs), reasoning (short string). "
            "Do NOT recommend position sizes, stop losses, or order placement. "
            "Do NOT claim certainty. If evidence is weak, set confidence low and "
            "uncertainty high.\n\n"
            f"Market: {market_id}\nQuestion: {question}\n"
            + (f"Context: {context}\n" if context else "")
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            if not content:
                return None
            import json

            data = json.loads(content)
            return ResearchHypothesis(
                market_id=market_id,
                question=question,
                direction=str(data.get("direction", "neutral")).lower(),
                confidence=float(data.get("confidence", 0.0)),
                uncertainty=float(data.get("uncertainty", 1.0)),
                sources=list(data.get("sources", []))[:5],
                reasoning=str(data.get("reasoning", ""))[:1000],
                model=self.model,
            )
        except Exception:
            # Any parse/network failure -> no hypothesis, safe fallback.
            return None
