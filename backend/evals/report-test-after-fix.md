# Eval report · test-after-fix

- Run: 2026-10-30 02:39 UTC · provider `openai` · read `gpt-5-mini` · evaluate `gpt-5` · write `gpt-5-mini`
- Cases: 15 · crashes: 0

| Metric | Result | Target |
|---|---|---|
| Gate decision matches label | 15/15 (100%) | 100% |
| Hard facts extracted correctly | 70/70 (100%) | 100% |
| Criterion verdicts match label | 56/56 (100%) | report |
| Suggested next step matches label | 15/15 (100%) | report |
| False rejects (good candidate → not a fit) | 0 | 0 |
| Unsafe invites (should not be invited → invite) | 0 | 0 |
| Injection attempts flagged | 2/2 (100%) | 100% |
| Verdict flips in counterfactual pairs | 0 across 2 pairs | 0 |
| Model quotes that failed verification (dropped) | 1/88 (1%) | report |
| Invalid quotes left after the verifier | 0 (by construction) | 0 |
| Email drafts · failed checks | 11 drafts · 1 failed checks | 0 |
| Median seconds per candidate | 24.4 s | report |
| Tokens (read + evaluate) | 31,676 in · 27,281 out | report |

## Per criterion

| Criterion | Agreement |
|---|---|
| `shipped_llm` | 14/14 (100%) |
| `measures_quality` | 14/14 (100%) |
| `deliberate_design` | 14/14 (100%) |
| `open_weight` | 14/14 (100%) |

## Mismatches

None.
