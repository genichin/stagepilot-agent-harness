# delivery-runner -> dev-impl

This handoff is transport-agnostic. It may be issued through ordinary runner-to-worker instructions, documents, or messages. Kanban representation is forbidden.

## Required fields

- exact bounded task
- relevant approved docs
- acceptance target
- commands/tests to run
- evidence required back

## Output expectation

Implementation should return changed files, executed checks, and any remaining risks.
