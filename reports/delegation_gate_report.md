# Delegation Gate Report

See the module docstring in `delegation_gate.py` for the full delegation map. This report shows the three hard stops actually firing (or not) against the current run.

## Hard Stop 3 -- Stale calibration check
**Before any calibration record exists:** fired=True, condition: no calibration fingerprint on record at all, response=BLOCK, resolver: Whoever operates the tool -- must run src/calibrate_shift.py before using the outcome policy; parity policy remains available with no calibration dependency.

**With a fingerprint from a stale (different) population on record:** fired=True, response=BLOCK, resolver: Whoever operates the tool -- must re-run src/calibrate_shift.py against the current population before using the outcome policy.

**After re-running calibration against the current population:** fired=False -- outcome policy is cleared to run.

## Hard Stops 1 and 2 -- per-candidate checks across the gated population

**Hard Stop 1 (time-critical) fired for 17 of 213 candidates.** Example: C0032 -- visa_constrained=True, weeks_remaining=2 <= 4

**Hard Stop 2 (low-confidence) fired for 213 of 213 candidates (100%).**

**This is a genuine, unflattering finding, not a footnote:** a gate that fires on 100% of the population is not usefully discriminating anything -- it's equivalent to a permanent warning label, which people learn to ignore. The root cause is structural, not a tuning slip: single-week expected values here are small (roughly 0.05-0.15 expected hires), so a small number of Bernoulli trials at low probability produces a wide interval relative to its own mean by simple variance arithmetic, regardless of how good the underlying rate estimates are. **The honest fix is not a smaller threshold constant** (that would just move the fire rate from 100% toward some other uninformative extreme) -- it is changing what the gate compares. A better version would flag candidates whose interval is wide *relative to their peers* (e.g. top quartile of interval width across the population) or aggregate the estimate over several weeks before gating on it, rather than comparing every single-week estimate to an absolute ratio. We are naming this as a real limitation of the current gate design rather than quietly picking a threshold that produces a better-looking fire rate without fixing the underlying problem.

## What this means in practice

For the 2-weeks-remaining candidate found in component 4 (C0032): Hard Stop 1 fires. The tool does NOT hand that candidate a bare 'apply=3.93h, network=10.52h' recommendation. It blocks presentation of the raw number and requires the realizable-EV table to be reviewed first -- exactly the corrective action component 4 and component 5 both independently concluded was needed.
