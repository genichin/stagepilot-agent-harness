# stagepilot-agent-harness

> **Delivery profiles:** [fast / standard / guarded](docs/delivery-profiles.md) make orchestration proportional to change risk. This repository defines the source harness only; it does not roll changes into active Hermes profiles or already-running sessions.

A reusable operating harness for StagePilot-style multi-agent delivery using four core roles:

- `lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

This repository standardizes role boundaries, handover contracts, state transitions, notification hooks, profile templates, **and skill sources** so the operating model can be reused across projects instead of living only in chat context.

## Goals

- Keep the **lead** user-facing and decision-oriented.
- Keep the **delivery-runner** responsible for orchestration across the delivery chain.
- Keep **implementation** and **QC** as distinct worker roles.
- Make handovers explicit, reviewable, and reusable.
- Treat persisted artifacts/state as the canonical operational signals rather than informal chat memory.
- Use a small but explicit root delivery-state record plus typed escalation/completion artifacts so runner status can be read mechanically, not only inferred from prose.
- Keep docs, templates, SOUL baselines, and Hermes skills under a single source of truth.

## Repository Layout

```text
stagepilot-agent-harness/
  docs/                    Architecture and operating model docs
  roles/                   Role charters and boundaries
  handoffs/                Required handover contracts and examples
  templates/               Kickoff / escalation / completion templates
  skills/                  In-repo Hermes skill sources for this harness
  profiles/templates/      Baseline SOUL.md templates by role
  scripts/                 Harness helper scripts
  playbooks/               Operational runbooks
  verification/            Checklists for role and handover quality
  projects/trex/           TREX-specific overlay and examples
```

## Core Model

### Roles

| Role | Primary purpose | Must avoid |
|---|---|---|
| `lead` | Discovery drafting, Discovery approval, REQ drafting, REQ approval, prioritization, user collaboration | Getting trapped in long-running delivery execution |
| `delivery-runner` | Choose delivery grouping inside approved REQ scope and orchestrate the delivery chain after approved Discovery and approved REQ handoff | Acting as product owner or silently changing scope |
| `dev-impl` | Implement approved scope and provide concrete evidence | Declaring acceptance by itself |
| `dev-qc` | Independently verify acceptance, gaps, and regressions | Becoming a rubber stamp for implementation |

### Canonical handovers

Use these as the normative defaults:

- Kanban is forbidden in this harness. Do not use board/card transport for kickoff, queueing, implementation, QC, or completion.
- `lead` owns Discovery drafting/approval and REQ drafting/approval.
- `delivery-runner` starts after approved Discovery + approved REQ handoff and owns delivery orchestration within that approved scope, including default batch grouping and `draft-batch` execution unless a true governance escalation sends the decision back to `lead`.
- A confirmed Discovery may be handed to `delivery-runner` as a **Discovery-level root delivery objective** once the related eligible REQs have passed `confirm-req`. In that mode, the runner consumes the Discovery plus its Approved/Implemented REQ set, creates or adopts a batch queue, and executes the queue one batch at a time.
- After `confirm-req`, the lead may auto-kick off delivery unless the user explicitly asked to hold, defer, batch later, or wait.
- Default root transport is an explicit kickoff artifact plus a small delivery-state record; optional Telegram notification may mirror it for visibility, but notification is not the source of truth.
- `docs/state-machine.md` is the canonical schema reference for the root delivery-state record and escalation artifact fields.
- Artifact creation alone does not start execution. The lead explicitly launches `delivery-runner`. The default launcher path prepares an isolated per-kickoff git worktree/branch and starts a detached background `tmux` session. A `fast` kickoff may instead use foreground/current-workdir only for an exclusive local/reversible checkout and only with both `--allow-fast-degraded` and `--ack-fast-shared-workdir-risk`; root state records all selected fallbacks and residual risk.
- Downstream impl/QC handoffs are transport-agnostic and must not use kanban.
- Runner-owned impl slicing should normally target work that can show concrete progress evidence within about 5 minutes and is likely to close within about 30 minutes, i.e. roughly half of the default supervised checkpoint/runtime budget.
- If an impl slice is unlikely to close within about 30 minutes, the runner should split it further before launch unless the work is genuinely atomic and further slicing would create worse context loss or rework.
- If an impl task remains genuinely atomic and still cannot reasonably fit inside the default 60-minute supervised cap, the runner may use an explicit long-run supervised exception with a larger checkpoint/runtime budget, recorded early-progress evidence expectations, and a stated hard cap.
- A default root kickoff is considered claimed only when the delivery state names `delivery-runner` as owner target, moves from `ready` to canonical `running`, and is acknowledged by the runner. Legacy `claimed` / `in_progress` records should be read as `running` and normalized on the next write.
- Default runner concurrency is one root kickoff item in active execution globally; additional kickoff items remain queued in `ready`.
- One root kickoff item maps to one primary PR by default. Exception: an explicitly declared Discovery-level root delivery may own a batch queue; each queued batch may produce its own PR or a grouped PR according to the runner's batch plan, but the root kickoff is not `done` until all queued/remaining Approved REQs are Implemented, explicitly deferred, or escalated with lead-visible evidence.
- The lead/human Discovery + REQ workspace and the runner delivery PR workspace must be isolated by default: lead/human edits stay in the main checkout, while runner delivery work happens in a dedicated git worktree/branch prepared for that kickoff.
- For PR-bound `guarded` delivery, run publication auth preflight from the isolated delivery worktree before substantial impl/QC time. `fast` and `standard` do not make this a default gate; escalate to `guarded` when publication or release-sensitive risk enters scope. The standard helper is `scripts/check-publication-auth.sh --json`, which uses only an explicit `STAGEPILOT_GH_HOME` override or the current `HOME`, checks `git remote get-url origin`, `gh auth status`, `git ls-remote origin`, and `git push --dry-run origin HEAD:refs/heads/<current-branch>`, and emits no raw auth command output. Failures surface as explicit `publication_auth_missing...` blocked/escalation reasons.
- Core harness fixes the isolation rule and a local default only: unless a project overlay/bootstrap convention says otherwise, the default runner worktree root is repo-local `.worktrees/`.
- Core harness does **not** fix the umbrella folder layout for every project (for example `repos/`, shared mono-workspaces, or external centralized worktree roots). Those parent-directory conventions belong in project adoption / overlay guidance.
- Live Discovery/REQ edits made after kickoff must not flow automatically into the runner PR branch; they require an explicit re-handoff or sync decision from the lead.
- The standard path includes `delivery-runner -> dev-qc` before `confirm-batch-verification`.
- QC retry budget is 3 verdict cycles for the same acceptance scope; the 3rd unresolved verdict escalates to `lead`.
- Required successful completion signal: delivery state reaches lead-visible `done` with persisted delivery artifacts. Separate completion summary is optional by default. `archived` is reserved for terminal historical closure of a root kickoff that should not continue, for example superseded or withdrawn work, and is not the normal successful delivery completion signal.

- `lead -> delivery-runner`
- `delivery-runner -> dev-impl`
- `delivery-runner -> dev-qc`
- `delivery-runner -> lead` escalation
- `delivery-runner -> lead` completion summary (optional)

### Default handoff chain

| Step | Handoff | Default meaning |
|---|---|---|
| 1 | `lead -> delivery-runner` | Approved Discovery + Approved REQ handoff starts delivery orchestration through a kickoff artifact + delivery-state record, then the lead explicitly launches the runner in the background via `scripts/lead-launch-runner.sh`. For a Discovery-level root, the handoff names the confirmed Discovery, already Implemented REQs, remaining Approved REQs, and the runner-owned batch-queue obligation. The launcher prepares a dedicated git worktree/branch for the kickoff so delivery PR work is isolated from ongoing lead/human Discovery edits in the main checkout. After the Hermes runner process exits, the wrapper checks the delivery-state record and leaves inspectable `exit_file`/`status_file` output; root delivery only exits cleanly once the state reaches lead-visible `done`, explicit `blocked`, or terminal `archived` closure. Optional Telegram notification may mirror the kickoff. |
| 2 | `delivery-runner -> dev-impl` | Runner explicitly launches a worker lane with `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` for short/simple bounded work; the first impl handoff for a batch starts fresh, while healthy same-handoff continuation may reuse the lane under the worker-lane policy, and should prefer `scripts/runner-launch-impl.sh --supervised --implementation-context <context> ...` for non-trivial implementation handoffs. Supervised impl now requires a runner-prepared implementation-context artifact by default: target files, edit anchors, service seams, return shape, render insertion point, test assertions, forbidden data exposure, allowed search budget, validation commands, and first-progress expectations. Once the readiness gate passes, dev-impl must use patch-first execution: read exact target snippets, then edit/write or record a concrete blocker rather than rediscovering the system. Before burning substantial impl time on a PR-bound kickoff, the runner should run publication auth preflight in the delivery worktree so missing `gh`/push capability becomes an early blocked escalation rather than an end-of-run surprise. Impl slices should normally be chosen so concrete progress evidence can appear within about 5 minutes and completion is likely within about 30 minutes; larger work should usually be split further, with only explicit long-run supervised exceptions allowed past the default 60-minute cap. Supervised mode checkpoints `.stagepilot/worker-progress/` plus git evidence, extends only on concrete progress, and stops early on first-progress deadline misses, context compaction loops, or read/search loops without diff/progress evidence. |
| 3 | `delivery-runner -> dev-qc` | Runner explicitly launches a worker lane with `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>` for short/simple bounded review work; the first QC handoff for a verification target starts fresh, while same-verdict healthy continuation may reuse the lane under the worker-lane policy, and should prefer `scripts/runner-launch-qc.sh --supervised ...` for non-trivial QC handoffs. Supervised mode checkpoints `.stagepilot/worker-progress/` plus git evidence and extends only on concrete progress, never on heartbeat-only output; repeated no-progress stops should be classified with stall subtypes such as `context_compaction_loop`, `read_loop_no_diff`, or `progress_artifact_missing` when the evidence supports it. |
| 4 | `delivery-runner -> lead` escalation | Scope, priority, approval, or release-policy questions go back to the lead instead of being decided silently in delivery. |
| 5 | `delivery-runner -> lead` completion summary (optional) | Optional wrap-up message after runner delivery reaches merge-ready evidence / hand-back. The required successful completion signal is the delivery state moving to lead-visible `done` with persisted delivery artifacts available for lead merge/release review. `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue, not normal successful completion. |

#### Visual chain

```text
┌──────────────┐
│    lead      │
│ Discovery /  │
│ REQ approval │
└──────┬───────┘
       │ approved Discovery + approved REQ
       ▼
┌──────────────┐
│delivery-runner│
│ batch grouping │
│ + orchestration│
└───┬────────┬──┘
    │        │
    │ impl   │ escalation / release-policy / scope / priority
    ▼        └──────────────────────────────────────────────► lead
┌──────────┐
│ dev-impl │
│ changes +│
│ evidence │
└────┬─────┘
     │ verification target + evidence bundle
     ▼
┌──────────┐
│  dev-qc  │
│independent│
│ verification │
└────┬─────┘
     │ QC verdict
     ▼
┌──────────────────────────────┐
│ confirm-batch-verification   │
└──────────────┬───────────────┘
               │ verification approved
               ▼
┌──────────────────────────────┐
│  confirm-req-implemented     │
└──────────────┬───────────────┘
               │ delivery complete
               ▼
┌──────────────┐
│    lead      │
│ draft-release│
│confirm-release│
└──────────────┘
```

#### Fast mental model

`lead` → `delivery-runner` → fresh `dev-impl` child session → fresh `dev-qc` child session → `confirm-batch-verification` → `lead` (merge) → `confirm-req-implemented`

Notes:

- `dev-impl` and `dev-qc` are intentionally distinct; QC is not an extension of implementation. Each new batch/verdict starts a fresh worker lane; healthy same-handoff continuation may reuse the lane, but failures/retries/rework/new batches are fresh and receive prior context only through artifacts.
- Only `fast`, or a low-risk `standard` `batch-lite` path with a structured waiver, may skip explicit QC handoff. The root state must record targeted validation, waiver reason, and residual risk.
- Escalate immediately instead of spending retry budget when the issue is caused by REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, or any decision outside runner authority.
- Waiver is not allowed for core functional failures, security/privacy issues, data integrity risks, or other unresolved blocking defects.
- Release-family work resumes with the lead after runner-managed delivery reaches merge-ready hand-back; by default the lead merges first, then performs `confirm-req-implemented` as the post-merge REQ sync step.

## Skill strategy

This repository now treats `skills/` as part of the harness source tree and as the source-of-truth StagePilot skill catalog.

- The repo holds the editable source of StagePilot-related Hermes skills.
- Docs in `docs/`, contracts in `handoffs/`, and role definitions in `roles/` remain the human-readable operating model.
- Skills package the same model into agent-facing instructions that can be copied or symlinked into a Hermes profile later.
- `scripts/export_skills.py` can export the in-repo skills into a target Hermes skills directory.
- `docs/skills.md` tracks the current catalog and `docs/skill-audit.md` tracks overlap, gap, and optimization analysis.

The current catalog contains **28 skills**:

- **3 harness-core skills**
  - `skills/stagepilot-agent-harness/`
  - `skills/stagepilot-role-topology/`
  - `skills/stagepilot-handoffs/`
- **3 operational governance skills**
  - `skills/stagepilot-bootstrap-seed-ops/`
  - `skills/stagepilot-doctor-ops/`
  - `skills/stagepilot-skill-catalog-governance/`
- **22 consolidated StagePilot workflow skills**
  - discovery, requirements, batch, release, and orchestration skills now maintained directly in this repo

Repository policy: `skills/` should contain skill directories only. Catalog/audit prose belongs under `docs/`.

## Use

1. Start from the docs in `docs/` and `roles/`.
2. Use `docs/profile-bootstrap.md` when turning the harness into real Hermes profiles.
3. Use `docs/model-policy.md` for the default role-to-model mapping.
4. Copy or adapt the baseline role SOUL templates from `profiles/templates/`.
5. Use the handover templates in `templates/` and the contracts in `handoffs/`. For machine-readable runner state and escalation payloads, treat `docs/state-machine.md` as the canonical schema reference.
6. Use `scripts/lead-launch-runner.sh <kickoff_artifact> <delivery_state>` when the lead needs to start a root runner handoff; the default launcher runs in a detached background `tmux` session. Seed the root state with canonical fields such as `status`, `current_stage`, `owner_target`, `goal`, `kickoff_artifact`, and `updated_at`.
7. Use `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` and `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>` for short/simple downstream worker launches. Harness launchers are expected to run in place from the harness repo (often by absolute path) while the runner cwd remains the target delivery worktree; helper scripts resolve relative to the launcher location, while worker `--workdir`, git evidence, and `.stagepilot/worker-progress/` stay rooted in the target worktree. Before major PR-bound delivery effort, run `scripts/check-publication-auth.sh --json` in that same delivery worktree and escalate immediately on `publication_auth_missing...`. For non-trivial child work, prefer `--supervised` with checkpoint/max runtime options; progress extension is allowed only on concrete evidence such as git changes or updated `.stagepilot/worker-progress/<handoff-id>.md`, not heartbeat-only output. `scripts/supervise_worker.py` now records stall subtypes like `context_compaction_loop`, `read_loop_no_diff`, and `progress_artifact_missing` when no-progress terminations have enough evidence. Escalations should preserve machine-readable fields such as `reason_class`, `blocker_code`, `blocker_detail`, `required_lead_decision`, and `evidence_paths` rather than relying on prose only. `runner-launch-impl.sh` supports runtime-budget presets (`--preset default|stretched|long-run`) that map to the standard impl supervision profiles, while still allowing explicit minute overrides when a nonstandard budget is justified. For impl slicing, use the default planning heuristic of roughly half-budget: choose work that can usually show evidence within about 5 minutes and close within about 30 minutes; if that is impossible for genuinely atomic work, record and use an explicit long-run supervised exception with a larger hard cap.
8. Install or export the repo-backed skills when you want Hermes profiles to consume the harness directly.
9. Place project-specific deviations under `projects/<project>/` rather than mutating core assumptions unnecessarily.
10. Run the verification checklists before adopting a new topology.

## Initial scope

This scaffold now captures both the operating model and its agent-facing skill layer, with hooks for:

- artifact/state-driven orchestration
- Telegram/home-channel notification rules
- profile bootstrap automation
- project overlays such as TREX
- future skill export/install automation

## Status

Harness scaffold plus initial in-repo StagePilot skill sources created by Hermes Agent.


### Supervised worker lifecycle integrity

- Runner-owned supervised impl/QC calls should launch in background/tmux mode by default; foreground supervised execution is an explicit short-runtime exception only when the caller timeout is safely above the child max runtime.
- The runner must poll the launcher `exit_file`, worker log, and supervisor `final-result.json`. If `final-result.json` is missing or has `result_class=supervisor_interrupted`, classify it as `supervisor_integrity_failure` / harness execution failure, not as implementation acceptance failure.
- Child logs, diffs, and progress artifacts may be used as secondary evidence, but they do not replace the canonical supervisor final result.
- If a completed implementation has a simple same-scope implementation-context mismatch (for example visible label or CTA wording), the runner may create a fresh bounded rework handoff without lead escalation. Escalate only when the contract itself is ambiguous, scope changes, or governance/product authority is needed.
- Implementation contexts with user-visible copy requirements should include machine-checkable assertions such as required visible strings, forbidden visible strings, and required metric labels before QC handoff.
