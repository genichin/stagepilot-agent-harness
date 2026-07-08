---
name: confirm-req-implemented
description: "Use when: confirming that approved requirements have merge-backed implementation and verification evidence, running /confirm-req-implemented with a REQ ID, BAT ID, or file path, promoting docs/srs/<Type>/req-XXX_<slug>.md from Approved to Implemented, or updating docs/srs/index.md after merge-backed delivery confirmation."
version: 0.7.0
author: Justin Ko
license: private
argument-hint: "예: req-001 또는 bat-001 또는 docs/srs/Interface/req-001_picker-cli-run.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, requirements, implementation, validation, sdlc]
    related_skills: [draft-batch-verification, confirm-batch-verification, draft-release, stagepilot-doctor-ops]
---

# Purpose

This skill validates that an approved requirement has merge-backed implementation and verification evidence, then promotes it to `Implemented` only when every acceptance criterion is traceable to delivery evidence.

`Implemented`는 배포 완료 자체를 뜻하지 않는다. 기본 기준은 merge 이후 canonical codebase에 반영된 구현과 검증 증거가 확보된 상태이며, 일반적으로 `merged` 또는 `released` batch의 verification 결과를 근거로 삼는다.

# When to use

- `/confirm-req-implemented req-001`처럼 특정 REQ를 `Implemented`로 전환해야 할 때
- `/confirm-req-implemented bat-001`처럼 merge 이후 포함 REQ 상태를 동기화해야 할 때
- `/confirm-req-implemented`처럼 입력 없이 현재 저장소의 `Approved` REQ 중 merge-backed 구현 완료로 승격 가능한 대상을 일괄 점검해야 할 때
- `docs/srs/index.md`의 REQ 상태가 실제 merge-backed verification evidence와 어긋나 있을 때

# Inputs

- 선택 입력
  - `REQ-ID` prefix
  - REQ 파일 경로
  - `BAT-ID` prefix
  - batch 경로
- 입력이 없으면 `docs/srs/**/req-*.md` 전체에서 `Status: Approved` REQ를 후보로 찾는다.
- 대상 REQ 문서 또는 대상 batch 문서
- `docs/srs/index.md`
- `docs/batches/index.md`
- 관련 `docs/batches/<BAT_ID>/index.md`
- 관련 `docs/batches/<BAT_ID>/verification.md`
- 필요하면 관련 `docs/batches/<BAT_ID>/implementation.md`

# Core Rules

## 1. 입력 해석

- `req-001` 같은 prefix가 주어지면 `docs/srs/**/req-001_*.md` 형식으로 찾는다.
- `bat-001` 같은 prefix가 주어지면 `docs/batches/` 아래 matching batch를 찾고, 포함 REQ 중 `Approved` 상태만 후보로 삼는다.
- 입력이 없으면 `docs/srs/` 아래에서 `req-template.md`를 제외한 모든 `req-*.md`를 읽고, 그중 `Status: Approved` 문서를 후보로 삼는다.
- 같은 prefix에 여러 문서가 매칭되면 임의 선택하지 않는다.
- 입력이 없는 일괄 모드에서는 여러 후보가 정상이며, 각 후보를 개별 게이트로 평가한다.

## 2. 구현 완료 전환 게이트

- 아래 조건을 모두 만족해야 `Implemented`로 전환한다.
  - 대상 REQ의 현재 `Status`가 `Approved`다.
  - 연결된 batch가 `merged` 또는 `released` 상태다.
  - batch `verification.md`에 해당 REQ의 `Acceptance Mapping`이 존재한다.
  - REQ의 모든 `Acceptance Criteria`가 verification evidence와 연결된다.
  - batch verification의 `Blocking Issues`가 이 REQ를 미통과 상태로 남기지 않는다.
- release 배포 완료는 필수 조건이 아니지만, merge는 필수다. 즉 canonical codebase에 반영된 구현과 검증 evidence가 충분하면 `merged` 상태에서 `Implemented` 전환이 가능하다.
- 연결된 batch를 찾지 못하거나 evidence가 부족하면 상태를 바꾸지 않는다.
- 하나의 REQ가 여러 batch에 걸쳐 있고 어떤 batch를 근거로 삼아야 할지 명확하지 않으면 임의로 전환하지 않는다.

## 3. 허용되는 수정

- AI가 근거 있게 정리할 수 있는 오타, 링크, 표현 불일치는 보강할 수 있다.
- 전환 성공 시 아래 변경을 수행한다.
  - REQ 문서의 `Status`를 `Implemented`로 변경
  - `Change Log`에 구현 완료 전환 기록 추가
  - `docs/srs/index.md`의 해당 Register 행 상태를 `Implemented`로 갱신
  - 필요하면 `Recent Change Log Summary`를 갱신
- evidence 자체를 새로 만들어 내거나, batch verification의 blocker를 임의 해소하지 않는다.
- 사람 판단이 필요한 범위 변경, acceptance criteria 재정의, batch 재매핑은 임의로 확정하지 않는다.

# Execution Procedure

1. 입력에서 대상 REQ 하나, REQ 목록, 또는 batch 경로를 확정한다.
2. batch 입력인 경우 batch `index.md`에서 Included REQ를 읽고 `Approved` REQ만 후보로 만든다.
3. 입력이 없는 경우 `docs/srs/**/req-*.md`를 스캔해 `Status: Approved` 문서를 후보 목록으로 만든다.
4. 각 후보 REQ에 대해 `docs/batches/index.md`와 batch 문서를 읽어 연결된 batch를 찾고, 그 batch가 `merged` 또는 `released` 상태인지 확인한다.
5. 연결된 batch의 `verification.md`에서 REQ acceptance mapping, evidence, blocking issue를 점검한다.
6. 게이트를 통과한 REQ만 `Implemented`로 전환하고 `Change Log`, `docs/srs/index.md`를 갱신한다.
7. 게이트를 통과하지 못한 REQ는 상태를 유지하고 남은 blocker를 수집한다.
8. 입력이 batch 또는 무인자 일괄 모드인 경우, 성공 목록과 보류 목록을 분리해 보고한다.

# Output Expectations

- 단일 입력 모드
  - 대상 REQ 또는 batch 경로
  - 구현 완료 전환 성공 여부
  - 사용한 근거 batch와 merge-backed verification evidence 요약
  - 자동 보강한 항목 목록
  - 남은 blocker 또는 미해결 항목
  - `docs/srs/index.md` 갱신 결과
- batch/무인자 일괄 모드
  - 검토한 REQ 전체 목록
  - `Implemented` 전환 성공한 REQ 목록
  - 전환 보류한 REQ 목록과 각 blocker
  - `docs/srs/index.md` 갱신 결과

# Validation

- 전환 성공인 경우 REQ 문서와 `docs/srs/index.md` 상태가 모두 `Implemented`인지 확인한다.
- 전환 성공인 경우 사용한 근거 batch가 `merged` 또는 `released` 상태인지 확인한다.
- 전환 보류인 경우 상태가 잘못 바뀌지 않았는지 확인한다.
- 사용한 verification evidence가 실제 REQ acceptance criteria와 연결되는지 확인한다.
- batch 입력 모드에서는 batch에 포함된 `Approved` REQ만 처리되었는지 확인한다.