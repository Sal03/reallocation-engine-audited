# Causal Reasoning Report -- Pearl's Three Rungs

## Rung 1 -- Observation
Under the **parity** policy (network hours do NOT depend on live_conversations by design), the correlation between live_conversations and expected_weekly_hires_contribution is **r = 0.1493**.
For comparison, hours_available_per_week and live_conversations -- two fields sampled completely independently in our generator -- have a measured correlation of r = 0.1493 across the gated population. This is the noise floor: any correlation of similar magnitude elsewhere in this analysis is indistinguishable from finite-sample noise, not signal.

Under the **outcome** policy (network hours DO depend on live_conversations, by explicit design), the same correlation is **r = 0.0131** -- smaller, not larger, than under parity. This is not a contradiction: the outcome policy was explicitly calibrated (component 3) to flatten the EV gap between network groups, so a near-zero correlation here is the intended effect of that correction showing up as a side effect in Rung 1, not a new finding.

**The honest reading is stronger than 'similar to noise':** r1_parity and the noise floor are not merely close, they are IDENTICAL to full precision (0.1493 = 0.1493). This is not a coincidence -- it is a mathematical necessity of the model as built. Under parity, `apply_h` and `network_h` are fixed proportions of `hours_available_per_week` alone, and the conversion-rate constants are identical for every candidate, so `expected_weekly_hires_contribution` is an exact linear function of `hours_total` and NOTHING else. Correlating live_conversations against EV under parity is therefore mathematically guaranteed to reproduce whatever accidental correlation exists between live_conversations and hours_total -- which is pure sampling noise from two independently-drawn fields. Our own synthetic model does not contain an organic Rung-1 correlation between network size and outcome at all -- it only appears once we deliberately build an allocation rule that responds to network size.

This is a real limitation worth naming plainly: Chapter 2's headline statistic (54% of hires via connections, referral conversion many times higher than cold) describes something about REAL hiring markets that our model does not structurally encode on its own. We import that correlation as an assumption (the fixed base_conversion_referral constant) rather than deriving it from anything our synthetic data independently produces. If Chapter 2's own statistic is wrong or doesn't transfer to a given candidate, nothing in our simulation would catch that -- it isn't an emergent finding, it's a premise we typed in.

## Rung 2 -- Intervention
The question Rung 2 asks: does actually reallocating hours toward networking CAUSE a better outcome, or does our model just assume it by construction? Here, by construction, YES it does -- but only because we hardwired `CONVO_TO_REFERRAL_RATE` and `base_conversion_referral` as fixed, population-wide constants that apply mechanically to any candidate who receives more network hours. That is an assumed interventional relationship, not a measured one. We have never run an actual experiment (e.g., randomizing real candidates to different hour-splits and observing real hire outcomes) to confirm the rate transfers.

**Named confounders that could make this correlation vanish under a real intervention:**

1. **Prior social capital / professional experience.** A candidate with 15 live conversations likely has that count *because* of pre-existing professional experience, alumni networks, or interpersonal skill -- the same underlying trait plausibly ALSO raises their referral-to-interview conversion rate directly (a warmer, higher-quality network converts better per conversation, not just more conversations). Our model applies the identical `base_conversion_referral` to everyone regardless of network_group, which could either overstate the benefit for low-network candidates (if their conversations convert worse) or understate it for high-network candidates (if theirs convert better). We do not know which, and our current design cannot distinguish the two.
2. **Reverse causation.** A candidate who senses an offer is close might increase networking activity in response to that momentum, rather than networking causing the offer. Our data has no time-ordering within a single snapshot to rule this out.
3. **Sector/company-tier confound.** Some sectors have denser professional networking norms independent of an individual candidate's effort; industry choice could inflate both live_conversations and hire rate without hours-allocated-to-networking doing any causal work at all.

## Rung 3 -- Counterfactual
**The specific past case:** candidate C0032 (network_group=low, live_conversations=3, weeks_remaining_on_authorization=2). The tool actually recommended the outcome-policy split: apply=3.93h, network=10.52h.

**The counterfactual question:** what would have happened to THIS candidate, in THIS week, had the engine given the plain parity split instead (apply=5.25h, network=7.88h)?

| | Actual (outcome policy) | Counterfactual (parity policy) |
|---|---|---|
| Raw total EV | 0.07091 | 0.06694 |
| Realizable EV (within 2 weeks) | 0.00785 | 0.01050 |

**Reading this plainly:** on the RAW total, the tool's actual recommendation (0.07091) beats the counterfactual parity split (0.06694) -- which is exactly why the tool recommended it. But on the REALIZABLE total, the ranking flips: the counterfactual parity split (0.01050) would have done better for this specific candidate than what the tool actually recommended (0.00785). This is the same finding as component 4's critique, arrived at independently through the counterfactual lens rather than the decomposition lens: for a candidate whose real constraint is time, not raw expected value, the engine's own recommendation was the worse choice, and a plainer default would have served them better.

**Assumptions this counterfactual rests on** (named, not hidden):

1. **SUTVA (stable unit treatment value assumption):** this candidate's outcome depends only on their own allocation, not on other candidates' allocations. This is questionable in a real referral market -- if many candidates from the same program compete for the same handful of warm introductions, one candidate's networking success can reduce another's opportunity. Our model does not represent this at all.
2. **External validity of population-average rates to this individual.** We apply the same cold/referral conversion constants to this candidate as to everyone else. We have no individual-level data to justify that transfer.
3. **Rate stability across the actual 2-week window.** We assume the conversion rates don't change during the candidate's remaining runway (e.g., due to a hiring freeze, a visa-policy shift, or a sudden market change) -- Chapter 15 names exactly this risk (a healthy skip rate with zero responses can reflect a frozen market, not a bad filter), and we cannot distinguish it here.

## Plain verdict: does this engine reallocate on correlation dressed as causation?
**Yes, mostly.** The tool's core mechanism inherits a real-world, population-level statistic (Chapter 2's ~54% hires-via-connections figure, and its referral-vs-cold conversion-rate comparison) and encodes it as if it were a stable, individually-applicable causal treatment effect -- without confounder adjustment, without an experimental intervention to confirm it transfers, and, as Rung 1 showed, without our own synthetic model even reproducing an organic version of that correlation on its own. Worth noting explicitly: the book's own footnotes mark these same figures with '**[verify]** -- trace to primary survey before publication,' meaning the number we built our entire allocation mechanism on top of was never claimed as verified even by its own source. We built a tool that treats an unverified observational statistic as a calibrated causal rate. That is the honest status of this engine, and it is the single most important limitation in this report.
