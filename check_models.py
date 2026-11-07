"""List usable models for your keys, and optionally ping one.
  python check_models.py                       # list Gemini + free OpenRouter models
  python check_models.py --ping "gemini|<name>"  # one live test call
"""
import json, os, sys, urllib.request
from promofinder.llm import load_env, LLM, PROVIDERS
load_env()

def get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

if "--ping" in sys.argv:
    spec = sys.argv[sys.argv.index("--ping") + 1]
    llm = LLM(models=[spec], use_cache=False)
    print(llm.chat("Reply with exactly: OK", "ping", max_tokens=50, expect_json=False, tag="ping"))
    sys.exit()

k = os.environ.get("GEMINI_API_KEY")
if k:
    try:
        ms = get(PROVIDERS["gemini"][0] + "/models", k)["data"]
        ids = sorted(m["id"].replace("models/", "") for m in ms)
        print("GEMINI models (use as  gemini|<name>):")
        for i in ids:
            if "gemini" in i and "embed" not in i and "image" not in i and "tts" not in i:
                print("  ", i)
    except Exception as e:
        print("Gemini list failed:", e)
k = os.environ.get("OPENROUTER_API_KEY")
if k:
    try:
        ms = get(PROVIDERS["openrouter"][0] + "/models", k)["data"]
        free = [m for m in ms if str(m.get("pricing", {}).get("prompt")) == "0" and str(m.get("pricing", {}).get("completion")) == "0"]
        free.sort(key=lambda m: -(m.get("context_length") or 0))
        print("\nOPENROUTER free models, biggest context first (use as  openrouter|<id>):")
        for m in free[:20]:
            print(f"   {m['id']}   ctx={m.get('context_length')}")
    except Exception as e:
        print("OpenRouter list failed:", e)