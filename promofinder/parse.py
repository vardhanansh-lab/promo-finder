"""Deterministic parser for Kuku-style timestamped microdrama screenplays.

Turns each episode .txt into structured events. No AI involved, so timestamps
are exact. Case-insensitive because some episodes (e.g. episode 6) use
upper-case headers such as "SCENE START:".
"""
from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass, field, asdict

TS = r"(\d+):(\d+)\.(\d+)"
RE_SCENE = re.compile(r"^SCENE\s+(\d+)\s*$", re.I)
RE_HEADING = re.compile(r"^SCENE HEADING:\s*(.*)$", re.I)
RE_SSTART = re.compile(r"^SCENE START:\s*" + TS, re.I)
RE_SEND = re.compile(r"^SCENE END:\s*" + TS, re.I)
RE_HDR = re.compile(r"^\*\*(.+?):\*\*\s*$")
RE_TIMES = re.compile(r"^Start:\s*\(" + TS + r"\)\s*\|\s*End:\s*\(" + TS + r"\)\s*$", re.I)
NON_SPEECH = {"CAMERA", "ACTION", "SOUND FX"}


def to_sec(m: str, s: str, f: str) -> float:
    # fractional part is written as hundredths ("04.80" -> .80, "02.5" -> .5)
    return int(m) * 60 + int(s) + float("0." + f)


def fmt(t: float) -> str:
    m = int(t // 60)
    s = t - 60 * m
    return f"{m:02d}:{s:05.2f}"


@dataclass
class Event:
    kind: str            # DIALOGUE | ACTION | CAMERA | SOUND
    start: float
    end: float
    text: str
    speaker: str | None = None
    delivery: str | None = None   # e.g. "Cold, Commanding"
    voice: str | None = None      # "O.S." / "V.O." when present
    scene: int = 0


@dataclass
class Episode:
    number: int
    file: str
    logline: str = ""
    continuity: str = ""
    duration: float = 0.0
    scenes: list = field(default_factory=list)   # {n, heading, start, end}
    events: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def parse_header(raw: str):
    """'JULIANA (Shaken, Whispering)' -> speaker, delivery, voice."""
    raw = raw.strip()
    name = raw
    delivery = None
    voice = None
    # collect all parentheticals
    paren = re.findall(r"\(([^)]*)\)", raw)
    name = re.sub(r"\([^)]*\)", "", raw).strip().rstrip(":").strip()
    for p in paren:
        if p.strip().upper() in ("O.S.", "V.O.", "OS", "VO"):
            voice = p.strip().upper()
        else:
            delivery = p.strip()
    return re.sub(r"\s+", " ", name).upper(), delivery, voice


def parse_episode(path: str) -> Episode:
    lines = open(path, encoding="utf-8").read().splitlines()
    ep = Episode(number=-1, file=os.path.basename(path))
    scene = 0
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i].strip()
        if ln.upper().startswith("EPISODE NUMBER:"):
            mm = re.search(r"(\d+)", ln)
            ep.number = int(mm.group(1)) if mm else -1
        elif ln.upper().startswith("EPISODE LOGLINE:"):
            ep.logline = ln.split(":", 1)[1].strip()
        elif ln.upper().startswith("CONTINUITY NOTES:"):
            ep.continuity = ln.split(":", 1)[1].strip()
        elif RE_SCENE.match(ln):
            scene = int(RE_SCENE.match(ln).group(1))
            ep.scenes.append({"n": scene, "heading": "", "start": None, "end": None})
        elif RE_HEADING.match(ln) and ep.scenes:
            ep.scenes[-1]["heading"] = RE_HEADING.match(ln).group(1).strip()
        elif RE_SSTART.match(ln) and ep.scenes:
            ep.scenes[-1]["start"] = to_sec(*RE_SSTART.match(ln).groups())
        elif RE_SEND.match(ln) and ep.scenes:
            ep.scenes[-1]["end"] = to_sec(*RE_SEND.match(ln).groups())
        else:
            h = RE_HDR.match(ln)
            if h and i + 1 < n and RE_TIMES.match(lines[i + 1].strip()):
                t = RE_TIMES.match(lines[i + 1].strip()).groups()
                st, en = to_sec(*t[:3]), to_sec(*t[3:])
                # body: following lines until blank line / next header / marker
                j = i + 2
                body = []
                while j < n:
                    b = lines[j].strip()
                    if not b:
                        if body:
                            break
                        j += 1
                        continue
                    if RE_HDR.match(b) or RE_SCENE.match(b) or b.startswith("--- SCRIPT"):
                        break
                    body.append(b)
                    j += 1
                text = " ".join(body).strip()
                raw = h.group(1)
                key = re.sub(r"\([^)]*\)", "", raw).strip().upper()
                if key in NON_SPEECH:
                    kind = {"CAMERA": "CAMERA", "ACTION": "ACTION", "SOUND FX": "SOUND"}[key]
                    ep.events.append(Event(kind, st, en, text, scene=scene))
                else:
                    spk, deliv, voice = parse_header(raw)
                    ep.events.append(Event("DIALOGUE", st, en, text.strip('"').strip("“”"),
                                           speaker=spk, delivery=deliv, voice=voice, scene=scene))
                i = j - 1
        i += 1

    ends = [s["end"] for s in ep.scenes if s["end"] is not None]
    ep.duration = max(ends) if ends else (max((e.end for e in ep.events), default=0.0))
    ep.events.sort(key=lambda e: (e.start, e.end))
    validate(ep)
    return ep


def validate(ep: Episode):
    w = ep.warnings
    if ep.number < 0:
        w.append("episode number missing")
    if not ep.scenes:
        w.append("no scenes parsed")
    for s in ep.scenes:
        if s["start"] is None or s["end"] is None:
            w.append(f"scene {s['n']} missing start/end")
    dlg = [e for e in ep.events if e.kind == "DIALOGUE"]
    if not dlg:
        w.append("no dialogue parsed")
    last_end = max((e.end for e in ep.events), default=0)
    if ep.duration and abs(last_end - ep.duration) > 3.0:
        w.append(f"last event ends {last_end:.1f}s but scenes end {ep.duration:.1f}s")
    for e in ep.events:
        if e.end < e.start:
            w.append(f"negative duration at {fmt(e.start)}")
        if e.end > ep.duration + 3.0:
            w.append(f"event past episode end at {fmt(e.start)}")
    for a, b in zip(ep.scenes, ep.scenes[1:]):
        if a["end"] is not None and b["start"] is not None and abs(a["end"] - b["start"]) > 0.5:
            w.append(f"gap between scene {a['n']} and {b['n']}")
    # speakers that look like noise
    for e in dlg:
        if not e.text:
            w.append(f"empty dialogue at {fmt(e.start)} ({e.speaker})")


def load_show(folder: str) -> list[Episode]:
    files = sorted(glob.glob(os.path.join(folder, "*.txt")))
    eps = [parse_episode(f) for f in files]
    eps.sort(key=lambda e: e.number)
    return eps


def to_json(eps: list[Episode]) -> list[dict]:
    return [asdict(e) for e in eps]


if __name__ == "__main__":
    import sys
    folder = sys.argv[1]
    eps = load_show(folder)
    for e in eps:
        d = sum(1 for x in e.events if x.kind == "DIALOGUE")
        print(f"EP{e.number:02d} {e.duration:6.1f}s scenes={len(e.scenes)} events={len(e.events)} dialogue={d} warn={len(e.warnings)}")
        for w in e.warnings:
            print("   !", w)
