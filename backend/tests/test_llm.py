"""The provider calls, checked against the real SDK signatures. No network and no API key."""

import inspect
from types import SimpleNamespace

import anthropic
import openai
import pytest
from pydantic import BaseModel

from app import config, llm


class Out(BaseModel):
    answer: str


class FakeParse:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.kwargs = response, error, None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def claude(monkeypatch, fake):
    monkeypatch.setattr(config, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(llm, "_anthropic_client", SimpleNamespace(messages=SimpleNamespace(parse=fake)))


def gpt(monkeypatch, fake):
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(llm, "_openai_client", SimpleNamespace(responses=SimpleNamespace(parse=fake)))


def claude_response(stop_reason="end_turn", parsed=Out(answer="x")):
    return SimpleNamespace(parsed_output=parsed, stop_reason=stop_reason,
                           usage=SimpleNamespace(input_tokens=1, output_tokens=2))


def gpt_response(status="completed", parsed=Out(answer="x")):
    return SimpleNamespace(output_parsed=parsed, status=status, usage=SimpleNamespace(input_tokens=1, output_tokens=2))


def call(role="evaluate"):
    return llm.parse(role=role, system="s", user="u", schema=Out)


@pytest.fixture(autouse=True)
def no_model_overrides(monkeypatch):
    for role in ("READ", "EVALUATE", "WRITE"):
        monkeypatch.delenv(f"MODEL_{role}", raising=False)


def test_claude_call_fits_the_sdk_signature(monkeypatch):
    fake = FakeParse(claude_response())
    claude(monkeypatch, fake)
    result = call()
    inspect.signature(anthropic.Anthropic(api_key="x").messages.parse).bind(**fake.kwargs)
    assert fake.kwargs["model"] == "claude-sonnet-5-5"
    assert fake.kwargs["output_config"] == {"effort": "medium"}
    assert result.complete and result.parsed.answer == "x"


def test_haiku_is_called_without_effort(monkeypatch):
    fake = FakeParse(claude_response())
    claude(monkeypatch, fake)
    call("read")
    assert fake.kwargs["model"] == "claude-haiku-4-5"
    assert "output_config" not in fake.kwargs


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_claude_cut_off_or_refused_is_incomplete(monkeypatch, stop_reason):
    claude(monkeypatch, FakeParse(claude_response(stop_reason)))
    assert call().complete is False


def test_claude_connection_error_becomes_llm_error(monkeypatch):
    claude(monkeypatch, FakeParse(error=anthropic.APIConnectionError(request=None)))
    with pytest.raises(llm.LLMError):
        call()


def test_openai_call_fits_the_sdk_signature(monkeypatch):
    fake = FakeParse(gpt_response())
    gpt(monkeypatch, fake)
    result = call()
    inspect.signature(openai.OpenAI(api_key="x").responses.parse).bind(**fake.kwargs)
    assert fake.kwargs["model"] == "gpt-5"
    assert fake.kwargs["reasoning"] == {"effort": "low"}
    assert result.complete and result.parsed.answer == "x"


def test_openai_incomplete_status_is_incomplete(monkeypatch):
    gpt(monkeypatch, FakeParse(gpt_response("incomplete")))
    assert call().complete is False


def test_openai_connection_error_becomes_llm_error(monkeypatch):
    gpt(monkeypatch, FakeParse(error=openai.APIConnectionError(request=None)))
    with pytest.raises(llm.LLMError):
        call()
