# Pre-screen Copilot

A copilot for recruiters at a LatAm staffing agency. It reads each candidate's written reply to the screening questionnaire, shows which role criteria are met with the candidate's exact words as evidence, applies hard rules in code, and drafts the next email. The recruiter makes every decision.

> Work in progress. Built step by step for the Rad Hires Harness Challenge. Design notes: [docs/DECISIONS.md](docs/DECISIONS.md).

## Status

| Step | What | State |
|---|---|---|
| 1 | Repo, Docker, first model call (input gate) | done |
| 2 | Role config (questionnaire, criteria, hard rules, bias check) | done |
| 3 | Sample candidates (5 handmade dev cases with labels) | done |
| 4 | Read: structured extraction with verbatim checks | done |
| 5 | Hard rules in code | done |
| 6 | Evaluate each criterion with quotes | done |
| 7 | Quote verifier, injection and CV-contradiction checks | done |
| 8 | Triage + email draft | next |
| 9 | Eval dataset (30 cases) | |
| 10 | Eval runner + report | |
| 11 | Recruiter UI (Vite + React) | |
| 12 | README, DESIGN.md, demo video | |

## Run it locally

Requirements: [uv](https://docs.astral.sh/uv/), Docker, an Anthropic API key.

Requirements also include a key for one provider. `LLM_PROVIDER` in `.env` picks it: `anthropic` (target) or `openai`.

```bash
cp .env.example .env        # set LLM_PROVIDER and that provider's key
make models                 # optional: list the model ids your key can use
make install                # install backend dependencies
make test                   # deterministic tests, no API key needed
make hello                  # first Claude call: runs the gate on 3 sample emails
make dev                    # API on http://localhost:8000 (docs at /docs)
make up                     # same API, inside Docker
```

## Deploy

- Backend (FastAPI): Railway, built from `backend/Dockerfile` (reads `PORT`).
- Frontend (Vite + React): Vercel. Added in step 11.
