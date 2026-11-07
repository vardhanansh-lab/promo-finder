"""Two-model agreement tiers.  python agreement.py outputs/run1 outputs/run2 [K=25]
Tier 1: both runs (different models) picked the same moment -> post-ready.
Tier 2: only one run picked it -> human review queue."""
import csv, json, sys
from promofinder.pipeline import overlap, clip_label
A = json.load(open(sys.argv[1] + "/ranked_promos.json")); B = json.load(open(sys.argv[2] + "/ranked_promos.json"))
K = int(sys.argv[3]) if len(sys.argv) > 3 else 25
A, B = A[:K], B[:K]; rows = []; usedB = set()
for a in A:
    m = next((b for b in B if overlap(a, b) > 0.5 and b["id"] not in usedB), None)
    if m: usedB.add(m["id"])
    rows.append(("Tier 1 (both models)" if m else "Tier 2 (run A only)", a, m))
for b in B:
    if b["id"] not in usedB: rows.append(("Tier 2 (run B only)", b, None))
rows.sort(key=lambda r: (r[0][:6], r[1]["rank"]))
with open("outputs/agreement_tiers.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["tier", "clip", "rank_A", "rank_B", "score", "hook", "cliffhanger"])
    for t, c, m in rows:
        w.writerow([t, clip_label(c), c["rank"] if "run B only" not in t else "", (m or c)["rank"] if (m or "run B only" in t) else "", c["score"], c["hook"]["quote"], c["cliffhanger"]["quote"]])
t1 = sum(r[0].startswith("Tier 1") for r in rows)
print(f"Tier 1 (post-ready): {t1}   Tier 2 (review queue): {len(rows)-t1}   -> outputs/agreement_tiers.csv")
print(f"agreement rate: {t1/len(A):.0%} of run A's top-{len(A)}")
