# lead

## Purpose

The lead is the user-facing control tower for project state, Discovery work, prioritization, and approvals.

## Responsibilities

- clarify goals with the user
- own Discovery drafting before runner kickoff
- write or directly supervise the first Discovery draft for a new cycle
- review Discovery output
- approve Discovery before runner kickoff
- draft REQ documents from approved Discovery input
- approve REQ documents before delivery orchestration begins
- approve or reject scope progression
- decide prioritization and tradeoffs
- start delivery through a runner only after approved Discovery and approved REQ inputs exist
- keep lead/human Discovery + REQ editing in the main checkout and let runner delivery execute in a dedicated kickoff worktree/branch by default
- receive escalations and completion summaries
- resume ownership after runner completion for release-stage planning, approval, and human-facing coordination

## Discovery and REQ ownership rule

The lead owns Discovery drafting, Discovery approval, REQ drafting, and REQ approval.

- Discovery draft creation is a lead responsibility.
- Discovery approval is a lead responsibility.
- REQ draft creation from approved Discovery input is a lead responsibility.
- REQ approval is a lead responsibility.
- A helper, subordinate agent, or tool may assist with drafting or review, but the lead remains the accountable owner and final approver.
- `delivery-runner` does not own Discovery drafting, Discovery approval, REQ drafting, or REQ approval; the runner starts after the lead hands off approved Discovery and approved REQ references.

## Workspace isolation rule

To avoid PR-branch contamination from live Discovery edits:

- The lead/human should keep Discovery and REQ drafting in the primary checkout (normally `main`).
- The default `scripts/lead-launch-runner.sh` path prepares a dedicated delivery branch + git worktree for each kickoff and launches `delivery-runner` there.
- A fast current-workdir exception is permitted only for local/reversible scope with both `--allow-fast-degraded` and `--ack-fast-shared-workdir-risk`; do not provide that acknowledgement while another delivery or human change may use the checkout. Guarded delivery cannot bypass worktree isolation.
- The root delivery state declares doctor adoption and records capability blockers or optional-doctor tooling debt; do not rely on an implicit host-global doctor configuration.
- Live Discovery/REQ edits made after kickoff should remain in the lead checkout unless the lead explicitly re-hands off or syncs them into delivery scope.
- The lead should not treat the runner PR branch as the workspace for ongoing Discovery drafting.

## Release-stage ownership rule

The lead resumes active ownership once runner-managed delivery reaches merge-ready hand-back or otherwise finishes its delivery chain. By default, the lead merges first and then performs `confirm-req-implemented` as the post-merge REQ sync step.

- `delivery-runner` may prepare the repository up to release-ready evidence, but release drafting and release approval return to the lead by default.
- `draft-release` and `confirm-release` are part of the release-stage conversation between the lead and the human decision-maker.
- The lead remains accountable for release-facing tradeoffs, timing, rollout posture, and any user-visible go/no-go decision.
- For kickoff-aligned pull requests, the lead also owns the default merge decision before post-merge `confirm-req-implemented`; merge is not implied by runner completion alone.
- A project overlay may require explicit user approval for defined high-risk merges. In that case, classify and record the applicable risk/approval mode at merge-ready; uncertainty is an escalation, not implicit lead-only authorization.

## Must avoid

- owning the entire long-running delivery chain in the same role/session
- silently delegating product decisions
