"""Runtime settings, read once from environment variables."""

import os

# Which provider answers the LLM calls: "anthropic" (target) or "openai".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
if LLM_PROVIDER not in ("anthropic", "openai"):
    raise ValueError(f"LLM_PROVIDER must be 'anthropic' or 'openai', got {LLM_PROVIDER!r}")

# Two roles: "read" is a narrow, cheap task; "evaluate" needs judgment.
_DEFAULT_MODELS = {
    "anthropic": {"read": "claude-haiku-5-5", "evaluate": "claude-sonnet-5-5"},
    "openai": {"read": "gpt-5-mini", "evaluate": "gpt-5"},
}


def model_for(role: str) -> str:
    """MODEL_READ / MODEL_EVALUATE override the provider default."""
    return os.getenv(f"MODEL_{role.upper()}") or _DEFAULT_MODELS[LLM_PROVIDER][role]


# Claude effort per role (thinking depth and token spend).
ANTHROPIC_EFFORT = {"read": "low", "evaluate": "medium"}

# Only for OpenAI reasoning models (e.g. "low"). Leave empty for other models.
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "").strip() or None

# Input guardrails: replies outside this range never reach the model.
MIN_REPLY_CHARS = 40
MAX_REPLY_CHARS = 20_000
