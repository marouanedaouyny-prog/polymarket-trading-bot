"""
Builder profile and fee management module.
"""

class BuilderProfile:
    """Manages the builder profile and fees for the Polymarket bot."""

    def __init__(self, builder_code: str = "default_builder"):
        self.builder_code = builder_code
        self.builder_fees_enabled = False
        self.fee_percentage = 0.0  # Default no fees

    def set_builder_code(self, code: str):
        """Set the builder code for the bot."""
        self.builder_code = code

    def enable_builder_fees(self, fee_percentage: float = 0.1):
        """Enable builder fees with a percentage."""
        self.builder_fees_enabled = True
        self.fee_percentage = fee_percentage

    def get_builder_info(self) -> dict:
        """Get builder profile information."""
        return {
            "builder_code": self.builder_code,
            "fees_enabled": self.builder_fees_enabled,
            "fee_percentage": self.fee_percentage if self.builder_fees_enabled else 0.0
        }

    def calculate_builder_fees(self, trade_amount: float) -> float:
        """Calculate builder fees for a trade."""
        if self.builder_fees_enabled:
            return trade_amount * self.fee_percentage
        return 0.0