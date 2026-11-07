"""Stability check: how much do two runs agree?  python compare.py outputs/run1 outputs/run2 [K]"""
import json, sys
from promofinder.pipeline import overlap
a = json.load(open(sys.argv[1] + "/ranked_promos.json"))
b = json.load(open(sys.argv[2] + "/ranked_promos.json"))
K = int(sys.argv[3]) if len(sys.argv) > 3 else 15
A, B = a[:K], b[:K]
match = [(x["rank"], y["rank"]) for x in A for y in B if overlap(x, y) > 0.5]
print(f"top-{K}: {len({m[0] for m in match})} of {len(A)} clips from run A are also in run B's top-{K}")
print("pairs (rankA, rankB):", sorted(match))
