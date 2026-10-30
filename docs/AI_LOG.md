# AI log

How AI tools were used to build this project, and what was checked or changed by hand.

| Date | Step | AI helped with | Checked / changed by me |
|---|---|---|---|
| 2026-10-29 | 1 · Repo + gate | Scaffold, Dockerfile, first gate prompt, provider switch (Claude / OpenAI) | First real run on OpenAI `gpt-5-mini`: real reply passed, recipe rejected, injection rejected (3/3). ~4 s per call. |
| 2026-10-29 | 2 · Role config | Role JSON, Pydantic validation, bias-term list, tests | |
| 2026-10-29 | 3 · Dev cases | Drafted 5 cases and their labels (strong, polished-generic, non-native, injection, rule fail) | Gate run: 5/5 pass as expected. Labels still draft: to be reviewed by me. |
| 2026-10-29 | 4 · Read step | Extraction prompt, verify helpers, tests with a fake model, comparison script | Ran on the 5 dev cases: 20/20 facts. Measured default vs low reasoning effort and kept low for reading (same accuracy, ~2x faster). |
| 2026-10-30 | 5–8 · Rules, evaluation, triage, email, eval runner | Code for each step and its tests, eval runner | First full dev run: 5/5 next step, 18/20 verdicts. Reviewed the 2 mismatches and 3 failed email checks by hand: fixed my own email guardrail (false positive on "AI Engineer"), sharpened an ambiguous criterion, fixed an ambiguous test case. |
