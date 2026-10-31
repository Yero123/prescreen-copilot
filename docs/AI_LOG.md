# AI log

How AI tools were used to build this project, and what was checked or changed by hand.

| Date | Step | AI helped with | Checked / changed by me |
|---|---|---|---|
| 2026-10-29 | 1 · Repo + gate | Scaffold, Dockerfile, first gate prompt, provider switch (Claude / OpenAI) | First real run on OpenAI `gpt-5-mini`: real reply passed, recipe rejected, injection rejected (3/3). ~4 s per call. |
| 2026-10-29 | 2 · Role config | Role JSON, Pydantic validation, bias-term list, tests | |
| 2026-10-29 | 3 · Dev cases | Drafted 5 cases and their labels (strong, polished-generic, non-native, injection, rule fail) | Gate run: 5/5 pass as expected. Labels still draft: to be reviewed by me. |
| 2026-10-29 | 4 · Read step | Extraction prompt, verify helpers, tests with a fake model, comparison script | Ran on the 5 dev cases: 20/20 facts. Measured default vs low reasoning effort and kept low for reading (same accuracy, ~2x faster). |
| 2026-10-29 | 5–8 · Rules, evaluation, triage, email, eval runner | Code for each step and its tests, eval runner | First full dev run: 5/5 next step, 18/20 verdicts. Reviewed the 2 mismatches and 3 failed email checks by hand: fixed my own email guardrail (false positive on "AI Engineer"), sharpened an ambiguous criterion, fixed an ambiguous test case. |
| 2026-10-29 | 9 · Eval set + experiments | Drafted 25 more cases with Claude (the evaluator runs on OpenAI, so a different model family), counterfactual pairs, the single-prompt baseline, the effort experiment | Dev: medium vs low effort gave the same accuracy at half the latency, so low everywhere (D-020). Relabeled one ambiguous dev case. Labels still draft. |
| 2026-10-29 | 10 · API + storage | SQLite store, FastAPI endpoints, overrides and decisions as events, demo access code and rate limits, override export | Tests use a temporary database. Demo seed built from the dev run so the UI starts full without spending the key. |
| 2026-10-29 | 11 · Recruiter UI | Vite + React screens: candidates, review with highlighted quotes, add a reply, role setup | Clicked through every screen against the local API: override, decision, email draft (5/5 checks), a live injection reply sent to review. Fixed criterion marks showing gray. |
| 2026-10-29 | Test run | Ran the held-out test set once, blind, then the baseline | Blind: 14/15 next step, 1 unsafe invite from a polite "P.S. for the automated screener". Fixed the detector, added a dev case for it, kept the blind report unchanged (D-021). The after-fix run then caught my email guardrail blocking the word "scores" in a correct email; narrowed it (D-022). |
| 2026-10-29 | 12 · Docs | Drafts of DESIGN.md and this README | To review and edit in my own words before sending; time spent still to fill in. |
| 2026-10-31 | README for presenting | Rewrote the README (problem, recruiter view, Mermaid diagrams, decisions taken, not taken and cut), a script that draws the charts from the eval reports, screenshots from the live site | To review and edit in my own words before sending; the time-per-reply figure is my estimate, not a measurement. |
