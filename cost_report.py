"""Token use and cost projection from the real call log.
  python cost_report.py [--price-in 0.30 --price-out 2.50]   (USD per 1M tokens, ASSUMED: set to your model's real price)"""
import argparse, json, collections
ap = argparse.ArgumentParser(); ap.add_argument("--log", default="outputs/llm_log.jsonl")
ap.add_argument("--price-in", type=float, default=0.30); ap.add_argument("--price-out", type=float, default=2.50)
ap.add_argument("--shows-per-month", type=int, default=40); a = ap.parse_args()
n = collections.Counter(); pin = collections.Counter(); pout = collections.Counter(); models = collections.Counter()
for ln in open(a.log):
    r = json.loads(ln); u = r.get("usage") or {}; k = (r["tag"] or "x").split("_")[0]
    n[k] += 1; pin[k] += u.get("prompt_tokens", 0); pout[k] += u.get("completion_tokens", 0); models[r["model"]] += 1
tin, tout = sum(pin.values()), sum(pout.values())
print("calls by step:", dict(n)); print("calls by model:", dict(models))
print(f"tokens logged: {tin:,} in, {tout:,} out ({sum(n.values())} calls)")
cost = tin / 1e6 * a.price_in + tout / 1e6 * a.price_out
print(f"cost at ${a.price_in}/${a.price_out} per 1M (in/out): ${cost:.2f} for this log")
print(f"projection: {a.shows_per_month} shows/month x 1 pass each ~= ${cost * a.shows_per_month:.0f}/month (assumes this log is one 50-episode show)")
