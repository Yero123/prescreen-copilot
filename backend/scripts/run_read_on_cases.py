"""Run the read step on every dev case and compare the hard facts with the labels.

Usage (from the repo root):  make read-cases
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.read import run_read  # noqa: E402
from app.roles import load_role  # noqa: E402
from evals.cases import load_cases  # noqa: E402

role = load_role("ai-engineer-latam")
cases = load_cases("dev")
fact_hits = fact_total = 0
print(f"Read on {len(cases)} dev cases · {config.LLM_PROVIDER} · {config.model_for('read')}\n")

for case in cases:
    start = time.perf_counter()
    result = run_read(case.reply, role)
    seconds = time.perf_counter() - start
    if not result.ok:
        print(f"ERROR {case.id}: {result.warnings}")
        continue
    exp, got = case.expected.facts, result.facts
    pairs = {
        "country": (exp.country_code, got.country_code),
        "rate": (exp.rate_usd_per_hour, got.rate_max_usd_per_hour),
        "english": (exp.english_self_rating, got.english_self_rating),
        "overlap": (exp.overlap_hours_us_eastern, got.overlap_hours_us_eastern),
    }
    marks = []
    for name, (want, have) in pairs.items():
        ok = want == have
        fact_hits += ok
        fact_total += 1
        marks.append(f"{name}={'ok' if ok else f'WANT {want} GOT {have}'}")
    print(f"{case.id:<22} answers={sorted(result.answers)}  {seconds:.1f}s  "
          f"tokens in/out={result.input_tokens}/{result.output_tokens}")
    print(f"    {'  '.join(marks)}")
    if result.warnings:
        print(f"    warnings: {result.warnings}")

print(f"\nHard facts: {fact_hits}/{fact_total} match the labels")
