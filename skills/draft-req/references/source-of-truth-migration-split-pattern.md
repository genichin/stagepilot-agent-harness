# Source-of-truth migration REQ split pattern

Use this reference when a confirmed Discovery changes the canonical source of truth for a domain while removing an old local implementation.

## Pattern observed

A source-of-truth migration often drafts more cleanly as multiple independently approvable REQs instead of one broad requirement:

1. **Interface REQ**
   - Removes the old local tool/API surface.
   - Covers manifest/registration/schema/handler removal.
   - Covers generic type enum removal if the old domain was accepted by shared tools.
   - Includes non-regression criteria for local domains that remain supported.

2. **Integration REQ**
   - Defines the new canonical external service route.
   - Covers read/write operations, auth scopes, reauthorization needs, and failure behavior.
   - Explicitly forbids fallback to the old local implementation when the policy requires a hard cutover.
   - Redacts tokens, OAuth code/state, credentials, and secret values in evidence.

3. **Documentation/Baseline REQ**
   - Aligns README, companion skills, project structure docs, runtime flow docs, interface contracts, and data model docs.
   - Separates user-facing policy from implementation details.
   - Preserves documentation for unrelated local domains that remain active.

4. **Migration/Data REQ**
   - Handles destructive cleanup of old local data separately from code removal.
   - Requires target-path confirmation, already-absent handling, and preservation checks for unrelated data.
   - States whether archive/migration is intentionally out of scope.

## Boundary rule

When another Discovery/batch owns an adjacent domain, keep acceptance criteria scoped to the current Discovery and explicitly delegate the adjacent cleanup to the other trace. Example: a todo migration REQ should not require calendar residual cleanup if calendar is already tracked by a separate calendar Discovery/batch.

## Traceability verification

After creating the REQs:

- Update `docs/srs/index.md` `Next Requirement ID`, register, and recent change log.
- Update the source Discovery `생성된 REQ 참조` line with all REQ IDs on the same line, followed by detailed path bullets if useful.
- Run StagePilot doctor and confirm the new REQs map back to the source Discovery without orphan warnings.
