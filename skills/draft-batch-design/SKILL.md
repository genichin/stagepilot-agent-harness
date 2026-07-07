---
name: draft-batch-design
description: "Use when: drafting the design document for an existing batch, running /draft-batch-design with a BAT ID, filling docs/batches/<BAT_ID>/design.md, recording architecture and interface decisions before implementation, or planning updates to docs/project-structure.md and docs/runtime-flows.md."
version: 0.8.0
author: Justin Ko
license: private
argument-hint: "예: bat-001 또는 docs/batches/bat-001_20260424_scaffold"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, design, architecture, sdlc]
    related_skills: [draft-batch, draft-batch-planning, run-batch-implementation]
---

# Purpose

This skill writes the design document for a batch by summarizing architecture, changed areas, key decisions, and edge cases from the batch plan and included REQs.

`docs/project-structure.md`와 `docs/runtime-flows.md`가 존재하면, 이 skill은 해당 baseline 문서를 읽고 이번 batch의 구조 영향과 흐름 영향을 비교해야 한다.

# Inputs

- `BAT-ID` 또는 batch 경로
- `docs/batches/<BAT_ID>/planning.md`
- 포함된 REQ 문서들
- `docs/batches/<BAT_ID>/design.md`
- `docs/project-structure.md` (존재하는 경우)
- `docs/runtime-flows.md` (존재하는 경우)

# Core Rules

- planning이 없거나 범위가 비어 있으면 설계를 진행하지 않는다.
- 설계는 구현 전에 결정해야 할 구조와 인터페이스를 중심으로 적는다.
- `batch-lite`이고 planning의 `Design Gate`가 `no`이며 구조/인터페이스/런타임 영향이 없다면 design 단계는 생략할 수 있다.
- REQ 간 공통 설계 전제가 있다면 batch design에 끌어올린다.
- baseline 문서가 있으면 이번 batch 설계는 baseline 대비 변경점과 유지점이 무엇인지 명시해야 한다.
- `design.md`에는 최소한 아래 내용을 포함해야 한다.
	- Architecture Summary
	- Changed Areas
	- Key Decisions
	- Edge Cases
	- Architecture Impact (`none` | `project-structure` | `runtime-flows` | `both`)
	- Reference Doc Update Plan
- 기존 템플릿에 위 섹션이 없으면 설계 문서에 추가해 채운다.

# Execution Procedure

1. batch 경로를 확정한다.
2. planning과 포함 REQ를 읽는다.
3. planning의 `Design Gate`가 `no`이고 batch profile이 `batch-lite`면 design 없이 진행 가능한지 다시 확인하고, 그대로면 design 생략 결정을 유지한다.
4. `docs/project-structure.md`와 `docs/runtime-flows.md`가 있으면 읽고 현재 baseline과 batch 범위를 비교한다.
5. `design.md`에 Architecture Summary, Changed Areas, Key Decisions, Edge Cases를 채운다.
6. Architecture Impact와 Reference Doc Update Plan을 명시한다.
7. 설계상 blocker가 있으면 문서에 명시하고 구현으로 넘기지 않는다.

# Validation

- design 문서에 Architecture Summary, Changed Areas, Key Decisions, Edge Cases가 모두 있는지 확인한다.
- planning에서 정의한 핵심 범위가 design에서 누락되지 않았는지 확인한다.
- 구조 또는 흐름 영향이 있는 batch라면 Architecture Impact와 Reference Doc Update Plan이 채워졌는지 확인한다.
- `batch-lite`에서 design을 생략한 경우 planning의 `Design Gate`와 batch index profile이 그 결정을 설명하는지 확인한다.