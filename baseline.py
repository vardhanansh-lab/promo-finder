"""Naive baseline: the last ~40s of every episode (episodes already end on cliffhangers).
Scored with the SAME blind-viewer and judge steps as the real pipeline, so the comparison is fair.
  python baseline.py data/show1 [--out outputs/baseline] [--run-id r1]"""
import argparse, json, os, statistics as st
from promofinder.llm import LLM
from promofinder.parse import load_show
from promofinder import pipeline as P

def tail_clip(ep, target=40.0):
    ev = [e for e in ep.events if e.kind != "CAMERA"]
    lo = max(0.0, ep.duration - target)
    starts = [e.start for e in ev if e.start >= lo - 0.01]
    s = starts[0] if starts else ev[0].start
    dl = [e for e in ev if e.kind == "DIALOGUE" and e.end > s]
    first, last = dl[0], dl[-1]
    return {"id": f"B{ep.number:02d}", "source": "baseline_tail",
            "segments": [{"episode": ep.number, "start": round(s, 2), "end": round(ep.duration, 2)}],
            "duration": round(ep.duration - s, 2), "cross_episode": False,
            "hook": {"quote": first.text, "type": "", "at": first.start, "offset_in_clip": round(first.start - s, 2)},
            "cliffhanger": {"quote": last.text, "type": "", "at": last.end}, "why": "baseline: last 40s", "issues": []}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--out", default="outputs/baseline")
    ap.add_argument("--run-id", default="r1"); ap.add_argument("--ranked", default="outputs/run1/ranked_promos.json")
    a = ap.parse_args()
    eps = load_show(a.folder); llm = LLM()
    cands = [tail_clip(e) for e in eps]
    cands = [c for c in cands if P.MIN_DUR <= c["duration"] <= P.MAX_DUR]
    print(f"{len(cands)} baseline clips")
    P.blind_test(llm, cands, eps, a.run_id); P.judge(llm, cands, eps, a.run_id)
    for c in cands: P.score(c)
    os.makedirs(a.out, exist_ok=True)
    json.dump(cands, open(os.path.join(a.out, "scored.json"), "w"), indent=2)
    ok = [c for c in cands if c["score"] is not None]
    lines = [f"baseline (last ~40s of each episode): n={len(ok)}, mean score {st.mean(c['score'] for c in ok):.1f}, "
             f"mean standalone {st.mean(c['score_parts']['standalone'] for c in ok)/2.5+1:.2f}/5"]
    if os.path.exists(a.ranked):
        r = json.load(open(a.ranked))
        for k in (10, 25):
            top = r[:k]
            if top:
                lines.append(f"pipeline top-{len(top)}: mean score {st.mean(c['score'] for c in top):.1f}")
        med = st.median(c["score"] for c in r[:25])
        lines.append(f"share of baseline clips scoring below the pipeline top-25 median ({med:.1f}): "
                     f"{sum(c['score'] < med for c in ok)/len(ok):.0%}")
    open(os.path.join(a.out, "summary.txt"), "w").write("\n".join(lines))
    print("\n".join(lines))
