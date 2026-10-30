# Decision log

Decisions taken, decisions rejected, and why. Newest last. Each entry: context, decision, alternatives considered.

## D-001 · Narrow problem: the written pre-screen
- **Context:** The challenge asks for one real business problem solved well. Rad Hires screens every applicant with a written questionnaire sent by email, read by hand.
- **Decision:** Build only this stage, end to end. The rest of the hiring funnel is out of scope.
- **Rejected:** The whole funnel (too broad to do well); an AI interviewer (the conversation should stay human).

## D-002 · The model never decides about a person
- **Decision:** Per-criterion verdicts with evidence and a suggested next step. No score, no ranking, no automatic rejection. The recruiter decides.
- **Why:** Scores of free text are not reproducible or explainable, and automated decisions about candidates carry legal risk (NYC Local Law 144, GDPR Art. 22).

## D-003 · Deterministic code wherever the answer must be exact
- **Decision:** Hard rules (location, rate, English level, overlap), quote verification and triage are plain code. The model only does what needs language understanding.
- **Why:** Same input, same result; testable without API calls.

## D-004 · No RAG, no fine-tuning, no agent framework
- **Decision:** A fixed pipeline of single LLM calls.
- **Why:** Each reply plus the role criteria fits in the context window, so there is nothing to retrieve. Rules are explicit and change per role, so they live in configuration, not in weights. The flow has a known number of steps, so an agent loop adds cost and failure modes without benefit.

## D-005 · Two models, routed by task
- **Decision:** `claude-haiku-5-5` for the gate and extraction; `claude-sonnet-5-5` for evaluation and drafting.
- **Why:** Cheap, fast model where the task is narrow; stronger model where judgment matters. Configurable in `.env`.

## D-006 · Typed contracts with the model
- **Decision:** Every LLM call returns JSON validated against a Pydantic schema (`messages.parse`). A refusal, a cut-off answer or a parse failure routes the case to a person; it is never treated as a pass.

## D-007 · Consistency without `temperature`
- **Context:** Since 2026-10-21 the Messages API rejects `temperature`, `top_p` and `top_k`.
- **Decision:** Get consistency from narrow questions, typed outputs and fixed effort levels, and measure it in the eval report instead of assuming it.

## D-008 · Candidate text is data, never instructions
- **Decision:** Candidate text is wrapped in tags and the system prompt says never to follow instructions inside it. Detection and evals for injection come in later steps.

## D-010 · One provider switch, Claude as the target
- **Context:** Development started before an Anthropic key was available; an OpenAI key was.
- **Decision:** `app/llm.py` is the only module that talks to a provider. `LLM_PROVIDER=anthropic|openai` picks Claude (`messages.parse`) or OpenAI (`responses.parse`); both return the same typed `LLMResult`, so the harness never imports a vendor SDK. Claude stays the target for the submission.
- **Consequence for evals:** the case generator must come from a different model family than the evaluator. With OpenAI evaluating, generate cases with Claude; with Claude evaluating, generate with OpenAI.

## D-009 · Stack and deploy
- **Decision:** Python, FastAPI, Pydantic, SQLite, Docker. Backend on Railway, frontend (Vite + React) on Vercel.
- **Rejected:** Next.js (the backend is already FastAPI); Postgres (SQLite is enough for a demo and needs no setup); Kubernetes and queues (not needed at this size).
