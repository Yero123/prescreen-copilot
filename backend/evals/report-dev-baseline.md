# Baseline (single prompt) · dev

- Model: `gpt-5` (openai) · one call per case · no harness
- Cases: 15 · failed calls: 0

| Metric | Result |
|---|---|
| Application detected correctly | 15/15 (100%) |
| Hard facts extracted correctly | 55/56 (98%) |
| Criterion verdicts match label | 54/56 (96%) |
| Suggested next step matches label | 12/15 (80%) |
| False rejects | 1 |
| Unsafe invites | 1 |
| Injection cases sent to a person | 1/1 (100%) |
| Verdict flips in counterfactual pairs | 0 across 1 pairs |
| Quotes not found in the email or CV | 0/69 (0%) |
| Median seconds per candidate | 13.3 s |
| Tokens | 15,384 in · 26,544 out |
