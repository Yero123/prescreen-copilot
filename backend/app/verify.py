"""Deterministic checks on what the model returns. No model calls here.

The model may paraphrase, fix a candidate's grammar or invent a number.
These checks make sure every quote really exists in the source text and every
number really appears in its quote.
"""

import re

_TYPOGRAPHY = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def normalize(text: str) -> str:
    """Ignore differences that are not content: curly quotes, dashes, spacing, case."""
    return re.sub(r"\s+", " ", text.translate(_TYPOGRAPHY)).strip().casefold()


def quote_in(source: str, quote: str | None) -> bool:
    """True if `quote` appears word for word in `source` (after normalizing)."""
    if not quote or not quote.strip():
        return False
    return normalize(quote) in normalize(source)


def numbers_in(text: str) -> list[float]:
    return [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text)]


def number_in(quote: str | None, value: float) -> bool:
    """True if the extracted value is literally one of the numbers in its quote."""
    if quote is None:
        return False
    return any(abs(n - value) < 1e-9 for n in numbers_in(quote))
