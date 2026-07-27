"""
generate_candidates.py

Generates a SYNTHETIC population of job-search candidates for the
Reallocation Engine (Audited) assignment.

This data does NOT capture real applicant outcomes, real network growth
dynamics, or real selection effects. It is a controlled simulation built to
demonstrate the reallocation tool's logic and its bias audit. See
reports/data_provenance.md for a full statement of what this data does and
does not represent.

Anchor: Chapter 2 ("The Reallocation Principle") and Chapter 15
("The Pipeline Tracker and the Skip Rate") of The Reallocation Engine
(N. Bear Brown), which supply:
  - base_conversion_cold ~ 0.2%  (Ch.2, cold-application conversion)
  - base_conversion_referral ~ 2-4%, midpoint 3% (Ch.2, referral conversion)
  - the >=10 live-conversations threshold as the "healthy network" cutoff
    (Ch.15's freed-hour rule: networking gets freed time when live
    conversations < ~10)

Intentional data-quality problems are injected on purpose (see INJECT_*
constants below) so that the GIGO gate (src/gigo_gate.py) has real,
checkable work to do rather than passing a suspiciously clean table.
"""

import csv
import random
import os

random.seed(7375)  # fixed seed: reproducible run, named after the course

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_raw.csv")

N_PER_GROUP = 80          # candidates per network_group bucket
GROUPS = ["low", "mid", "high"]

# Fixed, book-sourced constants (documented above)
BASE_CONVERSION_COLD = 0.002
BASE_CONVERSION_REFERRAL = 0.03

# ---- Intentional data-quality injections (for the GIGO gate to catch) ----
INJECT_MISMATCHED_BUCKET_RATE = 0.04   # bucket label disagrees with live_conversations count
INJECT_MISSING_FIELD_RATE = 0.03       # a required field is blank
INJECT_OUT_OF_RANGE_RATE = 0.03        # hours_available_per_week outside plausible range
INJECT_DUPLICATE_ID_RATE = 0.02        # duplicate candidate_id (data pipeline bug simulation)
INJECT_CONVERSION_DRIFT_RATE = 0.02    # a row silently has a different conversion constant
                                        # (simulates a stale/second data source sneaking in)


def bucket_range(group):
    if group == "low":
        return (0, 3)
    if group == "mid":
        return (4, 9)
    return (10, 20)  # high


def make_row(idx, group):
    lo, hi = bucket_range(group)
    live_conversations = random.randint(lo, hi)
    visa_constrained = random.choice([True, False])
    row = {
        "candidate_id": f"C{idx:04d}",
        "network_group": group,
        "live_conversations": live_conversations,
        "weeks_in_search": random.randint(1, 12),
        "hours_available_per_week": random.randint(20, 40),
        "visa_constrained": visa_constrained,
        # Only meaningful when visa_constrained=True; blank otherwise.
        # Range chosen to span comfortable (12+) down to acute (<=4) cases.
        "weeks_remaining_on_authorization": random.randint(2, 20) if visa_constrained else "",
        "portfolio_pieces_deployed_90d": random.choices([0, 1, 2, 3], weights=[4, 3, 2, 1])[0],
        "base_conversion_cold": BASE_CONVERSION_COLD,
        "base_conversion_referral": BASE_CONVERSION_REFERRAL,
    }
    return row


def inject_problems(rows):
    n = len(rows)
    n_mismatch = int(n * INJECT_MISMATCHED_BUCKET_RATE)
    n_missing = int(n * INJECT_MISSING_FIELD_RATE)
    n_out_of_range = int(n * INJECT_OUT_OF_RANGE_RATE)
    n_dup = int(n * INJECT_DUPLICATE_ID_RATE)
    n_drift = int(n * INJECT_CONVERSION_DRIFT_RATE)

    idx_pool = list(range(n))
    random.shuffle(idx_pool)

    # 1) mismatched bucket: relabel network_group without changing live_conversations
    for i in idx_pool[:n_mismatch]:
        true_group = rows[i]["network_group"]
        other_groups = [g for g in GROUPS if g != true_group]
        rows[i]["network_group"] = random.choice(other_groups)

    # 2) missing field: blank out hours_available_per_week
    for i in idx_pool[n_mismatch:n_mismatch + n_missing]:
        rows[i]["hours_available_per_week"] = ""

    # 3) out-of-range value
    for i in idx_pool[n_mismatch + n_missing:n_mismatch + n_missing + n_out_of_range]:
        rows[i]["hours_available_per_week"] = random.choice([2, 5, 95, 120])

    # 4) duplicate candidate_id (copy an existing id onto a different row)
    dup_start = n_mismatch + n_missing + n_out_of_range
    for i in idx_pool[dup_start:dup_start + n_dup]:
        donor = idx_pool[(idx_pool.index(i) + 1) % n]
        rows[i]["candidate_id"] = rows[donor]["candidate_id"]

    # 5) conversion drift: a stale/second source with different constants
    drift_start = dup_start + n_dup
    for i in idx_pool[drift_start:drift_start + n_drift]:
        rows[i]["base_conversion_cold"] = 0.005          # stale higher estimate
        rows[i]["base_conversion_referral"] = 0.06        # stale higher estimate

    return rows


def main():
    rows = []
    idx = 1
    for group in GROUPS:
        for _ in range(N_PER_GROUP):
            rows.append(make_row(idx, group))
            idx += 1

    rows = inject_problems(rows)

    fieldnames = list(rows[0].keys())
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} synthetic candidate rows to {OUT_PATH}")
    print("Injected problems (by design, for the GIGO gate to catch):")
    print(f"  mismatched bucket labels : ~{int(len(rows)*INJECT_MISMATCHED_BUCKET_RATE)}")
    print(f"  missing required field   : ~{int(len(rows)*INJECT_MISSING_FIELD_RATE)}")
    print(f"  out-of-range values      : ~{int(len(rows)*INJECT_OUT_OF_RANGE_RATE)}")
    print(f"  duplicate candidate_id   : ~{int(len(rows)*INJECT_DUPLICATE_ID_RATE)}")
    print(f"  stale conversion-rate row: ~{int(len(rows)*INJECT_CONVERSION_DRIFT_RATE)}")


if __name__ == "__main__":
    main()
