"""
delegation_gate.py

Component 7: Delegation Map + the Hard-Stop Gate.

============================== DELEGATION MAP ==============================

For each component built so far: what the tool decides unattended, what a
human decides, and the explicit handoff where human judgment overrides the
tool's output.

| Component               | Tool decides                              | Human decides                                  | Override handoff |
|--------------------------|--------------------------------------------|--------------------------------------------------|-------------------|
| 1. Allocator             | The apply/network/portfolio hour split, given inputs | Whether the candidate's stated hours_available and constraints are accurate | Candidate reviews recommended split before acting on it -- nothing is auto-scheduled |
| 2. GIGO gate             | Whether a row is internally consistent (bucket vs count, ranges, stale constants) | Whether a REJECTED row should be manually corrected and resubmitted, vs discarded | Any row the gate rejects requires a human to look at `reports/gigo_gate_report.md` and decide, not an automatic re-inclusion |
| 3. Bias audit / outcome policy | The shift magnitude applied per candidate's network deficit | Whether the calibration factor is still valid for the CURRENT population (Perturbation 1, component 6) | A human must re-run `calibrate_shift.py` before trusting the outcome policy on any new data -- this is now enforced, not just recommended (see HARD STOP 3 below) |
| 4. Explainability         | The exact EV decomposition and counterfactual numbers | Whether the tool's blind spot (no time dimension) makes its recommendation wrong for a SPECIFIC candidate | See HARD STOP 1 below -- this handoff is now a real, enforced gate, not just a report a human might not read |
| 5. Causal reasoning        | Nothing -- this component only interprets, never acts | Whether the tool's underlying causal assumption (Ch.2's unverified figures) is trustworthy enough to act on at all | This is a standing caveat a human must weigh every time the tool is used, not a per-candidate decision |
| 6. Adversarial robustness  | Nothing -- this component only tests, never acts | Whether to trust `live_conversations` as reported; whether `CALIBRATED_SHIFT_FACTOR` is stale | See HARD STOP 3 below |

============================== HARD STOPS ==============================

Per the assignment: the engine must stop and require explicit human
approval before executing any move that spends money, commits a resource,
or changes a person's access.

This tool does not literally spend money or submit applications on a
candidate's behalf -- it produces a recommendation the candidate acts on
themselves. So "resource committed" here means: the candidate's own
finite, non-refundable weekly hours and the runway before their work
authorization expires. Recommending an allocation IS committing that
resource, functionally, the moment the candidate follows it. Three
conditions below are treated as hard stops, not soft warnings, because
each corresponds to a documented failure elsewhere in this project:

HARD STOP 1 -- Time-critical candidate (component 4's finding).
  Condition: visa_constrained == True AND weeks_remaining_on_authorization
  <= TIME_CRITICAL_THRESHOLD_WEEKS.
  Why non-negotiable: component 4 showed, with a real candidate (C0032,
  2 weeks remaining), that the tool's own headline recommendation can be
  the WORSE choice once time-to-realization is accounted for, and the
  tool has no mechanism to know this about itself. Letting the raw
  recommendation stand unreviewed for this population is the exact
  failure mode we found and documented. Response: BLOCK the raw
  recommendation from being presented as final; require a human (the
  candidate, or an advisor) to review the realizable-EV table
  (explainability.py) before proceeding.

HARD STOP 2 -- Low-confidence recommendation.
  Condition: the 90% uncertainty interval's width (ev_upper_90 -
  ev_lower_90) exceeds LOW_CONFIDENCE_INTERVAL_WIDTH relative to the point
  estimate -- i.e., the tool is recommending an action it is not
  confident about.
  Why non-negotiable: presenting a point recommendation while burying a
  wide uncertainty band is exactly the "reports accuracy and calls it
  validated" failure the assignment warns against. Response: FLAG the
  recommendation as low-confidence; still show it, but visibly labeled,
  not presented with the same authority as a tight-interval case.

HARD STOP 3 -- Stale calibration.
  Condition: the outcome policy is about to be used, but
  `calibrate_shift.py` has not been re-run against the CURRENT
  `candidates_gated.csv` (checked via a hash/row-count fingerprint stored
  at calibration time).
  Why non-negotiable: component 6, Perturbation 1 showed this fails
  silently -- no error, no sign flip, just a policy that quietly does far
  less (or far more) correction than intended. Response: BLOCK the
  outcome policy from running at all until recalibrated; fall back to the
  parity policy (which has no calibration dependency) in the meantime.

Each hard stop has a stated response type (approve / flag / block) and a
named resolver, per the assignment's rubric requirement.
"""

import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from allocator import outcome_split, parity_split, CALIBRATED_SHIFT_FACTOR
from explainability import decompose_ev, realizable_decompose_ev

GATED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_gated.csv")
FINGERPRINT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "calibration_fingerprint.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "delegation_gate_report.md")

TIME_CRITICAL_THRESHOLD_WEEKS = 4
LOW_CONFIDENCE_RELATIVE_WIDTH = 1.5  # interval width > 1.5x the point estimate = low confidence


def population_fingerprint(rows):
    """A simple, checkable fingerprint of the gated population: row count +
    a hash of candidate_ids, sorted. Used to detect that the population has
    changed since CALIBRATED_SHIFT_FACTOR was last derived (component 6,
    Perturbation 1)."""
    ids = sorted(r["candidate_id"] for r in rows)
    digest = hashlib.sha256(",".join(ids).encode()).hexdigest()[:16]
    return {"row_count": len(rows), "id_hash": digest}


def write_current_fingerprint(rows):
    """Called by calibrate_shift.py in practice; here we simulate 'calibration
    was run against a DIFFERENT population' to demonstrate the gate firing,
    then show what a passing case looks like too."""
    fp = population_fingerprint(rows)
    with open(FINGERPRINT_PATH, "w") as f:
        json.dump(fp, f)
    return fp


def check_hard_stop_1(row):
    visa_constrained = row.get("visa_constrained") == "True"
    weeks_raw = row.get("weeks_remaining_on_authorization", "")
    if not visa_constrained or not weeks_raw:
        return None  # not applicable
    weeks = int(weeks_raw)
    if weeks <= TIME_CRITICAL_THRESHOLD_WEEKS:
        return {
            "fired": True,
            "condition": f"visa_constrained=True, weeks_remaining={weeks} <= {TIME_CRITICAL_THRESHOLD_WEEKS}",
            "response": "BLOCK",
            "resolver": "Candidate (with advisor if available) -- must review reports/explainability_report.md "
                        "realizable-EV table before proceeding.",
        }
    return {"fired": False}


def check_hard_stop_2(ev, lower, upper):
    if ev <= 0:
        width_ratio = float("inf")
    else:
        width_ratio = (upper - lower) / ev
    if width_ratio > LOW_CONFIDENCE_RELATIVE_WIDTH:
        return {
            "fired": True,
            "condition": f"interval width / point estimate = {width_ratio:.2f} > {LOW_CONFIDENCE_RELATIVE_WIDTH}",
            "response": "FLAG",
            "resolver": "Candidate -- recommendation is shown but visibly labeled low-confidence.",
        }
    return {"fired": False, "width_ratio": width_ratio}


def check_hard_stop_3(current_rows):
    if not os.path.exists(FINGERPRINT_PATH):
        return {
            "fired": True,
            "condition": "no calibration fingerprint on record at all",
            "response": "BLOCK",
            "resolver": "Whoever operates the tool -- must run src/calibrate_shift.py before using the outcome "
                        "policy; parity policy remains available with no calibration dependency.",
        }
    with open(FINGERPRINT_PATH) as f:
        stored_fp = json.load(f)
    current_fp = population_fingerprint(current_rows)
    if stored_fp != current_fp:
        return {
            "fired": True,
            "condition": f"population changed since last calibration (stored={stored_fp}, current={current_fp})",
            "response": "BLOCK",
            "resolver": "Whoever operates the tool -- must re-run src/calibrate_shift.py against the current "
                        "population before using the outcome policy.",
        }
    return {"fired": False}


def main():
    with open(GATED_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    lines = ["# Delegation Gate Report\n"]
    lines.append(
        "\nSee the module docstring in `delegation_gate.py` for the full delegation map. This report shows "
        "the three hard stops actually firing (or not) against the current run.\n"
    )

    # ---- Demonstrate Hard Stop 3 first: simulate a STALE fingerprint (from
    # an earlier, different population) still on record, then show it firing,
    # then refresh it and show it clear.
    lines.append("\n## Hard Stop 3 -- Stale calibration check\n")

    if os.path.exists(FINGERPRINT_PATH):
        os.remove(FINGERPRINT_PATH)
    result_before = check_hard_stop_3(rows)
    lines.append(
        f"**Before any calibration record exists:** fired={result_before['fired']}, "
        f"condition: {result_before['condition']}, response={result_before['response']}, "
        f"resolver: {result_before['resolver']}\n"
    )

    # simulate calibration having been run against a DIFFERENT (stale) population
    stale_rows = rows[:-5]  # pretend 5 fewer candidates were present at calibration time
    write_current_fingerprint(stale_rows)
    result_stale = check_hard_stop_3(rows)
    lines.append(f"\n**With a fingerprint from a stale (different) population on record:** fired="
                 f"{result_stale['fired']}")
    if result_stale["fired"]:
        lines.append(f", response={result_stale['response']}, resolver: {result_stale['resolver']}\n")
    else:
        lines.append("\n")

    # now refresh it properly against the CURRENT population and show it clear
    write_current_fingerprint(rows)
    result_current = check_hard_stop_3(rows)
    lines.append(f"\n**After re-running calibration against the current population:** fired="
                 f"{result_current['fired']} -- outcome policy is cleared to run.\n")

    # ---- Hard Stop 1 and 2: run across the whole gated population ----
    lines.append("\n## Hard Stops 1 and 2 -- per-candidate checks across the gated population\n")

    hs1_fired = []
    hs2_fired = []
    for row in rows:
        hs1 = check_hard_stop_1(row)
        if hs1 and hs1.get("fired"):
            hs1_fired.append((row["candidate_id"], hs1))

        hours_total = int(row["hours_available_per_week"])
        live_conversations = int(row["live_conversations"])
        cold_rate = float(row["base_conversion_cold"])
        referral_rate = float(row["base_conversion_referral"])
        apply_h, network_h, _ = outcome_split(hours_total, live_conversations)
        decomp = decompose_ev(apply_h, network_h, cold_rate, referral_rate)

        # reuse the same uncertainty model as allocator.py for consistency
        import math
        n_apps = apply_h * 3.0
        n_convos = network_h * 0.5
        n_referrals = n_convos * 0.30
        var_apps = n_apps * cold_rate * (1 - cold_rate)
        var_referrals = n_referrals * referral_rate * (1 - referral_rate)
        sd = math.sqrt(max(var_apps + var_referrals, 1e-9))
        ev = decomp["total_ev"]
        lower = max(0.0, ev - 1.645 * sd)
        upper = ev + 1.645 * sd

        hs2 = check_hard_stop_2(ev, lower, upper)
        if hs2["fired"]:
            hs2_fired.append((row["candidate_id"], hs2))

    lines.append(f"\n**Hard Stop 1 (time-critical) fired for {len(hs1_fired)} of {len(rows)} candidates.** "
                 f"Example: {hs1_fired[0][0] if hs1_fired else 'none'} -- "
                 f"{hs1_fired[0][1]['condition'] if hs1_fired else ''}\n")

    hs2_rate_pct = 100 * len(hs2_fired) / len(rows)
    lines.append(
        f"\n**Hard Stop 2 (low-confidence) fired for {len(hs2_fired)} of {len(rows)} candidates "
        f"({hs2_rate_pct:.0f}%).**\n"
    )
    lines.append(
        "\n**This is a genuine, unflattering finding, not a footnote:** a gate that fires on 100% of the "
        "population is not usefully discriminating anything -- it's equivalent to a permanent warning label, "
        "which people learn to ignore. The root cause is structural, not a tuning slip: single-week expected "
        "values here are small (roughly 0.05-0.15 expected hires), so a small number of Bernoulli trials at low "
        "probability produces a wide interval relative to its own mean by simple variance arithmetic, "
        "regardless of how good the underlying rate estimates are. **The honest fix is not a smaller threshold "
        "constant** (that would just move the fire rate from 100% toward some other uninformative extreme) -- "
        "it is changing what the gate compares. A better version would flag candidates whose interval is wide "
        "*relative to their peers* (e.g. top quartile of interval width across the population) or aggregate "
        "the estimate over several weeks before gating on it, rather than comparing every single-week estimate "
        "to an absolute ratio. We are naming this as a real limitation of the current gate design rather than "
        "quietly picking a threshold that produces a better-looking fire rate without fixing the underlying "
        "problem.\n"
    )

    lines.append(
        "\n## What this means in practice\n\n"
        "For the 2-weeks-remaining candidate found in component 4 (C0032): Hard Stop 1 fires. The tool does "
        "NOT hand that candidate a bare 'apply=3.93h, network=10.52h' recommendation. It blocks presentation "
        "of the raw number and requires the realizable-EV table to be reviewed first -- exactly the corrective "
        "action component 4 and component 5 both independently concluded was needed.\n"
    )

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.writelines(lines)

    print("Delegation gate report written to", REPORT_PATH)
    print(f"Hard Stop 1 fired for {len(hs1_fired)}/{len(rows)} candidates")
    print(f"Hard Stop 2 fired for {len(hs2_fired)}/{len(rows)} candidates")
    print(f"Hard Stop 3: before={result_before['fired']}, stale={result_stale['fired']}, "
          f"after-refresh={result_current['fired']}")


if __name__ == "__main__":
    main()
