"""Deterministic red-flag checks: prompt injection, CV contradictions, protected attributes.

These run in code on every reply. They do not depend on the model noticing
anything, so a model that is fooled still cannot hide the attempt.
"""

import re
from datetime import date

# Text that addresses an AI or a reviewer instead of answering the questions.
_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget)\b[^.\n]{0,40}\b(previous|prior|above|earlier|all|your)\b[^.\n]{0,20}\b(instructions?|prompts?|rules?)\b",
    r"\b(system prompt|developer message)\b",
    r"\byou are (now|an? (ai|assistant|language model))\b",
    r"\b(mark|rate|score|grade|label)\b[^.\n]{0,30}\b(every|all|each)\b[^.\n]{0,20}\b(criteri(on|a)|met|as met)\b",
    r"\b(note|message|instruction)s? (to|for) (the )?(ai|llm|model|reviewer|screener|recruiter bot)\b",
    r"\b(as an ai|dear (ai|chatgpt|claude|model))\b",
    # Polite or indirect requests to an automated screener (found by the test set, see DECISIONS D-021).
    r"\b(automated|automatic|ai)\s+(screen(ing|er)?|review(er)?|system|bot|tool)\b[^.\n]{0,40}\b(reading|processing|reviewing|evaluating)\s+this\b",
    r"\b(treat|consider|mark|count|rate|score|record)\b[^.\n]{0,25}\b(all|every|each)\b[^.\n]{0,20}\b(criteri(on|a)|requirements?)\b[^.\n]{0,25}\b(met|satisfied|fulfilled|passed)\b",
    r"\bdear\s+(screening\s+)?(bot|system|algorithm|screener)\b",
]

# Personal attributes a screening must never use or mention.
_PROTECTED_PATTERNS = [
    r"\b(age|aged|years old|young|old(er)?)\b",
    r"\b(gender|male|female|woman|man|pregnan\w*|maternity)\b",
    r"\b(nationality|ethnicity|race|racial)\b",
    r"\bnative (english )?speaker\b",
    r"\baccent\b",
    r"\b(religio\w*|married|marital|children|disabilit\w*)\b",
]


def find_injection(text: str) -> list[str]:
    """Snippets that look like instructions aimed at an AI or a reviewer."""
    hits = []
    for pattern in _INJECTION_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append(m.group(0))
    return hits


def mentions_protected_attribute(text: str) -> list[str]:
    hits = []
    for pattern in _PROTECTED_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append(m.group(0))
    return hits


def cv_years(cv: str, today: date | None = None) -> float | None:
    """Years since the earliest work year written in the CV (e.g. '2021 – present')."""
    today = today or date.today()
    years = [int(y) for y in re.findall(r"\b(19[89]\d|20[0-4]\d)\b", cv) if int(y) <= today.year]
    if not years:
        return None
    return float(today.year - min(years))


def contradicts_cv(claimed_years: float | None, cv: str, tolerance: float = 2.0, today: date | None = None) -> bool:
    """True when the reply claims clearly more experience than the CV can account for."""
    from_cv = cv_years(cv, today)
    if claimed_years is None or from_cv is None:
        return False
    return claimed_years > from_cv + tolerance
