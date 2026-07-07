---
name: bootstrap-baseline
description: "Use when: initializing StagePilot in a project before the first real Discovery, running /bootstrap-baseline to create baseline documents and active indexes, or backfilling missing docs/project-structure.md, docs/runtime-flows.md, docs/interface-contract.md, and docs/data-model.md without creating a Discovery unit."
version: 1.0.1
author: Justin Ko
license: private
argument-hint: "예: 신규 저장소 baseline 초기화, StagePilot init, baseline 문서/인덱스 생성"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, bootstrap, baseline, documentation, sdlc]
    related_skills: [new-discovery, run-sdlc, stagepilot-doctor-ops, stagepilot-agent-harness]
---

# Purpose

This skill initializes the StagePilot baseline outside the normal Discovery -> REQ -> Batch -> Release flow.

`docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md`, 그리고 active index 문서는 첫 real Discovery 전에 준비하는 bootstrap 산출물이다. 이 skill은 baseline과 index를 먼저 만들고, 첫 Discovery가 실제 제품/서비스 변경 주제로 시작되도록 만든다.

greenfield 저장소처럼 읽을 코드나 설정이 아직 없으면, 이 skill은 사용자에게 최소 질문 세트를 묻고 `.stage-pilot/bootstrap/baseline.yaml` seed를 만든 뒤 baseline 문서를 렌더링한다.

# When to use

다음 상황에서 사용한다.

- StagePilot을 새 프로젝트에 처음 적용한 직후 baseline 문서와 index를 만들 때
- `/bootstrap-baseline` 또는 유사한 init 요청으로 baseline 초기화를 수행할 때
- `docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md`, `docs/discovery/index.md`, `docs/srs/index.md`, `docs/batches/index.md`, `docs/releases/index.md` 중 일부가 없어서 SDLC를 시작하기 전에 뼈대를 복구해야 할 때
- 첫 real Discovery를 기능, 운영 문제, 기술 결정 같은 실제 변경 주제로 시작하고 싶을 때

다음 상황에는 이 skill을 기본 경로로 사용하지 않는다.

- 이미 진행 중인 Discovery/REQ/Batch/Release가 있고, baseline 변경 책임이 특정 active unit에 속하는 경우
- 실제 제품/서비스 변경 주제가 이미 명확하여 Discovery 초안 생성이 우선인 경우

# Inputs

이 skill은 아래 입력을 사용한다.

- 현재 저장소 루트와 디렉터리 구조
- `docs/discovery/`, `docs/srs/`, `docs/batches/`, `docs/releases/` 존재 여부
- `.stage-pilot/bootstrap/baseline.yaml` 존재 여부
- `docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md` 존재 여부
- 문서 scaffold source
	- baseline seed scaffold
	- active index scaffolds (`docs/discovery/index.md`, `docs/srs/index.md`, `docs/batches/index.md`, `docs/releases/index.md`)
	- cross-cutting baseline doc scaffolds (`docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md`)
- 현재 시각 (KST)

## Template and scaffold resolution

- 이 harness repo는 repo-backed source-of-truth이며, workflow skill은 특정 legacy install path(`.stage-pilot/...`, `~/.stage-pilot/...`)를 전제하지 않는다.
- bootstrap과 baseline 문서 scaffold는 다음 순서로 해석한다.
	1. 현재 repository 또는 project overlay가 제공하는 bootstrap/baseline scaffold source
	2. 현재 workspace가 실제로 제공하는 vendored/exported StagePilot document-template source
	3. 적절한 scaffold source가 없으면 현재 저장소의 기존 docs 형식을 exemplar로 삼아 최소 seed와 문서를 직접 작성한다.
- 여러 후보가 동시에 존재하면 가장 우선순위가 높은 한 곳만 사용하고, 서로 다른 source를 섞지 않는다.
- scaffold source path와 생성 target path를 혼동하지 않는다.
	- source: repo/project-local scaffold source
	- target: `.stage-pilot/bootstrap/baseline.yaml`, `docs/discovery/index.md`, `docs/srs/index.md`, `docs/batches/index.md`, `docs/releases/index.md`, `docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md`

# Core Rules

## 0. 단위 경계

- `bootstrap-baseline`은 Discovery, REQ, Batch, Release 중 어느 것도 아니다.
- 이 skill은 초기 운영 기준선을 만드는 bootstrap 단계다.
- 이 skill은 Discovery 문서를 생성하지 않는다.
- baseline 초기화가 끝난 뒤 첫 real Discovery는 실제 제품/서비스 변경, 운영 이슈, 기술 결정 같은 주제로 시작한다.

## 1. 생성 대상

- 아래 경로가 없으면 생성한다.
	- `.stage-pilot/bootstrap/baseline.yaml`
	- `docs/discovery/index.md`
	- `docs/srs/index.md`
	- `docs/batches/index.md`
	- `docs/releases/index.md`
	- `docs/project-structure.md`
	- `docs/runtime-flows.md`
	- `docs/interface-contract.md`
	- `docs/data-model.md`
- 이미 존재하는 파일은 임의로 덮어쓰지 않는다.
- 일부만 없는 경우에는 누락된 파일만 생성한다.

## 1.5 최소 질문 세트

- 저장소 관찰만으로 baseline 핵심 정보가 부족하면 먼저 질문을 수행한다.
- 질문은 아래 다섯 개를 기본 세트로 사용한다.
	- `project-summary`
		- 질문: `이 프로젝트를 한 문장으로 설명하면 무엇인가?`
		- 답변 형식: 한 문장 자유 텍스트
	- `primary-domain`
		- 질문: `이 프로젝트의 주요 도메인은 무엇인가?`
		- 답변 형식: 짧은 명사구 또는 분야명
	- `tech-stack`
		- 질문: `계획 중인 주 언어, 프레임워크, 핵심 인프라는 무엇인가?`
		- 답변 형식: 쉼표로 구분한 목록
	- `primary-runtime`
		- 질문: `계획 중인 주 실행 형태는 무엇인가?`
		- 답변 형식: `cli` | `api-service` | `web-app` | `worker` | `library` | `mixed` | `other`
	- `primary-entrypoints`
		- 질문: `대표 진입점 1~3개를 적어 달라.`
		- 답변 형식: 줄마다 `name :: purpose`
- 아래 질문은 선택 입력이다.
	- `planned-top-level-areas`
		- 질문: `이미 알고 있는 top-level 경로가 있으면 적어 달라.`
		- 답변 형식: 줄마다 `path :: responsibility`
	- `interface-contracts`
		- 질문: `대표 인터페이스 1~2개가 있으면 적어 달라.`
		- 답변 형식: 줄마다 `name :: type :: actors :: purpose`
	- `interface-inputs`
		- 질문: `각 인터페이스의 대표 input을 적어 달라.`
		- 답변 형식: 줄마다 `interface-name :: input contract or invocation note`
	- `interface-outputs`
		- 질문: `각 인터페이스의 대표 output을 적어 달라.`
		- 답변 형식: 줄마다 `interface-name :: output contract or artifact`
	- `interface-errors`
		- 질문: `각 인터페이스의 대표 error를 적어 달라.`
		- 답변 형식: 줄마다 `interface-name :: error code or failure behavior`
	- `core-entities`
		- 질문: `핵심 엔티티 1~2개가 있으면 적어 달라.`
		- 답변 형식: 줄마다 `name :: purpose`
	- `persistence-backend`
		- 질문: `주 persistence backend가 있으면 적어 달라.`
		- 답변 형식: 짧은 backend 또는 storage 이름
	- `compatibility-rules`
		- 질문: `인터페이스 호환성 규칙이 있으면 적어 달라.`
		- 답변 형식: 줄마다 `interface-name :: rule` 또는 `* :: rule`
	- `known-unknowns`
		- 질문: `아직 미정인 핵심 항목이 있으면 적어 달라.`
		- 답변 형식: 줄마다 항목 하나
- 이미 읽을 수 있는 저장소 증거가 있으면 질문 수를 줄이고, seed의 비어 있는 값만 보충한다.
- `interface-contracts`, `interface-inputs`, `interface-outputs`, `interface-errors`, `core-entities`, `persistence-backend`, `compatibility-rules`가 비어 있더라도 bootstrap은 `runtime`, `primary-entrypoints`, `primary-domain`, `tech-stack`, `planned-top-level-areas`, `known-unknowns`를 바탕으로 기본 초안을 유도해 seed를 보강할 수 있다.

## 1.6 seed 파일 source-of-truth 규칙

- bootstrap 질문 결과와 저장소 관찰 결과의 합성 source of truth는 `.stage-pilot/bootstrap/baseline.yaml`이다.
- seed 파일은 active SDLC unit가 아니라 bootstrap 선언 파일이다.
- seed 파일이 있으면 baseline 문서 생성과 갱신 시 이를 우선 읽는다.
- seed 파일이 없고 저장소 증거가 충분하지 않으면 질문 없이 baseline 문서를 추정 생성하지 않는다.
- 저장소 관찰값과 사용자 답변이 함께 있으면 `capture_mode`는 `mixed`다.
- 저장소 관찰값만으로 충분하면 `capture_mode`는 `observed`다.
- 사용자 선언이 중심이고 저장소 관찰값은 보조면 `capture_mode`는 `declared`다.

## 2. baseline 문서 작성 원칙

- `docs/project-structure.md`는 seed의 `project`, `stack`, `runtime`, `structure` 값을 먼저 반영하고, 저장소 관찰 결과가 있으면 보강한다.
- `docs/runtime-flows.md`는 seed의 `runtime`과 `notes` 값을 먼저 반영하고, 저장소 관찰 결과가 있으면 보강한다.
- `docs/interface-contract.md`는 seed의 `interfaces` 섹션을 먼저 반영하고, 값이 부족하면 `runtime`, `primary-entrypoints`, `known-unknowns`를 바탕으로 대표 외부 API, CLI, 이벤트, 파일 I/O 계약의 기본 초안을 구체화한다.
- `docs/data-model.md`는 seed의 `data_model` 섹션을 먼저 반영하고, 값이 부족하면 `primary-domain`, `tech-stack`, `planned-top-level-areas`, `known-unknowns`를 바탕으로 핵심 엔티티, 관계, 상태, persistence 규칙의 기본 초안을 구체화한다.
- 입력만으로 알 수 없는 항목은 의미 있는 플레이스홀더로 남기되, 추론 가능한 구조 정보는 실제 문장으로 채운다.
- baseline 문서의 `Source Discovery / Batch`는 bootstrap 산출물임을 드러내는 값으로 채운다.
- baseline 문서는 `declared`, `observed`, `mixed` 중 어느 모드로 렌더링되었는지와 seed 경로를 드러내야 한다.

## 3. index 작성 원칙

- index 문서는 템플릿을 기반으로 생성한다.
- 초기화 시점에는 register 본문만 만들고 실제 Discovery/REQ/Batch/Release 항목은 비워 둔다.
- index 생성은 active unit 생성으로 간주하지 않는다.

## 4. 진행 중 unit가 있는 경우

- 진행 중인 Discovery/REQ/Batch/Release가 이미 있고 baseline 문서만 일부 비어 있다면, 먼저 현재 active unit가 그 변경을 소유해야 하는지 판정한다.
- 특정 active unit의 요구사항이나 설계/검증 근거로 baseline 변경이 필요한 경우에는 그 unit 안에서 처리한다.
- 단순 bootstrap 누락 복구이고 active unit 책임이 아니라면 `bootstrap-baseline`으로 누락 파일만 보강할 수 있다.

# Execution Procedure

1. 저장소에서 active docs 루트와 baseline 파일 존재 여부를 확인한다.
2. `.stage-pilot/bootstrap/baseline.yaml`이 없거나 핵심 필드가 비어 있으면 저장소 관찰로 채울 수 있는 값과 질문이 필요한 값을 분리한다.
3. 저장소 관찰만으로 부족하면 최소 질문 세트를 사용해 사용자 선언 입력을 수집한다.
4. 적절한 baseline seed scaffold source를 해석한 뒤 `.stage-pilot/bootstrap/baseline.yaml`을 생성 또는 보강한다. 적절한 source가 없으면 저장소 관찰과 사용자 답변을 바탕으로 최소 seed를 직접 작성한다.
5. 누락된 디렉터리가 있으면 `docs/discovery`, `docs/srs`, `docs/batches`, `docs/releases`를 먼저 준비한다.
6. 필요한 논리 템플릿 경로를 현재 환경의 물리 경로로 해석한 뒤, 누락된 index 파일을 각 템플릿으로 생성한다.
7. seed 파일과 저장소 상태를 반영해 `docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md`를 생성 또는 보강한다.
8. 이미 존재하는 파일은 보존하고, 필요한 경우에만 누락 복구 또는 seed 반영 사실을 결과에 기록한다.
9. 저장소가 repo-local bootstrap helper를 제공하면 수동 파일 작성 전에 먼저 사용할 수 있는지 확인한다. helper를 사용할 때도 active index(`docs/discovery/index.md`, `docs/srs/index.md`, `docs/batches/index.md`, `docs/releases/index.md`)와 cross-cutting baseline 문서 4종(`docs/project-structure.md`, `docs/runtime-flows.md`, `docs/interface-contract.md`, `docs/data-model.md`)이 모두 실제로 생겼는지 별도로 확인한다.
10. 완료 후 다음 단계로 `new-discovery`를 사용해 첫 real Discovery를 시작하도록 안내한다.

# Output Expectations

- 생성 또는 복구한 파일 목록
- seed 파일 상태 (`created` | `preserved` | `updated`)
- baseline 문서 상태 (`created` | `preserved` | `missing-information`)
- index 문서 상태 (`created` | `preserved`)
- 첫 real Discovery에서 다뤄야 할 주제 후보 또는 다음 action

# Validation

- 생성한 파일 경로가 active docs 구조와 일치하는지 확인한다.
- `.stage-pilot/bootstrap/baseline.yaml`의 필수 필드가 비어 있지 않은지 확인한다.
- baseline 문서와 index에 남아 있는 플레이스홀더가 정말 사람 결정이 필요한 값인지 점검한다.
- `{{...}}`, unresolved template variables, accidental Python/format escaping artifacts, and generic `PLACEHOLDER`/`TBD` markers are treated as validation issues unless they are intentionally documented as human decisions still needed.
- 저장소가 repo-local doctor helper나 검증 스크립트를 제공하면 완료 전에 실행하고, warning도 가능한 한 수정한 뒤 재실행한다.
- baseline 문서의 `Project Summary`, `Primary Domain`, `Tech Stack`, `Primary Runtime`와 공통 계약 정보가 seed 및 저장소 관찰과 모순되지 않는지 확인한다.
- Discovery 문서를 생성하지 않았는지 확인한다.
- 생성 후 가능하면 일반 repository smoke validation도 실행한다. 예: `python3 -m compileall .`, `python3 -m pytest -q -o 'addopts='`.