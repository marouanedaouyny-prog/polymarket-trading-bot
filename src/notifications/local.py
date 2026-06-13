import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class LocalNotifier:
    def __init__(self, log_file: str = "data/notifications.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, level: str, message: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        pass  # Logging to file only

    def send_message(self, message: str) -> bool:
        self._log("INFO", message)
        return True

    async def send_message_async(self, message: str) -> bool:
        self._log("INFO", message)
        return True

    async def send_trade_alert(self, trade: dict) -> bool:
        msg = f"Trade: {trade.get('direction')} {trade.get('symbol')} ${trade.get('amount')} | PnL: ${trade.get('pnl', 0):.2f}"
        self._log("TRADE", msg)
        return True

    async def send_stop_loss(self, trade: dict, loss: float) -> bool:
        self._log("STOP_LOSS", f"Stop loss triggered! Loss: ${loss:.2f} | Symbol: {trade.get('symbol')}")
        return True

    async def send_daily_summary(self, stats: dict) -> bool:
        msg = f"Daily: {stats.get('total_trades')} trades | Win Rate: {stats.get('win_rate', 0):.1f}% | PnL: ${stats.get('total_pnl', 0):.2f}"
        self._log("SUMMARY", msg)
        return True

    def get_recent(self, count: int = 10) -> list:
        if not self.log_file.exists():
            return []
        with open(self.log_file, "r") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-count:]]


class WindowsToastNotifier:
    def send(self, title: str, message: str) -> bool:
        try:
            import win32api
            import win32con
            win32api.MessageBox(0, message, title, win32con.MB_OK)
            return True
        except:
            return self._powershell_toast(title, message)

    def _powershell_toast(self, title: str, message: str) -> bool:
        import subprocess
        script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $text = $template.GetElementsByTagName("text")
        $text[0].AppendChild($template.CreateTextNode("{title}")) | Out-Null
        $text[1].AppendChild($template.CreateTextNode("{message}")) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Polymarket Bot").Show($toast)
        '''
        try:
            subprocess.run(["powershell", "-Command", script], capture_output=True)
            return True
        except:
            return False