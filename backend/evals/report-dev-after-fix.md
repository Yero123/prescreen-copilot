# Eval report · dev-after-fix

- Run: 2026-10-30 02:37 UTC · provider `openai` · read `gpt-5-mini` · evaluate `gpt-5` · write `gpt-5-mini`
- Cases: 16 · crashes: 0

| Metric | Result | Target |
|---|---|---|
| Gate decision matches label | 16/16 (100%) | 100% |
| Hard facts extracted correctly | 75/75 (100%) | 100% |
| Criterion verdicts match label | 58/60 (97%) | report |
| Suggested next step matches label | 16/16 (100%) | report |
| False rejects (good candidate → not a fit) | 0 | 0 |
| Unsafe invites (should not be invited → invite) | 0 | 0 |
| Injection attempts flagged | 2/2 (100%) | 100% |
| Verdict flips in counterfactual pairs | 0 across 1 pairs | 0 |
| Model quotes that failed verification (dropped) | 2/99 (2%) | report |
| Invalid quotes left after the verifier | 0 (by construction) | 0 |
| Email drafts · failed checks | 11 drafts · 0 failed checks | 0 |
| Median seconds per candidate | 26.2 s | report |
| Tokens (read + evaluate) | 34,449 in · 29,043 out | report |

## Per criterion

| Criterion | Agreement |
|---|---|
| `shipped_llm` | 15/15 (100%) |
| `measures_quality` | 14/15 (93%) |
| `deliberate_design` | 14/15 (93%) |
| `open_weight` | 15/15 (100%) |

## Mismatches

- **honest-not-shipped**: bucket: want needs_review, got needs_review; verdicts: {'measures_quality': 'want does_not_meet, got not_enough_evidence', 'deliberate_design': 'want does_not_meet, got meets'}; reasons: ['Check “Has shipped LLM features to production”: They explicitly state they have not shipped any LLM feature to production.']
