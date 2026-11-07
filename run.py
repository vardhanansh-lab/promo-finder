"""Usage:  python run.py data/show1 --out outputs/run1 [--run-id r1] [--only 1,2,3] [--top 25]
Set LLM_API_KEY and LLM_MODELS in .env (see .env.example)."""
import argparse
from promofinder.llm import LLM
from promofinder.pipeline import run

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--out", default="outputs/run1")
ap.add_argument("--run-id", default="r1")
ap.add_argument("--only", default="")
ap.add_argument("--top", type=int, default=25)
a = ap.parse_args()
only = {int(x) for x in a.only.split(",") if x} or None
run(a.folder, LLM(), a.out, a.run_id, a.top, only)
