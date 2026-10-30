"""The read step keeps only what it can verify. The model is faked: no API calls."""

from app import llm, read
from app.roles import load_role
from app.schemas import ReadAnswer, ReadFacts, ReadLLMResult
from app.verify import number_in, quote_in

ROLE = load_role("ai-engineer-latam")

EMAIL = (
    "1- i make a QA pipeline for the support calls.\n"
    "2- we take 200 calls and compare with the model, agreement went 70% to 88%.\n"
    "5- Lima Peru, 30 usd per hour, english 7 of 10, i can work 8 hours same time with US east."
)


def facts(**overrides) -> ReadFacts:
    base = dict(
        country_code="PE", country_quote="Lima Peru",
        rate_min_usd_per_hour=30, rate_max_usd_per_hour=30, rate_quote="30 usd per hour",
        english_self_rating=7, english_quote="english 7 of 10",
        overlap_hours_us_eastern=8, overlap_quote="i can work 8 hours same time with US east",
        years_experience_claimed=None, years_experience_quote=None,
    )
    base.update(overrides)
    return ReadFacts(**base)


def run_with(answers, f):
    parsed = ReadLLMResult(answers=answers, facts=f)
    fake = llm.LLMResult(parsed=parsed, complete=True, provider="fake", model="fake",
                         input_tokens=0, output_tokens=0)
    original = llm.parse
    llm.parse = lambda **_: fake
    try:
        return read.run_read(EMAIL, ROLE)
    finally:
        llm.parse = original


GOOD_ANSWERS = [
    ReadAnswer(question_id="Q1", text="i make a QA pipeline for the support calls."),
    ReadAnswer(question_id="Q2", text="we take 200 calls and compare with the model, agreement went 70% to 88%."),
]


def test_quote_and_number_helpers():
    assert quote_in("Lima  Peru,\n30 usd", "lima peru, 30 USD")
    assert not quote_in("Lima Peru", "Bogotá")
    assert number_in("english 7 of 10", 7)
    assert not number_in("english 7 of 10", 8)


def test_verbatim_answers_and_facts_are_kept():
    result = run_with(GOOD_ANSWERS, facts())
    assert result.ok
    assert set(result.answers) == {"Q1", "Q2"}
    assert result.facts.country_code == "PE"
    assert result.facts.rate_max_usd_per_hour == 30
    assert "no_answer:Q3" in result.warnings


def test_answer_with_fixed_grammar_is_dropped():
    paraphrased = [ReadAnswer(question_id="Q1", text="I built a QA pipeline for support calls.")]
    result = run_with(paraphrased, facts())
    assert "Q1" not in result.answers
    assert "answer_not_verbatim:Q1" in result.warnings


def test_answer_to_unknown_question_is_dropped():
    result = run_with([ReadAnswer(question_id="Q9", text="i make a QA pipeline")], facts())
    assert "answer_unknown_question:Q9" in result.warnings


def test_number_not_in_its_quote_is_dropped():
    result = run_with(GOOD_ANSWERS, facts(english_self_rating=9))
    assert result.facts.english_self_rating is None
    assert "fact_unverified:english_self_rating" in result.warnings


def test_invented_quote_is_dropped():
    result = run_with(GOOD_ANSWERS, facts(rate_quote="my rate is 30 dollars"))
    assert result.facts.rate_max_usd_per_hour is None
    assert "fact_unverified:rate_max_usd_per_hour" in result.warnings


def test_country_must_be_a_code_backed_by_a_quote():
    result = run_with(GOOD_ANSWERS, facts(country_code="Peru"))
    assert result.facts.country_code is None
    result = run_with(GOOD_ANSWERS, facts(country_code="pe"))
    assert result.facts.country_code == "PE"


def test_single_rate_fills_both_ends():
    result = run_with(GOOD_ANSWERS, facts(rate_min_usd_per_hour=None))
    assert result.facts.rate_min_usd_per_hour == result.facts.rate_max_usd_per_hour == 30


def test_provider_error_is_not_ok():
    original = llm.parse
    def boom(**_):
        raise llm.LLMError("OpenAI returned HTTP 500")
    llm.parse = boom
    try:
        result = read.run_read(EMAIL, ROLE)
    finally:
        llm.parse = original
    assert not result.ok
    assert result.warnings[0].startswith("llm_error")
