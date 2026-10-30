"""The only module that talks to a model provider.

The harness asks for a typed answer. This module sends it to the provider set
in LLM_PROVIDER (Claude or OpenAI) and returns the same result shape, so the
rest of the code never depends on a vendor SDK.
"""

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

import pydantic

from app import config

T = TypeVar("T", bound=pydantic.BaseModel)
Role = Literal["read", "evaluate"]


class LLMError(Exception):
    """The provider could not be reached or rejected the request."""


@dataclass
class LLMResult(Generic[T]):
    parsed: T | None
    complete: bool  # False on refusal, cut-off answer or unparseable output
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


def parse(*, role: Role, system: str, user: str, schema: type[T], max_tokens: int = 4096) -> LLMResult[T]:
    model = config.model_for(role)
    if config.LLM_PROVIDER == "openai":
        return _parse_openai(model, role, system, user, schema, max_tokens)
    return _parse_anthropic(model, role, system, user, schema, max_tokens)


# ---------- Claude ----------

_anthropic_client = None


def _parse_anthropic(model, role, system, user, schema, max_tokens):
    import anthropic

    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    try:
        r = _anthropic_client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            output_config={"effort": config.ANTHROPIC_EFFORT[role]},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude returned HTTP {e.status_code}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Could not reach Claude") from e
    except pydantic.ValidationError:
        return LLMResult(None, False, "anthropic", model, 0, 0)

    parsed = r.parsed_output
    return LLMResult(
        parsed=parsed,
        complete=r.stop_reason == "end_turn" and parsed is not None,
        provider="anthropic",
        model=model,
        input_tokens=r.usage.input_tokens,
        output_tokens=r.usage.output_tokens,
    )


# ---------- OpenAI ----------

_openai_client = None


def _parse_openai(model, role, system, user, schema, max_tokens):
    import openai

    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI()  # reads OPENAI_API_KEY

    effort = config.openai_effort(role, model)
    extra = {"reasoning": {"effort": effort}} if effort else {}
    try:
        r = _openai_client.responses.parse(
            model=model,
            instructions=system,
            input=user,
            text_format=schema,
            max_output_tokens=max_tokens,
            **extra,
        )
    except openai.APIStatusError as e:
        raise LLMError(f"OpenAI returned HTTP {e.status_code}") from e
    except openai.APIConnectionError as e:
        raise LLMError("Could not reach OpenAI") from e
    except pydantic.ValidationError:
        return LLMResult(None, False, "openai", model, 0, 0)

    parsed = r.output_parsed
    usage = r.usage
    return LLMResult(
        parsed=parsed,
        complete=r.status == "completed" and parsed is not None,
        provider="openai",
        model=model,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
    )
