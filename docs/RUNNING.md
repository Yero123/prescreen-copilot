# How to run it

This takes you from a fresh clone to the recruiter UI in about five minutes. You only need an API key to screen new replies; the demo candidates work without one.

## Option A: Docker (recommended)

You need [Docker](https://docs.docker.com/get-docker/) with Compose v2.

**1. Clone the repo**

```bash
git clone https://github.com/Yero123/prescreen-copilot.git
cd prescreen-copilot
```

**2. Add a key (optional)**

```bash
cp .env.example .env
```

Open `.env` and set the provider and its key:

```bash
LLM_PROVIDER=openai          # or anthropic
OPENAI_API_KEY=...           # or ANTHROPIC_API_KEY=...
```

Skip this step to look around with the demo data only.

**3. Start it**

```bash
make up                      # same as: docker compose up --build
```

The first build takes a few minutes. It is ready when the logs show `Application startup complete`.

| What | Where |
|---|---|
| Recruiter UI | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

**4. Try it**

1. Open the UI. **Candidates** lists 15 screened demo replies. Loading them calls no model.
2. Open a candidate to see the evidence quotes, the rules checked by code and the email draft. Change a verdict with **Override** and watch the suggested step update.
3. Go to **Add a reply**, load an example and press **Screen this reply**. This one calls the models, spends tokens and takes about 30 seconds. Without a key, the reply ends up as "Failed".

**5. Stop it**

```bash
make down                    # stop; your data stays in the app-data volume
docker compose down -v       # stop and delete the data; the demo candidates load again on the next start
```

To check a running stack without spending tokens, run `make smoke` in a second terminal. It needs the API open, so leave `DEMO_ACCESS_CODE` empty.

## Option B: without Docker

You need [uv](https://docs.astral.sh/uv/) and Node 22.12+.

```bash
cp .env.example .env         # optional, as above
make install                 # backend dependencies
make web-install             # frontend dependencies
make dev                     # API on http://localhost:8000
make web                     # UI on http://localhost:5173, in a second terminal
```

This uses its own database at `backend/data/app.db`, separate from the Docker volume.

## Run the tests

No API key is needed, and no test calls a model.

```bash
make test                    # backend (pytest)
make web-test                # frontend (Vitest)
```

The evals are different: `make eval SPLIT=dev` calls the real models and spends tokens.

## Continuous integration

`.circleci/config.yml` runs on every push:

| Job | What it does |
|---|---|
| `backend` | Installs from the lockfile and runs pytest |
| `frontend` | Runs lint, Vitest and the production build |
| `docker` | Runs after both pass: builds and starts the stack, then runs `scripts/smoke.sh` |

To turn it on, sign in at [circleci.com](https://circleci.com), choose **Projects**, find this repository and press **Set Up Project**, using the config already on the branch. CI needs no secrets, because no job calls a model.

## Common problems

| Symptom | Cause and fix |
|---|---|
| `port is already allocated` | Something else is using 8000 or 5173, such as `make dev`. Stop it and retry. |
| The UI loads but shows a network error | The API is down, or the browser origin is not allowed. Check `docker compose logs backend`. If you serve the UI elsewhere, set `ALLOWED_ORIGINS`. |
| The UI calls the wrong API | `VITE_API_URL` is fixed at build time. Change it, then run `make up` again so the UI is rebuilt. |
| A new reply shows "Failed" | The key is missing or wrong, or the model is not available to it. See `docker compose logs backend`. |
| The UI asks for an access code | `DEMO_ACCESS_CODE` is set in `.env`. Enter that value, or empty it and restart. |
| `429 Too many screenings` | You reached `MAX_SCREENS_PER_IP_PER_HOUR` (default 10). Raise it in `.env` and restart. The counters also reset on restart. |
| A reply stays on "Screening…" forever | The API restarted during the screening, and that row is not resumed. Add the reply again. |
