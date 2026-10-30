"""Typed contracts. The model's JSON must match these or the call fails."""

from typing import Literal

from pydantic import BaseModel, Field

# Per-criterion verdict. "needs_review" = a person must look (failed quote
# check, contradiction, injection in that answer, or inconsistent runs).
Verdict = Literal["meets", "does_not_meet", "not_enough_evidence", "needs_review"]

# Suggested next step for the recruiter. Never a final decision.
Bucket = Literal["invite", "more_info", "not_a_fit", "needs_review"]


class GateLLMResult(BaseModel):
    """What the model returns when asked: is this a reply to our questionnaire?"""

    is_screening_reply: bool = Field(
        description="True only if the text is a candidate answering the screening questions."
    )
    language: Literal["en", "es", "pt", "other"]
    reason: str = Field(description="One short sentence a recruiter can read.")


GateCode = Literal[
    "ok",
    "empty",
    "too_short",
    "too_long",
    "not_a_screening_reply",
    "needs_review",
]


class GateRequest(BaseModel):
    text: str


class GateResponse(BaseModel):
    ok: bool
    code: GateCode
    message: str
    checked_by: Literal["code", "llm"]
    language: str | None = None
