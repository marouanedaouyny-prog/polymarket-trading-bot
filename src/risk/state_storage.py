"""
Utility for persisting DynamicRiskManager state between runs.
"""
import json
from pathlib import Path
from typing import Dict

STATE_FILE = Path(__file__).parent.parent / 'data' / 'risk_state.json'

def save_state(state: Dict) -> None:
    """Write the risk manager state to disk safely."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with STATE_FILE.open('w', encoding='utf-8') as f:
            json.dump(state, f)
    except Exception as e:
        # Use the central logger if available
        try:
            from src.utils.logger import get_logger
            get_logger('risk_state').error(f"Failed to save risk state: {e}")
        except Exception:
            pass

def load_state() -> Dict:
    """Load persisted state; returns empty dict if not present or corrupted."""
    if not STATE_FILE.is_file():
        return {}
    try:
        with STATE_FILE.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        try:
            from src.utils.logger import get_logger
            get_logger('risk_state').error(f"Failed to load risk state: {e}")
        except Exception:
            pass
        return {}
