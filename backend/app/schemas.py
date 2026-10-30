"""Typed contracts. The model's JSON must match these or the call fails."""

from typing import Literal

from pydantic import BaseModel, Field


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
