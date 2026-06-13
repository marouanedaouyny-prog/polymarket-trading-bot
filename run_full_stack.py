"""
Start API backend and Stitch-based frontend.
"""

import atexit
import os
import signal
import subprocess
import sys
import time

processes = []


def cleanup() -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    print("\nAll services stopped")


def main() -> None:
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda _s, _f: sys.exit(0))

    root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root, "frontend")

    print("Starting Polymarket full stack")
    print("=" * 50)

    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=root)
    processes.append(api)
    time.sleep(2)

    frontend = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir)
    processes.append(frontend)
    time.sleep(2)

    print("API:      http://localhost:8000")
    print("Docs:     http://localhost:8000/docs")
    print("Frontend: http://localhost:3333/dashboard")
    print("Press Ctrl+C to stop")

    while True:
        if api.poll() is not None:
            raise RuntimeError("API process stopped unexpectedly")
        if frontend.poll() is not None:
            raise RuntimeError("Frontend process stopped unexpectedly")
        time.sleep(1)


if __name__ == "__main__":
    main()
