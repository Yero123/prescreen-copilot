"""Step 5 of the harness: suggest the next step, by explicit rules.

The bucket is a suggestion with its reasons, never a score or a ranking, and
never a final decision. Order matters; the first rule that applies wins:

1. A step failed (model error, unreadable reply)       -> needs_review
2. A hard rule failed (checked in code)                -> not_a_fit
3. A red flag (injection, CV contradiction)            -> needs_review
4. A criterion needs a person, or a must is contradicted -> needs_review
5. A must lacks evidence, or a rule fact is missing    -> more_info
6. Otherwise                                            -> invite

The model never rejects anyone: a "does_not_meet" on a must goes to a person,
and only a rule checked in code can lead to not_a_fit.
"""

from app.roles import Role
from app.rules import RulesResult
from app.schemas import Bucket, EvaluateResult, Flag


def triage(role: Role, rules: RulesResult | None, evaluation: EvaluateResult | None,
           flags: list[Flag]) -> tuple[Bucket, list[str]]:
    if rules is None or evaluation is None or not evaluation.ok:
        return "needs_review", ["The reply could not be fully processed. A person should read it."]

    if rules.any_fail:
        return "not_a_fit", [f"{c.label}: {c.detail}" for c in rules.failed()]

    if flags:
        return "needs_review", [f.message for f in flags]

    must_ids = set(role.must_ids())
    review = [a for a in evaluation.assessments if a.verdict == "needs_review"]
    contradicted = [a for a in evaluation.assessments
                    if a.criterion_id in must_ids and a.verdict == "does_not_meet"]
    if review or contradicted:
        reasons = [f"Check “{a.criterion_text}”: {a.rationale}" for a in review + contradicted]
        return "needs_review", reasons

    missing = [a for a in evaluation.assessments
               if a.criterion_id in must_ids and a.verdict == "not_enough_evidence"]
    if missing or rules.unknown:
        reasons = [f"No evidence yet for “{a.criterion_text}”" for a in missing]
        reasons += [f"{c.label}: not stated" for c in rules.checks if c.status == "unknown"]
        return "more_info", reasons

    return "invite", ["Meets every must-have and passes every rule."]
