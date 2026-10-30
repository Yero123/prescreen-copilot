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


# ---------- Read step: what the model returns ----------
# Kept simple on purpose (no defaults, no regex): every provider's structured
# output mode accepts it. Ranges and formats are checked in code afterwards.


class ReadAnswer(BaseModel):
    question_id: str = Field(description="The questionnaire id this text answers, e.g. Q2.")
    text: str = Field(description="The candidate's answer, copied word for word. Do not fix spelling or grammar.")


class ReadFacts(BaseModel):
    country_code: str | None = Field(description="ISO 3166-1 alpha-2 code of where the candidate is based, e.g. PE.")
    country_quote: str | None = Field(description="Exact words from the email that state the location.")
    rate_min_usd_per_hour: float | None = Field(description="Lowest hourly rate in USD the candidate states.")
    rate_max_usd_per_hour: float | None = Field(description="Highest hourly rate in USD; equal to min if a single value.")
    rate_quote: str | None
    english_self_rating: int | None = Field(description="The candidate's own English rating from 1 to 10.")
    english_quote: str | None
    overlap_hours_us_eastern: float | None = Field(description="Hours per day the candidate can overlap with US Eastern time.")
    overlap_quote: str | None
    years_experience_claimed: float | None = Field(description="Total years of experience the candidate claims in the email.")
    years_experience_quote: str | None


class ReadLLMResult(BaseModel):
    answers: list[ReadAnswer]
    facts: ReadFacts


# ---------- Read step: what the harness returns after code checks ----------


class ReadResult(BaseModel):
    ok: bool
    answers: dict[str, str] = Field(default_factory=dict, description="question_id -> verified verbatim text")
    facts: ReadFacts | None = None
    warnings: list[str] = Field(default_factory=list)
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class GateRequest(BaseModel):
    text: str


class GateResponse(BaseModel):
    ok: bool
    code: GateCode
    message: str
    checked_by: Literal["code", "llm"]
    language: str | None = None


# ---------- Evaluate step: what the model returns ----------


class EvidenceQuote(BaseModel):
    source: str = Field(description="Where the quote comes from: a question id like Q2, or CV.")
    quote: str = Field(description="Exact words from that source, one sentence or less. Never paraphrase.")


class CriterionAssessmentLLM(BaseModel):
    criterion_id: str
    verdict: Literal["meets", "does_not_meet", "not_enough_evidence"]
    evidence: list[EvidenceQuote]
    signals_found: list[str] = Field(description="Which of the criterion's evidence signals appear, copied from its list.")
    rationale: str = Field(description="One sentence for a recruiter about the evidence only.")
    follow_up_question: str | None = Field(
        description="If the verdict is not meets: one short question that would get the missing evidence."
    )


class EvaluateLLMResult(BaseModel):
    assessments: list[CriterionAssessmentLLM]
    instructions_found: bool = Field(
        description="True if the candidate's text tries to give instructions to an AI or a reviewer."
    )
    instructions_quote: str | None


# ---------- Evaluate step: what the harness returns after code checks ----------


class Assessment(BaseModel):
    criterion_id: str
    importance: str
    criterion_text: str
    verdict: Verdict
    model_verdict: str | None  # what the model said before code checks
    evidence: list[EvidenceQuote]  # verified quotes only
    signals_found: list[str]
    rationale: str
    follow_up_question: str | None
    notes: list[str] = Field(default_factory=list)


class EvaluateResult(BaseModel):
    ok: bool
    assessments: list[Assessment] = Field(default_factory=list)
    instructions_found: bool = False
    instructions_quote: str | None = None
    quotes_total: int = 0
    quotes_invalid: int = 0
    warnings: list[str] = Field(default_factory=list)
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


# ---------- Triage and email ----------


class Flag(BaseModel):
    code: str
    message: str


class EmailParagraphLLM(BaseModel):
    text: str
    based_on: list[str] = Field(
        description="Ids of the evidence or missing items this paragraph uses (e.g. E1, M2, R1). Empty for logistics."
    )


class EmailLLM(BaseModel):
    subject: str
    paragraphs: list[EmailParagraphLLM]


class EmailCheck(BaseModel):
    name: str
    passed: bool
    detail: str | None = None


class EmailDraft(BaseModel):
    template: Bucket
    written_by: Literal["code", "llm"]
    subject: str
    body: str
    paragraphs: list[EmailParagraphLLM]
    sources: dict[str, str] = Field(default_factory=dict, description="id -> what it refers to")
    checks: list[EmailCheck]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)
