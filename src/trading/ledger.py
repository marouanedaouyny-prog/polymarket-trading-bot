"""
Strict Paper Trading Ledger for production-grade auditing.
"""

import os
import json
import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class PaperLedger:
    def __init__(self, ledger_dir="data/results"):
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.ledger_dir / "paper_ledger.json"
        self.csv_path = self.ledger_dir / "paper_ledger.csv"
        
        if not self.json_path.exists():
            self._save_json([])
        if not self.csv_path.exists():
            self._init_csv()

    def _init_csv(self):
        headers = [
            "trade_id", "entry_timestamp", "market_id", "canonical_id", 
            "selected_outcome", "entry_price", "model_probability", 
            "ev", "edge", "bet_size", "fees", "slippage", 
            "resolution_timestamp", "actual_outcome", "realized_pnl"
        ]
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(headers)

    def _load_json(self) -> List[Dict]:
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_json(self, data: List[Dict]):
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def record_entry(self, trade_data: Dict[str, Any]) -> str:
        """Record trade entry, return unique trade_id."""
        trade_id = str(uuid.uuid4())
        trades = self._load_json()
        
        entry = {
            "trade_id": trade_id,
            "entry_timestamp": datetime.now().isoformat(),
            "market_id": trade_data.get('market_id'),
            "canonical_id": trade_data.get('canonical_id'),
            "selected_outcome": trade_data.get('selected_outcome'),
            "entry_price": trade_data.get('entry_price'),
            "model_probability": trade_data.get('model_probability'),
            "ev": trade_data.get('ev'),
            "edge": trade_data.get('edge'),
            "bet_size": trade_data.get('bet_size'),
            "fees": trade_data.get('fees', 0),
            "slippage": trade_data.get('slippage', 0),
            "resolution_timestamp": None,
            "actual_outcome": None,
            "realized_pnl": None
        }
        trades.append(entry)
        self._save_json(trades)
        return trade_id

    def record_resolution(self, trade_id: str, actual_outcome: str, realized_pnl: float) -> bool:
        """Record resolution, validate data completeness."""
        if actual_outcome not in ["yes", "no"]:
            raise ValueError("actual_outcome must be 'yes' or 'no'")
            
        trades = self._load_json()
        for t in trades:
            if t['trade_id'] == trade_id and t.get('actual_outcome') is None:
                t['resolution_timestamp'] = datetime.now().isoformat()
                t['actual_outcome'] = actual_outcome
                t['realized_pnl'] = realized_pnl
                self._save_json(trades)
                self._append_to_csv(t)
                return True
        return False

    def _append_to_csv(self, t: Dict):
        row = [t.get(h) for h in [
            "trade_id", "entry_timestamp", "market_id", "canonical_id", 
            "selected_outcome", "entry_price", "model_probability", 
            "ev", "edge", "bet_size", "fees", "slippage", 
            "resolution_timestamp", "actual_outcome", "realized_pnl"
        ]]
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(row)

    def get_stats(self) -> Dict:
        trades = self._load_json()
        resolved = [t for t in trades if t.get('actual_outcome') is not None]
        
        if not resolved:
            return {"total_resolved": 0, "pnl": 0, "win_rate": 0}
            
        wins = [t for t in resolved if t['realized_pnl'] > 0]
        losses = [t for t in resolved if t['realized_pnl'] <= 0]
        
        gross_profit = sum(t['realized_pnl'] for t in wins)
        gross_loss = abs(sum(t['realized_pnl'] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        total_pnl = sum(t['realized_pnl'] for t in resolved)
        
        # Max Drawdown
        peak, max_dd, running_pnl = 0, 0, 0
        for t in resolved:
            running_pnl += t['realized_pnl']
            if running_pnl > peak: peak = running_pnl
            dd = peak - running_pnl
            if dd > max_dd: max_dd = dd
        
        return {
            "total_resolved": len(resolved),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(resolved),
            "total_pnl": total_pnl,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd
        }
