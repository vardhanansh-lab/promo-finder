"""Score the pipeline against YOUR labels.  python eval_labels.py outputs/review"""
import csv, json, sys, statistics as st
d = sys.argv[1] if len(sys.argv) > 1 else "outputs/review"
key = json.load(open(f"{d}/label_key.json"))
lab = {}
for r in csv.DictReader(open(f"{d}/label_sheet.csv", encoding="utf-8-sig")):
    v = (r.get("verdict (keep / edit / reject)") or "").strip().lower()
    if v in ("keep", "edit", "reject"): lab[r["sheet_id"]] = (v, r.get("note (why)", ""))
out = [f"labelled {len(lab)} of {len(key)} clips\n"]
for src in ("pipeline_top", "pipeline_lower", "baseline"):
    ids = [i for i in lab if key[i]["source"] == src]
    if not ids: continue
    k = sum(lab[i][0] == "keep" for i in ids); e = sum(lab[i][0] == "edit" for i in ids)
    out.append(f"{src:15s} n={len(ids):2d}  keep {k/len(ids):.0%}  keep+edit {(k+e)/len(ids):.0%}  reject {1-(k+e)/len(ids):.0%}")
top = sorted([i for i in lab if key[i]["source"] == "pipeline_top"], key=lambda i: key[i]["rank"])
if len(top) >= 5:
    for n in (5, 10):
        t = top[:n]; out.append(f"precision@{len(t)} (keep+edit among best-ranked): {sum(lab[i][0] != 'reject' for i in t)/len(t):.0%}")
sc = [(key[i]["score"], lab[i][0] != "reject") for i in lab if key[i]["score"] is not None]
if sc:
    pos = [s for s, ok in sc if ok]; neg = [s for s, ok in sc if not ok]
    if pos and neg:
        out.append(f"mean score of clips you kept/edited {st.mean(pos):.1f} vs rejected {st.mean(neg):.1f}")
        pairs = [(p > n) + 0.5 * (p == n) for p in pos for n in neg]
        out.append(f"chance a kept clip outscores a rejected one (AUC): {sum(pairs)/len(pairs):.2f}  (0.5 = no better than random)")
out.append("\nrejection reasons you gave:")
for i, (v, n) in lab.items():
    if v == "reject" and n: out.append(f"  {i} ({key[i]['source']}): {n}")
open(f"{d}/eval.md", "w").write("\n".join(out)); print("\n".join(out))
