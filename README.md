# Pre-screen Copilot

A copilot for recruiters at a staffing agency that places Latin American engineers. It reads each candidate's written reply to the screening questionnaire, shows which role criteria are met with the candidate's exact words as evidence, checks hard rules in code, and drafts the next email. The recruiter makes every decision.

- **Design:** [docs/DESIGN.md](docs/DESIGN.md) (problem, interface, harness, evals, tradeoffs, reflections)
- **Decision log:** [docs/DECISIONS.md](docs/DECISIONS.md) · **How AI was used to build it:** [docs/AI_LOG.md](docs/AI_LOG.md)
- **Eval reports:** [backend/evals/](backend/evals/) (`report-test-blind.md` is the honest number)

## Run it locally

Requirements: [uv](https://docs.astral.sh/uv/), Node 20+, and an API key for one provider (Anthropic or OpenAI). Docker is optional.

```bash
cp .env.example .env    # set LLM_PROVIDER and that provider's key (see the table below)
make install            # backend dependencies
make web-install        # frontend dependencies
make test               # deterministic tests, no API key needed
make dev                # API on http://localhost:8000 (OpenAPI docs at /docs)
make web                # recruiter UI on http://localhost:5173 (second terminal)
```

On first start the API loads 15 pre-screened demo candidates (`backend/data/demo_seed.json`), so the UI is not empty and nothing is spent until you add a reply. Use **Add a reply** and pick a sample, or paste your own, to watch a live screening (about 25 s).

Other commands:

```bash
make eval SPLIT=dev          # run the harness on the dev cases → backend/evals/report-dev.md
make eval SPLIT=test         # the held-out test cases
make baseline SPLIT=test     # the same cases through a single prompt, for comparison
make export-overrides        # turn recruiter overrides into new draft eval cases
make models                  # list the model ids your key can use
make up                      # the API inside Docker
```

### Environment variables

| Variable | Where | Default | What it does |
|---|---|---|---|
| `LLM_PROVIDER` | API | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | API | | Key for the chosen provider |
| `MODEL_READ`, `MODEL_EVALUATE`, `MODEL_WRITE` | API | per provider | Override a model (Anthropic: Haiku / Sonnet / Sonnet; OpenAI: gpt-5-mini / gpt-5 / gpt-5-mini) |
| `OPENAI_REASONING_EFFORT`, `OPENAI_EFFORT_<ROLE>` | API | `low` | Reasoning effort for OpenAI reasoning models |
| `DEMO_ACCESS_CODE` | API | empty (off) | If set, every API call needs it; the UI asks for it once |
| `MAX_SCREENS_PER_IP_PER_HOUR` / `MAX_SCREENS_PER_DAY` | API | `10` / `100` | Limits on live screenings, so a public demo cannot spend the key |
| `ALLOWED_ORIGINS` | API | `http://localhost:5173` | CORS, comma separated (the Vercel URL in production) |
| `DB_PATH` | API | `backend/data/app.db` | SQLite file |
| `SEED_DEMO` | API | `1` | Load the demo candidates when the database is empty |
| `RECRUITER_SIGNATURE` | API | `Best,\nThe recruiting team` | Email sign-off |
| `VITE_API_URL` | UI (build time) | `http://localhost:8000` | Where the UI calls the API |

## Deploy

Live demo: **https://prescreen-copilot-ten.vercel.app** (asks for the access code sent with the submission). API: https://api-production-a2f0.up.railway.app/health

- **API → Railway**, built from `backend/Dockerfile` (it listens on `PORT`; `backend/.railwayignore` limits the upload). A volume is mounted at `/data` with `DB_PATH=/data/app.db`, so data survives redeploys. Variables: the provider key, `DEMO_ACCESS_CODE`, `ALLOWED_ORIGINS` (the Vercel URL), `LLM_PROVIDER`. Redeploy with `cd backend && railway up --service api`.
- **UI → Vercel**, from `frontend/` (Vite is detected: `npm run build`, output `dist`), with `VITE_API_URL` set to the Railway URL for production. Redeploy with `cd frontend && vercel deploy --prod`.

## What is real and what is stubbed

| Real | Stubbed or simplified |
|---|---|
| Every pipeline step, with real model calls and code checks | Data is synthetic: the role, the questionnaire (written in my own words) and all candidates |
| Storage of candidates, submissions, results and recruiter events (SQLite) | **Approve** marks the email approved; nothing is sent |
| Overrides, decisions, email edit and regenerate, triage recomputed after overrides | One role, loaded from `backend/roles/*.json`; no editor in the UI |
| Eval runner, single-prompt baseline, reports, override export | No login: one shared access code for the demo |

## Known limitations

- Eval labels are drafts (`label_status: draft`) until reviewed by hand, and 15 test cases are too few to show rare failures. See "What I am least sure about" in DESIGN.md.
- The reported numbers were measured on OpenAI. Claude is the intended provider and works through the same switch, but has not been evaluated yet.
- No redaction of emails or phone numbers before the model sees the reply.
- Screening runs as a background task inside the API process; if the process restarts mid-screening, that row stays in "processing".
- Injection detection is a regex net plus the model's own report. A new phrasing can get through; when it does, injected text still never counts as evidence.

## Repo map

```
backend/app/          pipeline steps (gate, read, rules, evaluate, checks, triage, email), API, storage
backend/roles/        the role config: questionnaire, criteria, hard rules
backend/evals/        cases (dev / test), runner, baseline, reports
backend/tests/        deterministic tests (no API key)
frontend/src/         the recruiter UI
docs/                 DESIGN.md, DECISIONS.md, AI_LOG.md
```
