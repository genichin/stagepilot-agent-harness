# Model Policy

This document defines the default model-selection policy for the StagePilot harness roles.

## Policy intent

Choose the cheapest model that still reliably supports the role's primary job.

The roles do not need symmetric model quality:

- `lead` needs stronger judgment and communication quality.
- `delivery-runner` needs reliable orchestration at good cost efficiency.
- `dev-impl` needs strong implementation throughput.
- `dev-qc` needs independent verification quality and enough skepticism to catch gaps.

## Recommended baseline mapping

| Role | Recommended model | Why |
|---|---|---|
| `<project>-dev-lead` | `gpt-5.5` | Best used for approval, prioritization, ambiguity handling, and user-facing judgment. |
| `delivery-runner` | `gpt-5.4` | Strong enough for batch grouping, delivery slicing, orchestration, and escalation framing while remaining below the lead tier. |
| `dev-impl` | `gpt-5.3-codex-spark` | Good fit for implementation-heavy work where coding throughput matters more than premium deliberation. |
| `dev-qc` | `gpt-5.4` | Stronger verification and review quality than the cheap runner tier, while still cheaper than the lead model. |

## Default interpretation

Treat the table above as the harness default unless a project overlay explicitly says otherwise.

This means the baseline operating recommendation is:

- `lead` → quality-first
- `delivery-runner` → second-tier delivery planning plus orchestration
- `dev-impl` → coding throughput
- `dev-qc` → verification confidence

## Selection heuristics by role

### `<project>-dev-lead`
Choose the highest-quality generally available model when the role is expected to:

- arbitrate ambiguity
- make approval recommendations
- summarize tradeoffs to the user
- absorb cross-cutting project context

Degrade only when cost pressure is more important than decision quality.

### `delivery-runner`
Prefer a model one step below the lead because the role now:

- chooses batch grouping and delivery slicing inside approved scope
- routes work
- tracks state
- performs handoffs
- escalates when authority is missing
- reports completion status

This role should be strong enough to make non-trivial delivery-planning judgments, but it still should not outrank the lead on product authority or approval quality.

### `dev-impl`
Prefer a coding-oriented model or the best implementation-throughput option available. Prioritize:

- code editing quality
- tool-use reliability
- ability to stay within bounded scope
- strong execution speed per dollar

### `dev-qc`
Prefer a model one tier stronger than the runner when possible. QC benefits from:

- skeptical reading
- mismatch detection
- evidence review quality
- clearer residual-risk reporting

Avoid using the weakest/cheapest model for QC if it materially reduces defect detection.

## Override conditions

Change the baseline mapping only when one of these is true:

1. A project requires a provider that the baseline model is unavailable on.
2. A role needs access to a model-specific capability not offered by the default.
3. Cost constraints require temporary downshifting.
4. A role is consistently overloaded with harder tasks than the topology originally intended.
5. Benchmarking or delivery evidence shows a different model is materially better for that role.

When overriding, document the exception in `projects/<name>/` or the profile bootstrap notes.

## Current live example

The current Hermes profile setup on this machine matches the intended policy:

| Profile | Observed model |
|---|---|
| `trex-dev-lead` | `gpt-5.5` |
| `delivery-runner` | `gpt-5.4` |
| `dev-impl` | `gpt-5.3-codex-spark` |
| `dev-qc` | `gpt-5.4` |

This is an example of the policy in practice, not a requirement that every project must use exactly the same provider/model names forever.

## Verification checklist

- [ ] The lead profile still uses the highest-judgment model among the active role set.
- [ ] The runner uses a second-tier model strong enough for delivery planning inside approved scope.
- [ ] The impl worker uses a coding-effective model.
- [ ] The QC worker is not weaker than the runner in ways that harm verification quality.
- [ ] Any deviation from the baseline mapping is documented in a project overlay or bootstrap note.
