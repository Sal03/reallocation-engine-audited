# Explainability Report
**Method:** exact additive contribution decomposition + counterfactual explainer (not SHAP/LIME -- justified in the module docstring: the allocator is a known, closed-form additive function, so exact decomposition IS the Shapley answer here; a sampling approximation would add noise, not insight).

## Part 1 -- Exact contribution decomposition (worked example: C0001)
- network_group: low, live_conversations: 2, hours_available: 37
- Recommended split: apply=6.59h, network=19.20h
- 19.76 applications sent -> 0.03952 expected hires (31.4% of total)
- 9.6 conversations -> 2.88 referrals -> 0.08641 expected hires (68.6% of total)
- **Total expected weekly hires contribution: 0.12593**

This decomposition is exact and exhaustive for this model: the two terms sum to the total EV with nothing left over, because the model is additive by construction. This IS what SHAP would converge to for this function, computed directly instead of approximated.

## Part 2 -- Counterfactual: what if C0001 had more live conversations?
| live_conversations (counterfactual) | apply_h | network_h | total_ev | share from network |
|---|---|---|---|---|
| 0 | 5.92 | 20.54 | 0.12793 | 72.2% |
| 2 | 6.59 | 19.20 | 0.12593 | 68.6% |
| 5 | 7.58 | 17.20 | 0.12293 | 63.0% |
| 10 | 9.25 | 13.88 | 0.11794 | 52.9% |
| 15 | 9.25 | 13.88 | 0.11794 | 52.9% |
| 20 | 9.25 | 13.88 | 0.11794 | 52.9% |

Reading this counterfactual honestly: as live_conversations rises toward and past the healthy threshold (10), the tool's own deficit-based logic recommends LESS extra network-hour shift (because the candidate needs less correction) -- yet total EV still rises, because more live conversations convert to referrals more efficiently regardless of allocation. The tool's recommendation and a candidate's raw expected value move somewhat independently here, which is worth stating plainly rather than eliding.

## Part 3 -- The critique: technically accurate, practically misleading

**The case:** candidate **C0032** -- network_group=low, live_conversations=3, visa_constrained=True, **weeks_remaining_on_authorization=2**.

The tool recommends: apply=3.93h, network=10.52h/week, with a stated total expected-hires contribution of **0.07091** (66.8% of it coming from the network-hour channel). **This number is correct** -- it follows exactly from the model's own assumptions and the decomposition in Part 1. There is no arithmetic error anywhere in it.

**What it omits:** the model has no concept of TIME. It reports total eventual expected value, not expected value realizable within this candidate's actual remaining runway. Applying an illustrative lag assumption (cold applications take roughly 1-4 weeks to fully convert into a response/interview process; referral-based hires take roughly 3-9 weeks, since they route through an introduction, a conversation, and then a referral before an interview process even starts -- these numbers are a modeling assumption, not a verified figure, see the module docstring):

| | Raw (what the tool reports) | Realizable within 2 weeks (what actually matters) |
|---|---|---|
| From apply hours | 0.02356 | 0.00785 (realization fraction: 0.33) |
| From network hours | 0.04734 | 0.00000 (realization fraction: 0.0) |
| **Total** | **0.07091** | **0.00785** |

**The lie by omission:** the tool's headline number (0.07091) implies the network-heavy recommendation is the better choice, with the network channel contributing 66.8% of it. Once discounted for what can actually land before this candidate's authorization runs out, the realizable picture actually FLIPS which channel wins -- apply hours, not network hours, produce more of what can land in time: apply-hours realizable EV = 0.00785 vs network-hours realizable EV = 0.00000. Every number in the tool's original output was correct. The one number that actually mattered for THIS candidate's decision -- which channel converts before the clock runs out -- was never computed by the tool at all.

This is exactly what Chapter 2 names directly but the tool cannot act on: "it cannot know that you are three weeks from a visa deadline, which changes the entire calculus of which channel can close fast enough to matter." The tool has no weeks_remaining term anywhere in its expected-value function -- not because the data wasn't available (it's sitting right there in the candidate record) but because the model was never built to weight EV by time-to-realization. That is the gap: a technically correct number, produced by a tool that had the relevant field in front of it and didn't use it.

## What this means for the tool going forward

This is the single clearest argument for the hard-stop gate (component 7): a tool that cannot reason about time should not be allowed to make an unreviewed recommendation for a candidate whose real constraint IS time. The fix is not a better explanation of the existing number -- it's refusing to let the existing number stand alone for this candidate population, and routing to the human-reviewed gate instead.
