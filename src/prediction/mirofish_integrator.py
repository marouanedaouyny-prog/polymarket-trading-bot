"""
High-level MiroFish integration interface for Polymarket trading bots.
Replaces the hardcoded get_llm_intelligence() with real swarm intelligence.

Usage:
    from src.prediction import MiroFishIntegrator
    mf = MiroFishIntegrator()
    signal = mf.analyze_market("Will BTC reach $100K by June?")
    # Returns: { edge, confidence, sentiment_score, consensus, sectors }
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Optional

from src.prediction.mirofish_client import MiroFishClient
from src.prediction.mirofish_cache import MiroFishCache

logger = logging.getLogger(__name__)


class MiroFishIntegrator:
    """
    Integrates MiroFish swarm intelligence into the Polymarket trading pipeline.

    Flow per market:
        1. Check cache for existing result
        2. Feed market question as seed into MiroFish
        3. MiroFish spawns agents → simulates → generates report
        4. Extract consensus signal (edge, confidence, sentiment)
        5. Cache result
    """

    def __init__(self, base_url: str = None, use_cache: bool = True,
                 cache_ttl: int = 3600, simulation_rounds: int = 50,
                 agent_count: int = 50,
                 min_call_interval_seconds: Optional[int] = None):
        self.client = MiroFishClient(base_url=base_url)
        self.cache = MiroFishCache(ttl_seconds=cache_ttl) if use_cache else None
        self.use_cache = use_cache
        self.simulation_rounds = simulation_rounds
        self.agent_count = agent_count
        if min_call_interval_seconds is None:
            self.min_call_interval_seconds = int(
                os.getenv("MIROFISH_MIN_CALL_INTERVAL_SECONDS", "30")
            )
        else:
            self.min_call_interval_seconds = max(0, int(min_call_interval_seconds))
        self._busy_until = 0.0
        self._available = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                self._available = self.client.health()
            except Exception:
                self._available = False
        return self._available

    def reset_availability(self):
        self._available = None

    def get_market_intelligence(self, question: str = "",
                                 market_data: dict = None) -> dict:
        """
        Main entry point for trading bots.
        Returns a dict matching the get_llm_intelligence() format used by all bots.

        Falls back to default values if MiroFish is unavailable.
        Only triggers full MiroFish analysis for meaningful questions (>10 chars).
        """
        context = json.dumps(market_data, sort_keys=True) if market_data else ""
        if self.use_cache and self.cache:
            cached = self.cache.get(question, context)
            if cached:
                return cached

        default = self._default_intelligence(question, market_data)
        if not self.available:
            return default

        if len(question.strip()) < 10:
            return default

        if self.mirofish_busy():
            return default
        
        try:
            signal = self.analyze_market(question, market_data)
            if signal:
                return signal
        except Exception as e:
            logger.warning(f"MiroFish analysis failed: {e}")

        return default
    
    def mirofish_busy(self) -> bool:
        """Rate-limit MiroFish calls using the configured minimum interval."""
        if self.min_call_interval_seconds <= 0:
            return False
        now = time.time()
        if now < self._busy_until:
            return True
        self._busy_until = now + self.min_call_interval_seconds
        return False

    def analyze_market(self, question: str, market_data: dict = None) -> Optional[dict]:
        """Run full MiroFish analysis on a single market question."""
        context = json.dumps(market_data, sort_keys=True) if market_data else ""

        if self.use_cache and self.cache:
            cached = self.cache.get(question, context)
            if cached:
                logger.info(f"[MiroFish] Cache hit for: {question[:50]}...")
                return cached

        logger.info(f"[MiroFish] Analyzing market: {question[:80]}...")
        start = time.time()

        try:
            text = self._build_seed_text(question, market_data)
            requirement = f"Predict the outcome of this prediction market: {question}"

            project = self.client.create_project_from_text(
                text=text,
                simulation_requirement=requirement,
                project_name=f"pm_{int(time.time())}",
            )
            if not project:
                logger.warning("[MiroFish] Failed to create project")
                return None

            project_id = project.get("project_id")
            graph_data = self.client.build_graph(project_id)
            if not graph_data:
                logger.warning("[MiroFish] Failed to build graph")
                return None

            task_id = graph_data.get("task_id")
            if task_id:
                result = self.client.wait_for_task(task_id, timeout=300.0)
                if not result:
                    logger.warning("[MiroFish] Graph build timed out")
                    return None

            sim = self.client.create_simulation(project_id)
            if not sim:
                logger.warning("[MiroFish] Failed to create simulation")
                return None

            sim_id = sim.get("simulation_id")
            prep = self.client.prepare_simulation(sim_id, parallel_profile_count=self.agent_count)
            if prep:
                prep_task_id = prep.get("task_id")
                if prep_task_id:
                    ready = self.client.wait_for_preparation(
                        task_id=prep_task_id, timeout=300.0
                    )
                    if not ready:
                        logger.warning("[MiroFish] Simulation prep timed out")

            run = self.client.start_simulation(
                sim_id,
                platform="parallel",
                max_rounds=self.simulation_rounds,
            )
            if not run:
                logger.warning("[MiroFish] Failed to start simulation")
                return None

            completed = self.client.wait_for_simulation(
                sim_id, timeout=3600.0
            )
            if not completed:
                self.client.stop_simulation(sim_id)
                logger.warning("[MiroFish] Simulation did not complete")
                return None

            report_data = self.client.generate_report(sim_id)
            if report_data:
                report_task_id = report_data.get("task_id")
                if report_task_id:
                    report_id = self.client.wait_for_report(
                        task_id=report_task_id, timeout=600.0
                    )
                else:
                    report_id = None
            else:
                report_id = None

            signal = self._extract_signal(question, sim_id, report_id)

            elapsed = time.time() - start
            logger.info(f"[MiroFish] Analysis complete in {elapsed:.0f}s for: {question[:50]}...")

            if signal and self.use_cache and self.cache:
                self.cache.set(question, signal, context)

            return signal

        except Exception as e:
            logger.error(f"[MiroFish] Analysis error: {e}")
            return None

    def _extract_signal(self, question: str, simulation_id: str,
                         report_id: Optional[str]) -> dict:
        """Extract prediction signal from simulation results."""
        posts = self.client.get_simulation_posts(simulation_id, limit=100)
        actions = self.client.get_simulation_actions(simulation_id, limit=200)

        yes_count = 0
        no_count = 0
        neutral_count = 0
        sentiment_accum = 0.0
        mentions = 0

        question_lower = question.lower()
        keywords = question_lower.split()

        for post in posts:
            content = (post.get("content") or "").lower()
            if not any(kw in content for kw in keywords if len(kw) > 3):
                continue

            if any(w in content for w in ["yes", "agree", "support", "bullish", "likely", "will"]):
                yes_count += 1
                sentiment_accum += 0.8
            elif any(w in content for w in ["no", "disagree", "oppose", "bearish", "unlikely", "won't"]):
                no_count += 1
                sentiment_accum += 0.2
            else:
                neutral_count += 1
                sentiment_accum += 0.5
            mentions += 1

        for action in actions:
            action_text = (action.get("action") or "").lower()
            content_text = (action.get("content") or "").lower()
            if not any(kw in content_text for kw in keywords if len(kw) > 3):
                continue

            if any(w in action_text for w in ["like", "create", "repost", "follow"]):
                sentiment_accum += 0.7
                mentions += 1
            elif any(w in action_text for w in ["dislike", "mute"]):
                sentiment_accum += 0.3
                mentions += 1

        total_mentions = yes_count + no_count + neutral_count
        if total_mentions > 0:
            consensus_yes = yes_count / total_mentions
        else:
            consensus_yes = 0.5

        if mentions > 0:
            sentiment_score = sentiment_accum / mentions
        else:
            sentiment_score = 0.5

        confidence = min(95, 50 + int(consensus_yes * 30) + int(mentions * 2))

        q_lower = question.lower()
        sectors = []
        for kw in ["crypto", "bitcoin", "ethereum", "solana", "btc", "eth"]:
            if kw in q_lower:
                sectors.append(kw)

        signal = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "simulation_id": simulation_id,
            "report_id": report_id,
            "sectors": sectors or ["general"],
            "sentiment_score": round(sentiment_score, 2),
            "consensus_yes_pct": round(consensus_yes * 100, 1),
            "confidence_boost": min(15, int(consensus_yes * 10) + 3),
            "edge": round(consensus_yes, 2),
            "confidence": confidence,
            "mentions": mentions,
            "total_posts": len(posts),
            "total_actions": len(actions),
            "yes_votes": yes_count,
            "no_votes": no_count,
            "neutral_votes": neutral_count,
        }

        report = None
        if report_id:
            report = self.client.get_report(report_id)
        if report:
            signal["report_summary"] = (report.get("markdown_content") or "")[:500]

        return signal

    def _build_seed_text(self, question: str, market_data: dict = None) -> str:
        """Build seed text from market data for MiroFish graph construction."""
        lines = [f"Prediction Market: {question}"]
        if market_data:
            for k, v in market_data.items():
                if k in ("question", "id", "outcomePrices", "volume"):
                    continue
                if isinstance(v, (str, int, float)):
                    lines.append(f"{k}: {v}")
        lines.append(f"\nPrediction question for swarm intelligence analysis: {question}")
        lines.append("Agents should discuss the likelihood of this outcome based on available information.")
        return "\n".join(lines)

    def _default_intelligence(self, question: str = "",
                               market_data: dict = None) -> dict:
        """Default intelligence when MiroFish is unavailable.
        Matches the format of the hardcoded get_llm_intelligence() methods."""
        q_lower = question.lower()
        sectors = []
        for kw in ["crypto", "bitcoin", "ethereum", "solana", "btc", "eth"]:
            if kw in q_lower:
                sectors.append(kw)

        return {
            "timestamp": datetime.now().isoformat(),
            "sectors": sectors or ["crypto", "bitcoin", "ethereum", "solana"],
            "sentiment_score": 0.85,
            "confidence_boost": 10,
            "trending": [
                {"sector": s, "sentiment": "bullish", "confidence": 85}
                for s in (sectors or ["crypto", "bitcoin"])
            ],
        }

    def build_trade_signal(
        self,
        question: str,
        market_data: dict = None,
        yes_price: Optional[float] = None,
        no_price: Optional[float] = None,
        volume: Optional[float] = None,
    ) -> dict:
        """Build a normalized trade signal from MiroFish intelligence.

        The returned structure is intentionally small so multiple trading modules
        can share the same scoring and side-selection logic.
        """
        intel = self.get_market_intelligence(question, market_data)
        consensus_yes_pct = intel.get("consensus_yes_pct")
        sentiment_score = float(intel.get("sentiment_score", 0.5))
        confidence = float(intel.get("confidence", 50))
        confidence_boost = float(intel.get("confidence_boost", 0))

        if consensus_yes_pct is not None:
            yes_prob = max(0.01, min(0.99, float(consensus_yes_pct) / 100.0))
            source = "mirofish"
        else:
            yes_prob = max(0.01, min(0.99, sentiment_score))
            source = "fallback"

        if yes_price is not None:
            reference_yes = max(0.01, min(0.99, float(yes_price)))
        else:
            reference_yes = 0.5

        if no_price is not None:
            reference_no = max(0.01, min(0.99, float(no_price)))
        else:
            reference_no = max(0.01, min(0.99, 1.0 - reference_yes))

        yes_edge = yes_prob - reference_yes
        no_prob = 1.0 - yes_prob
        no_edge = no_prob - reference_no

        if yes_edge >= no_edge:
            selected_side = "yes"
            selected_prob = yes_prob
            selected_price = reference_yes
            edge = yes_edge
        else:
            selected_side = "no"
            selected_prob = no_prob
            selected_price = reference_no
            edge = no_edge

        score = max(edge, 0.0) * (confidence / 100.0) * (1.0 + confidence_boost / 100.0)

        return {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "source": source,
            "selected_side": selected_side,
            "selected_outcome": selected_side,
            "selected_price": round(selected_price, 4),
            "predicted_prob": round(selected_prob, 4),
            "consensus_yes_pct": round(float(consensus_yes_pct), 1)
            if consensus_yes_pct is not None
            else None,
            "edge": round(edge, 4),
            "confidence": round(confidence, 2),
            "confidence_boost": round(confidence_boost, 2),
            "score": round(score, 4),
            "sentiment_score": round(sentiment_score, 2),
            "volume": volume,
            "intel": intel,
        }

    def batch_analyze(self, markets: list, max_workers: int = 3) -> list:
        """Analyze multiple markets sequentially (parallel via cache hits)."""
        results = []
        for m in markets:
            question = m.get("question", "")
            if not question:
                continue
            signal = self.get_market_intelligence(question, m)
            results.append({**m, "mirofish_signal": signal})
        return results
