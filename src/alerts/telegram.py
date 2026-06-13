"""
Telegram Alert System for Trading Bot
Sends notifications for trades, errors, and performance alerts
"""

import os
import json
import requests
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class AlertConfig:
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    enabled: bool = False
    
    # Alert thresholds
    notify_on_trade: bool = True
    notify_on_error: bool = True
    notify_on_milestone: bool = True  # e.g., double balance
    balance_alert_threshold: float = 0.0  # 0 = disabled


class TelegramAlerts:
    def __init__(self, config: AlertConfig = None):
        self.config = config or AlertConfig()
        self.last_balance = 0
        
    def load_config(self):
        """Load config from environment or config file"""
        self.config.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.config.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.config.enabled = bool(self.config.telegram_bot_token and self.config.telegram_chat_id)
        
        return self.config.enabled
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        if not self.config.enabled:
            return False
            
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        
        data = {
            "chat_id": self.config.telegram_chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[TELEGRAM] Failed to send: {e}")
            return False
    
    def format_trade_alert(self, trade: dict) -> str:
        """Format trade notification"""
        status = "[WIN]" if trade.get('won') else "[LOSS]"
        profit = trade.get('profit', 0)
        profit_str = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
        
        return f"""
[T] Trade Executed

{status} | Edge: {trade.get('edge', 0):.0%}
Bet: ${trade.get('bet', 0):.2f} @ ${trade.get('price', 0):.2f}
Profit: {profit_str}
Balance: ${trade.get('balance', 0):.2f}
"""
    
    def format_error_alert(self, error: str, context: str = "") -> str:
        """Format error notification"""
        return f"""
[E] Trading Bot Error

Error: {error}
Context: {context}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def format_milestone_alert(self, milestone: str, balance: float) -> str:
        """Format milestone notification"""
        return f"""
[M] Milestone Reached

{milestone}
Current Balance: ${balance:,.2f}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def format_session_summary(self, stats: dict) -> str:
        """Format session summary"""
        return f"""
[S] Session Summary

Trades: {stats.get('total', 0)}
Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}
Win Rate: {stats.get('win_rate', 0):.1f}%
Profit: ${stats.get('profit', 0):+.2f}
Balance: ${stats.get('balance', 0):,.2f}
"""
    
    # Convenience methods
    def notify_trade(self, trade: dict) -> bool:
        """Send trade notification"""
        if not self.config.notify_on_trade:
            return False
        return self.send_message(self.format_trade_alert(trade))
    
    def notify_error(self, error: str, context: str = "") -> bool:
        """Send error notification"""
        if not self.config.notify_on_error:
            return False
        return self.send_message(self.format_error_alert(error, context))
    
    def notify_milestone(self, milestone: str, balance: float) -> bool:
        """Send milestone notification"""
        if not self.config.notify_on_milestone:
            return False
        
        # Check if balance doubled from initial
        if balance >= self.last_balance * 2 and self.last_balance > 0:
            self.last_balance = balance
            return self.send_message(self.format_milestone_alert(milestone, balance))
        return False
    
    def notify_balance_alert(self, balance: float, threshold: float) -> bool:
        """Send balance threshold alert"""
        if threshold <= 0:
            return False
        if balance >= threshold:
            return self.send_message(self.format_milestone_alert(
                f"Balance reached ${balance:,.2f} (threshold: ${threshold:,.2f})",
                balance
            ))
        return False
    
    def send_session_summary(self, stats: dict) -> bool:
        """Send session summary"""
        return self.send_message(self.format_session_summary(stats))


def create_alert_system() -> TelegramAlerts:
    """Factory function to create alert system"""
    alerts = TelegramAlerts()
    alerts.load_config()
    return alerts


# Example usage
if __name__ == "__main__":
    # Test without config (will just print)
    alerts = TelegramAlerts()
    
    # Test messages
    print("Testing alert system...")
    
    test_trade = {
        'won': True,
        'profit': 45.67,
        'bet': 10.0,
        'price': 0.05,
        'edge': 0.95,
        'balance': 145.67
    }
    
    print(alerts.format_trade_alert(test_trade))
    print(alerts.format_error_alert("Connection timeout", "API call"))
    print(alerts.format_milestone_alert("Balance doubled!", 200.0))
    print(alerts.format_session_summary({
        'total': 50, 'wins': 45, 'losses': 5,
        'win_rate': 90.0, 'profit': 450.0, 'balance': 550.0
    }))
    
    print("\n[OK] Alert templates working!")
    print("\nTo enable Telegram alerts, set:")
    print("  TELEGRAM_BOT_TOKEN=your_token")
    print("  TELEGRAM_CHAT_ID=your_chat_id")