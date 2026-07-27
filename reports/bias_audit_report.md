# Bias Audit Report

## Group means: recommended_network_hours (by network_group)

| Policy | low | mid | high | DP_gap (low vs high) |
|---|---|---|---|---|
| parity | 10.89 | 11.03 | 11.73 | 0.84 |
| outcome | 15.33 | 13.02 | 11.73 | 3.61 |

## Group means: expected_weekly_hires_contribution (by network_group)

| Policy | low | mid | high | EO_gap (low vs high) |
|---|---|---|---|---|
| parity | 0.09257 | 0.09375 | 0.09970 | 0.00713 |
| outcome | 0.09923 | 0.09674 | 0.09970 | 0.00046 |

## The tradeoff, measured

- Switching from **parity** to **outcome** policy reduces the EO_gap by **93.5%** (0.00713 -> 0.00046).
- The cost: DP_gap increases from 0.84 to 3.61 hours (+2.77 hours/week of allocation difference between low- and high-network candidates).

**Neither policy minimizes both gaps at once.** The parity policy is fair by treatment but unfair by outcome; the outcome policy is fair by outcome but unfair by treatment. This is not a bug to fix -- it is the actual, unavoidable tradeoff named in the assignment rubric. We chose to report both rather than pick one silently.

## The naive (15%-shift) policy, and what we learned running it twice

Our first attempt at the outcome policy (`outcome_split_naive` in `allocator.py`) used a round, arbitrary 15%-of-hours shift magnitude, chosen before any calibration.

| Policy | EV mean, low | EV mean, high | Signed gap (low - high) |
|---|---|---|---|
| parity | 0.09257 | 0.09970 | -0.00713 |
| outcome_naive (15% shift) | 0.09812 | 0.09970 | -0.00157 (low still behind -- did not overshoot this run) |
| outcome (calibrated) | 0.09923 | 0.09970 | -0.00046 |

**The actual finding is bigger than a single overshoot.** When we first ran this audit, the 15% naive shift reliably overshot the gap (low-network candidates ended up ahead of high-network candidates), and the calibration boundary -- the largest safe shift factor -- sat at ~0.032. After adding one new field to the candidate generator (`weeks_remaining_on_authorization`), which changed nothing about the fairness mechanism but *did* change the sequence of random draws consumed during generation, we regenerated the same synthetic population from the same generation process and reran the exact same calibration search. The boundary moved to ~0.1925 -- roughly a 6x shift -- and the 15% naive policy that had reliably overshot before no longer overshoots in this run (see table above).

**Why this matters more than either single result:** a calibrated constant tuned against one draw of a synthetic population is not automatically safe against another draw from the *same* generation process, let alone against real data. `CALIBRATED_SHIFT_FACTOR` in `allocator.py` is refreshed by re-running `src/calibrate_shift.py` against whatever population is currently loaded -- it is not safe to hardcode once and reuse indefinitely. This is documented further as a fragility finding in `reports/adversarial_report.md` (component 6), because it is really a robustness problem wearing a bias-audit costume: the mechanism that closes a fairness gap is itself sensitive to a perturbation (here, incidental resampling) that a human reviewer would have no reason to expect to matter.

**Why the underlying overshoot risk is still real, even when this run didn't trigger it:** referral-hour expected value is far more efficient than apply-hour expected value in this model (referral conversion ~3% vs cold-application conversion ~0.2%, per Ch. 2's own figures). Any fixed shift large enough to close the low-vs-high gap for one population risks not stopping at parity for another -- the correction is a continuous, compounding lever, not a step function, and how far is 'enough' depends on the specific population it's run against.

**How we calibrate:** binary search (`src/calibrate_shift.py`) over the shift factor, solving for the largest factor that leaves low-network candidates' expected value at or below high-network candidates' (the boundary before sign-flip), re-run fresh against the current `candidates_gated.csv`. The naive version (fixed 15%) is kept in the code, unedited, specifically so both this run's result and the original overshoot are reproducible depending on which population is loaded -- not just asserted in prose.

## Leverage point

The initial allocation rule (parity_split vs outcome_split in `allocator.py`) is the single highest-leverage intervention point in this pipeline. It is the only component whose change measurably moves both gaps; downstream scoring/tiering logic (not built in this version) would operate on top of whatever allocation already occurred and cannot undo this effect.

## Caveat

This audit runs on a synthetic population with network_group assigned by construction, not a real dataset with measured hire outcomes by demographic group. The gap sizes here demonstrate the mechanism's direction and rough shape under stated assumptions (Ch. 2/15 conversion-rate constants), not a calibrated real-world estimate. See `reports/data_provenance.md`.
