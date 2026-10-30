"""Tests for the deterministic part of the gate. No API calls, no key needed."""

from app.gate import precheck, strip_quoted_lines


def test_quoted_original_message_is_removed():
    text = "My answers are below.\n> On Tue, Sofia wrote:\n> please answer"
    assert strip_quoted_lines(text) == "My answers are below."


def test_empty_text_is_rejected_by_code():
    result = precheck("   ")
    assert result.code == "empty"
    assert result.checked_by == "code"


def test_short_text_is_rejected_by_code():
    assert precheck("ok, thanks").code == "too_short"


def test_huge_text_is_rejected_by_code():
    assert precheck("a" * 20_001).code == "too_long"


def test_normal_text_passes_to_the_model():
    assert precheck("I built a ticket triage service on the Claude API for 2,000 tickets a day.") is None
