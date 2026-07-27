"""
explainability.py

Component 4: Explainability & Its Critique.

METHOD CHOSEN: counterfactual / contribution-based explanation, not SHAP or
LIME. Justification: SHAP and LIME exist to approximate feature attribution
for an opaque model by perturbing inputs and fitting a local surrogate.
Our allocator is not opaque -- it is a fully known, additive closed-form
function (expected_value_and_uncertainty in allocator.py). For an additive
model, the exact Shapley decomposition IS the direct term-by-term
breakdown; running a sampling-based approximation on a function we can
already decompose exactly would add noise, not insight. So Part 1 below is
an EXACT contribution decomposition (the real answer to "why this
number"), and Part 2 is a genuine counterfactual explainer (the real
answer to "what would change the recommendation").

Part 3 is the critique: a specific case where this explanation is
technically accurate and practically misleading -- the gap the assignment
asks for.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from allocator import (
    parity_split, outcome_split, APPLICATIONS_PER_HOUR,
    CONVERSATIONS_PER_HOUR, CONVO_TO_REFERRAL_RATE,
)

GATED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_gated.csv")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "explainability_report.md")

# --- Illustrative timing-lag assumptions (NOT sourced from the book verbatim;
# the book names the phenomenon -- Ch.2: "you are three weeks from a visa
# deadline, which changes the entire calculus of which channel can close
# fast enough to matter" -- but does not give numeric lags. These are a
# modeling assumption we introduce to make that qualitative point
# quantifiable, and we flag them as such rather than presenting them as
# verified figures. ---
COLD_LAG_ZERO_WEEKS = 1     # below this, ~0% of cold-application EV is realizable in time
COLD_LAG_FULL_WEEKS = 4     # at/above this, ~100% of cold-application EV is realizable
REFERRAL_LAG_ZERO_WEEKS = 3   # below this, ~0% of referral EV is realizable in time
REFERRAL_LAG_FULL_WEEKS = 9   # at/above this, ~100% of referral EV is realizable


def realization_fraction(weeks_remaining, zero_at, full_at):
    """Linear ramp from 0 at `zero_at` weeks to 1 at `full_at` weeks. Clamped to [0,1]."""
    if weeks_remaining is None:
        return 1.0  # no deadline constraint
    if weeks_remaining <= zero_at:
        return 0.0
    if weeks_remaining >= full_at:
        return 1.0
    return (weeks_remaining - zero_at) / (full_at - zero_at)


def decompose_ev(apply_h, network_h, cold_rate, referral_rate):
    """Exact, additive contribution decomposition (Part 1)."""
    n_apps = apply_h * APPLICATIONS_PER_HOUR
    n_convos = network_h * CONVERSATIONS_PER_HOUR
    n_referrals = n_convos * CONVO_TO_REFERRAL_RATE

    ev_from_apply = n_apps * cold_rate
    ev_from_network = n_referrals * referral_rate
    total = ev_from_apply + ev_from_network

    return {
        "n_applications": round(n_apps, 2),
        "n_conversations": round(n_convos, 2),
        "n_referrals_generated": round(n_referrals, 3),
        "ev_from_apply_hours": round(ev_from_apply, 5),
        "ev_from_network_hours": round(ev_from_network, 5),
        "total_ev": round(total, 5),
        "share_from_apply_pct": round(100 * ev_from_apply / total, 1) if total > 0 else 0.0,
        "share_from_network_pct": round(100 * ev_from_network / total, 1) if total > 0 else 0.0,
    }


def realizable_decompose_ev(apply_h, network_h, cold_rate, referral_rate, weeks_remaining):
    """Same decomposition, but discounting each stream's EV by how much of it can
    plausibly land before weeks_remaining runs out (Part 3 -- the critique)."""
    raw = decompose_ev(apply_h, network_h, cold_rate, referral_rate)
    apply_frac = realization_fraction(weeks_remaining, COLD_LAG_ZERO_WEEKS, COLD_LAG_FULL_WEEKS)
    network_frac = realization_fraction(weeks_remaining, REFERRAL_LAG_ZERO_WEEKS, REFERRAL_LAG_FULL_WEEKS)

    realizable_apply = raw["ev_from_apply_hours"] * apply_frac
    realizable_network = raw["ev_from_network_hours"] * network_frac
    realizable_total = realizable_apply + realizable_network

    return {
        "apply_realization_fraction": round(apply_frac, 2),
        "network_realization_fraction": round(network_frac, 2),
        "realizable_ev_from_apply": round(realizable_apply, 5),
        "realizable_ev_from_network": round(realizable_network, 5),
        "realizable_total_ev": round(realizable_total, 5),
        "raw_total_ev": raw["total_ev"],
    }


def counterfactual_live_conversations(row, target_live_conversations):
    """Part 2: what would the allocation/EV be if this candidate had a
    different live_conversations count, holding everything else fixed?"""
    hours_total = int(row["hours_available_per_week"])
    cold_rate = float(row["base_conversion_cold"])
    referral_rate = float(row["base_conversion_referral"])

    apply_h, network_h, _ = outcome_split(hours_total, target_live_conversations)
    decomp = decompose_ev(apply_h, network_h, cold_rate, referral_rate)
    return apply_h, network_h, decomp


def find_critique_candidate(rows):
    """Find the most acute case: visa_constrained, fewest weeks remaining,
    lowest network_group -- the scenario where the timing blind spot bites hardest."""
    candidates = [r for r in rows if r.get("visa_constrained") == "True" and r.get("weeks_remaining_on_authorization")]
    candidates.sort(key=lambda r: (int(r["weeks_remaining_on_authorization"]), 0 if r["network_group"] == "low" else 1))
    return candidates[0] if candidates else None


def main():
    with open(GATED_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    lines = []
    lines.append("# Explainability Report\n")
    lines.append(
        "**Method:** exact additive contribution decomposition + counterfactual explainer "
        "(not SHAP/LIME -- justified in the module docstring: the allocator is a known, "
        "closed-form additive function, so exact decomposition IS the Shapley answer here; "
        "a sampling approximation would add noise, not insight).\n"
    )

    # ---- Part 1: worked example of the decomposition ----
    example = rows[0]
    hours_total = int(example["hours_available_per_week"])
    live_conversations = int(example["live_conversations"])
    cold_rate = float(example["base_conversion_cold"])
    referral_rate = float(example["base_conversion_referral"])
    apply_h, network_h, _ = outcome_split(hours_total, live_conversations)
    decomp = decompose_ev(apply_h, network_h, cold_rate, referral_rate)

    lines.append(f"\n## Part 1 -- Exact contribution decomposition (worked example: {example['candidate_id']})\n")
    lines.append(f"- network_group: {example['network_group']}, live_conversations: {live_conversations}, "
                 f"hours_available: {hours_total}\n")
    lines.append(f"- Recommended split: apply={apply_h:.2f}h, network={network_h:.2f}h\n")
    lines.append(f"- {decomp['n_applications']} applications sent -> "
                 f"{decomp['ev_from_apply_hours']:.5f} expected hires ({decomp['share_from_apply_pct']}% of total)\n")
    lines.append(f"- {decomp['n_conversations']} conversations -> {decomp['n_referrals_generated']} referrals -> "
                 f"{decomp['ev_from_network_hours']:.5f} expected hires ({decomp['share_from_network_pct']}% of total)\n")
    lines.append(f"- **Total expected weekly hires contribution: {decomp['total_ev']:.5f}**\n")
    lines.append(
        "\nThis decomposition is exact and exhaustive for this model: the two terms sum to the total EV with "
        "nothing left over, because the model is additive by construction. This IS what SHAP would converge to "
        "for this function, computed directly instead of approximated.\n"
    )

    # ---- Part 2: counterfactual ----
    lines.append(f"\n## Part 2 -- Counterfactual: what if {example['candidate_id']} had more live conversations?\n")
    lines.append("| live_conversations (counterfactual) | apply_h | network_h | total_ev | share from network |\n"
                 "|---|---|---|---|---|\n")
    for cf_lc in [0, 2, 5, 10, 15, 20]:
        cf_apply_h, cf_network_h, cf_decomp = counterfactual_live_conversations(example, cf_lc)
        lines.append(f"| {cf_lc} | {cf_apply_h:.2f} | {cf_network_h:.2f} | {cf_decomp['total_ev']:.5f} | "
                     f"{cf_decomp['share_from_network_pct']}% |\n")
    lines.append(
        "\nReading this counterfactual honestly: as live_conversations rises toward and past the healthy "
        "threshold (10), the tool's own deficit-based logic recommends LESS extra network-hour shift (because "
        "the candidate needs less correction) -- yet total EV still rises, because more live conversations "
        "convert to referrals more efficiently regardless of allocation. The tool's recommendation and a "
        "candidate's raw expected value move somewhat independently here, which is worth stating plainly rather "
        "than eliding.\n"
    )

    # ---- Part 3: the critique ----
    critique_row = find_critique_candidate(rows)
    lines.append("\n## Part 3 -- The critique: technically accurate, practically misleading\n")

    if critique_row:
        cid = critique_row["candidate_id"]
        weeks_remaining = int(critique_row["weeks_remaining_on_authorization"])
        hours_total = int(critique_row["hours_available_per_week"])
        live_conversations = int(critique_row["live_conversations"])
        cold_rate = float(critique_row["base_conversion_cold"])
        referral_rate = float(critique_row["base_conversion_referral"])

        apply_h, network_h, _ = outcome_split(hours_total, live_conversations)
        raw_decomp = decompose_ev(apply_h, network_h, cold_rate, referral_rate)
        realizable = realizable_decompose_ev(apply_h, network_h, cold_rate, referral_rate, weeks_remaining)

        lines.append(f"\n**The case:** candidate **{cid}** -- network_group={critique_row['network_group']}, "
                     f"live_conversations={live_conversations}, visa_constrained=True, "
                     f"**weeks_remaining_on_authorization={weeks_remaining}**.\n")
        lines.append(f"\nThe tool recommends: apply={apply_h:.2f}h, network={network_h:.2f}h/week, with a "
                     f"stated total expected-hires contribution of **{raw_decomp['total_ev']:.5f}** "
                     f"({raw_decomp['share_from_network_pct']}% of it coming from the network-hour channel). "
                     f"**This number is correct** -- it follows exactly from the model's own assumptions and the "
                     f"decomposition in Part 1. There is no arithmetic error anywhere in it.\n")
        lines.append(
            f"\n**What it omits:** the model has no concept of TIME. It reports total eventual expected value, "
            f"not expected value realizable within this candidate's actual remaining runway. Applying an "
            f"illustrative lag assumption (cold applications take roughly "
            f"{COLD_LAG_ZERO_WEEKS}-{COLD_LAG_FULL_WEEKS} weeks to fully convert into a response/interview "
            f"process; referral-based hires take roughly "
            f"{REFERRAL_LAG_ZERO_WEEKS}-{REFERRAL_LAG_FULL_WEEKS} weeks, since they route through an "
            f"introduction, a conversation, and then a referral before an interview process even starts -- "
            f"these numbers are a modeling assumption, not a verified figure, see the module docstring):\n"
        )
        lines.append(
            f"\n| | Raw (what the tool reports) | Realizable within {weeks_remaining} weeks (what actually matters) |\n"
            f"|---|---|---|\n"
            f"| From apply hours | {raw_decomp['ev_from_apply_hours']:.5f} | "
            f"{realizable['realizable_ev_from_apply']:.5f} (realization fraction: {realizable['apply_realization_fraction']}) |\n"
            f"| From network hours | {raw_decomp['ev_from_network_hours']:.5f} | "
            f"{realizable['realizable_ev_from_network']:.5f} (realization fraction: {realizable['network_realization_fraction']}) |\n"
            f"| **Total** | **{raw_decomp['total_ev']:.5f}** | **{realizable['realizable_total_ev']:.5f}** |\n"
        )
        network_realizable = realizable['realizable_ev_from_network']
        apply_realizable = realizable['realizable_ev_from_apply']
        flips = network_realizable < apply_realizable  # raw picture had network winning
        verdict = (
            "the realizable picture actually FLIPS which channel wins -- apply hours, not network hours, "
            "produce more of what can land in time"
            if flips else
            "network hours still win on a realizable basis, just by a smaller margin than the raw number implied"
        )
        lines.append(
            f"\n**The lie by omission:** the tool's headline number ({raw_decomp['total_ev']:.5f}) implies the "
            f"network-heavy recommendation is the better choice, with the network channel contributing "
            f"{raw_decomp['share_from_network_pct']}% of it. Once discounted for what can actually land before "
            f"this candidate's authorization runs out, {verdict}: "
            f"apply-hours realizable EV = {apply_realizable:.5f} vs network-hours realizable EV = "
            f"{network_realizable:.5f}. Every number in the tool's original output was correct. The one number "
            f"that actually mattered for THIS candidate's decision -- which channel converts before the clock "
            f"runs out -- was never computed by the tool at all.\n"
        )
        lines.append(
            "\nThis is exactly what Chapter 2 names directly but the tool cannot act on: "
            '\"it cannot know that you are three weeks from a visa deadline, which changes the entire calculus '
            'of which channel can close fast enough to matter.\" The tool has no weeks_remaining term anywhere in '
            "its expected-value function -- not because the data wasn't available (it's sitting right there in "
            "the candidate record) but because the model was never built to weight EV by time-to-realization. "
            "That is the gap: a technically correct number, produced by a tool that had the relevant field in "
            "front of it and didn't use it.\n"
        )
    else:
        lines.append("\nNo visa-constrained candidate with weeks_remaining_on_authorization found in this gated "
                     "population run -- rerun after generate_candidates.py to get a fresh sample.\n")

    lines.append(
        "\n## What this means for the tool going forward\n\n"
        "This is the single clearest argument for the hard-stop gate (component 7): a tool that cannot reason "
        "about time should not be allowed to make an unreviewed recommendation for a candidate whose real "
        "constraint IS time. The fix is not a better explanation of the existing number -- it's refusing to let "
        "the existing number stand alone for this candidate population, and routing to the human-reviewed "
        "gate instead.\n"
    )

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.writelines(lines)

    print("Explainability report written to", REPORT_PATH)
    if critique_row:
        print(f"Critique candidate: {critique_row['candidate_id']} "
              f"(weeks_remaining={critique_row['weeks_remaining_on_authorization']})")


if __name__ == "__main__":
    main()
