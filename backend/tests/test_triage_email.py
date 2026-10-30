"""Triage rules and email checks are plain code. No API calls."""

from app.email import _rejection, check_email
from app.roles import load_role
from app.rules import check_rules
from app.schemas import Assessment, EmailLLM, EmailParagraphLLM, EvaluateResult, EvidenceQuote, Flag, ReadFacts
from app.triage import triage

ROLE = load_role("ai-engineer-latam")


def facts(**overrides) -> ReadFacts:
    base = dict(country_code="PE", country_quote="Lima", rate_min_usd_per_hour=30, rate_max_usd_per_hour=30,
                rate_quote="$30", english_self_rating=7, english_quote="7/10", overlap_hours_us_eastern=8,
                overlap_quote="8 hours", years_experience_claimed=None, years_experience_quote=None)
    base.update(overrides)
    return ReadFacts(**base)


def evaluation(**verdicts) -> EvaluateResult:
    assessments = []
    for c in ROLE.criteria:
        v = verdicts.get(c.id, "meets")
        evidence = [EvidenceQuote(source="Q1", quote="I built X")] if v == "meets" else []
        assessments.append(Assessment(criterion_id=c.id, importance=c.importance, criterion_text=c.text,
                                      verdict=v, model_verdict=v, evidence=evidence, signals_found=[],
                                      rationale="r", follow_up_question=None if v == "meets" else "Can you share an example?"))
    return EvaluateResult(ok=True, assessments=assessments)


def bucket(f=None, e=None, flags=()):
    return triage(ROLE, check_rules(f or facts(), ROLE.hard_rules), e or evaluation(), list(flags))[0]


def test_all_good_is_invite():
    assert bucket() == "invite"


def test_rule_fail_wins_over_everything():
    assert bucket(f=facts(country_code="ES"), flags=[Flag(code="x", message="m")]) == "not_a_fit"


def test_red_flag_goes_to_a_person():
    assert bucket(flags=[Flag(code="instructions_in_reply", message="m")]) == "needs_review"


def test_must_without_evidence_asks_for_more():
    assert bucket(e=evaluation(measures_quality="not_enough_evidence")) == "more_info"


def test_missing_rate_asks_for_more():
    assert bucket(f=facts(rate_min_usd_per_hour=None, rate_max_usd_per_hour=None)) == "more_info"


def test_nice_to_have_never_blocks_an_invite():
    assert bucket(e=evaluation(open_weight="not_enough_evidence")) == "invite"


def test_model_cannot_reject_a_must():
    assert bucket(e=evaluation(shipped_llm="does_not_meet")) == "needs_review"


def test_failed_step_goes_to_a_person():
    assert triage(ROLE, None, None, [])[0] == "needs_review"


def test_rejection_email_is_written_by_code_from_the_rules():
    rules = check_rules(facts(country_code="ES", rate_min_usd_per_hour=45, rate_max_usd_per_hour=45), ROLE.hard_rules)
    draft = _rejection(ROLE, rules, "Ana")
    assert draft.written_by == "code"
    assert draft.body.startswith("Hi Ana,")
    assert "within the budget of $40" in draft.body and "countries this role hires from" in draft.body


def email(*paragraphs):
    return EmailLLM(subject="Next step", paragraphs=[EmailParagraphLLM(text=t, based_on=ids) for t, ids in paragraphs])


def failed(checks):
    return [c.name for c in checks if not c.passed]


def test_good_invite_passes_every_check():
    material = {"E1": "shipped a triage service"}
    draft = email(("Your ticket triage work is very relevant.", ["E1"]),
                  ("Book a 30-minute call here: [SCHEDULING LINK].", []))
    assert failed(check_email("invite", ROLE, material, draft)) == []


def test_invite_without_grounded_sentence_fails():
    draft = email(("You seem like a great engineer!", []))
    assert "Personal sentence is backed by the candidate's answers" in failed(
        check_email("invite", ROLE, {"E1": "x"}, draft))


def test_forbidden_words_and_unknown_ids_fail():
    draft = email(("Our AI tool scored you highly and we can offer $50/h.", ["E9"]))
    names = failed(check_email("invite", ROLE, {"E1": "x"}, draft))
    assert "No salary, offers, scores or AI-screening language" in names
    assert "Every cited id exists" in names


def test_more_info_must_ask_everything_missing():
    material = {"M1": "How did you measure quality?", "R1": "What is your hourly rate in USD?"}
    draft = email(("How did you measure quality?", ["M1"]))
    checks = check_email("more_info", ROLE, material, draft)
    missing = next(c for c in checks if c.name == "Asks every missing item")
    assert not missing.passed and missing.detail == "R1"


def test_confidential_client_name_fails():
    role = ROLE.model_copy(update={"confidential_terms": ["Acme Labs"]})
    draft = email(("This role is with Acme Labs.", []))
    assert "No confidential names" in failed(check_email("invite", role, {}, draft))


def test_role_title_with_ai_is_allowed():
    draft = email(("Your support-call QA pipeline fits this AI Engineer role well.", ["E1"]))
    assert failed(check_email("invite", ROLE, {"E1": "x"}, draft)) == []


def test_flagged_word_is_allowed_when_it_echoes_the_candidates_evidence():
    material = {"E1": 'Measures quality: "we compare with 200 calls that supervisors already scored"'}
    draft = email(("I liked how you validate the model against calls your supervisors already scored.", ["E1"]))
    assert failed(check_email("invite", ROLE, material, draft)) == []
