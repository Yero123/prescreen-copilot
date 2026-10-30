"""The test cases are well formed and agree with the role. No API calls."""

from app.gate import precheck, strip_quoted_lines
from app.roles import load_role
from evals.cases import load_cases

ROLE = load_role("ai-engineer-latam")


def test_dev_cases_load():
    cases = load_cases("dev")
    assert len(cases) >= 5
    assert len({c.id for c in cases}) == len(cases)


def test_every_case_labels_every_criterion_of_the_role():
    role_ids = {c.id for c in ROLE.criteria}
    for case in load_cases():
        assert set(case.expected.verdicts) == role_ids, case.id


def test_expected_bucket_agrees_with_the_hard_rules():
    """If a labeled fact breaks a hard rule, the expected bucket must be not_a_fit."""
    rules = ROLE.hard_rules
    for case in load_cases():
        f = case.expected.facts
        breaks_rule = (
            (f.country_code is not None and f.country_code not in rules.allowed_country_codes)
            or (f.rate_usd_per_hour is not None and f.rate_usd_per_hour > rules.max_rate_usd_per_hour)
            or (f.english_self_rating is not None and f.english_self_rating < rules.min_english_self_rating)
            or (f.overlap_hours_us_eastern is not None and f.overlap_hours_us_eastern < rules.min_overlap_hours_us_eastern)
        )
        if breaks_rule:
            assert case.expected.bucket == "not_a_fit", case.id


def test_bucket_is_empty_exactly_when_the_gate_rejects():
    for case in load_cases():
        assert (case.expected.bucket is None) == (not case.expected.gate_ok), case.id


def test_counterfactual_pairs_share_labels():
    pairs = {}
    for case in load_cases():
        for tag in case.tags:
            if tag.startswith("pair:"):
                pairs.setdefault(tag, []).append(case)
    for tag, members in pairs.items():
        assert len(members) == 2, tag
        a, b = members
        assert a.expected.verdicts == b.expected.verdicts, tag
        assert a.expected.bucket == b.expected.bucket, tag


def test_gate_ok_cases_pass_the_deterministic_precheck():
    for case in load_cases():
        if case.expected.gate_ok:
            assert precheck(strip_quoted_lines(case.reply)) is None, case.id
