"""
calibrate_shift.py

Finds the shift-magnitude factor that closes the low-vs-high
expected-outcome gap (EO_gap) as close to zero as possible, WITHOUT
overshooting past zero (i.e. without flipping which group is ahead).

This exists because the first attempt (outcome_split_naive, factor=0.15)
overshot: it closed the gap and kept going, so low-network candidates ended
up ahead of high-network candidates instead of merely even with them. That
finding is kept and documented (see allocator.py's outcome_split_naive and
reports/bias_audit_report.md). This script is how we found a better number,
not just asserted one.

Method: binary search over the shift factor. At each candidate factor, run
the same expected-value model used in allocator.py across the gated
population, compute EO_gap SIGNED (mean_EV[low] - mean_EV[high]) under
parity vs a test outcome policy, and search for the factor where the
signed gap crosses zero -- i.e. the largest factor that still leaves
low-network candidates at or below high-network candidates in expected
value. That is the calibration boundary: any factor beyond it starts the
overshoot.
"""

import csv
import math
import os

GATED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_gated.csv")

APPLICATIONS_PER_HOUR = 3.0
CONVERSATIONS_PER_HOUR = 0.5
CONVO_TO_REFERRAL_RATE = 0.30


def parity_split(hours_total):
    total_ratio = 8
    return (hours_total * 2 / total_ratio,
            hours_total * 3 / total_ratio,
            hours_total * 3 / total_ratio)


def test_split(hours_total, live_conversations, factor, healthy_threshold=10):
    deficit = max(0, healthy_threshold - live_conversations) / healthy_threshold
    max_shift_hours = factor * hours_total
    shift = deficit * max_shift_hours
    apply_h, network_h, portfolio_h = parity_split(hours_total)
    apply_h -= shift / 2
    portfolio_h -= shift / 2
    network_h += shift
    return apply_h, network_h, portfolio_h


def ev(apply_h, network_h, cold_rate, referral_rate):
    n_apps = apply_h * APPLICATIONS_PER_HOUR
    n_convos = network_h * CONVERSATIONS_PER_HOUR
    n_referrals = n_convos * CONVO_TO_REFERRAL_RATE
    return n_apps * cold_rate + n_referrals * referral_rate


def signed_eo_gap(rows, factor):
    """mean_EV[low] - mean_EV[high] under a given shift factor. Negative = low still behind (good, not overshot).
    Positive = low ahead of high (overshot)."""
    sums = {"low": 0.0, "high": 0.0}
    counts = {"low": 0, "high": 0}
    for row in rows:
        g = row["network_group"]
        if g not in ("low", "high"):
            continue
        hours_total = int(row["hours_available_per_week"])
        live_conversations = int(row["live_conversations"])
        cold_rate = float(row["base_conversion_cold"])
        referral_rate = float(row["base_conversion_referral"])
        apply_h, network_h, _ = test_split(hours_total, live_conversations, factor)
        e = ev(apply_h, network_h, cold_rate, referral_rate)
        sums[g] += e
        counts[g] += 1
    mean_low = sums["low"] / counts["low"]
    mean_high = sums["high"] / counts["high"]
    return mean_low - mean_high


def main():
    with open(GATED_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    print("factor -> signed_eo_gap (mean_EV[low] - mean_EV[high])")
    print("negative = low still behind high (not yet overshot); positive = overshot\n")

    lo_factor, hi_factor = 0.0, 0.60
    for _ in range(30):
        mid = (lo_factor + hi_factor) / 2
        gap = signed_eo_gap(rows, mid)
        if gap < 0:
            lo_factor = mid  # not yet overshot, can push higher
        else:
            hi_factor = mid  # overshot, pull back

    # report a small table around the boundary for transparency
    for f in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, lo_factor, hi_factor, 0.45, 0.60]:
        gap = signed_eo_gap(rows, f)
        print(f"  factor={f:.4f}  signed_eo_gap={gap:+.5f}")

    chosen = round(lo_factor, 3)
    print(f"\nBoundary found by binary search: ~{lo_factor:.4f}")
    print(f"Chosen CALIBRATED_SHIFT_FACTOR (slightly conservative, rounded down): {chosen}")


if __name__ == "__main__":
    main()
