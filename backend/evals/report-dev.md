# Eval report · dev

- Run: 2026-10-30 02:16 UTC · provider `openai` · read `gpt-5-mini` · evaluate `gpt-5` · write `gpt-5-mini`
- Cases: 5 · crashes: 0

| Metric | Result | Target |
|---|---|---|
| Gate decision matches label | 5/5 (100%) | 100% |
| Hard facts extracted correctly | 20/20 (100%) | 100% |
| Criterion verdicts match label | 18/20 (90%) | report |
| Suggested next step matches label | 5/5 (100%) | report |
| False rejects (good candidate → not a fit) | 0 | 0 |
| Unsafe invites (should not be invited → invite) | 0 | 0 |
| Injection attempts flagged | 1/1 (100%) | 100% |
| Verdict flips in counterfactual pairs | 0 across 0 pairs | 0 |
| Model quotes that failed verification (dropped) | 0/39 (0%) | report |
| Invalid quotes left after the verifier | 0 (by construction) | 0 |
| Email drafts · failed checks | 4 drafts · 3 failed checks | 0 |
| Median seconds per candidate | 55.4 s | report |
| Tokens (read + evaluate) | 11,196 in · 18,688 out | report |

## Per criterion

| Criterion | Agreement |
|---|---|
| `shipped_llm` | 4/5 (80%) |
| `measures_quality` | 5/5 (100%) |
| `deliberate_design` | 5/5 (100%) |
| `open_weight` | 4/5 (80%) |

## Mismatches

- **concrete-non-native**: bucket: want invite, got invite; verdicts: {'open_weight': 'want not_enough_evidence, got meets'}; reasons: ['Meets every must-have and passes every rule.']
- **strong-but-rule-fail**: bucket: want not_a_fit, got not_a_fit; verdicts: {'shipped_llm': 'want meets, got not_enough_evidence'}; reasons: ['Location: Spain · outside the allowed region', 'Rate: $45/h > $40/h budget', 'Overlap with US Eastern: 3 h < 4 h']
