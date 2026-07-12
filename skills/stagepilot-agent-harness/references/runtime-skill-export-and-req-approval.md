# Runtime skill export and REQ approval-set behavior

## Lesson captured

A StagePilot harness install is incomplete if only the core runtime skills are present. The harness repository's `skills/` catalog contains both core skills and SDLC workflow skills such as `confirm-req`, `draft-req`, `run-sdlc`, batch, and release skills.

If a runtime profile can load `stagepilot-agent-harness` but cannot load `confirm-req`, the harness has been only partially exported to that profile.

## Required runtime export

Export the full repo catalog to every active StagePilot team profile:

```bash
cd /home/ubuntu/workspaces/stagepilot-agent-harness
python3 scripts/verify_structure.py
for profile in dev-butler delivery-runner dev-impl dev-qc; do
  python3 scripts/export_skills.py --dest "/home/ubuntu/.hermes/profiles/$profile/skills"
done
```

After export, verify key workflow skills exist and match the repo source:

```bash
for skill in confirm-req draft-req run-sdlc stagepilot-agent-harness; do
  sha256sum \
    "/home/ubuntu/workspaces/stagepilot-agent-harness/skills/$skill/SKILL.md" \
    /home/ubuntu/.hermes/profiles/{dev-butler,delivery-runner,dev-impl,dev-qc}/skills/$skill/SKILL.md
done
```

## REQ approval-set rule

`confirm-req` approval and delivery slicing are separate decisions.

When a confirmed Discovery produced multiple eligible Proposed REQs, the lead should run the approval gate across the eligible REQ set. Approval should not be limited to the first implementation slice merely because delivery will be sequenced later.

Correct flow:

```text
confirmed Discovery
→ draft one or more Proposed REQs
→ confirm-req evaluates eligible Proposed REQ set
→ Approved REQ set becomes delivery input
→ delivery-runner chooses batch grouping and implementation slicing
```

Do not confuse:

```text
REQ approval scope = delivery input readiness
implementation slice = runner/impl execution unit
```

## Discovery root handoff rule

It is valid to hand a confirmed Discovery root objective to `delivery-runner` after approval, provided the handoff names the approved REQ set and any already-implemented dependencies.

The runner should not forward the whole Discovery as one direct `dev-impl` task. It should create/choose batches and then hand smaller implementation tasks to `dev-impl`, followed by independent QC.
