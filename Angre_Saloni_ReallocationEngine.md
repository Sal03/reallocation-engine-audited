# The Reallocation Engine, Audited
## A Job-Search Time Allocator — Validation Report

**Author:** Saloni Angre
**Course:** INFO 7375 — Computational Skepticism for AI
**Domain:** People/time reallocation for an international job search on OPT
**Anchor:** *The Reallocation Engine*, Chapter 2 ("The Reallocation Principle")
and Chapter 15 ("The Pipeline Tracker and the Skip Rate")
**Repo:** see `README.md` for run instructions; all numbers below are
reproduced live in `reports/worked_run.md`

---

## What this tool does, in one sentence

**Objective:** reallocate a candidate's weekly job-search hours across
Apply / Network / Portfolio to maximize expected weekly hire-contribution,
given their current network size.

**What that objective leaves out** (stated up front, not discovered later):
role fit, company sponsorship history, posting liveness, geographic
constraints, the psychological cost of a given schedule, and — critically,
as component 4 below demonstrates — *time to realization*. A higher expected
value is not the same thing as a faster one, and this tool's core objective
function cannot see the difference on its own.

---

## 1. The Working Reallocation Tool (12 pts)

`src/allocator.py` ingests a gated candidate population and outputs a
concrete hour-by-hour split (apply / network / portfolio) plus an explicit
90% uncertainty interval on the resulting expected weekly hires
contribution — not a bare point estimate. Two policies are implemented:
**parity** (Chapter 2's default 3-3-2-style split, identical for everyone)
and **outcome** (shifts hours toward networking in proportion to a
candidate's network deficit, calibrated — see component 6).

Example, real run output:
```
Candidate C0001 | low network, 2 live conversations
  parity : apply=9.25h, network=13.88h, portfolio=13.88h | EV=0.11794 [0.0, 0.67809]
  outcome: apply=6.59h, network=19.2h,  portfolio=11.21h | EV=0.12593 [0.0, 0.70346]
```
Full detail: `reports/worked_run.md`.

---

## 2. Data Validation & the GIGO Gate (10 pts)

**Hidden assumptions named:** fields are sampled independently (real
candidates almost certainly have correlated network size, search duration,
and portfolio output); network_group buckets are balanced 1/3-1/3-1/3 by
construction (real populations skew toward "low"); conversion rates are
treated as fixed population-wide constants.

**The gate:** every candidate must have a unique ID, a network_group/
live_conversations pairing that's internally consistent, hours within a
plausible range, and non-stale conversion constants.

**Result:** of 240 generated candidates (with deliberately injected
problems), **213 passed, 27 were rejected** — 9 bucket mismatches, 7 missing
fields, 7 out-of-range values, ~4 duplicate IDs, ~4 stale conversion-rate
rows. Rejected rows are excluded entirely, never imputed. Full detail:
`reports/gigo_gate_report.md`.

---

## 3. Bias Audit (10 pts)

**Who is advantaged/starved, and where it enters:** Chapter 2's own
mechanism — referrals convert at roughly 15x the rate of cold applications,
and ~54% of hires come through personal connections — means candidates
without an existing US professional network (international students with
no prior US employment, the population this tool is built for) start
structurally behind, before any bias enters the model at all.

**Two fairness definitions in tension, measured, not asserted:**
- **Demographic parity** (same allocation for everyone) — the parity policy.
- **Equalized expected-outcome** (comparable EV across groups, even with
  different allocations) — the outcome policy.

**Result:** the outcome policy closes **93.5%** of the low-vs-high-network
EV gap (0.00713 → 0.00046), at the cost of a larger allocation gap (0.84h →
3.61h). **Neither policy minimizes both gaps at once** — this is the actual,
unavoidable tradeoff, reported rather than hidden.

**The most valuable finding in this component wasn't the tradeoff — it was
a mistake we caught:** our first calibration attempt (a round, arbitrary 15%
hour-shift) overshot the gap on its first test population, flipping which
group came out ahead. We fixed it — but then discovered, on a second
population draw from the *same* generator, that the overshoot boundary had
moved by roughly **6x** (from ~0.032 to ~0.1925) due to an unrelated field
addition changing the random draw sequence. That population-dependence
finding is developed fully in component 6. Full detail:
`reports/bias_audit_report.md`.

---

## 4. Explainability & Its Critique (10 pts)

**Method:** exact additive contribution decomposition + counterfactual
explainer, not SHAP/LIME — justified because the allocator is a known,
closed-form additive function; an exact decomposition IS the Shapley answer
here, and a sampling approximation would add noise, not insight.

**The critique — a specific, named case, not a category claim:** candidate
**C0032** (visa-constrained, **2 weeks remaining** on authorization). The
tool's raw recommendation reports a total expected-hires contribution with
68.8% of it coming from the network-hour channel — a completely accurate
number, arithmetically. But the model has no concept of *time*. Applying an
illustrative lag assumption (referral-based hires take longer to convert
than cold applications, since they route through an introduction, a
conversation, and a referral before an interview process starts), the
*realizable* picture — what can actually land before this candidate's
authorization runs out — **flips which channel wins entirely**: apply-hours
realizable EV (0.00785) exceeds network-hours realizable EV (0.00000).
Every number in the original output was correct. The one number that
mattered for this candidate's actual decision was never computed at all.
Full detail: `reports/explainability_report.md`.

---

## 5. Causal & Counterfactual Reasoning — Pearl's Three Rungs (15 pts)

**Rung 1 (Observation):** under the parity policy, the correlation between
live_conversations and expected outcome is **r=0.1493** — which turns out to
be mathematically *identical* to the pure sampling-noise floor between two
independently-drawn fields (hours and live_conversations, r=0.1493, to full
precision). Our own synthetic model does not contain an organic Rung-1
correlation at all; it only appears once we deliberately build an
allocation rule that responds to network size. We import Chapter 2's
correlation as an assumption; we do not derive it.

**Rung 2 (Intervention):** named confounders that could make the
correlation vanish under a real intervention: prior social capital/
professional experience (may raise conversion rate itself, not just
conversation count); reverse causation (momentum toward an offer might
drive more networking, not the other way around); sector/company-tier
confounds.

**Rung 3 (Counterfactual):** for candidate C0032's actual week, we compare
the tool's real recommendation against the counterfactual parity split.
**On raw EV, the actual recommendation wins. On realizable EV, the
counterfactual parity split wins** — independently confirming component 4's
finding through a completely different method (counterfactual comparison
rather than decomposition).

**Plain verdict:** **yes, this engine mostly reallocates on correlation
dressed as causation.** It encodes Chapter 2's population-level statistic as
an individually-applicable causal rate, without confounder adjustment or
experimental validation — and the book's own footnotes mark these same
figures `[^verify]`, meaning we built our core mechanism on a number its own
source never claimed was verified. Full detail:
`reports/causal_reasoning_report.md`.

---

## 6. Adversarial Robustness & Fragility (8 pts)

**Perturbation 1 — stale calibration under ordinary resampling (the
strongest finding in this project).** A calibration constant tuned against
one population sample doesn't survive an incidental resample from the exact
same generator. Reusing the old, stale constant on the new population closes
only **15.6%** of the fairness gap instead of **93.5%** — silently, with no
error thrown and no sign flip to signal the problem.

**Perturbation 2 — a gameable, unverified self-reported input.**
`live_conversations` is self-reported with no external verification. A
high-network candidate who relabels themselves consistently (both
`network_group` and `live_conversations`, since the GIGO gate only checks
that the two agree with each other, not that either is true) gains **+5.04
recommended network hours and +8.5% reported expected value** for zero
verification cost.

**Perturbation 3 — a second, genuinely fresh population draw can erase the
disparity entirely, added after running a real Frictional Journal probe.**
On a completely independent resample (a different seed, not the one
shipped), the "low" network group already has a *higher* mean EV than the
"high" group under plain parity — before any correction is applied at all.
`calibrate_shift.py` cannot distinguish "no correction needed because the
gap never existed in this sample" from "the correction worked perfectly" —
those are different claims, and the current tooling conflates them. This is
a more serious version of Perturbation 1: it's not just that a calibrated
constant goes stale, it's that some population draws may not have a real
disparity to calibrate against in the first place. Full detail:
`reports/frictional_journal.md` (the logged prediction) and
`src/frictional_probe.py` (the reproducible script).

---

## 7. Delegation Map + the Hard-Stop Gate (10 pts)

Full delegation map (what the tool decides vs. what a human decides, per
component) is in `src/delegation_gate.py`'s module docstring. Three hard
stops are implemented and tested, not just specified:

| Hard stop | Condition | Response | Resolver |
|---|---|---|---|
| 1. Time-critical | visa_constrained AND weeks_remaining ≤ 4 | **BLOCK** | Candidate/advisor reviews realizable-EV table first |
| 2. Low-confidence | 90% interval width > 1.5x point estimate | **FLAG** | Candidate sees the recommendation, visibly labeled |
| 3. Stale calibration | population changed since last calibration | **BLOCK** | Operator must re-run `calibrate_shift.py`; parity policy remains available |

**Real results:** Hard Stop 1 fires for **17 of 213** candidates, including
C0032 — directly blocking the exact recommendation components 4 and 5 both
proved was misleading for them. Hard Stop 3 correctly blocks on a stale
fingerprint and clears after recalibration.

**An honest failure we're not hiding:** Hard Stop 2 fires for **213 of 213**
candidates (100%). A gate that fires on everyone isn't discriminating
anything — it's a permanent warning label people learn to ignore. The root
cause is structural (single-week EVs are small, so intervals are wide
relative to their mean regardless of estimate quality), and the real fix is
comparing candidates to their peers rather than to an absolute ratio — a
limitation named plainly rather than tuned away to look better. Full
detail: `reports/delegation_gate_report.md`.

---

## Uncertainty Communication

![Point estimate and 90% interval by candidate](reports/uncertainty_chart.png)

**The plain sentence:** for a typical candidate, the tool estimates roughly
0.1 expected hires per week — but the honest range, given how few
applications and conversations a single week produces, is roughly 0 to 0.7.
Treat the number as *plausible, not precise*: useful for comparing two
allocations against each other, not for predicting a specific week's
outcome.

**Where I would not trust this tool:** every single candidate in this run
(213/213) has an interval wider than 1.5x its own point estimate (Hard Stop
2, above). Do not trust this tool's point estimate on its own, for any
candidate, as a prediction of what will actually happen in a given week.
Full detail: `reports/uncertainty_communication.md`.

---

## What went further than the core rubric (for the quality score)

1. The population-dependent calibration boundary (~6x swing from an
   incidental resample) — an unplanned discovery, investigated rather than
   dismissed as noise, and then confirmed a second time with a genuine,
   pre-registered Frictional Journal probe (a fresh, un-reconstructed
   before/after cycle) that turned up an even stronger version of the same
   problem: some population draws have no real fairness gap to correct at
   all, and the calibration script currently cannot tell that apart from
   "the fix worked."
2. Two independent methods (explainability's decomposition, causal
   reasoning's counterfactual) converging on the same conclusion for the
   same candidate, without being orchestrated to do so.
3. Naming Hard Stop 2's 100% fire rate as a design failure rather than
   quietly picking a threshold that produces a better-looking number.
4. A real deliberate break attempt (corrupting an already-gated value) that
   surfaced a worse-than-expected finding: corrupted input suppressed a
   safety flag instead of triggering one.

---

## Required gates

- **Frictional Journal:** `reports/frictional_journal.md` — both required
  parts (prediction, reflection) are present. The original prediction was
  written after the build (disclosed as such), but a real, contemporaneous
  before/after probe was added afterward (a genuine timestamped prediction,
  run, and reflection), which turned up a real finding — see component 6.
- **Worked Run + Attestation:** `reports/worked_run.md` — verbatim commands
  and output, verified-vs-inferred split, and a real deliberate break
  attempt with results that surprised us.

## AI Use Disclosure

**Tool(s) used:** Claude (Sonnet, claude.ai chat interface, with code execution).

**Portions assisted:** All source code (`src/*.py`), all generated reports
(`reports/*.md`), the README, and the drafting of this disclosure and the
Frictional Journal were produced through conversation with Claude. The
domain choice, the decision to reuse the H-1B/job-search context, the choice
of bias-audit design (Option A, network-access as the protected axis), and
the decision of which findings to keep versus fix (e.g., keeping the
overshoot policy in the codebase rather than deleting it) were made by the
student, in response to options and tradeoffs Claude presented.

**How used:** Claude wrote essentially all of the Python code and report
text in this repository, iteratively, one rubric component at a time, in
dependency order rather than rubric order. Each component's code was run
immediately after being written, and its actual output (not a description of
expected output) was inspected before moving to the next component.

**What I changed:** I did not hand-edit the generated code myself in this
session. Some corrections were self-initiated by Claude during the build —
for example, catching and rewriting the bias-audit report when a hardcoded
narrative about the overshoot became false after the population was
regenerated, and catching an imprecise claim in the adversarial-robustness
gaming scenario (the first draft understated what it actually takes to
game the system) — and I reviewed each as it was presented rather than
requesting them in advance. The one substantive change that was mine, not
Claude's, was the explicit constraint on the overshoot tradeoff described
below: Claude presented keeping vs. fixing the overshoot as an either/or
choice, and I changed that framing by requiring both.

**What the AI could not do:**

When the outcome policy's first calibration attempt overshot the bias-audit
fairness gap it was meant to close (component 3), Claude presented two
options: keep the overshoot as the documented "surprising failure" the
assignment rewards (Option B), or quietly recalibrate and lose the finding
(Option A). Claude framed this as an either/or choice. My actual answer —
"we can keep this move, only if it doesn't harm the tool implementation" —
was neither option as presented. It was a values-based tradeoff Claude could
not resolve on its own: I wanted the pedagogical honesty of a documented
real failure AND a tool that actually works as a deliverable, and I was not
willing to trade either one away for the other. That constraint reflects my
own priority about what this submission needs to be (both intellectually
honest and functionally sound), not something derivable from the technical
facts of the overshoot itself — Claude could tell me the overshoot happened
and could tell me how to fix it, but could not tell me how much I should be
willing to sacrifice tool correctness for a better story, or vice versa.
That judgment was mine to make, and it produced the actual design we shipped
with (the naive version kept, unedited, alongside a properly calibrated
version) — a synthesis Claude had not itself proposed as an option until I
asked for it.

(Full copy also kept as a standalone file at `reports/ai_use_disclosure.md`.)

---

## What this tool cannot do (the honest summary)

It cannot verify its own core statistics (inherited, unverified, from the
book's own `[^verify]`-flagged figures). It cannot distinguish correlation
from causation in its own recommendation. It cannot detect a stale
calibration constant without a human re-running the calibration script. It
cannot verify a self-reported input. It cannot reason about time, which is
the single most consequential blind spot found in this entire project. And
its own confidence gate can be fooled by exactly the kind of corrupted data
it should be most defensive against. Every one of these limits is named
here because finding them — not hiding them — is what this assignment
actually grades.
