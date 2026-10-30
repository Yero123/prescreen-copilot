"""How the gate reacts to each kind of model answer. The model is faked: no API calls."""

from app import gate, llm
from app.schemas import GateLLMResult


def fake_parse(result=None, error=None):
    def _parse(**_kwargs):
        if error:
            raise error
        return result
    return _parse


REPLY = "I built a ticket triage service on the Claude API that routes 2,000 tickets a day."


def make_result(parsed, complete=True):
    return llm.LLMResult(parsed=parsed, complete=complete, provider="fake", model="fake",
                         input_tokens=0, output_tokens=0)


def test_provider_error_goes_to_a_person(monkeypatch):
    monkeypatch.setattr(llm, "parse", fake_parse(error=llm.LLMError("OpenAI returned HTTP 500")))
    result = gate.run_gate(REPLY)
    assert result.code == "needs_review"
    assert not result.ok


def test_incomplete_answer_is_never_a_pass(monkeypatch):
    monkeypatch.setattr(llm, "parse", fake_parse(make_result(None, complete=False)))
    assert gate.run_gate(REPLY).code == "needs_review"


def test_model_says_not_a_reply(monkeypatch):
    answer = GateLLMResult(is_screening_reply=False, language="en", reason="It is a recipe.")
    monkeypatch.setattr(llm, "parse", fake_parse(make_result(answer)))
    result = gate.run_gate(REPLY)
    assert result.code == "not_a_screening_reply"
    assert result.message == "It is a recipe."


def test_model_says_valid_reply(monkeypatch):
    answer = GateLLMResult(is_screening_reply=True, language="en", reason="Answers the questions.")
    monkeypatch.setattr(llm, "parse", fake_parse(make_result(answer)))
    result = gate.run_gate(REPLY)
    assert result.ok and result.code == "ok" and result.checked_by == "llm"
