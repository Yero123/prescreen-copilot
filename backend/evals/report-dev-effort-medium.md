# Eval report · dev-effort-medium

- Run: 2026-10-30 02:27 UTC · provider `openai` · read `gpt-5-mini` · evaluate `gpt-5` · write `gpt-5-mini`
- Cases: 15 · crashes: 0

| Metric | Result | Target |
|---|---|---|
| Gate decision matches label | 15/15 (100%) | 100% |
| Hard facts extracted correctly | 70/70 (100%) | 100% |
| Criterion verdicts match label | 55/56 (98%) | report |
| Suggested next step matches label | 15/15 (100%) | report |
| False rejects (good candidate → not a fit) | 0 | 0 |
| Unsafe invites (should not be invited → invite) | 0 | 0 |
| Injection attempts flagged | 1/1 (100%) | 100% |
| Verdict flips in counterfactual pairs | 0 across 1 pairs | 0 |
| Model quotes that failed verification (dropped) | 0/88 (0%) | report |
| Invalid quotes left after the verifier | 0 (by construction) | 0 |
| Email drafts · failed checks | 11 drafts · 0 failed checks | 0 |
| Median seconds per candidate | 53.1 s | report |
| Tokens (read + evaluate) | 31,551 in · 49,109 out | report |

## Per criterion

| Criterion | Agreement |
|---|---|
| `shipped_llm` | 14/14 (100%) |
| `measures_quality` | 14/14 (100%) |
| `deliberate_design` | 13/14 (93%) |
| `open_weight` | 14/14 (100%) |

## Mismatches

- **honest-not-shipped**: bucket: want needs_review, got needs_review; verdicts: {'deliberate_design': 'want does_not_meet, got meets'}; reasons: ['Check “Has shipped LLM features to production”: States explicitly they have not shipped any LLM feature to production.', 'Check “Measures output quality (evals, test sets, agreement with humans)”: Describes only ad-hoc manual checks, with no test set or metrics.']
