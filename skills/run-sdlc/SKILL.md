---
name: run-sdlc
description: "Use when: orchestrating the next SDLC action from the current 3-phase state, running /run-sdlc with a Discovery, REQ, Batch, or Release ID, resuming from the first incomplete unit in docs/discovery, docs/srs, docs/batches, or docs/releases, or routing a no-history repository to bootstrap-baseline before the first real Discovery."
version: 0.7.0
author: Justin Ko
license: private
argument-hint: "예: dcy-001, bat-001, rel-001, req-001 req-002"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, orchestration, workflow, execution, sdlc]
    related_skills: [bootstrap-baseline, new-discovery, draft-req, draft-batch, run-discovery-delivery, run-batch-delivery, draft-release, stagepilot-agent-harness, stagepilot-doctor-ops]
---

# Purpose

This skill inspects the current state of Discovery, REQ, Batch, and Release documents and routes work to the next skill-only step in the 3-phase SDLC model.

`docs/project-structure.md`와 `docs/runtime-flows.md`는 별도 governance unit는 아니지만, 이 skill은 다음 단계를 추천할 때 해당 baseline 문서의 존재 여부와 갱신 필요 여부를 함께 확인한다.

# Inputs

- `DISCOVERY_ID`
- `REQ-ID` 목록
- `BAT-ID`
- `REL-ID`
- 관련 문서 경로
- `docs/project-structure.md` (존재하는 경우)
- `docs/runtime-flows.md` (존재하는 경우)

# Core Rules

- 이 skill은 `docs/discovery/`, `docs/srs/`, `docs/batches/`, `docs/releases/`만 active 경로로 사용한다.
- `docs/project-structure.md`와 `docs/runtime-flows.md`는 active routing 대상은 아니지만, 모든 단계에서 참고할 cross-cutting baseline 문서로 취급한다.
- prompt 기반 stage command는 사용하지 않는다.
- `review-*` 단계는 별도 명령으로 두지 않고 대응 `confirm-*` 절차에 흡수된 상태를 전제로 한다.
- `confirm-req` 이후에는 사용자의 별도 kickoff를 기본 전제로 두지 않는다. 사용자가 명시적으로 hold, defer, batch-later, 추가 확인 대기 조건을 주지 않았다면 lead가 `lead -> delivery-runner` handoff를 발행해 다음 delivery 단계를 시작할 수 있다.
- 단, 정확히 1개의 `Approved` REQ가 국소적이고 저위험 변경으로 판단되면 `delivery-runner`가 `minor-change` fast path로 `draft-batch`를 바로 진행할 수 있다. 이 경로의 batch profile은 `batch-lite`다.
- active unit가 아직 없고 baseline 문서 또는 active index가 비어 있으면, 첫 real Discovery 전에 `bootstrap-baseline`을 우선 추천한다.

# Execution Procedure

## 1. 입력 해석

- 입력이 `dcy-`로 시작하면 Discovery를 기준으로 현재 상태를 확인한다.
- 입력이 `req-` 목록이면 REQ 상태를 읽고 batch 생성 또는 추천 단계로 보낸다.
- 입력이 `bat-`로 시작하면 batch delivery 상태를 확인한다.
- 입력이 `rel-`로 시작하면 release 상태를 확인한다.
- 입력이 없으면 현재 저장소에서 첫 incomplete step을 판정한다.
- 어떤 입력이든 가능하면 `docs/project-structure.md`와 `docs/runtime-flows.md` 존재 여부를 함께 확인한다.

## 1.5 bootstrap baseline routing

- active unit가 없고 `docs/project-structure.md`, `docs/runtime-flows.md`, active index 중 일부라도 비어 있으면 `bootstrap-baseline`을 다음 skill로 제안한다.
- 이 경우 Discovery를 자동 생성하지 않는다.
- baseline 초기화가 끝난 뒤 `new-discovery`를 다음 real Discovery entrypoint로 안내한다.

## 2. Discovery 기준 routing

- Discovery가 아직 `confirmed`가 아니면 `confirm-discovery`를 우선 실행한다.
- Discovery는 confirmed지만 연결된 REQ가 없으면 `draft-req`를 다음 단계로 사용한다.
- `Approved` REQ는 있으나 batch가 없으면 기본적으로 `run-discovery-delivery`를 통해 `delivery-runner`가 Discovery-level root delivery를 시작한다. 이 root flow는 `suggest-batch-reqs`로 batch 후보를 정리하고, hold나 추가 승인 요구가 없으면 runner-owned `draft-batch` 및 queue 실행으로 이어진다.
- batch가 이미 생성되었고 Discovery root queue가 없거나 단일 batch만 직접 재개하려면 `run-batch-delivery`를 직접 entrypoint로 사용할 수 있다. Discovery root queue가 존재하면 `run-discovery-delivery`가 current batch부터 이어 가는 상위 entrypoint다.
- baseline 문서 갭이 있으면 상태 요약에 `docs/project-structure.md`와 `docs/runtime-flows.md` 갱신 필요 여부를 함께 기록한다.

## 3. REQ 기준 routing

- `Proposed` REQ면 `confirm-req`를 다음 단계로 사용한다.
- 기존 REQ의 `Requirement`, `Acceptance Criteria`, 구현 전제가 바뀌어 Change Log 기반 변경 관리가 필요하면 `change-req`를 다음 단계로 사용한다.
- `Approved` REQ가 `merged` 또는 `released` batch의 verification evidence와 연결돼 있으면 `confirm-req-implemented`를 다음 단계로 사용한다.
- 단일 `Approved` REQ이고 구조/인터페이스/런타임 영향이 없는 소규모 변경이면 `delivery-runner`가 `draft-batch`를 `minor-change -> batch-lite` 경로로 바로 진행할 수 있다.
- Approved REQ 묶음이 2개 이상이면 기본적으로 `delivery-runner`가 `run-discovery-delivery` 아래에서 `suggest-batch-reqs`를 통해 grouping을 정리하고, hold 지시가 없으면 runner-owned `draft-batch`와 sequential batch queue 실행으로 이어진다. 다만 scope, priority, release policy를 바꾸는 판단은 lead escalation이 필요하다.
- baseline 문서 갱신이 REQ에 포함돼 있으면 상태 요약에 이를 반영한다.

## 4. Batch 기준 routing

- `planning.md`가 비어 있거나 draft 수준이면 `draft-batch-planning`
- batch profile이 `standard`이거나 `batch-lite`라도 planning의 `Design Gate`가 `yes`면 `draft-batch-design`
- batch profile이 `batch-lite`이고 `Design Gate`가 `no`면 design 없이 `run-batch-implementation`
- 구현 로그와 코드 변경이 아직 없으면 `run-batch-implementation`
- verification 문서가 없거나 불완전하면 `draft-batch-verification`
- verification evidence가 있지만 release-candidate가 아니면 `confirm-batch-verification`
- batch가 `merged` 또는 `released`이고 포함 REQ 중 `Approved` 상태가 남아 있으면 `confirm-req-implemented`
- batch가 `release-candidate`이고 포함 REQ 구현 상태 동기화까지 끝났으면 `draft-release`
- batch design 또는 verification에 structure/flow 영향이 보이면 baseline 문서 갱신 필요 여부를 상태 요약에 포함한다.

## 5. Release 기준 routing

- release 문서가 draft면 profile(`docs-only` | `tooling` | `app-service`)에 맞는 근거가 채워졌는지 확인한 뒤 `confirm-release`
- `feedback-captured` release에 follow-up 입력이 있으면 `suggest-next-discovery` 또는 `change-req`를 다음 단계 후보로 제안한다.
- release가 confirmed 이후 운영 관찰이 남아 있지 않으면 `capture-release-feedback`

# Output Expectations

- 입력으로 해석한 단위 종류
- 현재 상태 요약
- baseline 문서 상태 (`present` | `missing` | `update-likely-required` | `bootstrap-required`)
- 바로 실행할 다음 skill 1개 또는 다음 연쇄(`run-discovery-delivery`, `suggest-batch-reqs -> draft-batch`, `run-batch-delivery` 등)
- 자동으로 진행하지 않고 멈춘 이유가 있으면 그 사유 (`user hold`, approval gate, missing evidence, escalation required 등)

# Validation

- 다음 단계가 현재 문서 상태와 모순되지 않는지 확인한다.
- 제안한 다음 skill이 현재 harness skill catalog(`skills/` tree 또는 그 export copy) 안에 실제로 존재하는지 확인한다.
- baseline 문서가 필요한 상황에서 상태 요약 또는 추천 사유에 그 정보가 누락되지 않았는지 확인한다.