"""
Risk limits module — delegates to DynamicRiskManager.
Kept for backward-compatible imports.
"""

from .dynamic_risk import DynamicRiskManager

# Re-export with original class name for compatibility
RiskManager = DynamicRiskManager