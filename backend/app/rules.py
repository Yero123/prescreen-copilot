"""Step 3 of the harness: hard rules, in plain code.

Rules only see facts that survived verification in the read step. The model
never compares numbers or decides whether a rule passes.

Two choices protect candidates from wrong rejections:
- A missing fact is "unknown", not "fail": the next step is to ask, not reject.
- A rate range passes if its lowest value fits the budget (noted for the
  recruiter); it fails only when even the lowest value is above the limit.
"""

from typing import Literal

from pydantic import BaseModel

from app.roles import HardRules
from app.schemas import ReadFacts

RuleStatus = Literal["pass", "fail", "unknown"]

COUNTRY_NAMES = {
    "AR": "Argentina", "BO": "Bolivia", "BR": "Brazil", "CL": "Chile", "CO": "Colombia",
    "CR": "Costa Rica", "DO": "Dominican Republic", "EC": "Ecuador", "GT": "Guatemala",
    "HN": "Honduras", "MX": "Mexico", "NI": "Nicaragua", "PA": "Panama", "PE": "Peru",
    "PY": "Paraguay", "SV": "El Salvador", "UY": "Uruguay", "VE": "Venezuela",
    "US": "United States", "CA": "Canada", "ES": "Spain", "PT": "Portugal",
}


class RuleCheck(BaseModel):
    rule: Literal["location", "rate", "english", "overlap"]
    label: str
    status: RuleStatus
    detail: str


class RulesResult(BaseModel):
    checks: list[RuleCheck]

    @property
    def any_fail(self) -> bool:
        return any(c.status == "fail" for c in self.checks)

    @property
    def unknown(self) -> list[str]:
        return [c.rule for c in self.checks if c.status == "unknown"]


def _num(value: float) -> str:
    return f"{value:g}"


def check_location(facts: ReadFacts, rules: HardRules) -> RuleCheck:
    code = facts.country_code
    if code is None:
        return RuleCheck(rule="location", label="Location", status="unknown",
                         detail="Not stated in the reply")
    name = COUNTRY_NAMES.get(code, code)
    if code in rules.allowed_country_codes:
        return RuleCheck(rule="location", label="Location", status="pass",
                         detail=f"{name} · in the allowed region")
    return RuleCheck(rule="location", label="Location", status="fail",
                     detail=f"{name} · outside the allowed region")


def check_rate(facts: ReadFacts, rules: HardRules) -> RuleCheck:
    lo, hi, limit = facts.rate_min_usd_per_hour, facts.rate_max_usd_per_hour, rules.max_rate_usd_per_hour
    if lo is None:
        return RuleCheck(rule="rate", label="Rate", status="unknown", detail="Not stated in the reply")
    asked = f"${_num(lo)}/h" if lo == hi else f"${_num(lo)}–{_num(hi)}/h"
    if lo > limit:
        return RuleCheck(rule="rate", label="Rate", status="fail",
                         detail=f"{asked} > ${_num(limit)}/h budget")
    if hi is not None and hi > limit:
        return RuleCheck(rule="rate", label="Rate", status="pass",
                         detail=f"{asked}: low end fits the ${_num(limit)}/h budget, top end does not")
    return RuleCheck(rule="rate", label="Rate", status="pass",
                     detail=f"{asked} ≤ ${_num(limit)}/h budget")


def check_english(facts: ReadFacts, rules: HardRules) -> RuleCheck:
    rating, minimum = facts.english_self_rating, rules.min_english_self_rating
    if rating is None:
        return RuleCheck(rule="english", label="English (self-rated)", status="unknown",
                         detail="Not stated in the reply")
    ok = rating >= minimum
    return RuleCheck(rule="english", label="English (self-rated)", status="pass" if ok else "fail",
                     detail=f"{rating}/10 {'≥' if ok else '<'} {minimum}")


def check_overlap(facts: ReadFacts, rules: HardRules) -> RuleCheck:
    hours, minimum = facts.overlap_hours_us_eastern, rules.min_overlap_hours_us_eastern
    if hours is None:
        return RuleCheck(rule="overlap", label="Overlap with US Eastern", status="unknown",
                         detail="Not stated in the reply")
    ok = hours >= minimum
    return RuleCheck(rule="overlap", label="Overlap with US Eastern", status="pass" if ok else "fail",
                     detail=f"{_num(hours)} h {'≥' if ok else '<'} {_num(minimum)} h")


def check_rules(facts: ReadFacts, rules: HardRules) -> RulesResult:
    return RulesResult(checks=[
        check_location(facts, rules),
        check_rate(facts, rules),
        check_english(facts, rules),
        check_overlap(facts, rules),
    ])
