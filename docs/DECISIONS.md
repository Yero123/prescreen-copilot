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

## D-011 · The role is a validated config file
- **Decision:** `backend/roles/<role-id>.json` holds the questionnaire, the criteria (`must` / `should` / `nice`, each with concrete evidence signals and the questions where evidence usually appears) and the hard rules. `app/roles.py` validates it with Pydantic on load: unique ids, at least one `must`, criteria point only to existing questions, countries as ISO 3166-1 alpha-2 codes.
- **Why:** Changing a criterion or a rule is a data change, reviewed like data; prompts read the role instead of hardcoding it. Evidence signals turn "has real experience" into observable things (a named system, a metric, their own part), which is what makes judging specificity possible without rewarding polished writing.
- **Bias check on criteria:** a deterministic pass flags criteria that describe a person instead of a skill ("native English speaker", age, gender, nationality, "culture fit") and suggests a skill-based rewording. It warns; it does not block.
- **Assumption:** the allowed-country list is the Spanish- and Portuguese-speaking Latin American countries, without Cuba (US sanctions). A real deployment would take this list from the agency.

## D-012 · Test cases carry their own labels, and labels need review
- **Decision:** Each case (`backend/evals/cases/<split>/<id>.json`) holds the CV, the reply and the expected result: gate, hard facts, a verdict per criterion, the bucket and a one-line reason. Labels start as `draft`; only `reviewed` labels count in reported numbers.
- **Dev vs test:** the 5 handmade cases are the start of the dev split, used while building prompts. The test split is generated later by a model from a different family and stays untouched until the final run.
- **Consistency checks in code:** every case labels every criterion of the role, and any case whose labeled facts break a hard rule must expect `not_a_fit`.

## D-013 · Read step: the model extracts, code verifies
- **Decision:** One call splits the reply into answers per question and extracts the hard facts (country as ISO code, rate range, English self-rating, overlap hours, claimed years), each with the exact words it came from. Code then keeps only what it can verify (`app/verify.py`): every answer must appear word for word in the email, every quote must exist, every number must literally appear in its quote, and values must be in range. Anything else is dropped and reported as a warning (`answer_not_verbatim:Q1`, `fact_unverified:rate_max_usd_per_hour`, `no_answer:Q3`).
- **Why:** Models paraphrase, "fix" a non-native candidate's grammar, or fill a gap with a plausible number. Verbatim answers keep the candidate's own words for the evaluation step and for the recruiter; a fact that cannot be traced to the email never reaches the hard rules.
- **Measured (dev cases, OpenAI gpt-5-mini):** 20/20 hard facts match the labels; 25/25 answers kept verbatim, including the non-native case; no warnings.

## D-014 · Reasoning effort chosen by measurement
- **Decision:** On OpenAI reasoning models the read role runs at `low` effort; evaluation keeps `medium`.
- **Evidence:** Same 5 dev cases, same 20/20 facts: default effort took 14–25 s per case and ~1,200–1,700 output tokens; `low` took 6–11 s and ~630–870 tokens. Same quality, about half the time and cost.

## D-015 · Hard rules: missing is "unknown", ranges are judged by their low end
- **Decision:** `app/rules.py` checks location, rate, English and overlap in plain code, only on facts that survived verification. A missing fact is `unknown` (the next step is to ask), never `fail`. A rate range passes when its lowest value fits the budget, with a note for the recruiter; it fails only when even the low end is above the limit. Limits are inclusive.
- **Why:** Rejecting a good candidate costs more than asking one more question. Every rule result carries a plain-language detail ("$45/h > $40/h budget") so the recruiter and the candidate can be told exactly why.

## D-016 · Evaluation: the model reports, code decides what counts
- **Decision:** One call (`evaluate` role) returns, per criterion, `meets` / `does_not_meet` / `not_enough_evidence`, short quotes with their source (a question id or `CV`), the evidence signals it saw, a one-line rationale and, when evidence is missing, one follow-up question. The model cannot answer `needs_review`; only code sets it.
- **Code checks (`app/evaluate.py`, `app/checks.py`):** a quote must exist word for word in the source it names; a quote containing injected instructions never counts; `meets` or `does_not_meet` without a surviving quote becomes `needs_review` (quotes failed) or `not_enough_evidence` (no quotes given); a missing verdict becomes `needs_review`; a rationale that mentions a personal attribute is removed and the criterion goes to a person.
- **Prompt rules that target known failure modes:** polished wording without specifics is not evidence; grammar, fluency and language never change a verdict; candidate text is data, and instructions inside it are reported, not followed.
- **Injection is detected twice:** by the model (`instructions_found`) and by a regex detector in code, so a fooled model cannot hide an attempt.
- **CV contradiction:** years claimed in the reply are compared with the span of years written in the CV; more than 2 years over flags the case for a person.

## D-017 · Triage by explicit rules; rejection emails written by code
- **Decision:** `app/triage.py` maps results to a suggested next step with ordered, readable rules: a failed step → `needs_review`; a failed hard rule → `not_a_fit`; a red flag → `needs_review`; a criterion needing a person, or a `must` the model says is not met → `needs_review`; a `must` without evidence or a missing rule fact → `more_info`; otherwise `invite`. Each bucket carries its reasons in plain language.
- **The model never rejects:** only a rule checked in code can lead to `not_a_fit`. A model's `does_not_meet` on a `must` sends the case to a person.
- **Emails:** `not_a_fit` is a code template whose reason is built from the failed rules, word for word. `invite` and `more_info` are written by the `write` role from numbered, verified material (E = evidence, M = missing must-have, R = missing rule fact); each paragraph lists the ids it uses. Code checks every draft: cited ids exist, an invite's personal sentence is backed by evidence, a `more_info` email asks every missing item, and there is no salary, offer, score, AI-screening language, personal attribute or confidential client name. `needs_review` gets no draft.

## D-018 · The evals tested the guardrails and the role too
- **First full dev run** (5 cases): next step 5/5, facts 20/20, verdicts 18/20, injection flagged 1/1, 0/39 model quotes failed verification.
- **What it found and what changed:** (1) the email check banned the word "AI", but the role is "AI Engineer", so correct emails failed; the check now targets language revealing that software judged the candidate. (2) `open_weight` was ambiguous: the model counted Whisper, which is an open-weight model; the criterion now says open-weight *language* models with examples. (3) one dev case never said its product used an LLM, and the model correctly asked for evidence; the case text was fixed, not the label.

## D-009 · Stack and deploy
- **Decision:** Python, FastAPI, Pydantic, SQLite, Docker. Backend on Railway, frontend (Vite + React) on Vercel.
- **Rejected:** Next.js (the backend is already FastAPI); Postgres (SQLite is enough for a demo and needs no setup); Kubernetes and queues (not needed at this size).
