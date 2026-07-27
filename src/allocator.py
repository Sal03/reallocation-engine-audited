"""
allocator.py

Component 1: The Working Reallocation Tool.

OBJECTIVE (stated plainly, per the assignment's requirement):
  "Reallocate a candidate's weekly search hours across Apply / Network /
  Portfolio to maximize expected weekly referral-and-application-driven
  hire probability, given their current network size."

WHAT THIS OBJECTIVE LEAVES OUT (also required to state):
  It does not account for role fit, company sponsorship history, posting
  liveness, geographic constraints, mental health / burnout cost of a given
  schedule, or the fact that expected-value math says nothing about
  variance -- a candidate near a visa deadline may rationally prefer a
  lower-expected-value plan with less variance (a guaranteed interview
  pipeline) over a higher-expected-value, higher-variance one. This tool
  optimizes ONE variable named in Chapter 2; it is not a complete
  job-search strategy.

MECHANISM: takes Q hours of a candidate's weekly search-hour budget and
moves them from a default Apply-heavy split toward whatever split the
allocator computes maximizes expected outcome, given the candidate's
current network size (Ch. 2's reallocation principle, Ch. 15's tracker
variables).

Three policies are implemented so the bias audit (src/bias_audit.py) can
compare them:
  - POLICY "parity"        : same 3-3-2-style split for every candidate,
                              regardless of network_group. (Chapter 2's
                              stated default.)
  - POLICY "outcome"       : CALIBRATED version. Split shifts extra hours
                              toward networking for candidates with fewer
                              live conversations, in proportion to their
                              network deficit, at a magnitude tuned (via
                              src/calibrate_shift.py) to close the
                              low-vs-high expected-outcome gap WITHOUT
                              overshooting past it. This is the policy the
                              tool actually ships with.
  - POLICY "outcome_naive" : our FIRST attempt at the above, kept
                              deliberately rather than deleted. It
                              overshoots -- see outcome_split_naive()'s
                              docstring and reports/bias_audit_report.md.
                              Retained so the failure is reproducible, not
                              just described after the fact.

UNCERTAINTY: expected_weekly_hires_contribution is reported with a simple
Beta-distribution-style credible interval (component 1 requires an
explicit uncertainty estimate, not just a point value). We treat each
candidate's applications and networking conversations as independent
Bernoulli trials at the (possibly stale, possibly wrong) book-sourced
conversion rates, and report a 90% interval via a lightweight normal
approximation to the Poisson-binomial sum. This is a real uncertainty
estimate, but it only captures SAMPLING variance around the assumed
conversion rates -- not model uncertainty about whether those rates are
correct for THIS candidate. That gap is named explicitly in the report,
not hidden.
"""

import csv
import math
import os

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_gated.csv")
OUT_PATH_PARITY = os.path.join(os.path.dirname(__file__), "..", "data", "allocations_parity.csv")
OUT_PATH_OUTCOME = os.path.join(os.path.dirname(__file__), "..", "data", "allocations_outcome.csv")
OUT_PATH_OUTCOME_NAIVE = os.path.join(os.path.dirname(__file__), "..", "data", "allocations_outcome_naive.csv")

# Fixed conversation/application throughput assumptions (stated, not hidden)
APPLICATIONS_PER_HOUR = 3.0
CONVERSATIONS_PER_HOUR = 0.5
CONVO_TO_REFERRAL_RATE = 0.30   # fraction of live conversations that become a real referral this week

Z_90 = 1.645  # z-score for a 90% two-sided interval


def parity_split(hours_total):
    """Fixed 3-3-2-style split, scaled to the candidate's actual available hours."""
    # base ratio 2:3:3 (apply:network:portfolio) from Chapter 2
    total_ratio = 2 + 3 + 3
    apply_h = hours_total * (2 / total_ratio)
    network_h = hours_total * (3 / total_ratio)
    portfolio_h = hours_total * (3 / total_ratio)
    return apply_h, network_h, portfolio_h


def outcome_split_naive(hours_total, live_conversations, healthy_threshold=10):
    """
    FIRST ATTEMPT -- kept intentionally, not deleted.

    Shifts hours toward networking in proportion to network deficit, using
    a 15%-of-hours maximum shift. This was our initial, arbitrary-ish
    calibration (a round "15%" guess).

    DOCUMENTED FINDING: whether this shift magnitude overshoots the
    low-vs-high expected-outcome gap turns out to be POPULATION-DEPENDENT.
    Against one random draw of the synthetic population, 15% reliably
    overshot (flipped which group came out ahead). Against a second draw
    from the exact same generation process, 15% does NOT overshoot -- the
    boundary moved from ~0.032 to ~0.1925. See
    reports/adversarial_report.md (component 6) for the full writeup: this
    is a fragility finding about calibrated constants, not just a modeling
    quirk. This function is kept in the codebase, unedited, so both
    behaviors are reproducible depending on which population is loaded.
    """
    deficit = max(0, healthy_threshold - live_conversations) / healthy_threshold  # 0..1
    max_shift_hours = 0.15 * hours_total  # the uncalibrated magnitude that overshoots

    shift = deficit * max_shift_hours

    apply_h, network_h, portfolio_h = parity_split(hours_total)
    apply_h -= shift / 2
    portfolio_h -= shift / 2
    network_h += shift

    return apply_h, network_h, portfolio_h


# Calibrated shift factor: chosen so the "outcome" policy closes the EO_gap
# toward zero WITHOUT flipping its sign. Derived empirically in
# src/calibrate_shift.py from the CURRENT candidates_gated.csv population.
#
# IMPORTANT FRAGILITY NOTE (see reports/adversarial_report.md, component 6):
# this boundary is population-dependent. An earlier run of the same
# generation process (before the weeks_remaining_on_authorization field was
# added, which shifted the random draw sequence) put the boundary at ~0.032;
# this run puts it at ~0.1925. A ~6x swing from ordinary sampling variation
# in the SAME generator. Do not treat this constant as safe to hardcode
# permanently -- re-run calibrate_shift.py against whatever population is
# actually in use before trusting this number.
CALIBRATED_SHIFT_FACTOR = 0.180


def outcome_split(hours_total, live_conversations, healthy_threshold=10):
    """
    Calibrated version: shifts hours toward networking in proportion to
    network deficit, capped at CALIBRATED_SHIFT_FACTOR (not 0.15) of total
    hours. This magnitude was chosen empirically to close the
    low-vs-high expected-outcome gap without overshooting past it -- see
    src/calibrate_shift.py.
    """
    deficit = max(0, healthy_threshold - live_conversations) / healthy_threshold  # 0..1
    max_shift_hours = CALIBRATED_SHIFT_FACTOR * hours_total

    shift = deficit * max_shift_hours

    apply_h, network_h, portfolio_h = parity_split(hours_total)
    apply_h -= shift / 2
    portfolio_h -= shift / 2
    network_h += shift

    return apply_h, network_h, portfolio_h


def expected_value_and_uncertainty(apply_h, network_h, cold_rate, referral_rate):
    """
    Returns (expected_hires_contribution, lower_90, upper_90).

    Models applications and referral-producing conversations as independent
    Bernoulli trials. Uses a normal approximation to the sum of Bernoullis
    (reasonable once n * p * (1-p) isn't tiny; flagged as an approximation).
    """
    n_apps = apply_h * APPLICATIONS_PER_HOUR
    n_convos = network_h * CONVERSATIONS_PER_HOUR
    n_referrals = n_convos * CONVO_TO_REFERRAL_RATE

    # Expected value: sum of two Bernoulli-sum means
    ev_apps = n_apps * cold_rate
    ev_referrals = n_referrals * referral_rate
    ev = ev_apps + ev_referrals

    # Variance of sum of independent Bernoullis: n*p*(1-p) for each stream
    var_apps = n_apps * cold_rate * (1 - cold_rate)
    var_referrals = n_referrals * referral_rate * (1 - referral_rate)
    sd = math.sqrt(max(var_apps + var_referrals, 1e-9))

    lower = max(0.0, ev - Z_90 * sd)
    upper = ev + Z_90 * sd
    return ev, lower, upper


def run_policy(rows, policy_name, split_fn):
    out_rows = []
    for row in rows:
        hours_total = int(row["hours_available_per_week"])
        live_conversations = int(row["live_conversations"])
        cold_rate = float(row["base_conversion_cold"])
        referral_rate = float(row["base_conversion_referral"])

        if policy_name == "parity":
            apply_h, network_h, portfolio_h = split_fn(hours_total)
        else:
            apply_h, network_h, portfolio_h = split_fn(hours_total, live_conversations)

        ev, lower, upper = expected_value_and_uncertainty(apply_h, network_h, cold_rate, referral_rate)

        out_rows.append({
            "candidate_id": row["candidate_id"],
            "network_group": row["network_group"],
            "live_conversations": live_conversations,
            "policy": policy_name,
            "recommended_apply_hours": round(apply_h, 2),
            "recommended_network_hours": round(network_h, 2),
            "recommended_portfolio_hours": round(portfolio_h, 2),
            "expected_weekly_hires_contribution": round(ev, 5),
            "ev_lower_90": round(lower, 5),
            "ev_upper_90": round(upper, 5),
        })
    return out_rows


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    with open(IN_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    parity_rows = run_policy(rows, "parity", parity_split)
    outcome_rows = run_policy(rows, "outcome", outcome_split)
    outcome_naive_rows = run_policy(rows, "outcome_naive", outcome_split_naive)

    write_csv(OUT_PATH_PARITY, parity_rows)
    write_csv(OUT_PATH_OUTCOME, outcome_rows)
    write_csv(OUT_PATH_OUTCOME_NAIVE, outcome_naive_rows)

    print(f"Ran {len(rows)} gated candidates through three policies.")
    print(f"Parity policy        -> {OUT_PATH_PARITY}")
    print(f"Outcome (calibrated) -> {OUT_PATH_OUTCOME}")
    print(f"Outcome (naive/overshoot, kept for documentation) -> {OUT_PATH_OUTCOME_NAIVE}")

    # Quick sanity print: one example candidate under both policies
    example = rows[0]
    print("\nExample candidate:", example["candidate_id"], "| network_group:", example["network_group"],
          "| live_conversations:", example["live_conversations"])
    p = [r for r in parity_rows if r["candidate_id"] == example["candidate_id"]][0]
    o = [r for r in outcome_rows if r["candidate_id"] == example["candidate_id"]][0]
    print("  parity :", p["recommended_apply_hours"], p["recommended_network_hours"], p["recommended_portfolio_hours"],
          "| EV:", p["expected_weekly_hires_contribution"], f"[{p['ev_lower_90']}, {p['ev_upper_90']}]")
    print("  outcome:", o["recommended_apply_hours"], o["recommended_network_hours"], o["recommended_portfolio_hours"],
          "| EV:", o["expected_weekly_hires_contribution"], f"[{o['ev_lower_90']}, {o['ev_upper_90']}]")


if __name__ == "__main__":
    main()
