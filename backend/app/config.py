"""Runtime settings, read once from environment variables."""

import os

# Which provider answers the LLM calls: "anthropic" (target) or "openai".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
if LLM_PROVIDER not in ("anthropic", "openai"):
    raise ValueError(f"LLM_PROVIDER must be 'anthropic' or 'openai', got {LLM_PROVIDER!r}")

# Three roles: "read" is narrow and cheap, "evaluate" needs judgment,
# "write" drafts short emails from verified evidence.
_DEFAULT_MODELS = {
    "anthropic": {"read": "claude-haiku-5-5", "evaluate": "claude-sonnet-5-5", "write": "claude-sonnet-5-5"},
    "openai": {"read": "gpt-5-mini", "evaluate": "gpt-5", "write": "gpt-5-mini"},
}


def model_for(role: str) -> str:
    """MODEL_READ / MODEL_EVALUATE override the provider default."""
    return os.getenv(f"MODEL_{role.upper()}") or _DEFAULT_MODELS[LLM_PROVIDER][role]


# Claude effort per role (thinking depth and token spend).
ANTHROPIC_EFFORT = {"read": "low", "evaluate": "medium", "write": "low"}

# OpenAI reasoning effort per role, applied only to reasoning models (gpt-5*, o*).
# All roles run at "low", chosen by measurement on the dev cases (DECISIONS
# D-014, D-020): same accuracy as the default, about half the time and ~45%
# fewer output tokens. The quote verifier catches the extra invented quotes.
OPENAI_EFFORT = {"read": "low", "evaluate": "low", "write": "low"}
_OPENAI_EFFORT_OVERRIDE = os.getenv("OPENAI_REASONING_EFFORT", "").strip() or None


def openai_effort(role: str, model: str) -> str | None:
    """OPENAI_EFFORT_<ROLE> (e.g. OPENAI_EFFORT_EVALUATE=low) > OPENAI_REASONING_EFFORT > default."""
    if not model.startswith(("gpt-5", "o1", "o3", "o4")):
        return None
    per_role = os.getenv(f"OPENAI_EFFORT_{role.upper()}", "").strip() or None
    return per_role or _OPENAI_EFFORT_OVERRIDE or OPENAI_EFFORT[role]

# Input guardrails: replies outside this range never reach the model.
MIN_REPLY_CHARS = 40
MAX_REPLY_CHARS = 20_000
