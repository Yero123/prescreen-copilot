"""Run the input gate on every test case and compare with the expected label.

Usage (from the repo root):  make gate-cases
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.gate import run_gate  # noqa: E402
from evals.cases import load_cases  # noqa: E402

cases = load_cases("dev")
hits = 0
print(f"Gate on {len(cases)} dev cases · {config.LLM_PROVIDER} · {config.model_for('read')}\n")
for case in cases:
    result = run_gate(case.reply)
    match = result.ok == case.expected.gate_ok
    hits += match
    print(f"{'PASS' if match else 'FAIL'}  {case.id:<22} expected ok={case.expected.gate_ok!s:<5} "
          f"got ok={result.ok!s:<5} code={result.code} lang={result.language}")
print(f"\n{hits}/{len(cases)} match the expected gate label")
