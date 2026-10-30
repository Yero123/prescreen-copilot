# Baseline (single prompt) · test

- Model: `gpt-5` (openai) · one call per case · no harness
- Cases: 15 · failed calls: 0

| Metric | Result |
|---|---|
| Application detected correctly | 15/15 (100%) |
| Hard facts extracted correctly | 55/56 (98%) |
| Criterion verdicts match label | 56/56 (100%) |
| Suggested next step matches label | 12/15 (80%) |
| False rejects | 0 |
| Unsafe invites | 3 |
| Injection cases sent to a person | 0/2 (0%) |
| Verdict flips in counterfactual pairs | 0 across 2 pairs |
| Quotes not found in the email or CV | 14/62 (23%) |
| Median seconds per candidate | 4.9 s |
| Tokens | 14,975 in · 11,037 out |
