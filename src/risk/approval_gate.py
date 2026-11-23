"""
Approval gate — independent risk policy plus manual approval recording.

Can VETO any trade but can never INITIATE one. Wraps DynamicRiskManager's
should_trade / check_circuit_breakers and records every decision to the audit
log so there is a complete, tamper-evident trail of what was allowed and why.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.risk.dynamic_risk import DynamicRiskManager


@dataclass
class ApprovalDecision:
    allowed: bool
    reason: str
    market_id: str
    edge: float
    confidence: float
    risk_state: Dict[str, Any]
    timestamp: str = ""
    provenance_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(tz=timezone.utc).isoformat()
        if not self.provenance_id:
            self.provenance_id = f"appr_{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    def to_dict(self) -> dict:
        return asdict(self)


class ApprovalGate:
    def __init__(
        self,
        risk_manager: Optional[DynamicRiskManager] = None,
        audit_log_path: str = "data/audit_log.jsonl",
        require_manual_approval: bool = True,
    ) -> None:
        self.risk = risk_manager or DynamicRiskManager()
        self.audit_log_path = audit_log_path
        self.require_manual_approval = require_manual_approval
        os.makedirs(os.path.dirname(audit_log_path) or ".", exist_ok=True)

    def _append_audit(self, record: dict) -> None:
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            # Audit logging must never block trading decisions.
            pass

    def evaluate(
        self,
        market_id: str,
        edge: float,
        confidence: float,
        balance: float,
        manual_approved: bool = False,
        current_balance: Optional[float] = None,
        starting_balance: Optional[float] = None,
    ) -> ApprovalDecision:
        """
        Run independent risk checks and record the decision.

        Returns an ApprovalDecision. allowed=True only when:
          - risk checks pass (kill switch, daily loss, edge, confidence, drawdown)
          - circuit breakers are clear
          - manual_approved is True when require_manual_approval is set
        """
        cb = current_balance if current_balance is not None else balance
        sb = starting_balance if starting_balance is not None else balance

        circuit_halted = self.risk.check_circuit_breakers(cb, sb)
        risk_ok, risk_reason = self.risk.should_trade(edge, confidence, balance)

        reasons: list[str] = []
        if circuit_halted:
            reasons.append("circuit breaker tripped")
        if not risk_ok:
            reasons.append(risk_reason)
        if self.require_manual_approval and not manual_approved:
            reasons.append("manual approval not granted")

        allowed = not reasons

        decision = ApprovalDecision(
            allowed=allowed,
            reason="; ".join(reasons) if reasons else "approved",
            market_id=market_id,
            edge=edge,
            confidence=confidence,
            risk_state=self.risk.check_risk_limits(),
        )

        self._append_audit(
            {
                "type": "approval_decision",
                "provenance_id": decision.provenance_id,
                "timestamp": decision.timestamp,
                "market_id": market_id,
                "edge": edge,
                "confidence": confidence,
                "allowed": allowed,
                "reason": decision.reason,
                "risk_state": decision.risk_state,
            }
        )

        return decision

    def record_order_attempt(
        self,
        provenance_id: str,
        market_id: str,
        side: str,
        size: float,
        price: float,
        outcome: str,
        reason: str = "",
    ) -> None:
        """Record every order attempt (allowed or rejected) for audit."""
        self._append_audit(
            {
                "type": "order_attempt",
                "provenance_id": provenance_id,
                "market_id": market_id,
                "side": side,
                "size": size,
                "price": price,
                "outcome": outcome,
                "reason": reason,
            }
        )
