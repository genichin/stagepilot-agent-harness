---
name: stagepilot-agent-harness
description: Use when setting up, refining, or operating the StagePilot multi-agent harness with lead, delivery-runner, dev-impl, and dev-qc roles.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, harness, multi-agent, roles, handoffs, artifacts]
    related_skills: [stagepilot-role-topology, stagepilot-handoffs, stagepilot-doctor-ops]
---

# StagePilot Agent Harness

## Overview

This skill is the umbrella entrypoint for the `stagepilot-agent-harness` operating model. Use it when the task is about shaping, adopting, or operating the four-role delivery topology built around:

- `lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

It compresses the repository's core operating assumptions into agent-facing guidance so Hermes can act consistently without relying on ad-hoc chat memory.

## When to Use

Use this skill when you need to:

- design or refine the StagePilot role topology;
- bootstrap a new project onto the harness;
- align SOUL templates, handoff contracts, and playbooks;
- decide whether a rule belongs in core harness vs project overlay;
- keep repo docs and runtime skills synchronized.

Do not use this skill as a substitute for project-specific implementation instructions. Pair it with a project overlay or delivery skill when work moves into concrete repo changes.

Runtime provisioning is part of applying the harness: the repo's `skills/` catalog includes both core skills and workflow skills such as `confirm-req`, `draft-req`, `run-sdlc`, batch, and release skills. See `references/runtime-skill-export-and-req-approval.md` when workflow skills appear missing or when approval-set behavior is unclear.

## Core operating model

### Role intent

| Role | Owns | Must not own |
|---|---|---|
| `lead` | user communication, prioritization, approval, ambiguity resolution | long-running delivery execution |
| `delivery-runner` | batch grouping inside approved REQ scope, orchestration, sequencing, handovers, escalation, completion reporting | product authority, silent scope changes |
| `dev-impl` | implementation, evidence, local validation | acceptance sign-off |
| `dev-qc` | independent verification, defect surfacing, release confidence | implementation ownership |

### Default operating rules that should stay synchronized with core docs

- After `confirm-req`, the lead may issue `lead -> delivery-runner` kickoff automatically unless the user explicitly asked to hold, defer, batch later, or wait for another confirmation point.
- `confirm-req` approval and delivery slicing are separate decisions: when a confirmed Discovery produced multiple eligible Proposed REQs, the approval gate should evaluate and approve the eligible REQ set together; the runner later groups/splits that Approved set into batches, PRs, and implementation slices.
- The default `lead -> delivery-runner` root transport is a kickoff artifact plus delivery-state record; optional Telegram notification may mirror kickoff for visibility, but notification is not the source of truth.
- The default root launcher (`scripts/lead-launch-runner.sh`) prepares a dedicated git worktree/branch per kickoff and runs `delivery-runner` inside it so lead/human Discovery edits in the main checkout do not contaminate the delivery PR branch.
- Downstream `delivery-runner -> dev-impl` and `delivery-runner -> dev-qc` handoffs are transport-agnostic by default and must not use kanban.
- The default downstream launch path is explicit runner-owned worker execution: `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` and `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>` for short/simple bounded work.
- Worker session management follows the **worker lane** policy: the first impl/QC handoff for a batch/verdict starts a fresh child execution session; a healthy same-handoff continuation may reuse the same lane only when scope/context/acceptance are unchanged and prior concrete progress exists; any error, timeout, blocker, context compaction, no-progress stop, failed-validation rework, new batch, or new root requires a fresh child execution with prior attempt context passed only through explicit artifacts.
- Harness launchers are intended to run in place from the harness repository (often via absolute path) while the current working directory remains the target delivery worktree; helper scripts are resolved relative to the launcher location, while worker `--workdir`, git evidence, and `.stagepilot/worker-progress/` remain tied to the target worktree.
- For non-trivial child work, the runner should prefer supervised checkpoint mode via `--supervised`; extension beyond the first checkpoint requires concrete git/progress evidence, and heartbeat-only output does not qualify.
- Supervised implementation work now requires a runner-prepared implementation-context artifact by default. The context must name target files, edit anchors, service seams, return shape, render insertion point, test assertions, forbidden data exposure, allowed search budget, validation commands, and first-progress expectations before `dev-impl` is launched. If a section is not applicable, the runner must write `N/A` with a reason rather than omit it.
- When such a context passes readiness gate, `dev-impl` must operate in patch-first mode: read the context once, read only exact target snippets, then patch/write or record a concrete blocker. It must not rediscover service seams, return shapes, render insertion points, or test assertions that the context already pins.
- `runner-launch-impl.sh --supervised` enforces an impl readiness gate unless `--no-readiness-gate` is explicitly used for a documented trivial/manual exception.
- `supervise_worker.py` enforces a first-progress deadline and early compaction/read-loop stops before the normal checkpoint when there is no git/progress evidence.
- Runner-owned impl slicing should normally target work that can show concrete progress evidence within about 5 minutes and is likely to close within about 30 minutes, i.e. roughly half of the default supervised checkpoint/runtime budget.
- If an impl slice is unlikely to close within about 30 minutes, split it further before launch unless the work is genuinely atomic and further slicing would create worse context loss or rework.
- If an impl task remains genuinely atomic and still cannot reasonably fit inside the default 60-minute supervised cap, the runner may use an explicit long-run supervised exception with a larger checkpoint/runtime budget, recorded early-progress evidence expectations, and a stated hard cap.
- `scripts/runner-launch-impl.sh` supports `--preset default|stretched|long-run` for the standard supervision budgets; explicit minute flags may still override when a justified nonstandard budget is needed.
- Default unsupervised short calls may remain foreground bounded execution, but supervised impl/QC calls default to background/tmux worker execution so the supervisor outlives invoking terminal timeouts; `--foreground-supervised` is an explicit short-runtime exception.
- Unless a project overlay documents otherwise, a `delivery-runner` should have at most one root kickoff item in active execution globally.
- By default, one root kickoff item maps to one primary pull request. Discovery-level root delivery is the explicit core exception: a confirmed Discovery root may own a batch queue and multiple batch PRs when the kickoff names the Approved/Implemented REQ set and the runner records queue state.
- Early in a PR-bound kickoff, the runner should run publication auth preflight from the isolated delivery worktree before spending substantial impl/QC time. Standard helper: `scripts/check-publication-auth.sh --json`, which checks remote presence, `gh auth status`, `git ls-remote origin`, and `git push --dry-run origin HEAD:refs/heads/<current-branch>`.
- If that preflight fails, the runner should stop early and record a blocked/escalation reason like `publication_auth_missing` or a narrower helper-derived suffix.
- Live post-kickoff Discovery/REQ edits must not flow automatically into the runner delivery branch; importing them requires explicit lead re-handoff or sync direction.
- The runner may open and update that PR during delivery, but the default merge decision belongs to the lead before post-merge `confirm-req-implemented`, during release-stage review.
- The standard delivery path includes an independent `delivery-runner -> dev-qc` handoff before `confirm-batch-verification`.
- Only a low-risk `batch-lite` path may skip explicit QC handoff, and the skip reason plus residual risk must be documented in verification output.
- The default QC retry cap is 3 verdict cycles for the same acceptance scope (initial review plus up to 2 rework/re-review loops).
- If the same QC gap remains unresolved on the 3rd verdict, the runner must escalate to the lead instead of continuing an unbounded loop.
- The canonical required successful completion signal is a lead-visible `done` delivery-state transition on the active root kickoff item plus persisted delivery artifacts/state. `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue, not normal successful completion. A separate completion summary is optional by default.
- Supervised child no-progress stops should be classified as specifically as the evidence allows. Prefer stall subtypes such as `context_compaction_loop`, `read_loop_no_diff`, and `progress_artifact_missing` over a bare generic timeout when the child log / artifact state supports that conclusion. Early-stop result classes include `first_progress_deadline_exceeded`, `early_context_compaction_loop`, and `early_read_loop_no_diff`.

### Harness layering

Use this decision rule:

1. **Core harness** if the rule should apply across projects.
2. **Project overlay** if the rule depends on one codebase, one board, one team, or one delivery chain.
3. **Profile template** if the rule belongs in role behavior at runtime.
4. **Skill text** if the agent needs the rule compressed into execution guidance.

## Required working style

1. Read the relevant files in `docs/`, `roles/`, `handoffs/`, and `projects/<name>/` before changing the model.
2. Keep role boundaries explicit; if a workflow blurs roles, document the exception and who is accountable.
3. Prefer canonical handovers over informal narration.
- 4. Keep blocked/unblocked/completed semantics externally inspectable through artifacts and state.
5. When you update a core operating rule, update the matching skill source in this repository in the same change.

## Common Pitfalls

1. **Treating the skill as the only source of truth.** The repository is authoritative; the skill is a compressed execution interface.
2. **Stuffing project-specific policy into core harness language.** Put those rules under `projects/<name>/` unless they truly generalize.
3. **Letting the runner become a shadow lead.** Runner may choose delivery grouping inside approved scope, but does not redefine scope, priority, or approvals.
4. **Collapsing impl and QC into one worker mindset.** Independent verification is part of the operating model, not optional ceremony.
5. **Updating core docs without updating the corresponding skills/templates.** This creates execution drift between human docs and runtime guidance.
6. **Mistaking partial runtime export for a complete harness install.** The current harness catalog includes workflow skills (`confirm-req`, `draft-req`, `run-sdlc`, batch/release skills) as well as the four core skills. If only the core skills are installed, export the full catalog from the harness repo to every active team profile; do not conclude that `confirm-req` does not exist.
7. **Approving only the first implementation slice.** `confirm-req` approves eligible Proposed REQs as delivery input. Implementation order, dependency sequencing, or small PR slicing belongs after approval and should not leave sibling eligible REQs in Proposed solely because they will be implemented later.
8. **Confusing Discovery root handoff with direct implementation handoff.** It is valid for the lead to hand a confirmed Discovery plus its Approved/Implemented REQ set to `delivery-runner` as a root delivery objective. The runner must then create/select batches and smaller impl/QC handoffs; do not forbid the root Discovery handoff merely because direct `dev-impl` work must be sliced.
9. **Treating one completed batch as a completed Discovery root.** A Discovery root remains open until every remaining Approved REQ in its queue is Implemented, explicitly deferred, or escalated with lead-visible evidence.
10. **Responding to worker stalls by reflexively slicing without root-cause diagnosis.** First identify which layer failed: root orchestration, batch queueing, impl handoff, supervision, or target code/data-source context. If root queueing worked but `dev-impl` produced no diff or final result, say so directly and tighten the implementation-context/service seam instead of presenting generic “smaller slice” as the answer.
11. **Assuming file anchors are an implementation-context.** File anchors alone are not sufficient. The context must pin exact service seams, return shapes, render insertion points, test assertions, and forbidden data exposure/broad-search paths; otherwise the worker can still enter context-compaction/read loops while technically following the handoff. If the runner cannot fill those fields, it must escalate or revise the batch document before launching `dev-impl`.
12. **Letting context-bearing impl handoffs bypass supervision.** If an impl handoff names an implementation-context, launch it through supervised readiness-gated mode or a launcher that auto-enables supervision. A plain chat launch with `implementation_context: not-provided` is a harness regression, not a valid shortcut.

## Verification Checklist

- [ ] The role or workflow change maps cleanly to core harness, profile template, or project overlay.
- [ ] Updated docs and updated skill text still say the same thing.
- [ ] Role boundaries remain explicit for lead, runner, impl, and qc.
- [ ] Handover or state changes are backed by artifacts, not only chat.
- [ ] Root handoff, PR-boundary, merge-ownership, QC-retry, and completion-signal rules still match the current core docs.

## References

- `references/implementation-worker-hardening.md` — implementation-context artifact, readiness gate, first-progress deadline, and early compaction/read-loop stops for `runner -> dev-impl` execution.
- `references/supervised-worker-lifecycle.md` — supervised impl/QC background execution, final-result integrity, interrupted supervisor classification, bounded rework autonomy, and machine-checkable acceptance guidance.
- `references/worker-session-lanes.md` — nuanced runner→impl/QC session policy: fresh first handoff/retry/new batch, artifact-only continuity, and limited same-lane continuation for healthy same-scope follow-up.
- `../../docs/delivery-health.md` — append-only transition evidence, one-command user health verification, and redacted opt-in harness issue reporting.

## Delivery health handoff

- The runner records `kickoff`, `impl-running`, `targeted-validation`/`qc-review`, and `merge-ready` with `record_delivery_transition.py` when writing the corresponding artifact.
- The user runs `verify_delivery_trace.py` once after delivery. A failed result creates only a local redacted report draft; GitHub Issue creation requires an explicit `--publish` request.
- Never include raw worker logs, absolute project paths, credentials, or remote URLs in a harness observation.


### Supervised worker lifecycle integrity

- Runner-owned supervised impl/QC calls should launch in background/tmux mode by default; foreground supervised execution is an explicit short-runtime exception only when the caller timeout is safely above the child max runtime.
- The runner must poll the launcher `exit_file`, worker log, and supervisor `final-result.json`. If `final-result.json` is missing or has `result_class=supervisor_interrupted`, classify it as `supervisor_integrity_failure` / harness execution failure, not as implementation acceptance failure.
- Child logs, diffs, and progress artifacts may be used as secondary evidence, but they do not replace the canonical supervisor final result.
- If a completed implementation has a simple same-scope implementation-context mismatch (for example visible label or CTA wording), the runner may create a fresh bounded rework handoff without lead escalation. Escalate only when the contract itself is ambiguous, scope changes, or governance/product authority is needed.
- Implementation contexts with user-visible copy requirements should include machine-checkable assertions such as required visible strings, forbidden visible strings, and required metric labels before QC handoff.
