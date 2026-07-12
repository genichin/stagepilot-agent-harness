---
name: run-batch-implementation
description: "Use when: implementing a confirmed batch design, running /run-batch-implementation with a BAT ID, applying code changes for docs/batches/<BAT_ID>, or updating implementation logs and validation evidence for a batch."
version: 0.7.2
author: Justin Ko
license: private
argument-hint: "예: bat-001 또는 docs/batches/bat-001_20260424_scaffold"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, implementation, execution, sdlc]
    related_skills: [draft-batch-planning, draft-batch-design, draft-batch-verification, confirm-req-implemented, stagepilot-doctor-ops]
---

# Purpose

This skill executes the implementation work for a batch, updates code, and records the changed files, execution log, validation, and remaining risks in the batch implementation document.

# Inputs

- `BAT-ID` 또는 batch 경로
- `docs/batches/<BAT_ID>/planning.md`
- `docs/batches/<BAT_ID>/design.md`
- `docs/batches/<BAT_ID>/implementation.md`
- 관련 REQ 문서와 실제 코드 경로

# Core Rules

- planning과 design이 없는 batch는 구현하지 않는다.
- non-trivial supervised `dev-impl` handoff 전에는 runner가 implementation-context artifact를 준비해야 한다. 이 artifact는 target files, edit anchors, service seams, return shape, render insertion point, test assertions, forbidden data exposure, allowed search budget, validation commands, first-progress deadline을 포함해야 한다.
- patch-ready implementation-context가 있으면 `dev-impl`는 patch-first 모드로 동작한다: context를 실행 계약으로 받아들이고, exact target snippets만 읽은 뒤 곧바로 edit/write 또는 concrete blocker를 남긴다. service seam/return shape/render insertion point가 이미 pin 되어 있으면 repo에서 다시 설계·탐색하지 않는다.
- 코드 변경 전 `implementation.md`의 Plan Summary와 Changed Files 초안을 먼저 맞춘다.
- 구현 직후 가장 좁은 테스트, lint, typecheck, 또는 동작 검증을 수행한다.
- Public interface/type removal이나 destructive data cleanup이 포함된 batch는 구현 문서에 삭제 전 대상 경로·파일 목록, 삭제 후 absence, non-regression 테스트, residual search, stagepilot-doctor 결과를 함께 남긴다.
- `stagepilot-doctor` warning은 즉시 실패로 단정하지 말고, 현재 stage에서 예상되는 traceability warning인지 분류한다. 구현 단계에서는 batch/REQ가 아직 release-candidate/Implemented가 아니어서 남는 warning이 있을 수 있으며, 이는 verification/confirmation stage의 follow-up으로 기록한다.
- stateful runtime을 host/PYDEBUG binding으로 검증할 때는 동일 입력 반복 호출이 내부 scan/cache/state를 누적할 수 있음을 먼저 점검한다. deterministic evidence가 필요하면 테스트 전에 reset hook을 추가하거나 초기 상태를 명시적으로 복원한 뒤 비교한다.
- blocker가 생기면 문서에 남기고 범위를 임의 확장하지 않는다.
- 구현을 시작한 batch는 `implementation.md`만 갱신하고 끝내지 말고, batch index와 batch index 문서의 Status도 최소 `in-delivery`로 맞춰 stage 상태가 어긋나지 않게 한다.
- 배치 문서 경로가 아직 없거나 추적 문서가 비어 있으면, 구현 단계에서 `index.md`, `implementation.md`, `verification.md` 기본 뼈대를 함께 정리해 이후 stage가 바로 이어질 수 있게 한다.

# Execution Procedure

1. batch 경로, plan, design, 관련 REQ를 읽는다.
2. 구현 범위와 변경 파일 후보를 요약한다. Runner/worker split이라면 implementation-context artifact와 readiness gate 결과를 먼저 확인한다.
   - readiness-gated context가 있으면 먼저 target snippets만 확인하고 patch/write로 진입한다.
   - context가 지정한 seam/path/key가 invalid하면 broad search로 대체 설계를 찾지 말고 progress artifact에 blocker를 기록하고 중단한다.
3. 실제 코드 변경을 수행한다.
   - Interface/type 제거 시 public registry, LLM-facing schema, runtime type enum, helper files, tests, docs/skills active guidance를 모두 확인한다.
   - Destructive cleanup이 승인된 경우 active profile/home을 먼저 resolve하고, 대상이 승인된 경로 아래인지 확인한 뒤 삭제 전 파일 목록과 삭제 후 absence를 기록한다. Archive/migration copy를 만들지 않기로 한 요구사항이면 임의 백업을 생성하지 않는다.
4. `implementation.md`의 Changed Files, Execution Log, Validation, Remaining Risks를 갱신한다.
5. batch index 상태를 필요하면 `in-delivery`로 유지 또는 보정한다.
6. 구현 검증으로 최소 다음을 고려한다: syntax/compile check, targeted smoke tests, deleted-file/data absence checks, residual text search, `stagepilot-doctor`. Warning이 남으면 stage상 예상인지 blocking인지 implementation.md에 분류한다.
7. persistence schema, flash migration, 또는 저장 포맷 호환성 이슈를 디버깅할 때는 호스트/PYDEBUG 빌드의 `sizeof(...)` 추정으로 결론내리지 말고, 타깃 펌웨어 쪽에 구조체 크기(`sizeof(struct prop_header)`, 관련 persisted struct), header probe 결과, 첫/둘째 `property_read(...)` 반환값을 직접 로그로 남겨 원인을 분리한다.

# Validation

- `implementation.md`에 실제 변경 파일과 검증 기록이 반영됐는지 확인한다.
- patch-ready supervised handoff에서 반복 read/search만 있고 diff 또는 concrete blocker가 없었다면 implementation failure로 취급하고 동일 재시도를 하지 않는다.
- 구현 직후 수행한 가장 좁은 검증 명령 또는 결과가 문서에 남았는지 확인한다.
- persistence/migration 디버깅 변경이라면, 타깃 로그로 ABI 크기와 read rc를 캡처하는 계측 또는 동등한 증거가 남았는지 확인한다.
- batch 문서 `index.md`와 `docs/batches/index.md`의 Status가 구현 진행 상태(`in-delivery` 등)와 일치하는지 확인한다.