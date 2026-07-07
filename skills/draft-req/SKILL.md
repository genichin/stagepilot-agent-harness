---
name: draft-req
description: "Use when: turning a confirmed Discovery into one or more requirement documents under `docs/srs/`, running /draft-req with a dcy-id or Discovery path, creating docs/srs/<Type>/req-XXX_<slug>.md files, updating docs/srs/index.md from FR/NFR input, or carrying forward constraints from docs/project-structure.md and docs/runtime-flows.md."
version: 1.0.4
author: Justin Ko
license: private
argument-hint: "예: dcy-001 또는 docs/discovery/dcy-001_20260424_krx-stock-picker-python-scaffold.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, requirements, drafting, documentation, sdlc]
    related_skills: [confirm-discovery, change-req, confirm-req, suggest-batch-reqs]
---

# Purpose

This skill converts a Discovery document into one or more requirement documents under `docs/srs/`, updates the SRS register, and writes the generated REQ references back to the source Discovery document.

Reference: template path portability guidance lives in `references/template-path-resolution.md`.

Reference: source-of-truth migrations that remove an old local implementation and route to a new canonical service can use the split pattern in `references/source-of-truth-migration-split-pattern.md`.

`docs/project-structure.md`와 `docs/runtime-flows.md`가 존재하면, REQ 작성 시 이 문서들을 공통 baseline 참조 문서로 읽고 필요한 구조 제약만 REQ에 반영한다.

# When to use

- `/draft-req dcy-001`처럼 confirmed Discovery를 REQ backlog로 정규화해야 할 때
- Discovery의 FR/NFR을 구현 가능한 requirement 문서로 분리해야 할 때
- `docs/srs/index.md`의 register와 Next Requirement ID를 함께 갱신해야 할 때
- Discovery가 구조 또는 runtime baseline 갱신을 요구할 때 이를 REQ backlog에 반영해야 할 때

## Do not use when

- source Discovery가 아직 `confirmed` 상태가 아니고, 아직 문제 정의나 범위 정리가 끝나지 않았을 때
- 기존 Discovery 문서를 검토/보강/승인해야 하는 단계일 때 (`review-discovery`, `confirm-discovery`가 더 적절함)
- 새 REQ를 만드는 것이 아니라 기존 REQ의 상태, acceptance criteria, 범위를 변경해야 할 때 (`change-req`가 더 적절함)
- 이미 승인된 REQ를 구현 batch로 묶는 단계일 때 (`suggest-batch-reqs`, `draft-batch`가 더 적절함)

# Inputs

- Discovery 식별자
	- `dcy-001` 같은 prefix
	- 전체 Discovery ID
	- `docs/discovery/<DISCOVERY_ID>.md` 경로
- 대상 Discovery 문서 본문
- `docs/project-structure.md` (존재하는 경우)
- `docs/runtime-flows.md` (존재하는 경우)
- 템플릿의 논리 경로
	- `stage-pilot/templates/srs/index.md`
	- `stage-pilot/templates/srs/req-template.md`

## Template path resolution

- 템플릿은 하나의 물리 경로만 고정하지 말고 `stage-pilot/templates/...`를 논리 경로로 취급한다.
- 물리 경로는 다음 순서로 해석한다.
	1. `.stage-pilot/templates/...`
	2. `~/.stage-pilot/templates/...`
- 여러 후보가 동시에 존재하면 가장 우선순위가 높은 한 곳만 사용하고, 서로 다른 설치 위치의 템플릿을 섞지 않는다.
- 템플릿 source path와 생성 target path를 혼동하지 않는다.
	- source: `stage-pilot/templates/...`
	- target: `docs/srs/index.md`, `docs/srs/<Type>/req-XXX_<slug>.md`
- 어떤 physical path를 선택했는지 생성 전에 내부적으로 확정하고, 경로 해석이 애매하면 이를 보고한다.

- Repository targets
	- `docs/srs/index.md`
	- `docs/srs/<Type>/req-XXX_<slug>.md`

# Core Rules

## 0. Entry gating and confirmed prerequisite

- source Discovery는 기본적으로 `confirmed` 상태여야 한다.
- source Discovery가 아직 `draft`이거나 confirmed 여부가 불명확하면, REQ drafting을 계속 진행하지 말고 그 사실을 먼저 보고한다.
- confirmed 전제가 충족되지 않으면 `review-discovery` 또는 `confirm-discovery`가 선행되어야 한다.
- 다만 사용자가 명시적으로 "초안 REQ를 미리 뽑아 달라"고 요청한 예외 상황에서는, 승인 전 초안임을 분명히 표시하고 `Proposed` 초안으로만 제한적으로 작성할 수 있다.

## 1. Baseline architecture reference rules

- `docs/project-structure.md`와 `docs/runtime-flows.md`는 REQ의 상세 본문을 대체하지 않지만, 구조 제약과 흐름 제약을 읽기 위한 공통 baseline 참조 문서로 사용한다.
- REQ에는 baseline 문서의 전체 구조나 전체 흐름을 복제하지 않는다. 구현에 필요한 제약과 acceptance 기준만 남긴다.
- source Discovery가 구조 또는 runtime baseline 갱신을 요구하면, REQ 후보에 baseline 문서 갱신 작업을 포함해야 한다.
- baseline 문서가 없고 source Discovery가 그 갭 보완을 직접 범위에 포함한다면, baseline 문서를 다루는 REQ를 누락하면 안 된다.
- baseline 문서가 없는데 source Discovery가 그 갭을 다루지 않는다면, `bootstrap-baseline` 선행 누락 가능성을 보고한다.

## 2. 입력 해석

- 입력이 prefix면 `docs/discovery/` 아래에서 일치하는 문서를 찾는다.
- 여러 후보가 나오면 임의 선택하지 않고 사용자 확인이 필요하다고 보고한다.
- `.stage-pilot/` 경로는 Discovery 문서 탐색 대상에서 제외한다.
- template source는 단일 고정 경로로 가정하지 않는다.
- `stage-pilot/templates/...`는 logical path로 취급하고, 실제 읽기 경로는 현재 workspace의 StagePilot 설치 형태에 맞게 해석한다.
- template source를 읽을 때는 아래 순서로 후보를 확인한다.
	1. `.stage-pilot/templates/...`
	2. `~/.stage-pilot/templates/...`
- 어떤 physical path를 선택했는지 생성 전에 내부적으로 확정하고, 경로 해석이 애매하면 이를 보고한다.

## 3. REQ 분해 원칙

- FR은 기본적으로 독립 구현과 독립 검증 가능 단위로 REQ 후보를 만든다.
- 하나의 FR이 과도하게 크면 복수 REQ로 분해한다.
- NFR은 독립 측정 가능성, 독립 backlog 가치, 운영 영향도가 충분할 때만 별도 REQ로 승격한다.
- 특정 FR 또는 batch 검증 기준에 흡수하는 편이 적절한 NFR은 별도 REQ를 만들지 말고 Notes에 연결 근거를 남긴다.
- baseline 문서 갱신 요구는 보통 `Documentation`, `Interface`, `Configuration` 중 가장 적절한 Type으로 분류한다.
- Discovery가 "기능 계약 + 성능/운영 기준 + baseline 문서 정렬"을 함께 요구하는 경우에는 다음 우선 분해 패턴을 먼저 검토한다.
	1. 기능 계약(상태 전이, 인터페이스, 실행 흐름) -> `Interface` 또는 가장 가까운 기능 Type
	2. 상태별 budget, latency, 처리 시간, 계측 의무 -> `Non-Functional`
	3. `docs/runtime-flows.md`/`docs/project-structure.md` 같은 baseline 정렬 -> `Documentation`
- 성능 수치가 구현 전 운영 계측값에 의존하더라도, 측정 경로와 목표 기준이 Discovery에 이미 정리돼 있으면 별도 `Non-Functional` REQ로 승격해 REQ 단계에서 evidence 수집을 요구하는 편을 우선한다.

## 4. Type 및 경로 규칙

- 아래 폴더 중 정확히 하나를 선택한다.
	- `Configuration`
	- `Data`
	- `Deployment`
	- `Documentation`
	- `Exception`
	- `Installation`
	- `Integration`
	- `Interface`
	- `Migration`
	- `Non-Functional`
	- `Testing`
- 새 REQ 경로는 `docs/srs/<Type>/req-XXX_<slug>.md` 형식을 사용한다.
- `REQ-XXX` 번호는 `docs/srs/index.md`의 `Next Requirement ID`를 source of truth로 사용한다.

## 5. 문서 작성 규칙

- `stage-pilot/templates/srs/req-template.md`에 해당하는 실제 template source를 해석한 뒤 문서를 만든다.
- 생성 대상 경로는 `docs/srs/<Type>/req-XXX_<slug>.md`다.
- `Status` 기본값은 `Proposed`다.
- `Intent`, `Requirement`, `Acceptance Criteria`, `Impacted Area`, `Notes`를 실제 문장으로 채운다.
- baseline 문서와 충돌하거나 baseline 문서를 갱신해야 하는 구조 제약이 있으면 `Impacted Area` 또는 `Notes`에 명시한다.
- 사람 승인 없이는 확정할 수 없는 항목은 비워 두지 말고 `Notes`에 결정 필요 또는 가정으로 명시한다.
- Change Log는 최초 생성 기록을 남긴다.

## 6. 인덱스 갱신 규칙

- REQ를 하나 이상 생성하면 `docs/srs/index.md`의 아래 항목을 함께 갱신한다.
	- `Next Requirement ID`
	- `Requirement Register`
	- `Recent Change Log Summary`
- 기존 `docs/srs/index.md`가 이미 존재하면, 먼저 현재 register/header 형식과 열 순서를 읽고 그 로컬 형식을 우선 보존한다.
- template의 예시 열(`ID, Title, Type, Status, Priority, Owner, Link`)은 기본 기준이지만, 기존 index가 다른 열 이름이나 순서를 사용 중이면 사용자나 저장소가 이미 채택한 형식을 임의로 템플릿 형식으로 갈아엎지 않는다.
- 기존 index에 없는 새 필드가 필요하면 가능한 한 기존 형식에 자연스럽게 확장하고, 대규모 형식 정규화는 별도 변경으로 다룬다.
- Register에는 현재 index 형식이 요구하는 최소 메타데이터를 누락 없이 추가한다.
- 기존 `docs/srs/index.md`가 이미 존재하면, template wording으로 통째로 덮어쓰지 말고 현재 저장소의 로컬 형식을 source of truth로 취급한다.
	- 기존 섹션 구조, 설명 문구, 표/리스트 형식, 열 순서는 가능한 한 유지한다.
	- `Next Requirement ID` 표현이 `- REQ-002` 형태인지, `- Current: \`REQ-002\`` 형태인지 등은 현재 파일 형식을 따른다.
	- 필요한 값만 in-place로 갱신하고, template source는 새 index bootstrap이 필요할 때만 사용한다.

## 7. Source Discovery 역참조 갱신 규칙

- REQ를 하나 이상 생성하면 source Discovery 문서의 `# 0. 문서 상태`에도 어떤 REQ가 생성됐는지 기록해야 한다.
- Discovery 문서에 `생성된 REQ 참조` 항목이 이미 있으면 생성된 REQ 목록으로 갱신하고, 없으면 `후속 Discovery 참조` 바로 아래에 추가한다.
- `생성된 REQ 참조`는 생성된 REQ 번호 순서대로 유지하고 중복을 허용하지 않는다.
- StagePilot doctor의 traceability parser는 `생성된 REQ 참조`가 포함된 같은 줄에서 REQ ID를 추출한다. 따라서 다중 bullet 상세 목록을 쓰더라도 헤더 줄 자체는 `- 생성된 REQ 참조: REQ-001, REQ-002`처럼 REQ ID를 같은 줄에 포함해야 한다.
- REQ별 경로 상세는 헤더 다음 줄에 bullet로 추가해도 되지만, 같은 줄 요약을 빼면 `orphan-req` warning이 발생할 수 있다.
- source Discovery 문서를 갱신했다면 `마지막 갱신 시각(KST)`도 함께 갱신한다.
- 생성된 REQ가 아직 없으면 `생성된 REQ 참조: 없음`을 유지한다.

# Execution Procedure

1. 입력에서 Discovery 경로를 확정한다.
2. Discovery 문서에서 FR/NFR, 범위 경계, 리스크, 성공 기준을 읽는다.
3. `docs/project-structure.md`와 `docs/runtime-flows.md`가 있으면 읽고, REQ에 남겨야 할 구조 제약과 흐름 제약을 추린다.
4. FR/NFR별 REQ 후보 목록을 만든다.
5. baseline 문서 갱신 또는 baseline 갭 보완 요구가 있으면 이를 반영한 REQ 후보를 포함한다.
6. 각 후보에 대해 Type, 제목, slug, Acceptance Criteria를 결정한다.
7. `docs/srs/index.md`의 다음 번호부터 순서대로 REQ 파일을 생성한다.
8. `docs/srs/index.md`를 갱신한다.
9. source Discovery 문서의 `생성된 REQ 참조`와 `마지막 갱신 시각(KST)`를 갱신한다.
10. 생성 결과와 제외한 NFR이 있으면 그 이유를 함께 보고한다.

# Output Expectations

- 생성된 REQ 파일 목록
- 각 REQ의 Type과 핵심 의도
- baseline 문서 참조 또는 생성/갱신 요구를 어떤 REQ에 반영했는지
- `docs/srs/index.md` 갱신 결과
- source Discovery 문서의 `생성된 REQ 참조` 갱신 결과
- 별도 REQ로 승격하지 않은 NFR 목록과 처리 이유

# Common Pitfalls

1. source Discovery가 아직 `confirmed`가 아닌데 REQ부터 만드는 실수
   - 이 경우 문제 정의와 범위가 흔들릴 수 있으므로 `review-discovery` 또는 `confirm-discovery`를 먼저 거친다.

2. NFR을 전부 별도 REQ로 승격하는 실수
   - 독립 측정 가능성, backlog 가치, 운영 영향이 약하면 FR 또는 batch 검증 기준에 흡수하는 편이 낫다.

3. baseline gap을 읽고도 관련 REQ를 만들지 않는 실수
   - source Discovery 범위에 baseline 보완이 포함되어 있으면, 그 갭을 다루는 REQ를 반드시 backlog에 포함한다.

4. template source와 generated target path를 혼동하는 실수
   - template source는 `stage-pilot/templates/...` logical path를 해석한 결과이고, 생성 대상은 `docs/srs/...`다.

5. `docs/srs/index.md`를 갱신하지 않고 REQ 파일만 만드는 실수
   - `Next Requirement ID`, `Requirement Register`, `Recent Change Log Summary`를 함께 갱신해야 register가 깨지지 않는다.

6. source Discovery 역참조를 빼먹는 실수
   - 생성된 REQ 참조와 `마지막 갱신 시각(KST)`를 source Discovery에도 반영해야 추적성이 유지된다.

7. `생성된 REQ 참조`를 bullet 목록으로만 쓰는 실수
   - `stagepilot-doctor.py`는 `생성된 REQ 참조` 문구가 있는 줄에서만 REQ ID를 추출한다.
   - 헤더 줄에 `REQ-001, REQ-002...`를 함께 넣고, 상세 경로는 다음 bullet에 둔다.
   - 검증에서 `orphan-req` warning이 나오면 Discovery의 같은 줄 REQ ID 요약을 먼저 확인한다.

# Verification Checklist

- [ ] source Discovery가 `confirmed` 상태인지 확인했다.
- [ ] Discovery 경로가 유일하게 확정되었고 prefix 충돌이 없다.
- [ ] `docs/project-structure.md`와 `docs/runtime-flows.md` 존재 여부를 확인했다.
- [ ] logical template path를 실제 physical path로 올바르게 해석했다.
- [ ] template source와 generated target path를 혼동하지 않았다.
- [ ] 모든 REQ가 `docs/srs/<Type>/req-XXX_<slug>.md` 형식을 따른다.
- [ ] `docs/srs/index.md`의 `Next Requirement ID`, `Requirement Register`, `Recent Change Log Summary`를 함께 갱신했다.
- [ ] source Discovery의 `생성된 REQ 참조`와 `마지막 갱신 시각(KST)`를 갱신했다.
- [ ] `생성된 REQ 참조` 헤더 줄 자체에 모든 생성 REQ ID가 포함되어 `stagepilot-doctor` traceability parser가 orphan warning 없이 읽을 수 있다.
- [ ] baseline 갭 보완이 source Discovery 범위에 포함되면 해당 REQ를 실제로 생성했다.
- [ ] 별도 REQ로 승격하지 않은 NFR은 이유를 함께 보고했다.