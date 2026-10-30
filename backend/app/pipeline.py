"""The whole harness for one reply: gate -> read -> rules -> evaluate -> red flags -> triage -> email."""

import time

from pydantic import BaseModel, Field

from app.checks import contradicts_cv, find_injection
from app.email import draft_email
from app.evaluate import run_evaluate
from app.gate import run_gate
from app.read import run_read
from app.roles import Role
from app.rules import RulesResult, check_rules
from app.schemas import Bucket, EmailDraft, EvaluateResult, Flag, GateResponse, ReadResult
from app.triage import triage


class ScreenResult(BaseModel):
    gate: GateResponse
    read: ReadResult | None = None
    rules: RulesResult | None = None
    evaluation: EvaluateResult | None = None
    flags: list[Flag] = Field(default_factory=list)
    bucket: Bucket | None = None  # None = not an application (gate rejected it)
    reasons: list[str] = Field(default_factory=list)
    email: EmailDraft | None = None
    warnings: list[str] = Field(default_factory=list)
    seconds: dict[str, float] = Field(default_factory=dict)

    @property
    def tokens(self) -> tuple[int, int]:
        parts = [p for p in (self.read, self.evaluation) if p is not None]
        return sum(p.input_tokens for p in parts), sum(p.output_tokens for p in parts)


def red_flags(reply: str, cv: str, read: ReadResult, evaluation: EvaluateResult | None) -> list[Flag]:
    flags: list[Flag] = []
    snippets = find_injection(f"{reply}\n{cv}")
    if snippets or (evaluation is not None and evaluation.instructions_found):
        quote = snippets[0] if snippets else (evaluation.instructions_quote or "")
        flags.append(Flag(code="instructions_in_reply",
                          message=f"The reply contains text aimed at the AI or a reviewer (“{quote[:80]}”). "
                                  "It was treated as text and changed no verdict."))
    claimed = read.facts.years_experience_claimed if read.facts else None
    if contradicts_cv(claimed, cv):
        flags.append(Flag(code="cv_contradiction",
                          message=f"The reply claims {claimed:g} years of experience; the CV covers fewer."))
    return flags


def screen(reply: str, cv: str, role: Role, candidate_name: str | None = None) -> ScreenResult:
    seconds: dict[str, float] = {}

    def timed(name, fn, *args):
        start = time.perf_counter()
        out = fn(*args)
        seconds[name] = round(time.perf_counter() - start, 2)
        return out

    gate = timed("gate", run_gate, reply)
    if not gate.ok:
        bucket = "needs_review" if gate.code == "needs_review" else None
        return ScreenResult(gate=gate, bucket=bucket, reasons=[gate.message], seconds=seconds)

    read = timed("read", run_read, reply, role)
    if not read.ok:
        return ScreenResult(gate=gate, read=read, bucket="needs_review",
                            reasons=["The reply could not be read. A person should check it."], seconds=seconds)

    rules = check_rules(read.facts, role.hard_rules)
    evaluation = timed("evaluate", run_evaluate, read.answers, cv, role)
    flags = red_flags(reply, cv, read, evaluation)
    bucket, reasons = triage(role, rules, evaluation, flags)
    email, warnings = timed("email", draft_email, role, bucket, rules, evaluation, candidate_name)

    return ScreenResult(gate=gate, read=read, rules=rules, evaluation=evaluation, flags=flags,
                        bucket=bucket, reasons=reasons, email=email,
                        warnings=read.warnings + evaluation.warnings + warnings, seconds=seconds)
