# Eval report · dev

- Run: 2026-10-30 02:23 UTC · provider `openai` · read `gpt-5-mini` · evaluate `gpt-5` · write `gpt-5-mini`
- Cases: 15 · crashes: 0

| Metric | Result | Target |
|---|---|---|
| Gate decision matches label | 15/15 (100%) | 100% |
| Hard facts extracted correctly | 70/70 (100%) | 100% |
| Criterion verdicts match label | 53/56 (95%) | report |
| Suggested next step matches label | 15/15 (100%) | report |
| False rejects (good candidate → not a fit) | 0 | 0 |
| Unsafe invites (should not be invited → invite) | 0 | 0 |
| Injection attempts flagged | 1/1 (100%) | 100% |
| Verdict flips in counterfactual pairs | 0 across 1 pairs | 0 |
| Model quotes that failed verification (dropped) | 0/86 (0%) | report |
| Invalid quotes left after the verifier | 0 (by construction) | 0 |
| Email drafts · failed checks | 11 drafts · 1 failed checks | 0 |
| Median seconds per candidate | 47.8 s | report |
| Tokens (read + evaluate) | 31,192 in · 48,037 out | report |

## Per criterion

| Criterion | Agreement |
|---|---|
| `shipped_llm` | 14/14 (100%) |
| `measures_quality` | 13/14 (93%) |
| `deliberate_design` | 12/14 (86%) |
| `open_weight` | 14/14 (100%) |

## Mismatches

- **cv-contradiction**: bucket: want needs_review, got needs_review; verdicts: {'deliberate_design': 'want meets, got not_enough_evidence'}; reasons: ['The reply claims 9 years of experience; the CV covers fewer.']
- **honest-not-shipped**: bucket: want needs_review, got needs_review; verdicts: {'measures_quality': 'want not_enough_evidence, got does_not_meet', 'deliberate_design': 'want not_enough_evidence, got does_not_meet'}; reasons: ['Check “Has shipped LLM features to production”: They explicitly state they have not shipped to production and only built prototypes.', 'Check “Measures output quality (evals, test sets, agreement with humans)”: They report only informal spot checks with no test set, metrics, or human-agreement process.']
