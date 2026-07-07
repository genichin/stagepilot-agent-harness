---
name: change-req
description: "Use when: updating an existing requirement after approval or implementation, running /change-req with a REQ ID or file path, recording a change-request entry before overwriting a REQ, analyzing impacted batches/releases, or deciding whether an Implemented REQ must be downgraded and reverified."
version: 0.8.1
author: Justin Ko
license: private
argument-hint: "예: req-001 또는 docs/srs/Documentation/req-001_minor-docs.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, requirements, change-management, documentation, sdlc]
    related_skills: [draft-req, confirm-req, draft-batch]
---

# Purpose

This skill applies a controlled change to an existing REQ by recording a new change-request entry before editing the requirement body, analyzing downstream delivery impact, and updating status/index state when the prior implementation is no longer valid.

# When to use

- `/change-req req-001`처럼 기존 REQ의 Requirement, Acceptance Criteria, Impacted Area를 수정해야 할 때
- 운영 피드백이나 release feedback에서 기존 REQ 수정 필요가 확인됐을 때
- `Implemented` 또는 `Approved` REQ가 더 이상 현재 구현/검증 증거와 맞지 않는지 판단해야 할 때
- `docs/srs/index.md`의 REQ 상태와 실제 변경 영향 범위를 다시 동기화해야 할 때

# Inputs

- 선택 입력
  - `REQ-ID` prefix
  - REQ 파일 경로
- 변경 요청 근거
  - 사용자 요청
  - release feedback
  - batch verification 또는 implementation 결과
- 대상 REQ 문서
- `docs/srs/index.md`
- 관련 `docs/batches/index.md`
- 관련 `docs/releases/index.md`
- 영향이 의심되는 batch/release 문서들

# Core Rules

## 1. 입력 해석

- prefix 입력이면 `docs/srs/**/req-001_*.md` 형식으로 찾는다.
- 동일 prefix에 여러 문서가 매칭되면 임의 선택하지 않는다.
- REQ가 `Deprecated`면 기본적으로 새 변경 요청 대상으로 삼지 않는다. 복구가 필요하면 근거를 먼저 명시한다.

## 2. 변경 요청 기록 규칙

- 기존 `Requirement`, `Acceptance Criteria`, `Impacted Area`를 덮어쓰기 전에 새 `Change Log` 항목을 추가한다.
- 새 변경 항목 ID는 `CHG-YYYYMMDD-NN` 형식을 사용하고 같은 날짜 내에서 순차 증가시킨다.
- 새 항목에는 최소한 아래를 모두 기록한다.
  - `Change Summary`
  - `Intent`
  - `Acceptance Criteria Delta`
  - `Impacted Area Delta`
  - `Delivery Trace Delta`
  - `Revalidation Impact`
  - `Validation Plan`
- 과거 `Change Log` 항목은 삭제하거나 덮어쓰지 않는다.

## 3. 상태 영향 규칙

- 변경이 기존 구현 또는 verification evidence를 무효화하지 않으면 현재 상태를 유지할 수 있다.
- `Implemented` REQ의 기존 구현/검증 근거가 깨지면 상태를 `Approved`로 되돌린다.
- 변경이 승인 전제 자체를 다시 검토하게 만들면 상태를 `Proposed`로 되돌릴 수 있다.
- 상태를 되돌릴 때는 이유를 `Revalidation Impact`와 `Change Log`에 함께 남긴다.
- 상태가 바뀌면 `docs/srs/index.md`의 Register와 `Recent Change Log Summary`도 함께 갱신한다.

## 4. 영향 분석 규칙

- 관련 batch가 있으면 어떤 batch planning/design/verification이 다시 검토되어야 하는지 기록한다.
- 관련 release가 있으면 release 문서를 직접 덮어쓰지 말고 영향 범위와 후속 action을 REQ의 `Change Log`에 남긴다.
- 사람 판단이 필요한 범위 재정의, 우선순위 변경, 정책 변경은 임의 확정하지 않는다.

# Execution Procedure

1. 입력에서 대상 REQ 경로를 확정한다.
2. REQ 현재 상태와 최근 `Change Log`를 읽는다.
3. `docs/batches/index.md`, `docs/releases/index.md`, 관련 batch/release 문서를 읽어 현재 delivery trace를 요약한다.
4. 변경 요청 근거를 기존 구현/검증 상태와 비교한다.
5. 새 `Change Log` 항목을 먼저 추가하고 delta, trace, revalidation impact를 채운다.
6. 그 다음 REQ 본문(`Requirement`, `Acceptance Criteria`, `Impacted Area`, `Notes`)을 필요한 만큼 수정한다.
7. 상태 유지 또는 상태 되돌림 필요 여부를 결정해 REQ 본문과 `docs/srs/index.md`를 갱신한다.
8. `Recent Change Log Summary`에 최신 변경 항목을 반영한다.

# Output Expectations

- 대상 REQ 경로
- 새 `Change Log` 항목 ID
- 변경 요약
- 영향 받는 batch/release 목록
- 재검증 필요 여부
- 상태 유지 또는 상태 되돌림 결과
- `docs/srs/index.md` 갱신 결과

# Common Pitfalls

1. 활성 batch 안에서 계약/필드 순서 같은 외부 계약을 바꾸면서 REQ만 수정하고 delivery 산출물과 baseline 문서를 같이 재정렬하지 않는 실수
   - 예: persistence flat slot 순서, CTSP read/write 슬롯 순서, revision migration 시 기본값 채움 순서 변경.
   - 이런 변경은 `change-req` 후에 source Discovery, 연결된 Approved REQ들, 현재 batch의 `planning/design/implementation/verification`, 그리고 `CTSP_PROTOCOL`/`CONFIGURATION`/`runtime-flows` 같은 기준 문서를 같은 변경 묶음으로 갱신해야 한다.
   - verification evidence가 다시 필요해질 수 있으므로, 검증 전에는 batch를 `release-candidate`로 올리거나 REQ를 `Implemented`로 확정하지 않는다.

# Validation

- `Change Log` 새 항목이 REQ 본문 수정보다 앞선 시간순 근거로 남았는지 확인한다.
- `Acceptance Criteria Delta`, `Delivery Trace Delta`, `Revalidation Impact`가 모두 채워졌는지 확인한다.
- 상태 되돌림이 필요한 경우 REQ 문서와 `docs/srs/index.md` 상태가 함께 바뀌었는지 확인한다.
- 관련 batch/release 영향이 `Change Log`에 누락되지 않았는지 확인한다.