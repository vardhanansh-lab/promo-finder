"""Compact text views of the parsed screenplay, for prompts and for review."""
from __future__ import annotations

import re

from .parse import Episode, fmt

# display-only alias merge so the model sees one name per character
ALIASES = {"LADY JULIANA": "JULIANA", "LADY CATHERINE": "CATHERINE", "LADY CLARISSA": "CLARISSA"}


def spk(name: str) -> str:
    return ALIASES.get(name, name)


def render_episode(ep: Episode, until: float | None = None, with_times=True) -> str:
    """One line per event. Camera directions are dropped (they carry no story)."""
    out = []
    for e in ep.events:
        if e.kind == "CAMERA":
            continue
        if until is not None and e.start > until:
            break
        t = f"[{fmt(e.start)}-{fmt(e.end)}] " if with_times else ""
        if e.kind == "DIALOGUE":
            d = f" ({e.delivery})" if e.delivery else ""
            v = f" ({e.voice})" if e.voice else ""
            out.append(f'{t}{spk(e.speaker)}{v}{d}: "{e.text}"')
        elif e.kind == "ACTION":
            out.append(f"{t}ACTION: {e.text}")
        else:
            out.append(f"{t}SOUND: {e.text}")
    return "\n".join(out)


def render_clip(eps_by_num: dict, segments: list[dict]) -> str:
    """Clip as a cold viewer would get it: no timestamps, no show context."""
    parts = []
    for si, seg in enumerate(segments):
        ep = eps_by_num[seg["episode"]]
        lines = []
        for e in ep.events:
            if e.kind == "CAMERA":
                continue
            if e.end <= seg["start"] + 0.01 or e.start >= seg["end"] - 0.01:
                continue
            if e.kind == "DIALOGUE":
                lines.append(f'{spk(e.speaker)}: "{e.text}"')
            elif e.kind == "ACTION":
                lines.append(f"(action) {e.text}")
            else:
                lines.append(f"(sound) {e.text}")
        parts.append("\n".join(lines))
    return "\n-- CUT --\n".join(parts)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("’", "'")).strip()
