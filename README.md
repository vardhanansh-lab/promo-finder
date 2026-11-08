# Promo Finder (Kuku AI Generalist, Problem 1)

Reads timestamped microdrama screenplays and returns ranked promo clips: 20-60s, a hook in the first 3 seconds,
an unresolved ending, and understandable by someone who has never seen the show. Every clip lists the exact
episode and start/end timestamp of each segment, the hook, the cliffhanger and a one-line reason.

Live demo: https://promo-finder-6wzpzixgayfmzp65kphc4s.streamlit.app/ (upload screenplays, press Find promos).
The screenplays and the raw outputs are Kuku's content, so they are not in this repository.

## Result on the 50-episode pack (102.7 min, 3,727 script events)
- 49 of 50 episodes processed (EP45 skipped: its first attempt hit a free-tier rate limit and was not retried).
- 142 candidates proposed, 49 rejected by code, 93 kept and scored, 25 ranked from 20 episodes (10 multi-segment).
- 25 of 142 candidates (18%) quoted a line that does not exist in the script. All were rejected by the validators.
- Every ranked clip is 25-51s and has no timing warning.
- Cold-viewer test: mean 3.13 / 5 standalone clarity; 23% of clips scored 2 or below.
- Human spot check (5 clips, blind, shuffled): 3 keep, 1 edit, 1 reject.
- About 70 model calls for a clean pass; our call log shows 114 calls (about 319k input and 406k output tokens)
  including tests, retries and reruns. Cost was 0 on free tiers.

## Run
Python 3.10+. The pipeline needs no pip installs. The web app needs `pip install streamlit`.
1. Put the screenplay .txt files in `data/show1/`.
2. Copy `.env.example` to `.env` and add a key plus `LLM_MODELS`, for example
   `LLM_MODELS=gemini|gemini-2.5-flash,openrouter|nvidia/nemotron-3-ultra-550b-a55b:free`
   (providers: openrouter, gemini, mistral, groq, cerebras, nvidia; models are tried in order).
3. Smoke test: `python run.py data/show1 --only 1,2,3 --top 5 --out outputs/smoke`
4. Full run: `python run.py data/show1 --out outputs/run1 --run-id r1 --top 25`
5. Summary numbers: `python stats.py outputs/run1`
6. App: `python -m streamlit run app.py`, then upload screenplays or open a saved run.

Swapping the model means editing `LLM_MODELS` (or `LLM_BASE_URL` for any other OpenAI-compatible endpoint).
Every model call is cached in `outputs/cache`, independent of which model answered, so reruns are free and a
crash resumes where it stopped. Calls are logged to `outputs/llm_log.jsonl`.
On Windows, output files are written as UTF-8; run `python -X utf8 stats.py ...` to read them.

Optional: `PROMO_WORKERS` (parallel calls, default 4) and `PROMO_CALIBRATE=0` (skip the calibration pass).

## Pipeline
1. Parse (code): robust, case-insensitive screenplay parser, checked against the scene end times.
2. Extract (LLM): one call per episode proposes up to 4 candidates, with the next episode's first 40s available for cross-episode cuts.
3. Validate (code): snap cuts to line edges so no line is cut in half, enforce 20-60s, and verify the quoted hook and cliffhanger really appear in the clip. Drop duplicates and overlaps.
4. Cold-viewer test (LLM): sees only the clip text, no show context, and rates standalone clarity 1-5.
5. Judge (LLM): scores hook, cliffhanger, intensity and premise 0-10 in batches of 12.
6. Score and rank (code): weights hook 0.30, cliffhanger 0.30, standalone 0.20, intensity 0.10, premise 0.10, with penalties for a late hook or a cliffhanger quote far from the cut. At most 2 clips per episode, no clips that overlap more than 30%, no two clips on the same moment.
7. Calibration (LLM, optional): re-judges the top 30 clips and averages with the first pass. It ran as two halves of 15 because the single prompt returned invalid JSON. After calibration, 8 of the first-pass top 10 stayed in the top 10 (run on 9 Nov 2026, after submission).
8. Posting notes (LLM): one sentence per top-10 clip on why to post it at that rank.

## Evidence tools
- `stats.py`: counts, rejection reasons, score spread, top 10 and lowest 3, model calls and tokens.
- `label_sheet.py` and `eval_labels.py`: a blind, shuffled review sheet and the comparison with your verdicts.
- `baseline.py`, `compare.py`, `agreement.py`, `cost_report.py`: baseline, run-to-run stability, two-model agreement, cost.
- `fix_encoding.py`: copies a results folder to UTF-8 for sharing.

## Known limits
- Scores come from LLM judges, so they can share blind spots. Scores are comparable within a batch, not perfectly across batches; the ranking moved between earlier reruns (only 2 of the top 10 stayed). Calibration is meant to steady this; I have not yet rerun the full pipeline twice with it, so the effect on run-to-run stability is not measured.
- The cold-viewer test is noisy: the share rated 2 or below moved from 6% to 23% between runs.
- A clip that joins two episodes can repeat a beat, because episodes may open by replaying the last moment of the previous one. A trim for this is in the code (`trim_replays`); in the final run it did not fire on any ranked clip, and the one clip known to repeat dropped out of the top 25.
- Some hooks are stage directions, not spoken lines. They get a 1.5 point penalty, but #4 and #8 in the final top 10 still have one.
- The tool sees text only: no video, acting or pacing. Timestamps are planned timings.
- Free-tier models have daily quotas and sometimes return invalid JSON. A full run on a new pack needs a paid or higher-quota key to finish quickly.
