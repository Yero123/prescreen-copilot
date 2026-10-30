"""Role configuration: the questionnaire, the criteria and the hard rules.

A role is data, not prompt text. Recruiters change a criterion or a rule by
editing the role file; no code or prompt changes.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ROLES_DIR = Path(__file__).resolve().parents[1] / "roles"

Importance = Literal["must", "should", "nice"]


class Question(BaseModel):
    id: str = Field(pattern=r"^Q\d+$")
    text: str


class Criterion(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    importance: Importance
    text: str
    evidence_signals: list[str] = Field(min_length=1)
    main_questions: list[str] = Field(min_length=1)


class HardRules(BaseModel):
    allowed_country_codes: list[str] = Field(min_length=1)
    max_rate_usd_per_hour: float = Field(gt=0)
    min_english_self_rating: int = Field(ge=1, le=10)
    min_overlap_hours_us_eastern: float = Field(ge=0, le=24)

    @field_validator("allowed_country_codes")
    @classmethod
    def iso_codes(cls, codes: list[str]) -> list[str]:
        for code in codes:
            if not re.fullmatch(r"[A-Z]{2}", code):
                raise ValueError(f"{code!r} is not an ISO 3166-1 alpha-2 code")
        return codes


class Role(BaseModel):
    id: str
    title: str
    version: int = Field(ge=1)
    questionnaire: list[Question] = Field(min_length=1)
    criteria: list[Criterion] = Field(min_length=1)
    hard_rules: HardRules
    # Words that must never appear in an email to a candidate (e.g. the client's name).
    confidential_terms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self) -> "Role":
        question_ids = [q.id for q in self.questionnaire]
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("question ids must be unique")
        criterion_ids = [c.id for c in self.criteria]
        if len(set(criterion_ids)) != len(criterion_ids):
            raise ValueError("criterion ids must be unique")
        if not any(c.importance == "must" for c in self.criteria):
            raise ValueError("a role needs at least one 'must' criterion")
        for c in self.criteria:
            unknown = set(c.main_questions) - set(question_ids)
            if unknown:
                raise ValueError(f"criterion {c.id!r} points to unknown questions {sorted(unknown)}")
        return self

    def must_ids(self) -> list[str]:
        return [c.id for c in self.criteria if c.importance == "must"]


@lru_cache
def load_role(role_id: str) -> Role:
    path = ROLES_DIR / f"{role_id}.json"
    if not re.fullmatch(r"[a-z0-9-]+", role_id) or not path.is_file():
        raise KeyError(f"Unknown role {role_id!r}")
    return Role.model_validate(json.loads(path.read_text(encoding="utf-8")))


def list_role_ids() -> list[str]:
    return sorted(p.stem for p in ROLES_DIR.glob("*.json"))


# ---------- bias check on criteria (deterministic) ----------

# Terms that describe a person instead of a skill. A criterion that uses them
# can screen people out for who they are, so it gets a warning.
_BIAS_TERMS = {
    r"\bnative\b": "Can explain technical ideas clearly in English (judged by a person in the call)",
    r"\baccent\b": "Can explain technical ideas clearly in English (judged by a person in the call)",
    r"\b(young|youthful|digital native)\b": "Describe a skill or an outcome, not an age group",
    r"\b(recent grad(uate)?|years old)\b": "Describe a skill or an outcome, not an age group",
    r"\b(male|female|gender)\b": "Describe a skill or an outcome, not a personal trait",
    r"\b(nationality|citizen)\b": "Use the location rule instead of a nationality",
    r"\bculture fit\b": "Name the behavior you need (e.g. explains trade-offs, owns outcomes)",
}


class BiasWarning(BaseModel):
    criterion_id: str
    matched: str
    suggestion: str


def bias_warnings(role: Role) -> list[BiasWarning]:
    warnings = []
    for c in role.criteria:
        for pattern, suggestion in _BIAS_TERMS.items():
            m = re.search(pattern, c.text, flags=re.IGNORECASE)
            if m:
                warnings.append(BiasWarning(criterion_id=c.id, matched=m.group(0), suggestion=suggestion))
    return warnings
