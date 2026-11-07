"""Copy a results folder to UTF-8. Windows writes cp1252, which breaks on Mac/Linux.
Lossless re-encode of the same text; the original folder is left untouched.
    python fix_encoding.py outputs/run1 outputs/run1_utf8
The LLM response cache is skipped (it is ASCII and holds the full prompts)."""
import os, sys

src, dst = sys.argv[1], sys.argv[2]
n = 0
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d != "cache"]
    out = os.path.join(dst, os.path.relpath(root, src))
    os.makedirs(out, exist_ok=True)
    for f in files:
        raw = open(os.path.join(root, f), "rb").read()
        if f.endswith((".json", ".jsonl", ".csv", ".md", ".txt")):
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = raw.decode("cp1252")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1")
            raw = text.encode("utf-8-sig" if f.endswith(".csv") else "utf-8")   # BOM so Excel opens CSV correctly
        open(os.path.join(out, f), "wb").write(raw)
        n += 1
print(f"{n} files -> {dst}")
