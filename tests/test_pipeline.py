"""Offline test with a stand-in model. NOT used for any submitted output."""
import json, os, re, sys, random
sys.path.insert(0, ".")
os.environ["PROMO_CACHE"] = "outputs/test_cache"; os.environ["PROMO_LOG"] = "outputs/test_log.jsonl"
from promofinder.parse import load_show, fmt
from promofinder import pipeline as P

class Mock:
    """Returns plausible-shaped JSON. Includes deliberately bad candidates."""
    def __init__(self, eps): self.by={e.number:e for e in eps}; random.seed(1)
    def chat(self, system, user, max_tokens=0, expect_json=True, tag=""):
        if tag.startswith("extract_ep"):
            n=int(tag.replace("extract_ep","")); ep=self.by[n]
            dl=[e for e in ep.events if e.kind=="DIALOGUE"]
            tail=[e for e in dl if e.start>=ep.duration-38]
            good={"segments":[{"episode":n,"start":fmt(tail[0].start+0.3),"end":fmt(tail[-1].end-0.2)}],  # sloppy times -> must snap
                  "hook_quote":tail[0].text,"hook_type":"x","cliffhanger_quote":tail[-1].text,"cliffhanger_type":"x","why":"mock"}
            halluc=dict(good); halluc["hook_quote"]="I will take your kingdom and your crown tonight"
            toolong={"segments":[{"episode":n,"start":fmt(dl[0].start),"end":fmt(min(ep.duration,dl[0].start+80))}],
                     "hook_quote":dl[0].text,"cliffhanger_quote":dl[-1].text}
            mid=[e for e in dl if 20<e.start<60]
            c3={"segments":[{"episode":n,"start":fmt(mid[0].start+0.4),"end":fmt(mid[0].start+30)}],
                "hook_quote":mid[0].text,"cliffhanger_quote":mid[min(5,len(mid)-1)].text}
            return {"candidates":[good,halluc,toolong,c3]}
        if tag.startswith("blind"):
            ids=re.findall(r"### CLIP (\S+)",user)
            return {"clips":[{"id":i,"standalone":random.randint(2,5),"keep_watching":random.random()>.3,"what_is_happening":"mock"} for i in ids]}
        if tag.startswith("judge"):
            ids=re.findall(r"### CLIP (\S+)",user)
            return {"clips":[{"id":i,"hook":random.randint(3,9),"cliffhanger":random.randint(3,9),"intensity":random.randint(3,9),"premise":random.randint(3,9)} for i in ids]}
        ids=re.findall(r"### (\S+) rank",user); return {"notes":[{"id":i,"post_reason":"mock"} for i in ids]}

eps=load_show("data/show1")
ranked=P.run("data/show1", Mock(eps), "outputs/mock_test", "t", top=10)
rej=json.load(open("outputs/mock_test/rejected_by_validators.json"))
from collections import Counter
print(Counter(r["reason"].split(" outside")[0][:40] for r in rej).most_common(6))
allc=json.load(open("outputs/mock_test/all_scored_candidates.json"))
print("kept",len(allc),"issues sample",Counter(i[:22] for c in allc for i in c["issues"]).most_common(5))
assert all(20<=c["duration"]<=60 for c in allc)
# no kept clip may start/end mid-dialogue
for c in allc:
    for s in c["segments"]:
        ep=next(e for e in eps if e.number==s["episode"])
        for e in ep.events:
            if e.kind=="DIALOGUE":
                assert not (e.start+0.06 < s["start"] < e.end-0.06), (c["id"],"start mid-line")
                assert not (e.start+0.06 < s["end"] < e.end-0.06), (c["id"],"end mid-line")
print("top3:", [(c["rank"],P.clip_label(c),c["score"]) for c in ranked[:3]])
print("ALL ASSERTS PASSED")
