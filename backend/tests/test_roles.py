"""The role file loads, is consistent, and bad roles are rejected. No API calls."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.roles import Role, bias_warnings, load_role

ROLE_ID = "ai-engineer-latam"


def test_shipped_role_loads():
    role = load_role(ROLE_ID)
    assert role.must_ids() == ["shipped_llm", "measures_quality"]
    assert role.hard_rules.max_rate_usd_per_hour == 40
    assert "PE" in role.hard_rules.allowed_country_codes


def test_shipped_role_has_no_bias_warnings():
    assert bias_warnings(load_role(ROLE_ID)) == []


def base_role(**changes) -> dict:
    data = load_role(ROLE_ID).model_dump()
    data.update(changes)
    return data


def test_role_without_a_must_criterion_is_rejected():
    data = base_role()
    for c in data["criteria"]:
        c["importance"] = "nice"
    with pytest.raises(ValidationError, match="must"):
        Role.model_validate(data)


def test_criterion_pointing_to_unknown_question_is_rejected():
    data = base_role()
    data["criteria"][0]["main_questions"] = ["Q9"]
    with pytest.raises(ValidationError, match="Q9"):
        Role.model_validate(data)


def test_country_must_be_an_iso_code():
    data = base_role()
    data["hard_rules"]["allowed_country_codes"] = ["Peru"]
    with pytest.raises(ValidationError, match="ISO"):
        Role.model_validate(data)


def test_biased_criterion_gets_a_warning():
    data = base_role()
    data["criteria"][0]["text"] = "Native English speaker"
    warnings = bias_warnings(Role.model_validate(data))
    assert len(warnings) == 1
    assert warnings[0].matched.lower() == "native"
    assert "clearly in English" in warnings[0].suggestion


def test_api_serves_the_role_and_rejects_unknown_ones():
    client = TestClient(app)
    ok = client.get(f"/api/roles/{ROLE_ID}")
    assert ok.status_code == 200
    assert ok.json()["bias_warnings"] == []
    assert client.get("/api/roles/../../etc/passwd").status_code == 404
    assert client.get("/api/roles/unknown-role").status_code == 404
