---
name: confirm-req
description: "Use when: reviewing a proposed REQ for approval, running /confirm-req with a REQ ID or file path, running /confirm-req without arguments to review all unapproved REQs, promoting docs/srs/<Type>/req-XXX_<slug>.md from Proposed to Approved, updating docs/srs/index.md after approval, or when the user asks in Korean to '요구 사항 명세를 검토하고 승인해줘', '요구사항 명세를 검토하고 승인해줘', 'REQ를 검토하고 승인해줘', or '승인되지 않은 전체 req를 검토하고 승인해줘'."
version: 0.9.1
author: Justin Ko
license: private
argument-hint: "예: req-001 또는 docs/srs/Interface/req-001_picker-cli-run.md 또는 인자 없이 /confirm-req"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, requirements, approval, quality, sdlc]
    related_skills: [draft-req, change-req, draft-batch, stagepilot-doctor-ops]
---

# Purpose

This skill validates a proposed requirement document and promotes it to `Approved` only when it is ready to be used as delivery input.

# When to use

- `/confirm-req req-001`처럼 REQ 승인 게이트를 통과시켜야 할 때
- `/confirm-req`처럼 입력 없이 승인되지 않은 전체 REQ를 일괄 검토하고 승인 가능한 항목만 승격해야 할 때
- REQ 문서의 필수 필드와 Acceptance Criteria 충족 여부를 다시 확인해야 할 때
- `docs/srs/index.md` 상태를 REQ 문서와 맞춰야 할 때

## Do not use when

- REQ가 아직 실질적으로 초안 수준이라 먼저 새로 정리하거나 다시 써야 할 때 (`draft-req`가 더 적절함)
- 기존 `Approved` 또는 `Implemented` REQ의 Requirement, Acceptance Criteria, 범위를 변경해야 할 때 (`change-req`가 더 적절함)
- 승인된 REQ를 구현/검증 evidence 기준으로 `Implemented`로 전환하려는 단계일 때 (`confirm-req-implemented`가 더 적절함)
- 여러 `Approved` REQ를 delivery batch로 묶고 planning/design 단계로 넘기려는 시점일 때 (`suggest-batch-reqs`, `draft-batch`가 더 적절함)

# Inputs

- 선택 입력: REQ 식별자
  - `req-001` 같은 prefix
  - 전체 REQ 파일 경로
- 입력이 없으면 `docs/srs/**/req-*.md` 전체를 스캔해 승인되지 않은 REQ를 대상으로 삼는다.
- 대상 REQ 문서 또는 대상 REQ 문서 목록
- `docs/srs/index.md`

# Core Rules

## 0. 승인 전제

- 대상 REQ의 현재 `Status`는 기본적으로 `Proposed`여야 한다.
- REQ는 delivery input으로 넘길 수 있을 만큼 구체적이어야 하며, 단순 질문 목록이나 TODO 모음 수준이면 승인하지 않는다.
- source Discovery 또는 상위 변경 맥락과 명백히 모순되는 REQ는 승인하지 않는다.
- `Notes`에 남은 항목은 승인 blocker인지, 승인 후 후속 작업으로 남길 수 있는 메모인지 구분해서 판단한다.
- `Priority`, `Owner`, 핵심 범위, 승인 판단에 영향을 주는 open question이 비어 있거나 사람 결정을 필요로 하면 승인하지 않는다.
- 다만 승인 이후 batch planning에서 더 구체화 가능한 비핵심 운영 메모는 `Notes`에 남아 있어도 승인 blocker가 아닐 수 있다.

## 1. 입력 해석

- prefix 입력이면 `docs/srs/**/req-001_*.md` 형식으로 찾는다.
- 입력이 없으면 `docs/srs/` 아래에서 `req-template.md`를 제외한 모든 `req-*.md`를 찾고, 그중 `Status: Proposed`인 문서를 승인 후보로 삼는다.
- 후보가 0개면 진행하지 않는다.
- 후보가 여러 개면 임의 선택하지 않는다.
- 입력이 없는 일괄 모드에서는 여러 후보가 정상이며, 각 후보를 개별 승인 게이트로 평가한다.

## 2. 승인 게이트

- 아래 항목이 모두 있어야 승인 가능하다.
  - `Status`, `Type`, `Priority`, `Owner`
  - `Intent`
  - `Requirement`
  - 구체적인 `Acceptance Criteria`
  - `Impacted Area`
  - `Change Log`
- 미해결 placeholder, 사람 결정 필요 메모, blocker가 남아 있으면 승인하지 않는다.
- `Status`가 이미 `Approved`, `Implemented`, `Deprecated`이면 중복 승인하지 않는다.
- 일괄 모드에서는 승인 불가한 문서가 있더라도 전체 실행을 중단하지 않는다. 승인 가능한 문서만 승격하고, 나머지는 blocker와 함께 별도 보고한다.

## 3. 허용되는 수정

- AI가 근거 있게 바로 고칠 수 있는 표현, 오타, 누락 제목 정리는 보강할 수 있다.
- 승인 성공 시 아래 변경을 수행한다.
  - REQ 문서의 `Status`를 `Approved`로 변경
  - `Change Log`에 승인 기록을 새 항목으로 추가
  - `docs/srs/index.md`의 해당 Register 행 상태 갱신
  - 필요하면 `Recent Change Log Summary` 갱신
- `Change Log` 승인 기록은 기존 항목을 덮어쓰지 않고 append한다.
- 승인 보류인 REQ에는 승인 기록을 남기지 않는다.
- `docs/srs/index.md`가 이미 존재하면, template wording으로 통째로 덮어쓰지 말고 현재 저장소의 로컬 형식을 source of truth로 취급한다.
  - 기존 섹션 구조, 설명 문구, 표/리스트 형식, 열 순서는 가능한 한 유지한다.
  - 필요한 상태값과 요약 항목만 in-place로 갱신한다.
- 사람 판단이 필요한 우선순위, 범위, Owner는 임의로 확정하지 않는다.
- 일괄 모드에서도 허용되는 수정 범위는 동일하며, 승인 불가 문서의 상태는 바꾸지 않는다.

# Execution Procedure

1. 입력에서 대상 REQ 경로 하나 또는 대상 REQ 문서 목록을 확정한다.
2. 입력이 없는 경우 `docs/srs/**/req-*.md`를 스캔해 `Status: Proposed` 문서를 승인 후보 목록으로 만든다.
3. 대상 REQ들과 `docs/srs/index.md`를 읽는다.
4. 각 REQ마다 필수 필드, Acceptance Criteria, Notes의 blocker 여부를 확인한다.
5. AI가 근거 있게 정리할 수 있는 사소한 일관성 문제를 먼저 고친다.
   - 승인 기록을 append 하거나 문서 말미를 patch할 때는 대상 REQ 파일을 전체 기준으로 다시 읽었는지 확인한다. offset/limit 기반 부분 읽기나 도구 축약 출력만 본 상태에서 Change Log를 덧붙이면 `Change Summary` 같은 제목/본문이 잘린 채 저장될 수 있다.
   - 승인 패치 직후에는 최소한 (a) 대상 REQ의 새 Change Log tail, (b) `Status: Approved`, (c) `docs/srs/index.md`의 해당 Register 행을 다시 읽어 실제 저장 결과를 검증한다.
6. source Discovery가 명시돼 있거나 `생성된 REQ 참조`로 추적 가능한 경우, 승인 전에 Discovery의 범위/결정/오픈 질문과 REQ가 모순되지 않는지 확인한다.
   - 특히 Discovery의 `사용자 결정 필요 항목 요약`, `REQ로 넘기기 전 확인 체크`, `범위 경계`, `리스크/가정 목록`에서 승인 blocker가 남아 있지 않은지 본다.
   - Discovery에 `Open` 상태 질문, 미확정 DECIDE/CONFIRM/DATA 항목, handoff 미승인 상태가 남아 있으면 승인 보류를 우선 검토한다.
7. 각 REQ에 대해 승인 게이트를 다시 평가한다.
8. 게이트 통과한 REQ만 `Approved`로 전환하고 인덱스를 갱신한다.
9. 게이트 미통과한 REQ는 상태를 유지하고 남은 blocker를 수집한다.
10. 입력이 없는 경우 승인 성공 목록과 승인 불가 목록을 분리해 함께 보고한다.
11. `stagepilot-doctor` 실행 후 warning을 유형별로 분류한다.
   - 방금 승인한 REQ가 `orphan-approved-req`로 표시되면 다음 단계가 batch planning임을 보고하고, 사용자가 요청하지 않았으면 즉시 batch를 생성하지 않는다.
   - 기존 REQ가 `approved-req-no-release-candidate-batch`로 표시되면 현재 confirm 작업의 blocker인지 별도 흐름의 잔여 warning인지 구분해서 보고한다.
   - `0 error(s)`이고 REQ 본문/index 상태가 일치하면 warning만으로 승인을 되돌리지 않는다.

# Output Expectations

- 단일 입력 모드:
  - 대상 REQ 경로
  - 승인 성공 여부
  - 자동 보강한 항목 목록
  - 남은 blocker 또는 미해결 항목
  - `docs/srs/index.md` 갱신 결과
- 무인자 일괄 모드:
  - 검토한 REQ 전체 목록
  - 승인 성공한 REQ 목록
  - 승인 불가한 REQ 목록과 각 blocker
  - 자동 보강한 항목 목록
  - `docs/srs/index.md` 갱신 결과

# Common Pitfalls

0. `stagepilot-doctor`의 `orphan-approved-req` 경고를 승인 실패로 오해하는 실수
   - `confirm-req` 직후에는 Approved REQ가 아직 batch에 포함되지 않았기 때문에 `orphan-approved-req` warning이 정상적으로 발생할 수 있다.
   - 이 경고는 다음 단계(`suggest-batch-reqs`/`draft-batch`)로 넘길 신호이며, `Status: Approved` 반영과 index 동기화가 맞다면 승인 자체를 되돌릴 이유가 아니다.
   - 단, error가 있거나 REQ 본문/index 상태가 불일치하면 승인 완료로 보고하지 말고 먼저 수정한다.

1. 필수 섹션은 있지만 내용이 너무 비어 있는 REQ를 승인하는 실수
   - 필드 존재 여부만 보지 말고, 실제로 구현/검증 판단에 쓸 수 있을 정도로 구체적인지 확인한다.

2. `Notes`의 open question이나 사람 결정 필요 항목을 blocker로 처리하지 않고 승인하는 실수
   - Priority, Owner, 핵심 범위, 승인 판단에 영향을 주는 질문은 해소 전까지 승인하지 않는다.

3. 이미 `Approved`, `Implemented`, `Deprecated`인 REQ를 다시 confirm 대상으로 다루는 실수
   - 이 경우 중복 승인 대신 현재 상태 유지 또는 `change-req`, `confirm-req-implemented` 경로를 검토한다.

4. `docs/srs/index.md` 상태만 바꾸고 REQ 본문 상태를 같이 안 바꾸는 실수
   - 승인 성공 시 REQ 본문과 index register 상태를 함께 `Approved`로 맞춰야 한다.

5. 일괄 모드에서 일부 blocker가 있다고 전체를 중단하는 실수
   - 일괄 모드에서는 각 REQ를 독립 게이트로 평가하고, 승인 가능한 문서만 승격한다.

6. 승인 단계에서 사람이 정해야 할 Priority, Owner, 범위를 AI가 임의로 확정하는 실수
   - 사람이 결정해야 하는 항목은 자동으로 메우지 말고 blocker로 남긴다.

# Verification Checklist

- [ ] 대상 REQ 경로가 유일하게 확정되었거나, 일괄 모드 후보 집합이 올바르게 수집되었다.
- [ ] 대상 REQ의 현재 상태가 `Proposed`인지 확인했다.
- [ ] 필수 필드(`Status`, `Type`, `Priority`, `Owner`, `Intent`, `Requirement`, `Acceptance Criteria`, `Impacted Area`, `Change Log`)가 모두 존재한다.
- [ ] `Acceptance Criteria`가 구현/검증에 사용할 수 있을 만큼 구체적이다.
- [ ] 승인 blocker인 placeholder, open question, 사람 결정 필요 항목이 남아 있지 않다.
- [ ] source Discovery가 있으면 handoff 상태와 open question 정리가 승인 전제와 모순되지 않는다.
- [ ] 사람이 판단해야 하는 `Priority`, `Owner`, 범위를 AI가 임의 확정하지 않았다.
- [ ] 승인 성공 시 REQ 본문과 `docs/srs/index.md` 상태가 둘 다 `Approved`로 갱신되었다.
- [ ] 승인 보류 시 상태가 잘못 바뀌지 않았다.
- [ ] 일괄 모드에서는 승인 가능한 REQ만 승격되었다.
- [ ] `docs/srs/index.md`는 로컬 형식을 유지한 채 필요한 상태값만 in-place로 갱신되었다.