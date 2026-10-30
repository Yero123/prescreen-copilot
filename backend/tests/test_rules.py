"""Hard rules are plain code: exact, repeatable, no API calls."""

from app.roles import load_role
from app.rules import check_rules
from app.schemas import ReadFacts
from evals.cases import load_cases

RULES = load_role("ai-engineer-latam").hard_rules


def facts(**overrides) -> ReadFacts:
    base = dict(
        country_code="PE", country_quote="Lima, Peru",
        rate_min_usd_per_hour=30, rate_max_usd_per_hour=30, rate_quote="$30/h",
        english_self_rating=7, english_quote="7/10",
        overlap_hours_us_eastern=8, overlap_quote="8 hours",
        years_experience_claimed=None, years_experience_quote=None,
    )
    base.update(overrides)
    return ReadFacts(**base)


def status(result, rule):
    return next(c.status for c in result.checks if c.rule == rule)


def test_all_rules_pass():
    result = check_rules(facts(), RULES)
    assert not result.any_fail and result.unknown == []


def test_boundaries_are_inclusive():
    result = check_rules(facts(rate_min_usd_per_hour=40, rate_max_usd_per_hour=40,
                               english_self_rating=7, overlap_hours_us_eastern=4), RULES)
    assert not result.any_fail


def test_each_rule_can_fail():
    assert status(check_rules(facts(country_code="ES"), RULES), "location") == "fail"
    assert status(check_rules(facts(rate_min_usd_per_hour=45, rate_max_usd_per_hour=45), RULES), "rate") == "fail"
    assert status(check_rules(facts(english_self_rating=6), RULES), "english") == "fail"
    assert status(check_rules(facts(overlap_hours_us_eastern=3), RULES), "overlap") == "fail"


def test_rate_range_passes_when_the_low_end_fits():
    check = next(c for c in check_rules(facts(rate_min_usd_per_hour=35, rate_max_usd_per_hour=45), RULES).checks
                 if c.rule == "rate")
    assert check.status == "pass"
    assert "top end does not" in check.detail


def test_missing_fact_is_unknown_not_fail():
    result = check_rules(facts(rate_min_usd_per_hour=None, rate_max_usd_per_hour=None, country_code=None), RULES)
    assert not result.any_fail
    assert result.unknown == ["location", "rate"]


def test_labeled_cases_agree_with_the_rules():
    """A case fails a rule exactly when its label says not_a_fit."""
    for case in load_cases():
        f = case.expected.facts
        result = check_rules(facts(
            country_code=f.country_code,
            rate_min_usd_per_hour=f.rate_usd_per_hour, rate_max_usd_per_hour=f.rate_usd_per_hour,
            english_self_rating=f.english_self_rating, overlap_hours_us_eastern=f.overlap_hours_us_eastern,
        ), RULES)
        assert result.any_fail == (case.expected.bucket == "not_a_fit"), case.id
