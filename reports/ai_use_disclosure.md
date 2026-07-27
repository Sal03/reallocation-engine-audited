# AI Use Disclosure

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
session. Some corrections were self-initiated by Claude during the build --
for example, catching and rewriting the bias-audit report when a hardcoded
narrative about the overshoot became false after the population was
regenerated, and catching an imprecise claim in the adversarial-robustness
gaming scenario (the first draft understated what it actually takes to
game the system) -- and I reviewed each as it was presented rather than
requesting them in advance. The one substantive change that was mine, not
Claude's, was the explicit constraint on the overshoot tradeoff described
below: Claude presented keeping vs. fixing the overshoot as an either/or
choice, and I changed that framing by requiring both.

**What the AI could not do:**

When the outcome policy's first calibration attempt overshot the bias-audit
fairness gap it was meant to close (component 3), Claude presented two
options: keep the overshoot as the documented "surprising failure" the
assignment rewards (Option B), or quietly recalibrate and lose the finding
(Option A). Claude framed this as an either/or choice. My actual answer --
"we can keep this move, only if it doesn't harm the tool implementation" --
was neither option as presented. It was a values-based tradeoff Claude could
not resolve on its own: I wanted the pedagogical honesty of a documented
real failure AND a tool that actually works as a deliverable, and I was not
willing to trade either one away for the other. That constraint reflects my
own priority about what this submission needs to be (both intellectually
honest and functionally sound), not something derivable from the technical
facts of the overshoot itself -- Claude could tell me the overshoot happened
and could tell me how to fix it, but could not tell me how much I should be
willing to sacrifice tool correctness for a better story, or vice versa.
That judgment was mine to make, and it produced the actual design we shipped
with (the naive version kept, unedited, alongside a properly calibrated
version) -- a synthesis Claude had not itself proposed as an option until I
asked for it.
