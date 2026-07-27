"""
frictional_probe.py

A reproducible version of the probe logged in reports/frictional_journal.md
(added after TA feedback on a prior assignment, which offered the chance to
run a genuine timestamped before/after cycle rather than rely solely on a
reconstruction).

Regenerates the candidate population with a DIFFERENT seed than the shipped
pipeline (7375), in a scratch location, and checks:
  1. Where the calibration boundary lands on this new draw.
  2. Whether the "low" network group already has a natural EV advantage
     under PLAIN PARITY (factor=0), before any correction is applied at all
     -- which is the finding this probe actually turned up.
  3. Hard Stop 2's fire rate, for comparison against the shipped population.

Does not modify or overwrite any shipped file in data/ or reports/ from the
main pipeline -- everything here runs against a separate, temporary
population.
"""

import sys
import os
import csv
import math
import random
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

PROBE_SEED = 90210  # deliberately different from the shipped pipeline's 7375


def main():
    scratch_dir = tempfile.mkdtemp(prefix="frictional_probe_")
    print(f"Scratch directory: {scratch_dir}")

    import generate_candidates as gc
    random.seed(PROBE_SEED)  # re-seed AFTER import -- the module sets its
    # own seed(7375) at import time, so seeding before import gets silently
    # overwritten. This exact mistake was caught and fixed while running
    # this probe for real; see the Frictional Journal for that note.
    gc.OUT_PATH = os.path.join(scratch_dir, "candidates_raw.csv")
    gc.main()

    import gigo_gate as gg
    gg.IN_PATH = os.path.join(scratch_dir, "candidates_raw.csv")
    gg.PASS_PATH = os.path.join(scratch_dir, "candidates_gated.csv")
    gg.REPORT_PATH = os.path.join(scratch_dir, "gigo_report.md")
    gg.main()

    with open(gg.PASS_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    import calibrate_shift as cs

    print("\n--- Calibration boundary on this probe population ---")
    lo_factor, hi_factor = 0.0, 0.60
    for _ in range(30):
        mid = (lo_factor + hi_factor) / 2
        gap = cs.signed_eo_gap(rows, mid)
        if gap < 0:
            lo_factor = mid
        else:
            hi_factor = mid
    boundary_gap_at_zero = cs.signed_eo_gap(rows, 0.0)
    print(f"Boundary: ~{lo_factor:.4f}")
    print(f"Signed gap AT factor=0 (plain parity, no correction): {boundary_gap_at_zero:+.5f}")
    if boundary_gap_at_zero > 0:
        print("-> The 'low' network group ALREADY has higher EV than 'high' under plain parity, "
              "before any correction. There is no gap to correct in this sample; any positive "
              "shift would overshoot immediately.")
    else:
        print("-> A real gap exists at factor=0 in this sample (low group behind, as expected).")

    import allocator as alloc
    from explainability import decompose_ev

    print("\n--- Parity-policy mean EV by group (checking the sign) ---")
    low_evs, high_evs = [], []
    for row in rows:
        hours_total = int(row["hours_available_per_week"])
        cold_rate = float(row["base_conversion_cold"])
        referral_rate = float(row["base_conversion_referral"])
        apply_h, network_h, _ = alloc.parity_split(hours_total)
        decomp = decompose_ev(apply_h, network_h, cold_rate, referral_rate)
        if row["network_group"] == "low":
            low_evs.append(decomp["total_ev"])
        elif row["network_group"] == "high":
            high_evs.append(decomp["total_ev"])
    print(f"low group mean EV:  {sum(low_evs)/len(low_evs):.5f} (n={len(low_evs)})")
    print(f"high group mean EV: {sum(high_evs)/len(high_evs):.5f} (n={len(high_evs)})")

    print("\n--- Hard Stop 2 fire rate on this probe population ---")
    hs2_fired = 0
    for row in rows:
        hours_total = int(row["hours_available_per_week"])
        live_conversations = int(row["live_conversations"])
        cold_rate = float(row["base_conversion_cold"])
        referral_rate = float(row["base_conversion_referral"])
        apply_h, network_h, _ = alloc.outcome_split(hours_total, live_conversations)
        decomp = decompose_ev(apply_h, network_h, cold_rate, referral_rate)
        n_apps = apply_h * 3.0
        n_convos = network_h * 0.5
        n_referrals = n_convos * 0.30
        var_apps = n_apps * cold_rate * (1 - cold_rate)
        var_referrals = n_referrals * referral_rate * (1 - referral_rate)
        sd = math.sqrt(max(var_apps + var_referrals, 1e-9))
        ev = decomp["total_ev"]
        lower = max(0.0, ev - 1.645 * sd)
        upper = ev + 1.645 * sd
        width_ratio = (upper - lower) / ev if ev > 0 else float("inf")
        if width_ratio > 1.5:
            hs2_fired += 1
    print(f"Hard Stop 2 fired for {hs2_fired}/{len(rows)} candidates "
          f"(shipped population: 213/213, for comparison)")


if __name__ == "__main__":
    main()
