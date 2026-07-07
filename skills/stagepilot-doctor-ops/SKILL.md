---
name: stagepilot-doctor-ops
description: Use when running, interpreting, or triaging StagePilot doctor checks for a workspace, including bootstrap-required repos, traceability warnings, report generation, and expected-vs-blocking finding classification.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, doctor, validation, traceability, bootstrap, verification]
    related_skills: [stagepilot-agent-harness, bootstrap-baseline, draft-batch, confirm-req, run-batch-implementation, confirm-batch-verification, suggest-next-discovery]
---

# StagePilot Doctor Operations

## Overview

This skill standardizes how to run and interpret `stagepilot-doctor` in a StagePilot workspace. Use it when you need to validate document structure, traceability, feedback handoff integrity, placeholder cleanup, link health, or bootstrap readiness.

This skill is about **doctor execution and triage**, not authoring Discovery/REQ/Batch/Release content directly.

## When to Use

Use this skill when you need to:

- run StagePilot health checks on a workspace before or after SDLC work;
- decide whether doctor findings are blockers, expected transitional warnings, or informational guidance;
- generate a Markdown validation report for handoff, QC, or release evidence;
- interpret traceability-related findings such as orphan REQs or missing release-candidate linkage;
- detect whether a repository should run `bootstrap-baseline` before the first real Discovery.

## Command resolution

Prefer the most local available path in this order:

1. `python3 .stage-pilot/tools/stagepilot-doctor.py .`
2. `bash .stage-pilot/tools/stagepilot.sh doctor .`
3. An equivalent vendor/subtree path if the repository installed StagePilot under another local location.

Use these common variants:

```bash
python3 .stage-pilot/tools/stagepilot-doctor.py .
python3 .stage-pilot/tools/stagepilot-doctor.py --strict-missing-docs .
python3 .stage-pilot/tools/stagepilot-doctor.py --report artifacts/stagepilot-doctor.md .
```

## Core checks the doctor performs

The doctor validates or summarizes at least the following:

- active SDLC document roots and indexes
- state sync between indexes and body docs
- Discovery → REQ → Batch → Release traceability
- release feedback handoff continuity
- placeholder residue
- relative Markdown link integrity
- REQ type consistency
- template/skill contract drift
- bootstrap-required conditions for fresh repos
- optional cross-cutting baseline doc gaps when relevant

## Triage rules

### 1. Treat as blockers

Block progress when the doctor reports issues that mean the repository state or document graph is unreliable, for example:

- missing required active index files in a workspace that should already be active;
- document/index state mismatches that invalidate current lifecycle status;
- broken traceability that prevents identifying which Discovery, REQ, Batch, or Release a unit belongs to;
- unresolved placeholders in committed workflow documents when they should already be finalized;
- broken relative links in source-of-truth docs relied on by the current step;
- report write failures when a report was explicitly requested as deliverable evidence.

### 2. Treat as expected transitional warnings when the stage explains them

Some warnings can be acceptable mid-flow if you classify them explicitly in the working artifact or summary. Typical examples:

- `orphan-approved-req` immediately after `confirm-req` but before batch creation;
- `approved-req-no-release-candidate-batch` before verification confirmation promotes the batch;
- `bootstrap-required` on a fresh host repo before the first baseline bootstrap;
- warnings that are known to disappear only after the next intended StagePilot step.

Do **not** silently ignore these. Record why they are expected, which next step clears them, and when you will rerun the doctor.

### 3. Treat as informational guidance

Informational findings are advisory and should be reported, but do not block completion by themselves unless the user or project policy says otherwise.

## Execution procedure

1. Determine whether the repository is a fresh host repo, an active StagePilot workspace, or a package/self-check context.
2. Run `stagepilot-doctor` with the narrowest command that matches the local installation path.
3. If the task needs durable evidence, rerun with `--report <path>` and keep the path in the final artifact.
4. Classify each finding into blocker, expected transitional warning, or informational guidance.
5. When a warning is expected because of stage timing, name the exact next skill that should clear it.
6. After the relevant fix or state transition, rerun the doctor and compare the result.
7. In verification or release contexts, include the rerun outcome in the evidence summary.

## Common Pitfalls

1. **Treating every warning as a hard failure.** Some warnings reflect an in-between lifecycle state rather than a true defect.
2. **Treating every warning as harmless.** Expected transitional warnings still require explicit explanation and follow-up.
3. **Skipping reruns after a fix.** A claimed fix without a rerun is incomplete validation.
4. **Using doctor as a substitute for human approval.** Doctor validates structure and traceability, not product judgment.
5. **Forgetting `--report` when evidence must survive chat.** If the output matters later, persist it.

## Verification Checklist

- [ ] The doctor command path matched the repository's actual installation layout.
- [ ] Findings were classified as blocker, expected transitional warning, or informational guidance.
- [ ] Any expected warning has an explicit next-step explanation.
- [ ] A rerun was performed after fixes or status promotions when validation mattered.
- [ ] Report output was saved when the task required durable evidence.
