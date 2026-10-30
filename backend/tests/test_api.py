"""API flow with the harness faked: storage, history, overrides, decisions, email events."""

from fastapi.testclient import TestClient

import app.main as main
from app.pipeline import ScreenResult
from app.rules import check_rules
from app.roles import load_role
from app.schemas import Assessment, EvaluateResult, EvidenceQuote, GateResponse, ReadFacts, ReadResult

ROLE = load_role("ai-engineer-latam")


def fake_screen(reply, cv, role, name):
    facts = ReadFacts(country_code="PE", country_quote="Lima", rate_min_usd_per_hour=30, rate_max_usd_per_hour=30,
                      rate_quote="$30", english_self_rating=8, english_quote="8/10", overlap_hours_us_eastern=8,
                      overlap_quote="8 hours", years_experience_claimed=None, years_experience_quote=None)
    assessments = [Assessment(criterion_id=c.id, importance=c.importance, criterion_text=c.text,
                              verdict="meets", model_verdict="meets",
                              evidence=[EvidenceQuote(source="Q1", quote="I built X")], signals_found=[],
                              rationale="Concrete.", follow_up_question=None) for c in role.criteria]
    return ScreenResult(
        gate=GateResponse(ok=True, code="ok", message="ok", checked_by="llm", language="en"),
        read=ReadResult(ok=True, answers={"Q1": "I built X"}, facts=facts),
        rules=check_rules(facts, role.hard_rules),
        evaluation=EvaluateResult(ok=True, assessments=assessments),
        bucket="invite", reasons=["Meets every must-have and passes every rule."],
    )


def client(monkeypatch):
    monkeypatch.setattr(main, "screen", fake_screen)
    return TestClient(main.app)


NEW = {"name": "Ana Test", "email": "Ana.Test@example.com", "cv": "Engineer (2020 – present)",
       "reply": "I built X for 2,000 users and measured it on 300 labeled examples."}


def test_submit_list_and_read(monkeypatch):
    c = client(monkeypatch)
    created = c.post("/api/submissions", json=NEW)
    assert created.status_code == 202
    sid = created.json()["id"]
    detail = c.get(f"/api/submissions/{sid}").json()
    assert detail["status"] == "done" and detail["suggested_bucket"] == "invite"
    rows = c.get("/api/submissions").json()
    assert any(r["id"] == sid for r in rows)


def test_same_email_is_one_candidate_with_history(monkeypatch):
    c = client(monkeypatch)
    first = c.post("/api/submissions", json={**NEW, "email": "same@example.com"}).json()["id"]
    second = c.post("/api/submissions", json={**NEW, "email": "SAME@example.com"}).json()["id"]
    detail = c.get(f"/api/submissions/{second}").json()
    assert [h["id"] for h in detail["history"]] == [first, second]
    emails = [r["candidate"]["email"] for r in c.get("/api/submissions").json()]
    assert emails.count("same@example.com") == 1


def test_override_recomputes_the_suggested_step_without_a_model(monkeypatch):
    c = client(monkeypatch)
    sid = c.post("/api/submissions", json={**NEW, "email": "ov@example.com"}).json()["id"]
    after = c.post(f"/api/submissions/{sid}/overrides",
                   json={"criterion_id": "measures_quality", "verdict": "not_enough_evidence",
                         "reason": "Only a vague metric"}).json()
    assert after["suggested_bucket"] == "more_info"
    assert after["overrides"]["measures_quality"]["reason"] == "Only a vague metric"
    cleared = c.post(f"/api/submissions/{sid}/overrides",
                     json={"criterion_id": "measures_quality", "verdict": None}).json()
    assert cleared["suggested_bucket"] == "invite"


def test_decision_and_email_events(monkeypatch):
    c = client(monkeypatch)
    sid = c.post("/api/submissions", json={**NEW, "email": "dec@example.com"}).json()["id"]
    assert c.post(f"/api/submissions/{sid}/decision", json={"bucket": "more_info"}).json()["decision"] == "more_info"
    assert c.post(f"/api/submissions/{sid}/email/edit", json={"body": "Hi Ana, ..."}).json()["email_edited_body"] == "Hi Ana, ..."
    assert c.post(f"/api/submissions/{sid}/email/approve").json()["email_approved"] is True


def test_unknown_criterion_and_submission(monkeypatch):
    c = client(monkeypatch)
    sid = c.post("/api/submissions", json={**NEW, "email": "x@example.com"}).json()["id"]
    assert c.post(f"/api/submissions/{sid}/overrides",
                  json={"criterion_id": "nope", "verdict": "meets"}).status_code == 422
    assert c.get("/api/submissions/99999").status_code == 404


def test_access_code_is_enforced_when_set(monkeypatch):
    import app.security as security
    monkeypatch.setattr(security, "ACCESS_CODE", "letmein")
    c = client(monkeypatch)
    assert c.get("/api/submissions").status_code == 401
    assert c.get("/api/submissions", headers={"X-Access-Code": "letmein"}).status_code == 200
    assert c.get("/health").status_code == 200
