"""Build a blind review sheet: pipeline top clips + random lower-ranked clips + baseline clips, shuffled,
scores and sources hidden. You label keep / edit / reject. Then run eval_labels.py.
  python label_sheet.py data/show1 [--run outputs/run1] [--baseline outputs/baseline]"""
import argparse, csv, json, os, random
from promofinder.parse import load_show, fmt
from promofinder.render import render_clip
from promofinder.pipeline import clip_label
ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--run", default="outputs/run1")
ap.add_argument("--baseline", default="outputs/baseline"); ap.add_argument("--n-rand", type=int, default=10)
ap.add_argument("--n-base", type=int, default=10); ap.add_argument("--top", type=int, default=25)
a = ap.parse_args(); random.seed(7)
by = {e.number: e for e in load_show(a.folder)}
ranked = json.load(open(f"{a.run}/ranked_promos.json"))[: a.top]
allc = json.load(open(f"{a.run}/all_scored_candidates.json"))
rid = {c["id"] for c in ranked}
rest = [c for c in allc if c["id"] not in rid and c.get("score") is not None]
rows = [("pipeline_top", c) for c in ranked] + [("pipeline_lower", c) for c in random.sample(rest, min(a.n_rand, len(rest)))]
bp = f"{a.baseline}/scored.json"
if os.path.exists(bp):
    base = [c for c in json.load(open(bp)) if c.get("score") is not None]
    rows += [("baseline", c) for c in random.sample(base, min(a.n_base, len(base)))]
random.shuffle(rows)
os.makedirs(f"{a.run}/../review", exist_ok=True); d = f"{a.run}/../review"
key = {}
with open(f"{d}/label_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["sheet_id", "where_in_show", "duration_s", "clip_text", "verdict (keep / edit / reject)", "note (why)"])
    for i, (src, c) in enumerate(rows, 1):
        sid = f"L{i:02d}"
        key[sid] = {"id": c["id"], "source": src, "rank": c.get("rank"), "score": c.get("score"),
                    "score_parts": c.get("score_parts"), "blind_standalone": (c.get("blind") or {}).get("standalone")}
        w.writerow([sid, clip_label(c), c["duration"], render_clip(by, c["segments"]), "", ""])
json.dump(key, open(f"{d}/label_key.json", "w"), indent=2)
print(f"{len(rows)} clips -> {d}/label_sheet.csv  (fill the verdict column; keep label_key.json private)")
