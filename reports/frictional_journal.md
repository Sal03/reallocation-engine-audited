# Frictional Journal

*Note: the prediction below was written after the build was complete, not
logged contemporaneously before building began as the assignment specifies.
It is reconstructed from what we can verify was already under discussion
before any code existed. Both required parts of this journal (prediction,
reflection) are present.*

---

## Before (the required prediction, present -- reconstructed rather than contemporaneously logged, dated 2026-07-26)

At the point the domain was locked in (job-search time reallocation, anchored
to Chapters 2 and 15) and the bias-audit design was chosen (Option A,
network-access as the protected axis, synthetic candidate profiles), before
any code had been written, here is what we can honestly say was already
anticipated, because it is visible in the conversation itself:

**Expected hardest failure:** getting a real, quantitative bias audit without
real demographic outcome data. This was flagged explicitly before any code
existed -- the domain-selection discussion named "you don't have real
applicant demographic data" as the central risk of this whole component, and
the decision to use a synthetic population with a stated protected axis
(network_group) was made specifically to route around that gap. We expected
this to be the single hardest thing to get right, and expected it to require
an honest caveat about synthetic data rather than a clean result.

**Expected causal validity:** we expected the causal-reasoning component to
be comparatively strong on paper (the book's own worked example already
walks something like Pearl's three rungs without naming them that way) but
expected the tool itself to land on "correlation dressed as causation" as
its honest verdict, because the underlying book statistics (54% hires via
connections, referral vs. cold conversion rates) are population-level,
observational figures being applied as if they were individually-calibrated
causal rates, and we expected to have to name that plainly rather than claim
validity.

**Confidence:** we do not have an honestly reconstructable numeric
confidence value from before building began -- no number was stated at that
point in the conversation, and assigning one now would be exactly the kind
of retroactive precision this journal is supposed to prevent. What we can
say is that the domain-selection discussion treated the bias-audit data gap
as a known, named risk rather than a surprise, which implies moderate-to-low
confidence (rough estimate, stated as a reconstruction: 40-50%) that the
bias audit specifically would produce a clean, defensible result without
hitting a real problem along the way.

**What we did not anticipate at all, because nothing in the pre-build
conversation touches on it:** the calibration overshoot, the
population-dependence of the calibration boundary, the C0032 timing-blind-spot
critique, the Hard Stop 2 100%-fire-rate finding, and the corrupted-input
result fooling the confidence gate rather than triggering it. These were
not on our radar before building started, at any confidence level, because
we had not yet built the mechanism that would surface them.

---

## After (the required reflection, present) -- written 2026-07-26 immediately following the build

**What actually happened:** the predicted hardest failure (bias audit without
real demographic data) was real but turned out to be manageable -- we solved
it with a defensible synthetic design and an explicit caveat, and it did not
end up being the most interesting or most difficult finding in the project.
The genuinely hardest, most valuable findings were things we did not predict
at all:

1. The outcome policy's first calibration attempt overshot the fairness gap
   it was meant to close (component 3).
2. That overshoot boundary turned out to be population-dependent -- an
   unrelated field addition shifted it by roughly 6x with zero change to the
   actual mechanism (component 6).
3. The explainability critique (component 4) and the causal counterfactual
   (component 5) independently converged on the same conclusion for
   candidate C0032 -- that the tool's own recommendation was the worse
   choice for a time-constrained candidate -- arrived at through two
   completely different methods, which we did not orchestrate in advance.
4. Hard Stop 2 fired on 100% of the population, which is a real design
   failure in the gate itself, not a tuning inconvenience.
5. A deliberate data-corruption test (changing one already-gated candidate's
   conversion rate) did not just produce an obviously wrong number -- it
   made the tool's own confidence gate suppress its flag for that
   candidate, the opposite of what a defensive system should do.

**Where the prediction was wrong:** we correctly identified the bias-audit
data problem as A risk, but we substantially underestimated how much of the
real difficulty in this project would come from the ALLOCATION mechanism's
own fragility (calibration overshoot and population-dependence) rather than
from the data-availability problem we were worried about going in. We were
looking in the right general area (component 3) but focused on the wrong
specific failure mode within it.

**What this says about our calibration:** we were reasonably well-calibrated
about WHERE a problem was likely to live (the bias audit, given the
synthetic-data constraint) but poorly calibrated about WHAT KIND of problem
it would turn out to be. The actual failures were mechanism-level
(calibration constants, confidence-gate logic) rather than data-level, and
none of them were things we could have anticipated without actually building
and running the tool -- which is itself consistent with the assignment's
premise: validation is Tier 4/5 work that has to happen against a real,
running system, not something that can be fully reasoned out in advance on
paper. The gap between our reconstructed "before" and the actual "after" is,
honestly, the most useful evidence in this journal that building first and
reflecting after is not just a compliance step -- it produced findings that
advance planning would not have surfaced.

---

## A genuine contemporaneous probe (added after TA feedback)

The disclosure above covers the original build. Per TA feedback on a prior
assignment (2026-07-27), which offered the chance to run one real,
timestamped before/after cycle rather than rely solely on a reconstruction:
the following is written **before** running the probe described, with a
real timestamp, and the reflection was added immediately after actually
running it -- not reconstructed afterward.

### Before -- logged 2026-07-27, 20:25 UTC, before running anything below

**The probe:** regenerate the candidate population with a different random
seed (the shipped pipeline uses seed 7375; this probe uses a different
seed, in a scratch location that does not touch the shipped `data/`
files), then re-run the calibration search and the delegation gate against
that new population.

**Prediction:** based on what we already found once (the calibration
boundary moved from ~0.032 to ~0.1925 -- roughly 6x -- purely from adding
one unrelated field, which shifted the random draw sequence), we predict
the boundary will move AGAIN with a new seed, and by a similarly large
margin (our confidence: roughly 60%, since we've only seen this happen
once and don't know if 6x is typical or a fluke of that particular
comparison). We predict Hard Stop 2's fire rate will stay close to 100%
regardless of seed, since that failure is structural (small single-week
expected values producing wide relative intervals) rather than dependent
on the specific random draw. We are NOT confident about the direction the
boundary will move (higher or lower than 0.1925) -- we have no basis to
predict that, and we are stating that honestly rather than guessing and
calling it a prediction.

### After -- logged 2026-07-27, immediately following the probe run

**What we actually ran:** regenerated the population with seed 90210 (a
different seed from the shipped pipeline's 7375), confirmed the output
genuinely differs row-by-row from the shipped data (verified by diffing the
first rows before proceeding -- our first attempt at this accidentally
re-seeded before the module's own `random.seed(7375)` call overwrote it,
producing an identical population; we caught that by comparing output
files and fixed the seeding order before treating any result as real).

**What actually happened, compared to the prediction:**

The prediction that the boundary would move again, by a large margin, was
correct -- but not in the way we expected. We predicted a large NEW
threshold, somewhere else on the positive number line. What we actually
got: the binary search returned a boundary of **~0.0000** -- meaning even
with ZERO correction applied (the plain parity policy), the "low" network
group already has a HIGHER mean expected value (0.09827) than the "high"
group (0.09334) in this specific population draw. There is no gap to
correct in this sample; if anything, applying ANY positive shift toward
networking for the low group would immediately start overshooting, from
the very first unit of correction, because the group that's supposed to be
disadvantaged already comes out ahead by chance.

The second half of the prediction -- that Hard Stop 2's fire rate would
stay close to 100% regardless of seed, since that failure is structural --
was confirmed exactly: **213/213** fired again, identical to the shipped
population.

**Where the prediction was wrong, and what that reveals:** we anticipated
"the correction needed will vary in size." We did not anticipate "the
correction needed could vanish, or reverse, entirely from ordinary
sampling noise in which group happens to draw more total hours." This is a
more serious finding than the original 6x-boundary-swing, because it means
`calibrate_shift.py`'s search isn't just finding a different-sized fix each
time -- on some population draws, there may be no real disparity to fix at
all, and the tool has no way to distinguish "the gap closed because the
correction worked" from "there was never a gap in this sample to begin
with." A calibration script that reports a boundary without also reporting
whether a real gap existed at factor=0 is missing a check we now know it
needs.

**What this says about our calibration as a research process, not just
about the tool:** the first version of this finding (the 6x boundary
swing) could plausibly have been read as one unlucky fluke. Running a
second, genuinely fresh probe and finding an even stranger result --
the disadvantaged group having a natural, chance advantage in this
particular draw -- turns "this happened once" into "this is a real
property of small synthetic samples that any deployment of this tool
would need to check for, every time, not something we can calibrate once
and trust." That is a materially stronger and more honest conclusion than
either the original build or the first Frictional Journal reflection
reached, and it only exists because we ran a real, un-reconstructed
before/after cycle instead of reasoning about it in the abstract.
