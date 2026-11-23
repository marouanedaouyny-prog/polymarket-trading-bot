import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
import app.config
print("LLM_API_KEY:", app.config.Config.LLM_API_KEY[:20] if app.config.Config.LLM_API_KEY else "None")
print("ZEP_API_KEY:", app.config.Config.ZEP_API_KEY[:20] if app.config.Config.ZEP_API_KEY else "None")

# Now test LLM directly
from app.utils.llm_client import LLMClient
llm = LLMClient()
try:
    r = llm.chat([{"role": "user", "content": "Say hello in 3 words"}], max_tokens=50)
    print("LLM works:", r)
except Exception as e:
    print("LLM error:", str(e)[:200])
