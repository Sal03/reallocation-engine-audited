"""
gigo_gate.py

The GIGO Gate: a checkable quality standard a human could verify, run
BEFORE any candidate record is allowed into the reallocation tool.

Component 2 of the assignment. The gate's job is not to produce a clean
table -- it's to find and document what's wrong with the raw table, and to
make an explicit, defensible decision about what happens to each failure.

Hidden assumptions this dataset makes (named, not buried):
  1. Fields are sampled independently. In reality, network size, weeks in
     search, and portfolio output are almost certainly correlated (e.g.
     someone further into their search has likely had more time to build
     both network AND portfolio). This synthetic set does NOT capture that
     correlation, which likely means our bias-audit gap estimates (Ch. 3)
     are a LOWER bound on the real-world gap, not an upper bound.
  2. network_group buckets are balanced 1/3-1/3-1/3 by construction. Real
     search populations are almost certainly skewed toward "low" -- most
     international students do NOT arrive with 10+ live conversations.
     A balanced synthetic set understates how many people the "low" bucket
     really represents.
  3. base_conversion_cold / base_conversion_referral are treated as fixed,
     population-wide constants. Real conversion rates vary by sector,
     company size, and time period -- treating them as fixed is itself a
     simplification the report must name, not hide.
  4. visa_constrained is a boolean with no severity -- it doesn't
     distinguish "6 months left on OPT" from "6 weeks left." That's a real
     information loss the tool inherits.

Gate criteria (checkable by a human against this file):
  - candidate_id must be present and UNIQUE
  - network_group must be one of {low, mid, high}
  - live_conversations must match the stated range for network_group
      low: 0-3, mid: 4-9, high: 10-20
  - hours_available_per_week must be present and within [10, 60]
      (10-60 chosen as a "plausible search-hours" band; anything outside
      is either a data error or an extreme case needing separate handling,
      not silent inclusion)
  - base_conversion_cold and base_conversion_referral must match the
    documented, current book-sourced constants (0.002 / 0.03). Any other
    value indicates a stale or second data source and is rejected rather
    than silently blended in.
"""

import csv
import os

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_raw.csv")
PASS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_gated.csv")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "gigo_gate_report.md")

BUCKET_RANGES = {"low": (0, 3), "mid": (4, 9), "high": (10, 20)}
CURRENT_CONVERSION_COLD = "0.002"
CURRENT_CONVERSION_REFERRAL = "0.03"
HOURS_MIN, HOURS_MAX = 10, 60


def check_row(row, seen_ids):
    """Return list of failure reasons (empty list = pass)."""
    reasons = []

    cid = row.get("candidate_id", "").strip()
    if not cid:
        reasons.append("missing candidate_id")
    elif cid in seen_ids:
        reasons.append(f"duplicate candidate_id ({cid})")

    group = row.get("network_group", "").strip()
    if group not in BUCKET_RANGES:
        reasons.append(f"invalid network_group '{group}'")
    else:
        try:
            lc = int(row.get("live_conversations", ""))
            lo, hi = BUCKET_RANGES[group]
            if not (lo <= lc <= hi):
                reasons.append(
                    f"live_conversations={lc} does not match network_group='{group}' "
                    f"(expected {lo}-{hi}) -- bucket/value mismatch"
                )
        except (ValueError, TypeError):
            reasons.append("missing or non-numeric live_conversations")

    hrs_raw = row.get("hours_available_per_week", "")
    try:
        hrs = int(hrs_raw)
        if not (HOURS_MIN <= hrs <= HOURS_MAX):
            reasons.append(f"hours_available_per_week={hrs} out of plausible range [{HOURS_MIN},{HOURS_MAX}]")
    except (ValueError, TypeError):
        reasons.append("missing or non-numeric hours_available_per_week")

    cc = row.get("base_conversion_cold", "").strip()
    cr = row.get("base_conversion_referral", "").strip()
    if cc != CURRENT_CONVERSION_COLD or cr != CURRENT_CONVERSION_REFERRAL:
        reasons.append(
            f"stale/second-source conversion constants (cold={cc}, referral={cr}); "
            f"expected cold={CURRENT_CONVERSION_COLD}, referral={CURRENT_CONVERSION_REFERRAL}"
        )

    visa_constrained_raw = row.get("visa_constrained", "").strip()
    weeks_remaining_raw = row.get("weeks_remaining_on_authorization", "").strip()
    if visa_constrained_raw == "True":
        try:
            wk = int(weeks_remaining_raw)
            if not (0 <= wk <= 52):
                reasons.append(f"weeks_remaining_on_authorization={wk} out of plausible range [0,52]")
        except (ValueError, TypeError):
            reasons.append("visa_constrained=True but weeks_remaining_on_authorization is missing/non-numeric")
    elif visa_constrained_raw == "False" and weeks_remaining_raw not in ("", None):
        reasons.append("visa_constrained=False but weeks_remaining_on_authorization is populated (should be blank)")

    return reasons


def main():
    with open(IN_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    passed_rows = []
    failures = []  # list of (row, reasons)
    seen_ids = set()

    for row in rows:
        reasons = check_row(row, seen_ids)
        cid = row.get("candidate_id", "").strip()
        if reasons:
            failures.append((row, reasons))
        else:
            passed_rows.append(row)
            seen_ids.add(cid)

    # Write passing rows
    os.makedirs(os.path.dirname(PASS_PATH), exist_ok=True)
    with open(PASS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(passed_rows)

    # Write the human-readable gate report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write("# GIGO Gate Report\n\n")
        f.write(f"Input: `data/candidates_raw.csv` ({len(rows)} rows)\n\n")
        f.write(f"Passed gate: **{len(passed_rows)}** rows -> `data/candidates_gated.csv`\n\n")
        f.write(f"Rejected: **{len(failures)}** rows\n\n")
        f.write("## Rejection reasons (tallied)\n\n")

        tally = {}
        for _, reasons in failures:
            for r in reasons:
                key = r.split(" (")[0].split("=")[0][:40]
                tally[key] = tally.get(key, 0) + 1
        for key, count in sorted(tally.items(), key=lambda x: -x[1]):
            f.write(f"- {key}: {count}\n")

        f.write("\n## Full rejection log\n\n")
        f.write("| candidate_id | reasons |\n|---|---|\n")
        for row, reasons in failures:
            cid = row.get("candidate_id", "(missing)")
            f.write(f"| {cid} | {'; '.join(reasons)} |\n")

        f.write("\n## What we did about it\n\n")
        f.write(
            "Rejected rows are excluded from `candidates_gated.csv` entirely -- "
            "none are imputed, guessed, or silently corrected. This means the "
            "allocator and bias audit downstream run on a strictly smaller, "
            "verified population. We accept the reduced sample size as the cost "
            "of not laundering bad data into a confident-looking result.\n\n"
            "The stale-conversion-constant rows are the most consequential "
            "rejection category: had they been silently kept, they would have "
            "quietly inflated expected-return estimates for whichever rows "
            "carried them, without any visible signal in downstream output.\n"
        )

    print(f"Gate complete: {len(passed_rows)} passed, {len(failures)} rejected.")
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
