import sys, os

sys.stdout = sys.stderr
print("=== STARTUP ===", flush=True)

try:
    from api.main import app
    print("IMPORT OK", flush=True)
except Exception as e:
    print(f"IMPORT FAILED: {e}", flush=True)
    sys.exit(1)

import uvicorn
print("RUNNING UVICORN", flush=True)
uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
