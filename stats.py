"""One-shot facts for the write-up.  python stats.py [outputs/run1]"""
import json, re, sys, statistics as st, collections, os
d = sys.argv[1] if len(sys.argv) > 1 else "outputs/run1"
J = lambda n: json.load(open(f"{d}/{n}"))
raw, rej, allc, rk, meta = J("raw_llm_candidates.json"), J("rejected_by_validators.json"), J("all_scored_candidates.json"), J("ranked_promos.json"), J("show_meta.json")
fail = [r["episode"] for r in raw if r.get("error")]
prop = sum(len(r["candidates"]) for r in raw)
print(f"episodes {len(meta)}  runtime {sum(m['duration'] for m in meta)/60:.1f} min")
print(f"extraction failed for episodes: {fail or 'none'}")
print(f"candidates proposed {prop}; rejected by code {len(rej)}; kept {len(allc)}; scored {sum(c.get('score') is not None for c in allc)}; ranked {len(rk)}")
reasons = collections.Counter()
for r in rej:
    t = r["reason"]
    reasons["hook quote not in clip (invented)" if "hook quote" in t else "cliffhanger quote not in clip (invented)" if "cliffhanger quote" in t
            else "duration outside 20-60s" if "duration" in t else "timestamp not near a real line" if "not near" in t
            else "overlaps better clip" if "overlaps" in t else t[:40]] += 1
print("rejections:", dict(reasons))
sn = collections.Counter(re.sub(r"\d+(\.\d+)?s", "Ns", i.split(" (")[0])[:60] for c in allc for i in c["issues"]); print("fixes/flags on kept clips:", dict(sn))
sc = [c["score"] for c in allc if c.get("score") is not None]
if sc: print(f"score all kept: mean {st.mean(sc):.1f} min {min(sc)} max {max(sc)}; ranked mean {st.mean(c['score'] for c in rk):.1f}")
bl = [c["blind"]["standalone"] for c in allc if c.get("blind") and isinstance(c["blind"].get("standalone"), (int, float))]
if bl: print(f"cold-viewer standalone (1-5): mean {st.mean(bl):.2f}; share <=2: {sum(b<=2 for b in bl)/len(bl):.0%}; n={len(bl)}")
print("multi-segment clips in ranked:", sum(len(c['segments']) > 1 for c in rk), "| episodes represented:", len({c['segments'][0]['episode'] for c in rk}))
print("ranked clips with warnings:", sum(any(i.startswith(('hook lands','cliffhanger quote is')) for i in c['issues']) for c in rk))
print("\nTOP 10")
for c in rk[:10]:
    print(f"#{c['rank']} {' + '.join('Ep%d %.0f-%.0fs' % (s['episode'], s['start'], s['end']) for s in c['segments'])} {c['duration']}s score {c['score']} standalone {(c.get('blind') or {}).get('standalone')}")
    print(f"   HOOK: {c['hook']['quote'][:110]}\n   CLIFF: {c['cliffhanger']['quote'][:110]}")
print("\nLOWEST 3 RANKED (failure candidates)")
for c in rk[-3:]:
    print(f"#{c['rank']} Ep{c['segments'][0]['episode']} score {c['score']} parts {c.get('score_parts')} blind: {(c.get('blind') or {}).get('confusion')}")
lg = "outputs/llm_log.jsonl"
if os.path.exists(lg):
    m = collections.Counter(); ti = to = 0
    for ln in open(lg):
        r = json.loads(ln); m[r["model"]] += 1; u = r.get("usage") or {}; ti += u.get("prompt_tokens", 0); to += u.get("completion_tokens", 0)
    print("\nmodel calls (fresh calls only, cached reruns not logged):", dict(m), f"| tokens in {ti:,} out {to:,}")
