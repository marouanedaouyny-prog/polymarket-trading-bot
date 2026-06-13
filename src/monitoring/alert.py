"""
Simple alerting utility. In production you would configure an email/SMS webhook.
The Alert class provides `send` which logs and optionally posts to a webhook URL.
"""
import os
import logging
import requests

logger = logging.getLogger('polymarket_alert')
logger.setLevel(logging.INFO)

class Alert:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv('ALERT_WEBHOOK_URL')

    def send(self, title: str, message: str, level: str = 'info'):
        """Send an alert.
        level: 'info', 'warning', 'error'
        """
        payload = {
            'title': title,
            'message': message,
            'level': level,
        }
        logger.info(f"Alert [{level.upper()}] {title}: {message}")
        if self.webhook_url:
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=5)
                if resp.status_code != 200:
                    logger.warning(f"Webhook returned {resp.status_code}")
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
