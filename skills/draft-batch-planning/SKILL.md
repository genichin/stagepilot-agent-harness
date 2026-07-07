---
name: draft-batch-planning
description: "Use when: drafting the planning document for an existing batch, running /draft-batch-planning with a BAT ID, populating docs/batches/<BAT_ID>/planning.md, or setting batch scope and dependency notes before design."
version: 0.8.0
author: Justin Ko
license: private
argument-hint: "예: bat-001 또는 docs/batches/bat-001_20260424_scaffold"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, planning, implementation, sdlc]
    related_skills: [draft-batch, draft-batch-design, run-batch-implementation]
---

# Purpose

This skill writes the planning document for a batch by consolidating included REQs, scope, dependencies, milestones, and key risks.

# Inputs

- `BAT-ID` 또는 batch 경로
- `docs/batches/<BAT_ID>/index.md`
- 포함된 REQ 문서들
- `docs/batches/<BAT_ID>/planning.md`

# Core Rules

- planning은 batch 수준 범위, 의존성, 순서를 명확히 해야 한다.
- REQ 문서를 다시 쓰지 말고 delivery 관점의 묶음 계획으로 요약한다.
- planning은 design이 구현 전에 필요한지 여부를 명시해야 한다.
- `batch-lite`라면 planning에 왜 design을 생략할 수 있는지 또는 언제 design이 필요해지는지 남긴다.
- planning 작성 후 batch 상태는 `in-delivery`로 올릴 수 있다.

# Execution Procedure

1. 입력에서 batch 경로를 확정한다.
2. batch index와 포함 REQ를 읽는다.
3. `planning.md`에 scope, out-of-scope, dependency, milestone, risk를 채운다.
4. `planning.md`의 `Design Gate`에 design 필요 여부와 근거를 적는다.
4. 필요하면 batch `index.md`의 Status를 `in-delivery`로 갱신한다.

# Validation

- planning 문서에 Included REQ, Delivery Plan, Dependencies, Design Gate, Milestones, Risks가 모두 존재하는지 확인한다.
- batch index와 planning의 포함 REQ 목록이 일치하는지 확인한다.