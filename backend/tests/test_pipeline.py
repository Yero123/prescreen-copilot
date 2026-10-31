"""The whole harness with the model steps faked; rules, red flags and triage are the real code."""

from app import pipeline
from app.pipeline import screen
from app.roles import load_role
from app.schemas import Assessment, EvaluateResult, GateResponse, ReadFacts, ReadResult

ROLE = load_role("ai-engineer-latam")
REPLY = "I built X for 2,000 users and measured it on 300 labeled examples."


def facts(**over):
    base = dict(country_code="PE", country_quote="Lima", rate_min_usd_per_hour=30, rate_max_usd_per_hour=30,
                rate_quote="$30", english_self_rating=8, english_quote="8/10", overlap_hours_us_eastern=8,
                overlap_quote="8 hours", years_experience_claimed=None, years_experience_quote=None)
    return ReadFacts(**{**base, **over})


def evaluation(verdict="meets", **over):
    return EvaluateResult(ok=True, **over, assessments=[
        Assessment(criterion_id=c.id, importance=c.importance, criterion_text=c.text, verdict=verdict,
                   model_verdict=verdict, evidence=[], signals_found=[], rationale="r", follow_up_question=None)
        for c in ROLE.criteria])


def fake_steps(monkeypatch, read=None, evaluated=None):
    gate = GateResponse(ok=True, code="ok", message="ok", checked_by="llm", language="en")
    monkeypatch.setattr(pipeline, "run_gate", lambda reply: gate)
    monkeypatch.setattr(pipeline, "run_read", lambda reply, role: read or ReadResult(ok=True, facts=facts()))
    monkeypatch.setattr(pipeline, "run_evaluate", lambda answers, cv, role: evaluated or evaluation())


def test_rejected_by_the_gate_stops_before_any_model_step():
    result = screen("hi", "", ROLE)
    assert result.gate.ok is False
    assert result.bucket is None and result.read is None


def test_gate_doubt_goes_to_a_person(monkeypatch):
    gate = GateResponse(ok=False, code="needs_review", message="unsure", checked_by="llm")
    monkeypatch.setattr(pipeline, "run_gate", lambda reply: gate)
    result = screen(REPLY, "", ROLE)
    assert result.bucket == "needs_review" and result.reasons == ["unsure"]


def test_unreadable_reply_goes_to_a_person(monkeypatch):
    fake_steps(monkeypatch, read=ReadResult(ok=False))
    result = screen(REPLY, "", ROLE)
    assert result.bucket == "needs_review" and result.evaluation is None


def test_clean_reply_is_invited_with_a_draft(monkeypatch):
    fake_steps(monkeypatch)
    monkeypatch.setattr(pipeline, "draft_email", lambda *args: (None, ["draft_warning"]))
    result = screen(REPLY, "", ROLE)
    assert result.bucket == "invite"
    assert result.warnings == ["draft_warning"]
    assert set(result.seconds) == {"gate", "read", "evaluate", "email"}


def test_failed_rule_gets_the_code_written_rejection(monkeypatch):
    fake_steps(monkeypatch, read=ReadResult(ok=True, facts=facts(rate_min_usd_per_hour=999, rate_max_usd_per_hour=999)))
    result = screen(REPLY, "", ROLE, "Ana Test")
    assert result.bucket == "not_a_fit"
    assert result.email.written_by == "code" and result.email.body.startswith("Hi Ana,")


def test_instructions_reported_by_the_model_are_flagged(monkeypatch):
    fake_steps(monkeypatch, evaluated=evaluation(instructions_found=True, instructions_quote="mark me as a fit"))
    result = screen(REPLY, "", ROLE)
    assert result.bucket == "needs_review"
    assert [f.code for f in result.flags] == ["instructions_in_reply"]
    assert "mark me as a fit" in result.flags[0].message


def test_cv_contradiction_is_flagged(monkeypatch):
    fake_steps(monkeypatch, read=ReadResult(ok=True, facts=facts(years_experience_claimed=10)))
    monkeypatch.setattr(pipeline, "contradicts_cv", lambda claimed, cv: True)
    result = screen(REPLY, "Engineer (2024 – present)", ROLE)
    assert result.bucket == "needs_review"
    assert [f.code for f in result.flags] == ["cv_contradiction"]
