# Promo Finder (Kuku AI Generalist, Problem 1)

Reads timestamped microdrama screenplays and returns ranked promo clips
(20-60s, hook in first 3s, ends on a cliffhanger, understandable cold).

## Run (needs Python 3.10+, no pip installs)
1. Put the screenplay .txt files in `data/show1/` (not included: confidential).
2. `cp .env.example .env` and fill in your OpenRouter key and model names.
3. Smoke test: `python run.py data/show1 --only 1,2,3 --top 5 --out outputs/smoke`
4. Full run: `python run.py data/show1 --out outputs/run1 --run-id r1`
5. Stability run: `python run.py data/show1 --out outputs/run2 --run-id r2` then `python compare.py outputs/run1 outputs/run2`

Swap the model by editing `LLM_MODELS` (and `LLM_BASE_URL` for any OpenAI-compatible endpoint). Calls are cached in `outputs/cache`, so re-runs are free and a crash resumes where it stopped.

## Pipeline
parse (code) -> extract candidates per episode (LLM) -> snap to line edges, enforce 20-60s, verify quoted hook/cliffhanger exist in the clip (code) -> blind cold-viewer read (LLM, no show context) -> judge scores (LLM) -> weighted score + diversity ranking (code) -> posting-order notes (LLM).
