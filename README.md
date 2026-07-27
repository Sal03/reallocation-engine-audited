# Reallocation Engine (Audited) -- Job-Search Time Allocator

INFO 7375 — Computational Skepticism for AI
Domain: People/time reallocation for an international job search, anchored to
Chapter 2 ("The Reallocation Principle") and Chapter 15 ("The Pipeline
Tracker and the Skip Rate") of *The Reallocation Engine*.

## What this is

A tool that reallocates a candidate's weekly job-search hours across
Apply / Network / Portfolio to maximize expected weekly hire-contribution,
given their current network size -- built with the skeptical machinery
required by the assignment: a data quality gate, a bias audit with a
measured fairness tradeoff, an explainability critique, Pearl's three-rung
causal analysis, two adversarial/fragility findings, and a working
delegation map with three enforced hard stops. All seven rubric components
are implemented and runnable.

## Requirements

- Python 3.8+ (no external packages required -- standard library only)

## How to run, in order

Run these from the project root (`reallocation-engine/`). Each step reads
files written by the previous one, so run them in this order the first
time:

```bash
# 1. Generate the synthetic candidate population (with intentionally
#    injected data-quality problems for the gate to catch)
python3 src/generate_candidates.py

# 2. Run the GIGO gate -- rejects bad rows, writes a report explaining why
python3 src/gigo_gate.py

# 3. Run the core allocator tool (three policies: parity, outcome/calibrated,
#    outcome_naive/uncalibrated -- kept for the documented overshoot finding)
python3 src/allocator.py

# 4. Run the bias audit (demographic parity vs equalized-outcome tradeoff)
python3 src/bias_audit.py

# 5. Run the explainability module (decomposition + counterfactual + critique)
python3 src/explainability.py

# 6. Run the causal reasoning module (Pearl's three rungs)
python3 src/causal_reasoning.py

# 7. Run the adversarial robustness & fragility module (stale calibration +
#    gameable self-reported input)
python3 src/adversarial_robustness.py

# 8. Run the delegation map + hard-stop gate (the final component -- this
#    is what actually stops the tool from handing out an unreviewed
#    recommendation to a time-critical candidate)
python3 src/delegation_gate.py

# 9. Generate the uncertainty communication chart + writeup (a real chart
#    plus the two required plain-language elements)
python3 src/uncertainty_communication.py

# 10. Run the Frictional Journal probe -- a second, independent population
#     draw (different seed) that reproduces the finding logged in
#     reports/frictional_journal.md as a genuine before/after cycle
python3 src/frictional_probe.py
```

Or run everything at once:

```bash
bash run_all.sh
```

## What to look at afterward

**Primary submission document:** `Angre_Saloni_ReallocationEngine.md` (at
the project root) — the validation report that assembles all seven rubric
components, the required gates, and the uncertainty-communication
requirement into one coherent document. Everything below is the detailed,
re-runnable backing evidence for the claims made there.

- `reports/gigo_gate_report.md` -- what failed the quality gate and why
- `reports/bias_audit_report.md` -- the fairness tradeoff, plus the
  population-dependent calibration finding
- `reports/explainability_report.md` -- the decomposition, counterfactual,
  and the timing-blind-spot critique (candidate C0032)
- `reports/causal_reasoning_report.md` -- Pearl's three rungs, computed
  against the actual run data
- `reports/adversarial_report.md` -- two perturbations: stale calibration
  under resampling (both under- and over-correction), and a gameable
  self-reported input
- `reports/delegation_gate_report.md` -- the delegation map and three
  working hard stops (time-critical, low-confidence, stale calibration),
  with an honest critique of Hard Stop 2's current threshold
- `reports/worked_run.md` -- inputs, verbatim commands and output,
  verified-vs-inferred split, attestation (including a real deliberate
  break attempt), and reflection
- `reports/frictional_journal.md` -- before/after prediction and
  reflection, with an honest disclosure that the "before" entry is a
  reconstruction, not a contemporaneous log
- `reports/ai_use_disclosure.md` -- required disclosure block, with a
  specific, verifiable "what the AI could not do" instance
- `reports/uncertainty_communication.md` + `uncertainty_chart.png` -- a
  real chart of point estimate + 90% interval, a plain-language sentence,
  and an explicit "where I would not trust this tool" grounded in the
  actual Hard Stop 2 finding

All intermediate data lands in `data/`:

- `data/candidates_raw.csv` -- the raw synthetic population (240 rows,
  with injected problems)
- `data/candidates_gated.csv` -- what passed the GIGO gate (213 rows)
- `data/allocations_parity.csv`, `allocations_outcome.csv`,
  `allocations_outcome_naive.csv` -- the three policies' outputs

## Reproducibility note

The generator uses a fixed random seed (7375), so re-running
`generate_candidates.py` produces the exact same population every time --
this is important for the video: you can regenerate everything from
scratch on camera and it will match what's in this report.

## Recording the required video segment

The assignment (per the rubric) wants a genuine, unscripted terminal run,
not a narrated screenshot. Recommended flow for the live segment:

1. **Use this exact clean command, not `rm reports/*.md`:**
   ```bash
   rm -f data/*.csv data/*.json reports/gigo_gate_report.md \
     reports/bias_audit_report.md reports/explainability_report.md \
     reports/causal_reasoning_report.md reports/adversarial_report.md \
     reports/delegation_gate_report.md reports/uncertainty_communication.md \
     reports/uncertainty_chart.png
   ```
   This clears only the files the scripts regenerate. `worked_run.md`,
   `frictional_journal.md`, and `ai_use_disclosure.md` are written by hand
   and are NOT regenerated by any script -- a blanket `rm reports/*.md`
   will delete them permanently with no way to get them back except
   rewriting them from scratch.
2. Run the nine commands above (or `bash run_all.sh`), one at a time,
   letting the real output print
3. Open one report (e.g. `reports/bias_audit_report.md`) and show the
   numbers match what just printed to the terminal
4. Optionally, try to break it: edit a value in `data/candidates_gated.csv`
   by hand (e.g. set an EV field to something absurd) and show the report
   downstream doesn't silently "fix" it -- this exact test is already
   documented, with real results, in `reports/worked_run.md`'s Attestation
   section

## Project structure

```
reallocation-engine/
├── README.md              <- this file
├── run_all.sh              <- convenience script, runs all 6 steps
├── data/                   <- generated at runtime, not committed clean
├── reports/                <- generated at runtime, not committed clean
└── src/
    ├── generate_candidates.py
    ├── gigo_gate.py
    ├── allocator.py
    ├── calibrate_shift.py   <- used to derive CALIBRATED_SHIFT_FACTOR
    ├── bias_audit.py
    ├── explainability.py
    ├── causal_reasoning.py
    ├── adversarial_robustness.py
    └── delegation_gate.py
```
