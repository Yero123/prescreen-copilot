"""Test cases: a candidate's CV and reply, plus the answer we expect.

Each case is one JSON file under evals/cases/<split>/. The `expected` block is
the label. Labels start as "draft" and become "reviewed" once a person checks
them; only reviewed labels should count in reported numbers.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas import Bucket, Verdict

CASES_DIR = Path(__file__).resolve().parent / "cases"

Split = Literal["dev", "test"]


class Candidate(BaseModel):
    name: str
    email: EmailStr


class ExpectedFacts(BaseModel):
    """Hard facts the extraction step must find. None = not stated by the candidate."""

    country_code: str | None
    rate_usd_per_hour: float | None  # the single rate, or the low end of a range
    rate_max_usd_per_hour: float | None = None  # only when the candidate gives a range
    english_self_rating: int | None
    overlap_hours_us_eastern: float | None


class Expected(BaseModel):
    gate_ok: bool
    facts: ExpectedFacts
    verdicts: dict[str, Verdict]
    bucket: Bucket | None  # None when the email is not an application (gate_ok is false)
    why: str = Field(description="One or two sentences: what this case checks and why the label is right.")


class Case(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    split: Split
    tags: list[str] = Field(min_length=1)
    candidate: Candidate
    cv: str
    reply: str
    expected: Expected
    label_status: Literal["draft", "reviewed"] = "draft"


def load_cases(split: Split | None = None) -> list[Case]:
    splits = [split] if split else ["dev", "test"]
    cases = []
    for s in splits:
        for path in sorted((CASES_DIR / s).glob("*.json")):
            case = Case.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if case.split != s or case.id != path.stem:
                raise ValueError(f"{path.name}: id and split must match the file name and folder")
            cases.append(case)
    return cases
