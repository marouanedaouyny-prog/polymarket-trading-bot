"""
Self-Healing System Orchestrator
Concurrently manages API, Frontend, and Trading Bot with health monitoring.
"""

import atexit
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

class Orchestrator:
    def __init__(self):
        self.processes = {}
        self.root = os.path.dirname(os.path.abspath(__file__))
        self.frontend_dir = os.path.join(self.root, "frontend")
        self.is_running = True

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ORCHESTRATOR] {msg}")

    def start_service(self, name, command, cwd=None):
        self.log(f"Starting {name}...")
        p = subprocess.Popen(command, cwd=cwd or self.root)
        self.processes[name] = {
            'process': p,
            'command': command,
            'cwd': cwd or self.root,
            'starts': self.processes.get(name, {}).get('starts', 0) + 1
        }
        return p

    def cleanup(self):
        self.is_running = False
        self.log("Stopping all services...")
        for name, data in self.processes.items():
            p = data['process']
            if p.poll() is None:
                self.log(f"Terminating {name}...")
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
        self.log("All services stopped.")

    def run(self):
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, lambda _s, _f: sys.exit(0))

        # 1. Start API
        self.start_service("API", [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"])
        time.sleep(2)

        # 2. Start Frontend
        self.start_service("Frontend", ["npm.cmd", "run", "dev"] if sys.platform == "win32" else ["npm", "run", "dev"], cwd=self.frontend_dir)
        time.sleep(2)

        # 3. Start Trading Bot ($50 Live Training Mode)
        self.start_service("TradingBot", [sys.executable, "live_sim_50.py"])

        self.log("=" * 60)
        self.log("FULL TRADING STACK RUNNING")
        self.log("API:      http://localhost:8000")
        self.log("Frontend: http://localhost:3333/dashboard")
        self.log("=" * 60)

        while self.is_running:
            for name, data in self.processes.items():
                p = data['process']
                if p.poll() is not None:
                    if p.returncode == 0:
                        self.log(f"✅ {name} finished successfully.")
                        continue

                    self.log(f"⚠️ {name} stopped unexpectedly (Exit code: {p.returncode})")
                    if data['starts'] < 5:
                        self.log(f"Attempting to restart {name} (Attempt {data['starts']+1})...")
                        self.start_service(name, data['command'], data['cwd'])
                    else:
                        self.log(f"❌ {name} failed too many times. Manual intervention required.")
            time.sleep(5)

if __name__ == "__main__":
    Orchestrator().run()
