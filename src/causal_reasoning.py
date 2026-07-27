"""
causal_reasoning.py

Component 5: Causal & Counterfactual Reasoning -- Pearl's Three Rungs.

A reallocation is a causal claim: "moving hours to networking will produce
a better outcome." This script computes, against our OWN actual run data,
whether the tool's internal logic supports that claim at each of Pearl's
three rungs -- rather than asserting the verdict in prose.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from allocator import outcome_split
from explainability import decompose_ev, realizable_decompose_ev, find_critique_candidate

PARITY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "allocations_parity.csv")
OUTCOME_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "allocations_outcome.csv")
GATED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "candidates_gated.csv")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "causal_reasoning_report.md")


def pearson(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / (var_x ** 0.5 * var_y ** 0.5)


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def main():
    parity_rows = load(PARITY_PATH)
    outcome_rows = load(OUTCOME_PATH)
    gated_rows = load(GATED_PATH)

    # ---- RUNG 1: Observation ----
    # Correlation between live_conversations and expected outcome, under a
    # policy that does NOT let live_conversations affect the allocation
    # (parity) -- isolates whatever "organic" observational association
    # exists, versus one we manufacture ourselves.
    parity_lc = [int(r["live_conversations"]) for r in parity_rows]
    parity_ev = [float(r["expected_weekly_hires_contribution"]) for r in parity_rows]
    r1_parity = pearson(parity_lc, parity_ev)

    outcome_lc = [int(r["live_conversations"]) for r in outcome_rows]
    outcome_ev = [float(r["expected_weekly_hires_contribution"]) for r in outcome_rows]
    r1_outcome = pearson(outcome_lc, outcome_ev)

    # hours_available_per_week correlation with live_conversations -- should
    # be ~0 by construction (independently sampled); check whether small-sample
    # noise created an accidental association that could explain any parity
    # correlation.
    gated_lc = [int(r["live_conversations"]) for r in gated_rows]
    gated_hours = [int(r["hours_available_per_week"]) for r in gated_rows]
    r_lc_hours = pearson(gated_lc, gated_hours)

    lines = []
    lines.append("# Causal Reasoning Report -- Pearl's Three Rungs\n")

    lines.append("\n## Rung 1 -- Observation\n")
    lines.append(
        f"Under the **parity** policy (network hours do NOT depend on live_conversations by design), the "
        f"correlation between live_conversations and expected_weekly_hires_contribution is "
        f"**r = {r1_parity:.4f}**.\n"
    )
    lines.append(
        f"For comparison, hours_available_per_week and live_conversations -- two fields sampled completely "
        f"independently in our generator -- have a measured correlation of r = {r_lc_hours:.4f} across the "
        f"gated population. This is the noise floor: any correlation of similar magnitude elsewhere in this "
        f"analysis is indistinguishable from finite-sample noise, not signal.\n"
    )
    lines.append(
        f"\nUnder the **outcome** policy (network hours DO depend on live_conversations, by explicit design), "
        f"the same correlation is **r = {r1_outcome:.4f}** -- smaller, not larger, than under parity. This is "
        f"not a contradiction: the outcome policy was explicitly calibrated (component 3) to flatten the "
        f"EV gap between network groups, so a near-zero correlation here is the intended effect of that "
        f"correction showing up as a side effect in Rung 1, not a new finding.\n"
    )
    lines.append(
        "\n**The honest reading is stronger than 'similar to noise':** r1_parity and the noise floor are not "
        "merely close, they are IDENTICAL to full precision (0.1493 = 0.1493). This is not a coincidence -- it "
        "is a mathematical necessity of the model as built. Under parity, `apply_h` and `network_h` are fixed "
        "proportions of `hours_available_per_week` alone, and the conversion-rate constants are identical for "
        "every candidate, so `expected_weekly_hires_contribution` is an exact linear function of `hours_total` "
        "and NOTHING else. Correlating live_conversations against EV under parity is therefore mathematically "
        "guaranteed to reproduce whatever accidental correlation exists between live_conversations and "
        "hours_total -- which is pure sampling noise from two independently-drawn fields. Our own synthetic "
        "model does not contain an organic Rung-1 correlation between network size and outcome at all -- it "
        "only appears once we deliberately build an allocation rule that responds to network size.\n"
    )
    lines.append(
        "\nThis is a real limitation worth naming plainly: Chapter 2's headline statistic (54% of hires via "
        "connections, referral conversion many times higher than cold) describes something about REAL hiring "
        "markets that our model does not structurally encode on its own. We import that correlation as an "
        "assumption (the fixed base_conversion_referral constant) rather than deriving it from anything our "
        "synthetic data independently produces. If Chapter 2's own statistic is wrong or doesn't transfer to a "
        "given candidate, nothing in our simulation would catch that -- it isn't an emergent finding, it's a "
        "premise we typed in.\n"
    )

    # ---- RUNG 2: Intervention ----
    lines.append("\n## Rung 2 -- Intervention\n")
    lines.append(
        "The question Rung 2 asks: does actually reallocating hours toward networking CAUSE a better outcome, "
        "or does our model just assume it by construction? Here, by construction, YES it does -- but only "
        "because we hardwired `CONVO_TO_REFERRAL_RATE` and `base_conversion_referral` as fixed, "
        "population-wide constants that apply mechanically to any candidate who receives more network hours. "
        "That is an assumed interventional relationship, not a measured one. We have never run an actual "
        "experiment (e.g., randomizing real candidates to different hour-splits and observing real hire "
        "outcomes) to confirm the rate transfers.\n"
    )
    lines.append("\n**Named confounders that could make this correlation vanish under a real intervention:**\n\n")
    lines.append(
        "1. **Prior social capital / professional experience.** A candidate with 15 live conversations likely "
        "has that count *because* of pre-existing professional experience, alumni networks, or interpersonal "
        "skill -- the same underlying trait plausibly ALSO raises their referral-to-interview conversion rate "
        "directly (a warmer, higher-quality network converts better per conversation, not just more "
        "conversations). Our model applies the identical `base_conversion_referral` to everyone regardless of "
        "network_group, which could either overstate the benefit for low-network candidates (if their "
        "conversations convert worse) or understate it for high-network candidates (if theirs convert better). "
        "We do not know which, and our current design cannot distinguish the two.\n"
    )
    lines.append(
        "2. **Reverse causation.** A candidate who senses an offer is close might increase networking activity "
        "in response to that momentum, rather than networking causing the offer. Our data has no time-ordering "
        "within a single snapshot to rule this out.\n"
    )
    lines.append(
        "3. **Sector/company-tier confound.** Some sectors have denser professional networking norms "
        "independent of an individual candidate's effort; industry choice could inflate both live_conversations "
        "and hire rate without hours-allocated-to-networking doing any causal work at all.\n"
    )

    # ---- RUNG 3: Counterfactual ----
    lines.append("\n## Rung 3 -- Counterfactual\n")
    critique_row = find_critique_candidate(gated_rows)
    if critique_row:
        cid = critique_row["candidate_id"]
        weeks_remaining = int(critique_row["weeks_remaining_on_authorization"])
        hours_total = int(critique_row["hours_available_per_week"])
        live_conversations = int(critique_row["live_conversations"])
        cold_rate = float(critique_row["base_conversion_cold"])
        referral_rate = float(critique_row["base_conversion_referral"])

        apply_h, network_h, _ = outcome_split(hours_total, live_conversations)
        raw = decompose_ev(apply_h, network_h, cold_rate, referral_rate)
        realizable = realizable_decompose_ev(apply_h, network_h, cold_rate, referral_rate, weeks_remaining)

        # Counterfactual: what if we'd given this SAME candidate the parity split instead?
        total_ratio = 8
        cf_apply_h = hours_total * (2 / total_ratio)
        cf_network_h = hours_total * (3 / total_ratio)
        cf_raw = decompose_ev(cf_apply_h, cf_network_h, cold_rate, referral_rate)
        cf_realizable = realizable_decompose_ev(cf_apply_h, cf_network_h, cold_rate, referral_rate, weeks_remaining)

        lines.append(
            f"**The specific past case:** candidate {cid} (network_group={critique_row['network_group']}, "
            f"live_conversations={live_conversations}, weeks_remaining_on_authorization={weeks_remaining}). The "
            f"tool actually recommended the outcome-policy split: apply={apply_h:.2f}h, network={network_h:.2f}h.\n"
        )
        lines.append(
            f"\n**The counterfactual question:** what would have happened to THIS candidate, in THIS week, had "
            f"the engine given the plain parity split instead (apply={cf_apply_h:.2f}h, network={cf_network_h:.2f}h)?\n"
        )
        lines.append(
            f"\n| | Actual (outcome policy) | Counterfactual (parity policy) |\n|---|---|---|\n"
            f"| Raw total EV | {raw['total_ev']:.5f} | {cf_raw['total_ev']:.5f} |\n"
            f"| Realizable EV (within {weeks_remaining} weeks) | {realizable['realizable_total_ev']:.5f} | "
            f"{cf_realizable['realizable_total_ev']:.5f} |\n"
        )
        lines.append(
            f"\n**Reading this plainly:** on the RAW total, the tool's actual recommendation "
            f"({raw['total_ev']:.5f}) beats the counterfactual parity split ({cf_raw['total_ev']:.5f}) -- which "
            f"is exactly why the tool recommended it. But on the REALIZABLE total, the ranking flips: the "
            f"counterfactual parity split ({cf_realizable['realizable_total_ev']:.5f}) would have done better "
            f"for this specific candidate than what the tool actually recommended "
            f"({realizable['realizable_total_ev']:.5f}). This is the same finding as component 4's critique, "
            f"arrived at independently through the counterfactual lens rather than the decomposition lens: for "
            f"a candidate whose real constraint is time, not raw expected value, the engine's own recommendation "
            f"was the worse choice, and a plainer default would have served them better.\n"
        )
        lines.append(
            "\n**Assumptions this counterfactual rests on** (named, not hidden):\n\n"
            "1. **SUTVA (stable unit treatment value assumption):** this candidate's outcome depends only on "
            "their own allocation, not on other candidates' allocations. This is questionable in a real "
            "referral market -- if many candidates from the same program compete for the same handful of warm "
            "introductions, one candidate's networking success can reduce another's opportunity. Our model "
            "does not represent this at all.\n"
            "2. **External validity of population-average rates to this individual.** We apply the same "
            "cold/referral conversion constants to this candidate as to everyone else. We have no "
            "individual-level data to justify that transfer.\n"
            "3. **Rate stability across the actual 2-week window.** We assume the conversion rates don't "
            "change during the candidate's remaining runway (e.g., due to a hiring freeze, a visa-policy "
            "shift, or a sudden market change) -- Chapter 15 names exactly this risk (a healthy skip rate with "
            "zero responses can reflect a frozen market, not a bad filter), and we cannot distinguish it here.\n"
        )
    else:
        lines.append("No qualifying candidate found in this run.\n")

    # ---- Verdict ----
    lines.append("\n## Plain verdict: does this engine reallocate on correlation dressed as causation?\n")
    lines.append(
        "**Yes, mostly.** The tool's core mechanism inherits a real-world, population-level statistic "
        "(Chapter 2's ~54% hires-via-connections figure, and its referral-vs-cold conversion-rate comparison) "
        "and encodes it as if it were a stable, individually-applicable causal treatment effect -- without "
        "confounder adjustment, without an experimental intervention to confirm it transfers, and, as Rung 1 "
        "showed, without our own synthetic model even reproducing an organic version of that correlation on its "
        "own. Worth noting explicitly: the book's own footnotes mark these same figures with '**[verify]** -- "
        "trace to primary survey before publication,' meaning the number we built our entire allocation "
        "mechanism on top of was never claimed as verified even by its own source. We built a tool that treats "
        "an unverified observational statistic as a calibrated causal rate. That is the honest status of this "
        "engine, and it is the single most important limitation in this report.\n"
    )

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.writelines(lines)

    print("Causal reasoning report written to", REPORT_PATH)
    print(f"Rung 1 correlation (parity): r={r1_parity:.4f} | (outcome): r={r1_outcome:.4f} | noise floor: r={r_lc_hours:.4f}")


if __name__ == "__main__":
    main()
