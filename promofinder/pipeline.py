"""Promo finder pipeline.

AI does the judgment (find, blind-read, score). Code does everything that must
be exact: timestamps, snapping, duration limits, quote verification, final
ranking math and diversity.
"""
from __future__ import annotations

import csv
import concurrent.futures as _cf
import difflib
import json
import os
import re

from . import prompts
from .parse import Episode, load_show, fmt
from .render import render_episode, render_clip, norm

WORKERS = int(os.environ.get('PROMO_WORKERS', '4'))
MIN_DUR, MAX_DUR = 20.0, 60.0
HOOK_WINDOW = 3.5          # seconds: hook must land by here
SNAP_TOL = 2.0             # model times further than this from a real event edge are rejected
WEIGHTS = {"hook": 0.30, "cliffhanger": 0.30, "standalone": 0.20, "intensity": 0.10, "premise": 0.10}

_TS = re.compile(r"^\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\s*$")


def parse_ts(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    m = _TS.match(str(s))
    if not m:
        raise ValueError(f"bad timestamp {s!r}")
    h, mi, se = m.groups()
    return (int(h) * 3600 if h else 0) + int(mi) * 60 + float(se)


def pmap(fn, items):
    """Run fn over items in a small thread pool, results in input order."""
    if WORKERS <= 1:
        return [fn(x) for x in items]
    with _cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        return list(ex.map(fn, items))


# ---------------------------------------------------------------- extraction
def extract_candidates(llm, eps: list[Episode], run_id="r1", progress=print, targets=None):
    by = {e.number: e for e in eps}

    def one(ep):
        prev_ep, next_ep = by.get(ep.number - 1), by.get(ep.number + 1)
        user = [f"SHOW: 'I Married a Broken Soldier. He was a Duke' (English, US audience, period romance/revenge).",
                f"THIS EPISODE: {ep.number}  (length {fmt(ep.duration)})",
                f"Logline: {ep.logline}", f"Continuity: {ep.continuity}"]
        if prev_ep:
            user.append(f"Previous episode logline: {prev_ep.logline}")
        if next_ep:
            user.append(f"Next episode logline: {next_ep.logline}")
        user.append("\nSCREENPLAY (times are mm:ss.ss start-end):\n" + render_episode(ep))
        if next_ep:
            user.append(f"\nNEXT EPISODE OPENING (episode {next_ep.number}, first 40s, usable for cross-episode promos):\n"
                        + render_episode(next_ep, until=40.0))
        try:
            res = llm.chat(prompts.EXTRACT_SYSTEM + f"\n[run:{run_id}]", "\n".join(user),
                           max_tokens=3500, tag=f"extract_ep{ep.number}")
            cands = res.get("candidates", []) if isinstance(res, dict) else res
        except Exception as ex:  # keep going, record the failure
            progress(f"  EP{ep.number}: extraction failed: {ex}")
            return {"episode": ep.number, "error": str(ex), "candidates": []}
        progress(f"  EP{ep.number:02d}: {len(cands)} raw candidates")
        return {"episode": ep.number, "candidates": cands}

    return pmap(one, targets or eps)


# ---------------------------------------------------------------- validation
def _snap_start(ep: Episode, t: float):
    """Move to the start of the line that contains t, or of the nearest line start."""
    ev = [e for e in ep.events if e.kind != "CAMERA"]
    for e in ev:
        if e.start < t < e.end - 0.05 and e.kind == "DIALOGUE":
            return e.start, "start moved back to avoid cutting a line"
    nearest = min(ev, key=lambda e: abs(e.start - t))
    if abs(nearest.start - t) <= SNAP_TOL:
        return nearest.start, None if abs(nearest.start - t) < 0.06 else "start snapped"
    return None, "start not near any line"


def _snap_end(ep: Episode, t: float):
    ev = [e for e in ep.events if e.kind != "CAMERA"]
    for e in ev:
        if e.start < t < e.end - 0.05 and e.kind == "DIALOGUE":
            return e.end, "end moved forward to finish a line"
    nearest = min(ev, key=lambda e: abs(e.end - t))
    if abs(nearest.end - t) <= SNAP_TOL:
        return nearest.end, None if abs(nearest.end - t) < 0.06 else "end snapped"
    return None, "end not near any line"


def _match_event(quote: str, events, lo: float, hi: float):
    q = norm(quote)
    if len(q) < 4:
        return None
    best, best_r = None, 0.0
    for e in events:
        if e.kind == "CAMERA" or e.end < lo - 0.01 or e.start > hi + 0.01:
            continue
        t = norm(e.text)
        if not t:
            continue
        if q in t or t in q:
            r = 1.0
        else:
            r = difflib.SequenceMatcher(None, q, t).ratio()
            # allow quoting a long line partially
            if len(q) < len(t):
                r = max(r, difflib.SequenceMatcher(None, q, t[: len(q) + 10]).ratio())
        if r > best_r:
            best, best_r = e, r
    return (best, best_r) if best is not None and best_r >= 0.72 else None


def validate_candidates(raw, eps: list[Episode], source="llm"):
    by = {e.number: e for e in eps}
    good, rejected = [], []
    for item in raw:
        for ci, c in enumerate(item.get("candidates", [])):
            issues, cid = [], f"E{item['episode']:02d}-C{ci + 1}"
            try:
                segs = []
                for s in c["segments"]:
                    en = int(s["episode"])
                    if en not in by:
                        raise ValueError(f"unknown episode {en}")
                    ep = by[en]
                    a, b = parse_ts(s["start"]), parse_ts(s["end"])
                    a2, na = _snap_start(ep, a)
                    b2, nb = _snap_end(ep, b)
                    if a2 is None or b2 is None:
                        raise ValueError(na if a2 is None else nb)
                    for n_ in (na, nb):
                        if n_:
                            issues.append(n_)
                    if b2 - a2 < 3:
                        raise ValueError("segment shorter than 3s")
                    segs.append({"episode": en, "start": round(a2, 2), "end": round(b2, 2)})
                if not 1 <= len(segs) <= 3:
                    raise ValueError("1-3 segments allowed")
                # segments must be in order and not duplicated
                keyed = [(s["episode"], s["start"]) for s in segs]
                if keyed != sorted(keyed):
                    raise ValueError("segments out of order")
                dur = sum(s["end"] - s["start"] for s in segs)
                if not (MIN_DUR <= dur <= MAX_DUR):
                    raise ValueError(f"duration {dur:.1f}s outside 20-60s")
                # quote verification (anti-hallucination)
                first, last = segs[0], segs[-1]
                hk = _match_event(c.get("hook_quote", ""), by[first["episode"]].events,
                                  first["start"], first["end"])
                if not hk:
                    raise ValueError("hook quote not found in clip text")
                hook_off = max(0.0, hk[0].start - first["start"])
                if hook_off > HOOK_WINDOW:
                    issues.append(f"hook lands at {hook_off:.1f}s (> {HOOK_WINDOW}s)")
                ck = _match_event(c.get("cliffhanger_quote", ""), by[last["episode"]].events,
                                  last["start"], last["end"])
                if not ck:
                    raise ValueError("cliffhanger quote not found in clip text")
                tail_gap = last["end"] - ck[0].end
                if tail_gap > 6.0:
                    issues.append(f"cliffhanger quote is {tail_gap:.1f}s before the cut")
                good.append({
                    "id": cid, "source": source, "segments": segs,
                    "duration": round(dur, 2),
                    "cross_episode": len({s["episode"] for s in segs}) > 1 or len(segs) > 1,
                    "hook": {"quote": c.get("hook_quote", ""), "type": c.get("hook_type", ""),
                             "at": round(first["start"] + hook_off, 2), "offset_in_clip": round(hook_off, 2)},
                    "cliffhanger": {"quote": c.get("cliffhanger_quote", ""), "type": c.get("cliffhanger_type", ""),
                                    "at": round(ck[0].end, 2)},
                    "why": c.get("why", ""), "issues": issues,
                })
            except (KeyError, ValueError, TypeError) as ex:
                rejected.append({"id": cid, "reason": str(ex), "candidate": c})
    # drop near-duplicates inside the same episode (keep first = model's best)
    return dedupe(good, rejected), rejected


def overlap(a, b) -> float:
    tot = 0.0
    for s in a["segments"]:
        for t in b["segments"]:
            if s["episode"] == t["episode"]:
                tot += max(0.0, min(s["end"], t["end"]) - max(s["start"], t["start"]))
    return tot / max(1e-6, min(a["duration"], b["duration"]))


def dedupe(good, rejected, thresh=0.5):
    keep = []
    for c in good:
        if any(overlap(c, k) > thresh for k in keep):
            rejected.append({"id": c["id"], "reason": "overlaps a better candidate", "candidate": c})
        else:
            keep.append(c)
    return keep


# ---------------------------------------------------------------- scoring
def batches(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def blind_test(llm, cands, eps, run_id="r1", batch=10, progress=print):
    by = {e.number: e for e in eps}

    def one(item):
        bi, grp = item
        user = "\n\n".join(f"### CLIP {c['id']}\n{render_clip(by, c['segments'])}" for c in grp)
        try:
            res = llm.chat(prompts.BLIND_SYSTEM + f"\n[run:{run_id}]", user, max_tokens=3500, tag=f"blind_{bi}")
            rows = {r["id"]: r for r in res.get("clips", [])}
        except Exception as ex:
            progress(f"  blind batch {bi} failed: {ex}")
            rows = {}
        for c in grp:
            c["blind"] = rows.get(c["id"])
        progress(f"  blind batch {bi + 1} done")

    pmap(one, list(enumerate(batches(cands, batch))))


def judge(llm, cands, eps, run_id="r1", batch=12, progress=print):
    by = {e.number: e for e in eps}

    def one(item):
        bi, grp = item
        parts = []
        for c in grp:
            nums = sorted({s["episode"] for s in c["segments"]})
            ctx = " | ".join(f"Ep{n}: {by[n].logline}" for n in nums)
            parts.append(f"### CLIP {c['id']}\nContext (for you only): {ctx}\n{render_clip(by, c['segments'])}")
        try:
            res = llm.chat(prompts.JUDGE_SYSTEM + f"\n[run:{run_id}]", "\n\n".join(parts),
                           max_tokens=3500, tag=f"judge_{bi}")
            rows = {r["id"]: r for r in res.get("clips", [])}
        except Exception as ex:
            progress(f"  judge batch {bi} failed: {ex}")
            rows = {}
        for c in grp:
            c["judge"] = rows.get(c["id"])
        progress(f"  judge batch {bi + 1} done")

    pmap(one, list(enumerate(batches(cands, batch))))


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def score(c):
    j, b = c.get("judge"), c.get("blind")
    if not j or not b:
        c["score"] = None
        c["score_parts"] = None
        return
    stand = (min(5, max(1, _num(b.get("standalone"), 1))) - 1) * 2.5   # 1-5 -> 0-10
    parts = {"hook": _num(j.get("hook")), "cliffhanger": _num(j.get("cliffhanger")),
             "standalone": stand, "intensity": _num(j.get("intensity")), "premise": _num(j.get("premise"))}
    total = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS) * 10
    pen = 0.0
    if any(i.startswith("hook lands") for i in c["issues"]):
        pen += 5
    if any(i.startswith("cliffhanger quote is") for i in c["issues"]):
        pen += 3
    if b.get("keep_watching") is False:
        pen += 3
    c["score_parts"] = parts
    c["penalty"] = pen
    c["score"] = round(max(0.0, total - pen), 1)


def rank(cands, per_episode=2, top=None):
    scored = sorted([c for c in cands if c.get("score") is not None], key=lambda c: -c["score"])
    chosen, per_ep = [], {}
    for c in scored:
        key = c["segments"][0]["episode"]
        if per_ep.get(key, 0) >= per_episode:
            c["rank_note"] = "skipped: episode cap"
            continue
        if any(overlap(c, k) > 0.3 for k in chosen):
            c["rank_note"] = "skipped: overlaps a higher-ranked clip"
            continue
        chosen.append(c)
        per_ep[key] = per_ep.get(key, 0) + 1
        if top and len(chosen) >= top:
            break
    for i, c in enumerate(chosen, 1):
        c["rank"] = i
    return chosen


def post_reasons(llm, ranked, eps, run_id="r1", n=10):
    by = {e.number: e for e in eps}
    items = []
    for c in ranked[:n]:
        items.append(f"### {c['id']} rank {c['rank']} score {c['score']} parts {c['score_parts']}\n"
                     f"hook: {c['hook']['quote']}\ncliffhanger: {c['cliffhanger']['quote']}\n"
                     f"flags: {c['issues']} cross_episode={c['cross_episode']}")
    try:
        res = llm.chat(prompts.WHY_SYSTEM + f"\n[run:{run_id}]", "\n\n".join(items), max_tokens=2000, tag="why")
        notes = {r["id"]: r.get("post_reason", "") for r in res.get("notes", [])}
    except Exception:
        notes = {}
    for c in ranked[:n]:
        c["post_reason"] = notes.get(c["id"], "")


# ---------------------------------------------------------------- outputs
def clip_label(c):
    return " + ".join(f"Ep{s['episode']} {fmt(s['start'])}-{fmt(s['end'])}" for s in c["segments"])


def build_transcript(by, segments):
    """Clip as timestamped lines, for display and review."""
    rows = []
    for seg in segments:
        for e in by[seg["episode"]].events:
            if e.kind == "CAMERA" or e.end <= seg["start"] + 0.01 or e.start >= seg["end"] - 0.01:
                continue
            rows.append({"ep": seg["episode"], "t": round(e.start, 2), "kind": e.kind,
                         "speaker": e.speaker, "delivery": e.delivery, "text": e.text})
    return rows


def write_outputs(out_dir, eps, raw, cands, rejected, ranked):
    os.makedirs(out_dir, exist_ok=True)
    by = {e.number: e for e in eps}
    for c in ranked:
        c["transcript"] = build_transcript(by, c["segments"])
    json.dump([{"number": e.number, "duration": e.duration, "logline": e.logline,
                "dialogue_lines": sum(1 for x in e.events if x.kind == "DIALOGUE")} for e in eps],
              open(os.path.join(out_dir, "show_meta.json"), "w"), indent=2, ensure_ascii=False)
    dump = lambda name, obj: json.dump(obj, open(os.path.join(out_dir, name), "w"), indent=2, ensure_ascii=False)
    dump("raw_llm_candidates.json", raw)
    dump("rejected_by_validators.json", rejected)
    dump("all_scored_candidates.json", cands)
    dump("ranked_promos.json", ranked)
    with open(os.path.join(out_dir, "ranked_promos.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "score", "segments", "duration_s", "hook_time", "hook", "cliffhanger", "why_it_works",
                    "post_reason", "standalone_1to5", "flags"])
        for c in ranked:
            w.writerow([c["rank"], c["score"], clip_label(c), c["duration"], fmt(c["hook"]["at"]), c["hook"]["quote"],
                        c["cliffhanger"]["quote"], c["why"], c.get("post_reason", ""),
                        (c.get("blind") or {}).get("standalone"), "; ".join(c["issues"])])
    lines = ["# Ranked promos\n"]
    for c in ranked:
        b = c.get("blind") or {}
        lines += [f"## #{c['rank']}  {clip_label(c)}  ({c['duration']}s, score {c['score']})",
                  f"- **Hook** ({fmt(c['hook']['at'])}): {c['hook']['quote']}",
                  f"- **Cliffhanger**: {c['cliffhanger']['quote']}",
                  f"- **Why it works**: {c['why']}",
                  f"- **Post-order reason**: {c.get('post_reason', '')}" if c.get("post_reason") else "",
                  f"- Cold-viewer read: standalone {b.get('standalone')}/5. {b.get('what_is_happening', '')}",
                  f"- Flags: {'; '.join(c['issues']) or 'none'}\n"]
    open(os.path.join(out_dir, "ranked_promos.md"), "w").write("\n".join(lines))


def run(folder, llm, out_dir="outputs/run1", run_id="r1", top=25, only=None, progress=print):
    eps = load_show(folder)
    targets = [e for e in eps if not only or e.number in only]
    progress(f"parsed {len(eps)} episodes; extracting from {len(targets)}")
    progress("1/5 extracting candidates")
    raw = extract_candidates(llm, eps, run_id, progress, targets=targets)
    progress("2/5 validating and snapping")
    cands, rejected = validate_candidates(raw, eps)
    progress(f"   kept {len(cands)}, rejected {len(rejected)}")
    progress("3/5 blind-viewer test")
    blind_test(llm, cands, eps, run_id, progress=progress)
    progress("4/5 judge")
    judge(llm, cands, eps, run_id, progress=progress)
    for c in cands:
        score(c)
    ranked = rank(cands, top=top)
    progress("5/5 post-order notes")
    post_reasons(llm, ranked, eps, run_id)
    write_outputs(out_dir, eps, raw, cands, rejected, ranked)
    progress(f"done: {len(ranked)} ranked promos in {out_dir}")
    return ranked
