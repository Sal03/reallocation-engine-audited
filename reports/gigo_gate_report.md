# GIGO Gate Report

Input: `data/candidates_raw.csv` (240 rows)

Passed gate: **213** rows -> `data/candidates_gated.csv`

Rejected: **27** rows

## Rejection reasons (tallied)

- live_conversations: 9
- hours_available_per_week: 7
- missing or non-numeric hours_available_p: 7
- stale/second-source conversion constants: 4
- duplicate candidate_id: 1

## Full rejection log

| candidate_id | reasons |
|---|---|
| C0009 | hours_available_per_week=2 out of plausible range [10,60] |
| C0022 | live_conversations=3 does not match network_group='high' (expected 10-20) -- bucket/value mismatch |
| C0026 | stale/second-source conversion constants (cold=0.005, referral=0.06); expected cold=0.002, referral=0.03 |
| C0043 | live_conversations=3 does not match network_group='mid' (expected 4-9) -- bucket/value mismatch |
| C0057 | missing or non-numeric hours_available_per_week |
| C0073 | missing or non-numeric hours_available_per_week |
| C0078 | live_conversations=1 does not match network_group='mid' (expected 4-9) -- bucket/value mismatch |
| C0081 | missing or non-numeric hours_available_per_week |
| C0098 | live_conversations=7 does not match network_group='low' (expected 0-3) -- bucket/value mismatch |
| C0100 | live_conversations=9 does not match network_group='high' (expected 10-20) -- bucket/value mismatch |
| C0113 | hours_available_per_week=5 out of plausible range [10,60] |
| C0117 | live_conversations=4 does not match network_group='high' (expected 10-20) -- bucket/value mismatch |
| C0130 | live_conversations=4 does not match network_group='high' (expected 10-20) -- bucket/value mismatch |
| C0131 | hours_available_per_week=5 out of plausible range [10,60] |
| C0134 | stale/second-source conversion constants (cold=0.005, referral=0.06); expected cold=0.002, referral=0.03 |
| C0140 | live_conversations=7 does not match network_group='high' (expected 10-20) -- bucket/value mismatch |
| C0148 | hours_available_per_week=2 out of plausible range [10,60] |
| C0151 | hours_available_per_week=5 out of plausible range [10,60] |
| C0158 | hours_available_per_week=5 out of plausible range [10,60] |
| C0172 | missing or non-numeric hours_available_per_week |
| C0182 | stale/second-source conversion constants (cold=0.005, referral=0.06); expected cold=0.002, referral=0.03 |
| C0205 | missing or non-numeric hours_available_per_week |
| C0212 | live_conversations=14 does not match network_group='low' (expected 0-3) -- bucket/value mismatch |
| C0222 | missing or non-numeric hours_available_per_week |
| C0225 | hours_available_per_week=95 out of plausible range [10,60] |
| C0228 | duplicate candidate_id (C0228); stale/second-source conversion constants (cold=0.005, referral=0.06); expected cold=0.002, referral=0.03 |
| C0238 | missing or non-numeric hours_available_per_week |

## What we did about it

Rejected rows are excluded from `candidates_gated.csv` entirely -- none are imputed, guessed, or silently corrected. This means the allocator and bias audit downstream run on a strictly smaller, verified population. We accept the reduced sample size as the cost of not laundering bad data into a confident-looking result.

The stale-conversion-constant rows are the most consequential rejection category: had they been silently kept, they would have quietly inflated expected-return estimates for whichever rows carried them, without any visible signal in downstream output.
