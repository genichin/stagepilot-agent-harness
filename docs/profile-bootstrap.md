# Profile Bootstrap Guide

This guide explains how to turn the StagePilot harness into real Hermes profiles.

## Goal

Bootstrap a reusable four-role topology:

- `<project>-dev-lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

Use the shared worker profiles by default. Create project-specific worker variants only when credentials, compliance, tooling, or repository topology materially differ.

## Prerequisites

Before creating profiles:

1. Review `docs/role-topology.md`, `roles/`, and `handoffs/`.
2. Decide the project name for the lead profile, using the pattern `<project>-dev-lead`.
3. Decide the working directory each profile should default to.
4. Define the project's canonical kanban board and write it into `projects/<name>/overlay.md`. The baseline naming rule is to derive the board from the lead-owned project name, typically `<project>-stagepilot`, unless the project documents a different board convention explicitly. By default this board governs only the `lead -> delivery-runner` root kickoff and runner queue visibility; `delivery-runner -> dev-impl` and `delivery-runner -> dev-qc` stay transport-agnostic unless the overlay explicitly opts into kanban child cards.
5. Confirm which skills should be exported from this repo into the target Hermes runtime.

## Baseline profile set

| Profile | Scope | Default reuse rule |
|---|---|---|
| `<project>-dev-lead` | project-specific lead / approvals / user-facing coordination | Usually project-specific |
| `delivery-runner` | orchestration, sequencing, escalation, completion reporting | Shared across projects unless the orchestration environment diverges |
| `dev-impl` | implementation worker | Shared across projects unless repo/tooling constraints diverge |
| `dev-qc` | independent verification worker | Shared across projects unless verification environment diverges |

## Recommended bootstrap sequence

1. Create or update the profiles.
2. Copy the matching SOUL templates from `profiles/templates/`.
3. Export the harness skills into the active Hermes runtime.
4. Set per-profile defaults such as model, cwd, and enabled toolsets.
5. Verify each profile with `hermes profile show <name>`.

## Example commands

### 1) Create the profiles

```bash
hermes profile create trex-dev-lead
hermes profile create delivery-runner
hermes profile create dev-impl
hermes profile create dev-qc
```

If you want to start from an existing profile, use clone mode instead:

```bash
hermes profile create trex-dev-lead --clone-from default
```

### 2) Copy the SOUL templates

```bash
cp profiles/templates/lead.SOUL.md ~/.hermes/profiles/trex-dev-lead/SOUL.md
cp profiles/templates/delivery-runner.SOUL.md ~/.hermes/profiles/delivery-runner/SOUL.md
cp profiles/templates/dev-impl.SOUL.md ~/.hermes/profiles/dev-impl/SOUL.md
cp profiles/templates/dev-qc.SOUL.md ~/.hermes/profiles/dev-qc/SOUL.md
```

Then edit the copied files if the project needs explicit overlay rules.

### 3) Export skills from this repository

Export the in-repo skill catalog into the target Hermes runtime:

```bash
python3 scripts/export_skills.py --dest ~/.hermes/skills
```

If you maintain a non-default profile home or a packaging step, export to that skill directory instead.

### 4) Set profile working directories

Use project-specific cwd for the lead profile and shared/workspace cwd for the shared workers unless you have a stronger reason to isolate them differently.

```bash
hermes config set terminal.cwd /path/to/project --profile trex-dev-lead
hermes config set terminal.cwd /path/to/workspace --profile delivery-runner
hermes config set terminal.cwd /path/to/workspace --profile dev-impl
hermes config set terminal.cwd /path/to/workspace --profile dev-qc
```

If your local Hermes version does not accept `--profile` on `hermes config set`, switch profiles first or edit each profile's `config.yaml` directly via `hermes config edit -p <name>`.

### 5) Configure models

See `docs/model-policy.md` for the recommended role-to-model mapping.

### 6) Verify profiles

```bash
hermes profile show trex-dev-lead
hermes profile show delivery-runner
hermes profile show dev-impl
hermes profile show dev-qc
```

Check that each profile has:

- the expected model
- the expected cwd
- a present `SOUL.md`
- the expected skill catalog available

## Toolset guidance

These are operating defaults, not hard laws.

| Profile | Usually needed toolsets |
|---|---|
| `<project>-dev-lead` | `file`, `skills`, `todo`, plus project-dependent web/browser tools |
| `delivery-runner` | `file`, `skills`, `todo`, `delegation`, `cronjob`, plus messaging/kanban if used |
| `dev-impl` | `file`, `terminal`, `code_execution`, `skills` |
| `dev-qc` | `file`, `terminal`, `skills`, and verification-specific tools |

Restrict more aggressively only when the environment or governance model requires it.

## Overlay rules

Create project-specific worker variants only when one of these is true:

- the project needs different credentials or auth boundaries
- the project needs a different repository root or terminal backend
- the worker uses materially different tooling
- compliance or isolation rules prevent shared workers

Otherwise prefer the shared baseline workers and keep the project-specific variation on the lead profile plus `projects/<name>/` overlay docs.

For kanban-backed deployments of the harness, the project overlay should also record the canonical board name explicitly. Do not leave the board as an implicit chat convention. The default convention is `<project>-stagepilot`, based on the same project identifier used for the lead profile `<project>-dev-lead`, unless the overlay documents a different name.

## Verification checklist

- [ ] The topology still uses `<project>-dev-lead`, `delivery-runner`, `dev-impl`, `dev-qc` unless an exception is documented.
- [ ] The lead profile is project-specific and the worker profiles are shared unless a clear divergence exists.
- [ ] Each profile has the correct `SOUL.md` template copied in.
- [ ] Skills were exported from this repo and are visible in the target Hermes runtime.
- [ ] Each profile's cwd, model, and tool access match its role.
- [ ] Any project-specific deviations are written under `projects/<name>/`.
