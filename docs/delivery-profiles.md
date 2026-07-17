# Delivery profiles

Delivery profiles make control cost proportional to delivery risk. They are a policy applied by the `delivery-runner`, not a replacement for role authority: lead owns scope/approval, runner owns execution, impl owns implementation, and QC owns independent review when it is required.

The root delivery state is canonical. It must persist `delivery_profile` as `fast`, `standard`, or `guarded` (default: `standard`), plus the selected validation evidence and any waiver reason.

## Selection and escalation

Choose the least costly profile that still covers the risk. Escalate immediately to `standard` or `guarded` when the scope is unclear or expands.

| Profile | Eligible work | Required control path |
| --- | --- | --- |
| `fast` | One small, local, low-risk change with clear acceptance criteria | runner → foreground impl → targeted runner validation → root state `done`/`blocked` |
| `standard` | Ordinary bounded product/code change | normal runner handoff; QC and supervision are selected by documented risk triggers |
| `guarded` | High-risk, cross-boundary, release-sensitive, or uncertain work | isolated worktree, PR publication preflight when applicable, supervised impl, supervised independent QC |

`fast` is prohibited for authentication/authorization, sensitive data, database/schema/migration, public API or CLI contracts, dependency/infrastructure changes, multi-module changes, irreversible operations, or unclear acceptance criteria. Those conditions also trigger `guarded` unless the runner documents why `standard` is sufficient.

## Artifact and verification policy

- **Fast:** use the root state as the minimal delivery manifest. Do not create an impl implementation-context, worker-progress artifact, or QC handoff. Record `validation_commands`, `evidence_paths`, `qc_waiver_reason`, and `residual_risk` before terminal completion.
- **Standard:** keep the normal handoff/state trail, but create supervised worker artifacts only for work that needs them. Require QC for risk triggers: contract/data/security changes, multi-module work, externally visible release risk, or validation the runner cannot independently establish. A waiver must record `qc_waiver_reason`, `residual_risk`, and runner validation evidence in root state.
- **Guarded:** use the full artifact trail. Implementation context/readiness gate, worker progress/final result, independent QC verdict, and publication preflight (for PR-bound work) are mandatory.

A completion summary is secondary. The canonical success signal remains root delivery state `status=done` (or legacy-compatible `state=done`) with inspectable evidence. Use `blocked` and a structured escalation when a lead decision is needed.

## Launcher contract

`scripts/lead-launch-runner.sh`, `runner-launch-impl.sh`, and `runner-launch-qc.sh` accept `--delivery-profile fast|standard|guarded`; when omitted they read `delivery_profile` from the root state and default to `standard`.

- `runner-launch-impl.sh --delivery-profile fast <delivery_state>` is foreground and unsupervised; the root state replaces a separate impl handoff and it does not create a progress artifact or auto-enable an implementation-context readiness gate.
- `runner-launch-qc.sh --delivery-profile fast` fails deliberately: fast has runner-owned targeted validation rather than a QC handoff.
- `guarded` forces supervision in both child launchers; guarded implementation also requires a valid implementation-context.

## Capability and degraded-mode policy

Run `scripts/check-delivery-capabilities.sh --json` before a launcher path when the environment is uncertain. The helper classifies capability results as `ready`, `degraded`, or `blocked`; it does not expose credential values or raw auth output.

| Capability | `fast` | `standard` | `guarded` |
| --- | --- | --- | --- |
| Hermes profile and Python | required | required | required |
| `tmux` | required for default detached launch; explicit foreground fallback may be approved | required for detached launch | required |
| isolated worktree | default; explicit approved fallback only for local/reversible work | required when selected by the delivery plan | required |
| `gh` auth and publication remote | not a default requirement | only when publication is in scope | required for PR-bound publication |
| doctor | use declared adoption mode | use declared adoption mode | use declared adoption mode |

A degraded path is never implicit. Only `fast` may use the launcher’s `--allow-fast-degraded` option, and a current-workdir fallback additionally requires `--ack-fast-shared-workdir-risk`; that acknowledgement means the lead has confirmed the checkout is exclusive, clean, and local/reversible scope will not contaminate another delivery. A fast fallback is local-only: PR creation, push, release, or other publication work must stop and escalate to `standard` or `guarded`. When Git is available, the launcher also rejects a checkout with uncommitted changes. The launcher records `capability_status=degraded`, `fallbacks_selected`, `degraded_capabilities`, acknowledgement, and residual risk in root state. `standard` requires an explicit lead decision for any equivalent exception; `guarded` capability failures are blockers.

Doctor adoption is persisted in the root state as `required`, `optional`, or `not-adopted`; an overlay may supply the value only while creating that canonical state. `check-delivery-capabilities.sh --delivery-state <root-state> --json` reads it unless an explicit `--doctor-mode` is supplied. A missing required doctor blocks; an optional missing doctor records `tooling_debts` with `runner_validation_without_doctor`; a not-adopted doctor is not a failure by itself.

This repository is the source-of-truth harness only. Updating it does not modify an already-installed Hermes profile or a running session.
