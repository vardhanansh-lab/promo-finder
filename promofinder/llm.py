"""Thin, swappable LLM client.

Any OpenAI-compatible endpoint works (OpenRouter by default). Models are a
fallback chain: if one is rate limited or returns bad JSON, the next is tried.
Every call is cached on disk (so re-runs are free and raw outputs are
reproducible) and logged to outputs/llm_log.jsonl.

Config via env vars or .env:
  OPENROUTER_API_KEY, GEMINI_API_KEY   (set whichever you have)
  LLM_MODELS   comma separated, tried in order. Format  provider|model
               e.g.  gemini|gemini-2.5-flash,openrouter|<some-model>:free
               providers: openrouter, gemini. Any other OpenAI-compatible
               endpoint: leave the prefix off and set LLM_BASE_URL + LLM_API_KEY.
"""
from __future__ import annotations

import hashlib
import threading
import json
import os
import re
import time
import http.client
import urllib.request
import urllib.error

CACHE_DIR = os.environ.get("PROMO_CACHE", "outputs/cache")
LOG_PATH = os.environ.get("PROMO_LOG", "outputs/llm_log.jsonl")


def load_env(path=".env"):
    if os.path.exists(path):
        for ln in open(path):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


load_env()


PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
}


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (handles ``` fences)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        a, b = text.find(opener), text.rfind(closer)
        if a != -1 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no valid JSON in reply")


class LLM:
    def __init__(self, models=None, api_key=None, base_url=None, min_interval=4.0,
                 temperature=0.2, use_cache=True):
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
        env_models = os.environ.get("LLM_MODELS", "")
        self.models = models or [m.strip() for m in env_models.split(",") if m.strip()]
        self.min_interval = min_interval  # ~18 req/min, under the free 20/min cap
        self.temperature = temperature
        self.use_cache = use_cache
        self._last = 0.0
        self._lock = threading.Lock()
        self._dead = {}   # model spec -> time until which it is skipped (quota hit)
        self._idx = None
        self._idx_lock = threading.Lock()
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)

    def _legacy_index(self):
        """Index every cached reply by sha(system+user), so swapping models never throws away paid-for calls.
        Built once, under a lock, and published only when complete (worker threads must never see a half-built index)."""
        with self._idx_lock:
            if self._idx is None:
                idx = {}
                for fn in os.listdir(CACHE_DIR):
                    if not fn.endswith(".json"):
                        continue
                    try:
                        raw = open(os.path.join(CACHE_DIR, fn), "rb").read()
                        try:
                            txt = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            txt = raw.decode("cp1252", "replace")
                        r = json.loads(txt)
                        k = hashlib.sha256((r["system"] + "\x00" + r["user"]).encode()).hexdigest()[:24]
                        idx[k] = r["parsed"]
                    except Exception:
                        pass
                self._idx = idx
            return self._idx

    # ---- low level
    def _resolve(self, spec):
        """'gemini|gemini-2.5-flash' -> (model, base_url, api_key)."""
        if "|" in spec:
            prov, model = spec.split("|", 1)
            prov = prov.strip().lower()
            if prov not in PROVIDERS:
                raise RuntimeError(f"unknown provider {prov!r}; use one of {list(PROVIDERS)}")
            base, keyvar = PROVIDERS[prov]
            return model.strip(), base, os.environ.get(keyvar)
        return spec, self.base_url, self.api_key

    def _post(self, spec, messages, max_tokens):
        model, base, key = self._resolve(spec)
        if not key:
            raise urllib.error.HTTPError(base, 401, "missing API key for " + spec, None, None)
        # thinking models spend part of the budget on reasoning, so leave headroom
        body = json.dumps({"model": model, "messages": messages, "temperature": self.temperature,
                           "max_tokens": min(max_tokens * 2, 12000)}).encode()
        req = urllib.request.Request(
            base + "/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://example.com/promo-finder", "X-Title": "Promo Finder"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())

    def chat(self, system: str, user: str, max_tokens=4000, expect_json=True, tag="", wait=True):
        if not self.models:
            raise RuntimeError("No models. Put LLM_MODELS=gemini|gemini-2.5-flash,... in .env")
        key = hashlib.sha256((system + "\x00" + user).encode()).hexdigest()[:24]
        cpath = os.path.join(CACHE_DIR, key + ".json")
        if self.use_cache:
            if os.path.exists(cpath):
                return json.load(open(cpath))["parsed"]
            hit = self._legacy_index().get(key)   # replies cached before the key ignored the model list
            if hit is not None:
                return hit
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        last_err = None
        for model in self.models:
            if self._dead.get(model, 0) > time.time():
                continue
            for attempt in range(3):
                with self._lock:   # global pacing across threads
                    now = time.time()
                    slot = max(now, self._last + self.min_interval)
                    self._last = slot
                if slot > now:
                    time.sleep(slot - now)
                try:
                    resp = self._post(model, messages, max_tokens)
                    content = resp["choices"][0]["message"]["content"] or ""
                    parsed = extract_json(content) if expect_json else content
                    rec = {"tag": tag, "model": model, "system": system, "user": user,
                           "reply": content, "parsed": parsed,
                           "usage": resp.get("usage"), "ts": time.time()}
                    json.dump(rec, open(cpath, "w"))
                    with open(LOG_PATH, "a") as f:
                        f.write(json.dumps({k: rec[k] for k in ("tag", "model", "usage", "ts")}) + "\n")
                    return parsed
                except urllib.error.HTTPError as e:
                    last_err = f"{model} HTTP {e.code}"
                    if e.code == 429:
                        try:
                            body = e.read().decode("utf-8", "ignore").lower()
                        except Exception:
                            body = ""
                        daily = any(k in body for k in ("perday", "per day", "daily", "per_day"))
                        if daily or attempt >= 1:   # per-minute limit: park ~75s; daily quota: park 1h
                            wait = 3600 if daily else 75
                            self._dead[model] = time.time() + wait
                            print(f"  [llm] {model} {'daily quota' if daily else 'rate'} limited, parked {wait}s")
                            break
                        time.sleep(20)
                        continue
                    if e.code in (400, 401, 402, 403, 404):  # bad key / model unavailable: next model
                        break
                    time.sleep(5)
                except (ValueError, KeyError, OSError, http.client.HTTPException) as e:   # includes dropped connections (WinError 10054)
                    last_err = f"{model} {type(e).__name__}: {e}"
                    time.sleep(5)
        # every model parked or failed: wait for the earliest one to recover, once
        if self._dead and all(self._dead.get(m, 0) > time.time() for m in self.models):
            if not wait:
                raise RuntimeError("all models limited (not waiting)")
            soon = min(self._dead.values()) - time.time()
            print(f"  [llm] all models limited; waiting {soon:.0f}s")
            time.sleep(max(1, soon))
            self._dead.clear()
            return self.chat(system, user, max_tokens, expect_json, tag, wait)
        raise RuntimeError(f"All models failed. Last error: {last_err}")
