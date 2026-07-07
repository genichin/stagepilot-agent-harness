---
name: new-discovery
description: "Use when: deciding whether to update an existing Discovery document or start a new one, running /new-discovery with or without parameters, drafting docs/discovery/dcy-<id>_<YYYYMMDD>_<topic-slug>.md for a real product/service change, generating Discovery documents, or updating docs/discovery/index.md after baseline initialization is ready."
version: 1.0.2
author: Justin Ko
license: private
argument-hint: "예: 사용자 로그인 기능 추가 - OAuth2 소셜 로그인, 세션 관리, 로그아웃 처리"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, discovery, documentation, sdlc, planning]
    related_skills: [bootstrap-baseline, review-discovery, confirm-discovery, run-sdlc]
---

# Purpose

This skill decides whether an incoming request should update an existing Discovery document or start a new one, then drafts or updates Discovery documentation based on issues, user requests, meeting notes, or repository state.

입력이 없으면 현재 Discovery/SRS/batch/release 상태와 baseline 문서 상태를 읽어 새 Discovery가 필요한지 판정한다. baseline 초기화가 아직 끝나지 않은 저장소에서는 먼저 `bootstrap-baseline`으로 `docs/project-structure.md`, `docs/runtime-flows.md`, active index를 준비한 뒤 첫 real Discovery를 생성한다.

새 Discovery를 생성하기로 판정된 경우 generated output must follow this structure:

- `docs/discovery/dcy-<id>_<YYYYMMDD>_<topic-slug>.md`
- Update `docs/discovery/index.md`

# When to use

다음 상황에서 사용한다.

- 새로운 SDLC 주기를 시작해야 할 때
- 기존 SDLC의 요구사항, 범위, 성공 기준을 조정해야 하는데 새 주기 생성이 필요한지 먼저 판정해야 할 때
- 기존 Discovery의 Open Question(OQ)에 대해 사용자가 `dcy-002 oq-1 ...`처럼 답을 주거나 범위 결정을 내렸을 때
- `/new-discovery ...` 또는 파라미터 없는 `/new-discovery`로 Discovery 초안을 만들어야 할 때
- baseline 초기화가 완료된 뒤 첫 real Discovery를 시작해야 할 때
- 이슈/요청사항을 `docs/discovery/` 아래 표준 Discovery 문서로 전환해야 할 때
- Discovery 문서를 템플릿 기반으로 작성하되, 추론 가능한 내용을 실제 문장으로 채워야 할 때
- `docs/discovery/index.md`에 새 Discovery 링크를 추가해야 할 때

# Inputs

이 skill은 아래 입력을 사용한다.

- 이슈 식별 정보
	- GitHub issue link 또는 issue 번호
- 이슈 내용
	- 사용자 입력 원문 또는 이슈 본문 전체
	- 이슈 제목 또는 요청 요약
- SDLC 문맥
	- 기존 `docs/discovery/` 폴더 구조 및 파일 목록
	- 기존 `docs/srs/`, `docs/batches/`, `docs/releases/` 상태
	- 기존 `docs/discovery/index.md` 내용
	- `docs/project-structure.md`, `docs/runtime-flows.md` 존재 여부
	- 현재 시각 (KST)
- 저장소 문맥
	- 현재 저장소 상태
	- 저장소 현황 탐색 결과
- 템플릿의 논리 경로
	- `stage-pilot/templates/discovery/discovery.md`
	- `stage-pilot/templates/discovery/index.md`
	- `stage-pilot/templates/project-structure.md`
	- `stage-pilot/templates/runtime-flows.md`

## Template path resolution

- 템플릿은 하나의 물리 경로만 고정하지 말고 `stage-pilot/templates/...`를 논리 경로로 취급한다.
- 물리 경로는 다음 순서로 해석한다.
	1. `.stage-pilot/templates/...`
	2. `~/.stage-pilot/templates/...`
- 여러 후보가 동시에 존재하면 가장 우선순위가 높은 한 곳만 사용하고, 서로 다른 설치 위치의 템플릿을 섞지 않는다.
- 템플릿 source path와 생성 target path를 혼동하지 않는다.
	- source: `stage-pilot/templates/...`
	- target: `docs/discovery/<DISCOVERY_ID>.md`, `docs/discovery/index.md`, 이후 필요 시 참조하는 `docs/project-structure.md`, `docs/runtime-flows.md`

입력 해석 규칙:
- GitHub issue link 또는 issue 번호가 있으면 해당 이슈의 제목, 본문, 링크를 기준 입력으로 사용한다.
- 사용자 입력 원문과 요청 요약은 이슈 링크가 없거나 보조 설명이 필요할 때 함께 사용한다.
- 파라미터가 없으면 저장소 상태를 먼저 분류한 뒤 추천 Discovery 또는 진행 중인 반복 유지 여부를 판단한다.
- 저장소 현황 탐색 결과는 `# 3. 문제점의 요약` 중 `현재 상태` 작성에 사용한다.

# Core Rules

## 0. Baseline 문서 정책

- `docs/project-structure.md`와 `docs/runtime-flows.md`는 SDLC의 별도 governance unit가 아니라, 이후 Discovery/REQ/Batch/Release에서 공통으로 참조하는 cross-cutting baseline 문서다.
- baseline 초기화는 첫 Discovery와 분리된 `bootstrap-baseline` 경로를 기본값으로 사용한다.
- baseline 문서와 active index가 모두 없는 저장소에서는 `new-discovery`가 Discovery를 생성하기 전에 `bootstrap-baseline`을 우선 추천하고 중단한다.
- baseline 문서가 이미 있고, Discovery가 구조/런타임 변경을 다룰 때만 해당 Discovery 안에 baseline 문서 갱신 요구를 포함한다.

## 1. 파라미터 없는 실행 판정 규칙

- `/new-discovery`가 파라미터 없이 실행되면 먼저 아래 경로를 점검한다.
	- `docs/discovery/`
	- `docs/srs/`
	- `docs/batches/`
	- `docs/releases/`
	- `docs/project-structure.md`
	- `docs/runtime-flows.md`
- 파라미터 없는 실행은 아래 3가지 저장소 상태 중 하나로 판정한다.
	- `no-history`: Discovery와 후속 SDLC 문서가 사실상 없고 첫 반복을 시작해야 하는 상태
	- `active-cycle`: draft/review Discovery, Proposed REQ, 진행 중 batch, 미정리 release처럼 활성 unit가 존재해 파라미터 없는 실행만으로는 다음 반복 추천이 모호한 상태
	- `ready-for-next-iteration`: active unit는 없고 새 반복을 시작할 준비가 된 상태
- `no-history`이고 baseline 문서 또는 active index가 없으면 `bootstrap-baseline`을 우선 추천하고 새 Discovery를 생성하지 않는다.
- `no-history`이지만 baseline 초기화가 끝나 있으면 첫 real Discovery를 생성한다.
- `active-cycle`이면 새 Discovery를 생성하지 않고 중단한다. 대신 현재 반복을 계속 진행하도록 `run-sdlc` 또는 해당 후속 skill을 추천한다.
- `ready-for-next-iteration`이면 이전 Discovery, SRS, 구현 상태, baseline 문서 차이를 읽고 추천 follow-up Discovery를 생성한다.
- `ready-for-next-iteration`에서 후보 ranking만 먼저 필요하면 `suggest-next-discovery`를 사용하고, 실제 문서 생성이 확정되면 `new-discovery`로 이어 간다.
- baseline 문서가 없고 active unit도 없다면, follow-up Discovery보다 `bootstrap-baseline`을 우선한다.

## 2. 기존 Discovery 갱신 vs 새 Discovery 생성 판정 규칙

- 사용자가 기존 Discovery ID(`dcy-002` 등)와 OQ 번호(`oq-1`, `OQ-2` 등)를 함께 지정하면 기본 판정은 `기존 Discovery 갱신`이다. 이때 새 Discovery를 만들거나 index에 새 행을 추가하지 않는다.
- OQ 답변 갱신은 단순히 OQ 상태만 바꾸지 않는다. 결정 내용을 관련 FR/NFR, In Scope/Out of Scope, 리스크, 가정, 성공 기준, REQ 인계 체크, `# 10. 사용자 결정 필요 항목 요약`, Freeze rationale에 함께 반영한다.
- OQ가 `Answered`가 되면 `# 8. REQ로 넘기기 전 확인 체크`의 “모든 오픈 질문 없음” 항목도 실제 잔여 Open OQ 여부에 맞게 갱신한다.
- OQ 답변으로 breaking-change 정책이 확정된 경우(예: compatibility fallback 없이 완전 제거), 리스크를 숨기지 말고 “의도된 breaking change”로 쓰고 완화 방안은 acceptance criteria/문서/테스트 검증으로 둔다.
- 기존 주기 후보 탐색과 비교는 아래 `확인 절차`를 따른다.
- 후보 문서가 있고 아래 조건을 모두 만족하면 기존 Discovery를 갱신한다.
	- 변경이 기존 문제 정의와 핵심 사용자 시나리오를 유지한다.
	- FR/NFR 변경이 문구 명확화, 측정 가능성 보강, 범위 경계의 미세 조정, 우선순위 재정렬 수준이다.
	- 요구사항 삭제 또는 수정이 기존 REQ, batch planning, batch design, implementation 산출물을 사실상 무효화하지 않는다.
	- 대상 Discovery가 아직 초기 정리 단계이거나, 후속 단계 문서가 있어도 변경 영향이 국소적이라 동일 문서 안에서 추적 가능하다.
- 아래 조건 중 하나라도 만족하면 새 Discovery를 생성한다.
	- FR/NFR 삭제 또는 수정이 범위, 이해관계자, 핵심 사용자 시나리오, 성공 기준을 실질적으로 바꾼다.
	- 기존 하위 단계 문서나 구현 결과를 다시 써야 할 정도로 설계/구현 전제가 깨진다.
	- 기존 Discovery가 사실상 Freeze 이후 단계로 진행되어 변경 이력을 같은 문서에 계속 누적하면 책임 경계가 흐려진다.
	- 운영 환류, 새로운 이슈, 정책 전환 등으로 후속 반복을 독립 주기로 추적하는 편이 명확하다.
- 기존 Discovery를 더 이상 기준으로 쓰지 않더라도 기존 문서를 삭제하지 않는다. 새 문서를 생성하는 경우 기존 문서는 참조 대상으로 유지하고, 대체 또는 후속 관계를 문서에 남긴다.
- 판정 결과는 반드시 아래 둘 중 하나로 명시한다.
	- `기존 Discovery 갱신`
	- `새 Discovery 생성`

### 확인 절차

- 입력 원문 또는 추천 Discovery 주제에서 아래 식별 정보를 먼저 추출한다.
	- GitHub issue 번호 또는 링크
	- 이슈 제목의 핵심 명사
	- 기능명, 모듈명, 동사, 영향 범위 키워드
- `docs/discovery/` 아래 기존 문서를 탐색할 때는 `.stage-pilot/` 경로를 제외하고 아래 순서로 후보를 찾는다.
	- issue 번호 또는 링크의 정확 일치
	- 이슈 제목과 파일명 slug의 핵심 키워드 일치
	- 기존 Discovery 문서 안의 문제 정의, FR/NFR, 범위 경계 키워드 일치
- 후보 문서가 하나 이상 발견되면 각 후보마다 아래 항목을 비교한다.
	- 같은 문제 정의 또는 같은 기능 묶음을 다루는지
	- 현재 단계가 Discovery, REQ 정제, batch delivery, release 이후 어디까지 진행됐는지
	- 이번 변경이 기존 FR/NFR의 미세 조정인지, 핵심 요구사항 폐기 또는 재정의인지
	- 기존 하위 단계 문서와 구현 산출물을 유지 가능한지, 다시 작성해야 하는지
- 후보가 없으면 기본 판정은 `새 Discovery 생성`이다.
- 후보가 하나이고 판정 규칙에 명확히 부합하면 해당 후보를 기준으로 자동 판정한다.
- 후보가 여러 개이거나, 하나의 후보라도 `기존 Discovery 갱신`과 `새 Discovery 생성` 사이에서 명확히 갈리지 않으면 임의로 진행하지 않는다.
	- 후보 문서 경로 목록과 각 후보의 비교 근거를 사용자에게 보고한다.
	- 사용자 확인 전에는 새 폴더 생성이나 기존 문서 갱신을 하지 않는다.
- 최종 판정 결과에는 선택된 대상 문서 경로 또는 새로 만들 Discovery 생성 사유를 반드시 함께 기록한다.

## 3. Discovery ID 규칙

- `docs/discovery/` 아래 기존 문서 중 `dcy-<3자리>_` 패턴의 최대 번호를 찾는다.
- 다음 번호를 3자리 zero-pad로 계산한다.
- 오늘 날짜를 `YYYYMMDD` 형식으로 구한다.
- 사용자 입력 원문, 추천 Discovery 제목, 이슈 본문 전체, GitHub issue link에서 `topic-slug`를 만든다.
- `topic-slug`는 소문자 kebab-case의 형태로 만든다.
- slug 규칙:
	- 영문/숫자 외 문자는 `-`로 치환
	- 연속 `-`는 하나로 축약
	- 시작/끝 `-` 제거
	- 결과가 비면 `untitled` 사용
- 최종 `DISCOVERY_ID`는 `dcy-<id>_<YYYYMMDD>_<topic-slug>` 형식이어야 한다.

## 4. 문서 생성/갱신 규칙

- 판정 결과가 `새 Discovery 생성`이면 새 파일을 `docs/discovery/<DISCOVERY_ID>.md` 경로로 생성한다.
- `새 Discovery 생성`인 경우 `stage-pilot/templates/discovery/discovery.md`에 해당하는 실제 template source를 해석한 뒤 Discovery 문서를 생성한다.
- `docs/discovery/index.md`가 없으면 `stage-pilot/templates/discovery/index.md`에 해당하는 실제 template source를 해석한 뒤 생성한다.
- Discovery가 구조/런타임 baseline 갭을 직접 다루는 경우, `stage-pilot/templates/project-structure.md`와 `stage-pilot/templates/runtime-flows.md`를 이후 산출물의 논리 템플릿 참조로 취급한다.
- `기존 Discovery 갱신`이면 대상 Discovery 문서를 갱신한다.
- 동일 경로가 이미 있으면 덮어쓰지 말고 다음 ID를 재계산한다.
- 불필요한 파일은 만들지 않는다.

## 5. Discovery 초안 작성 원칙

- 입력 문장이 짧더라도 기능 목적, 예상 사용자, 산출물, 성공 조건을 합리적으로 추론해 초안을 작성한다.
- 입력만으로 추론 가능한 내용은 플레이스홀더로 남기지 말고 실제 문장으로 채운다.
- 사용자 승인, 외부 데이터, 정책 결정, 확정 범위 경계처럼 추론만으로 확정하면 안 되는 항목만 플레이스홀더로 남긴다.
- 공란은 허용하지 않는다.
- 합리적 기본안을 제시할 수 있으면 초안 문장으로 채운다.
- 사용자 확인이 반드시 필요하면 관련 본문에는 최소 플레이스홀더를 남기고 `# 10. 사용자 결정 필요 항목 요약`에 정리한다.
- `기존 Discovery 갱신`인 경우 FR/NFR 변경 또는 삭제 이유, 영향 받는 하위 단계, 기존 문서와의 차이를 문서 안에 명시해 변경 근거를 남긴다.
- Discovery가 구조/런타임 baseline 변경을 직접 다루는 경우 `# 4. 이번에 정의할 변경`, `# 5. 요구사항 목록`, `# 9. 파일 처리 결과`에 `docs/project-structure.md`와 `docs/runtime-flows.md` 갱신 요구를 명시한다.

## 6. 플레이스홀더 유지 규칙

- 사용자 승인 전 확정되면 안 되는 정책/범위/산출물 위치/대상 독자 결정은 본문에도 플레이스홀더를 남긴다.
- `# 10. 사용자 결정 필요 항목 요약`의 항목은 반드시 아래 형식 중 하나를 사용한다.
	- `{{DECIDE_*}}`
	- `{{CONFIRM_*}}`
	- `{{DATA_*}}`
- `TBD` 같은 일반 문자열보다 의미가 드러나는 플레이스홀더를 우선 사용한다.

# Discovery Sections To Fill

다음 섹션은 자동으로 채워야 한다.

## `# 1. 계획 상태 요약`

- `해석` 2줄은 입력 요청 또는 파라미터 없는 실행의 저장소 상태 해석을 바탕으로 직접 작성한다.

## `# 0. 문서 상태`

- `새 Discovery 생성`이면 `대체됨`, `후속 주기 참조` 기본값은 `없음`으로 둔다.
- 기존 Discovery를 대체하거나 이어받는 새 Discovery를 만드는 경우, 이전 Discovery 문서에도 해당 참조 필드를 갱신한다.
- `기존 Discovery 갱신`이면 기존 참조 값을 보존하고, 새 관계가 확정된 경우에만 관련 필드를 갱신한다.

플레이스홀더 치환 규칙:
- `{{DISCOVERY_ID:dcy-<3자리>_<YYYYMMDD>_<topic-slug>}}` -> 계산한 `DISCOVERY_ID`
- `{{SUPERSEDED_BY_DISCOVERY:없음 또는 docs/discovery/<DISCOVERY_ID>.md}}` -> `없음` 또는 대체 Discovery 경로
- `{{FOLLOW_UP_DISCOVERY_REF:없음 또는 docs/discovery/<DISCOVERY_ID>.md}}` -> `없음` 또는 후속 Discovery 경로

## `# 2. 요구사항 판정 결과`

- 기본값은 `신규`로 둔다.
- 입력만으로 명백한 중복/유사라고 판단 가능한 경우에만 다르게 쓴다.
- 근거 2줄도 직접 작성한다.

## `# 3. 문제점의 요약`

- 현재 상태, 기대 상태, 이해관계자, 주요 사용자 시나리오를 입력 기반으로 채운다.
- 특히 `현재 상태`는 저장소 탐색 결과와 baseline 문서 존재 여부를 반영해야 한다.

## `# 4. 이번에 정의할 변경`

- 핵심 변경 항목 1~3개를 직접 작성한다.
- Discovery가 구조 또는 runtime baseline 갭을 다루면 baseline 문서 갱신을 핵심 변경 항목에 포함한다.
- `영향 범위`의 코드/문서/운영 영향도 추론해 채운다.

## `# 5. 요구사항 목록`

- FR 2개 이상, NFR 1개 이상을 직접 작성한다.
- Discovery가 구조 또는 runtime baseline 갭을 다루는 경우, `docs/project-structure.md`와 `docs/runtime-flows.md` 갱신 요구를 FR에 포함한다.
- In Scope/Out of Scope는 초안 수준으로 제안한다.
- 사용자 승인 없이는 확정할 수 없는 범위 경계는 플레이스홀더로 남긴다.

## `# 6. 리스크/가정 목록`

- 리스크 2개 이상, 가정 2개 이상을 직접 작성한다.
- 오픈 질문은 정말 결정이 필요한 경우에만 남긴다.

## `# 7. 초기 성공 기준`

- 성공 기준 2개 이상을 작성한다.
- Discovery가 구조 또는 runtime baseline 변경을 다루는 경우 baseline 문서와 이후 산출물 참조 가능성을 성공 기준에 연결한다.
- 각 성공 기준에 대해 측정 방식과 데이터 출처 초안을 작성한다.

## `# 9. 파일 처리 결과`

- 생성 결과와 최소 참조 문서를 채운다.
- Discovery가 구조 또는 runtime baseline 갭을 다루면 `stage-pilot/templates/project-structure.md`와 `stage-pilot/templates/runtime-flows.md`를 참조 문서에 포함한다.
- 참조 문서가 없으면 `없음`이라고 쓴다.

## `# 10. 사용자 결정 필요 항목 요약`

- 자동 추론으로 확정할 수 없는 항목만 `DECIDE`, `CONFIRM`, `DATA`에 넣는다.
- 이 섹션 항목은 설명문이 아니라 플레이스홀더 형식으로 남긴다.

## `# 11. Discovery Freeze`

- `Handoff Decision` 기본값은 `보류`다.
- `Handoff Rationale`에는 현재 상태를 짧게 적는다.
	- 예: `초기 Discovery 초안 생성 완료, REQ 초안 작성 전 사용자 확인 필요`

# Repository Exploration

Discovery 문서의 `# 3. 문제점의 요약` 중 `현재 상태`를 채우기 위해 저장소 현황 탐색을 수행한다.

1. 이슈 원문 또는 추천 주제에서 핵심 키워드(기능명, 모듈명, 동사)를 추출한다.
2. 키워드를 기반으로 저장소에서 관련 파일, 디렉터리, 함수, 기존 문서를 탐색한다.
3. 탐색 범위는 아래와 같다.
	- 소스 파일: `.ts`, `.js`, `.py`, `.go`, `.java` 등
	- 설정 파일
	- 기존 `docs/` 문서
4. 아래 항목은 제외한다.
	- 테스트 파일
	- 의존성 잠금 파일 (`package-lock.json`, `.lock`)
5. 탐색 결과에서 아래 내용을 추출한다.
	- 관련 파일 경로 목록 (최대 10개)
	- 현재 구현 방식 요약 (함수명, 클래스명, 주요 로직 1~3줄)
	- 현재 상태에서 이슈 원문이 지적하는 문제가 실제로 존재하는지 여부
	- `docs/project-structure.md`, `docs/runtime-flows.md` 존재 여부와 최신성 판단에 필요한 단서
6. 관련 파일을 찾지 못하면 `관련 파일 없음 — 신규 기능으로 추정`으로 기록한다.
7. 탐색 결과는 `# 3. 문제점의 요약`의 `현재 상태` 기술에만 반영한다.

# Execution Procedure

다음 순서대로 작업한다.

1. 입력 원문이 있으면 이슈명을 한 문장으로 정리하고, 없으면 저장소 상태를 먼저 분류한다.
2. 파라미터 없는 실행이면 discovery/srs/batches/releases/baseline 문서 상태를 읽어 `no-history`, `active-cycle`, `ready-for-next-iteration` 중 하나로 판정한다.
3. 입력 원문이 없고 `active-cycle`이면 새 Discovery 자동 생성을 중단하고 현재 반복을 계속 진행해야 하는 이유와 추천 skill을 보고한다.
4. `no-history`이고 baseline 문서 또는 active index가 비어 있으면 `bootstrap-baseline`을 우선 추천하고 Discovery 생성을 중단한다.
5. `no-history`이지만 baseline 초기화가 끝나 있으면 첫 real Discovery 생성 대상으로 확정한다.
6. 입력 원문이 없고 `ready-for-next-iteration`이면 이전 Discovery, SRS, 구현 상태, baseline 문서 상태를 바탕으로 추천 follow-up Discovery 주제를 정한다.
7. 입력 원문, 이슈 링크, 신규 요구 요약처럼 명시적 신규 입력이 있으면 `active-cycle` 여부와 무관하게 위 `확인 절차`에 따라 issue 번호/링크, 제목 키워드, 기능명, 범위 키워드를 추출하고 기존 후보 주기를 찾는다.
8. 입력 원문이 없고 추천 Discovery 주제가 정해졌으면 위 `확인 절차`에 따라 issue 번호/링크, 제목 키워드, 기능명, 범위 키워드를 추출하고 기존 후보 주기를 찾는다.
9. 후보 비교 결과를 바탕으로 `기존 Discovery 갱신` 또는 `새 Discovery 생성`으로 판정한다.
10. `active-cycle` 상태에서 명시적 신규 입력으로 새 Discovery를 진행하는 경우, 기존 active unit와의 범위 충돌 여부와 병렬 진행 사유를 함께 기록한다.
11. 판정이 애매하면 사용자 확인 전까지 자동 생성 또는 자동 갱신을 중단하고 후보와 근거를 보고한다.
12. 저장소 현황 탐색을 수행한다.
13. 판정 결과가 `새 Discovery 생성`이면 기존 `docs/discovery/` 경로를 다시 스캔해 다음 번호를 계산한다.
14. `새 Discovery 생성`이면 날짜와 slug를 조합해 `DISCOVERY_ID`를 만든다.
15. `새 Discovery 생성`이면 `docs/discovery/<DISCOVERY_ID>.md` 파일을 생성한다.
16. `기존 Discovery 갱신`이면 대상 Discovery 문서를 갱신한다.
	- 사용자가 `dcy-<id> oq-<n>` 형태로 답변하면 해당 Discovery 파일을 열어 OQ 항목을 찾아 `상태`, `처리 방안`, `종료 조건`을 갱신한다.
	- 답변 내용이 범위나 요구사항을 바꾸면 FR/NFR, In Scope/Out of Scope, 리스크, 가정, 성공 기준, 측정 방식, REQ 인계 체크, 사용자 결정 필요 항목, Freeze rationale까지 일관되게 반영한다.
	- 답변된 OQ를 별도 새 heading으로 옮기지 말고 템플릿 heading 구조를 유지한다.
17. 아래 플레이스홀더를 우선 치환한다.
	- `{{DOC_STATUS:draft|review|confirmed}}` -> `draft`
	- `{{DISCOVERY_ID:dcy-<3자리>_<YYYYMMDD>_<topic-slug>}}` -> 계산한 `DISCOVERY_ID`
	- `{{ISSUE_NAME:짧은 한글 또는 영문 이슈명}}` -> 입력 원문 또는 요약 이슈명
	- `{{ISSUE_NAME}}` -> 입력 원문 또는 요약 이슈명
	- `{{CREATED_AT_KST:TBD}}` -> 현재 시각(KST)
	- `{{CREATED_AT_KST}}` -> 현재 시각(KST)
	- `{{UPDATED_AT_KST:TBD}}` -> 현재 시각(KST)
	- `{{UPDATED_AT_KST}}` -> 현재 시각(KST)
	- `{{SUPERSEDED_BY_DISCOVERY:없음 또는 docs/discovery/<DISCOVERY_ID>.md}}` -> `없음` 또는 대체 Discovery 경로
	- `{{FOLLOW_UP_DISCOVERY_REF:없음 또는 docs/discovery/<DISCOVERY_ID>.md}}` -> `없음` 또는 후속 Discovery 경로
	- `{{OUTPUT_PATH}}` -> 생성 파일 경로
	- `{{FILE_RESULT:생성|갱신|미생성}}` -> `생성`
18. Discovery가 구조 또는 runtime baseline 갭을 직접 다루면 `docs/project-structure.md`와 `docs/runtime-flows.md` 갱신 요구를 핵심 변경과 FR에 반영한다.
19. `기존 Discovery 갱신`인 경우 `{{OUTPUT_PATH}}`와 `{{FILE_RESULT}}`는 갱신 대상 파일과 `갱신`으로 해석한다.
20. `새 Discovery 생성`이면서 기존 Discovery를 대체하거나 이어받는 경우, 기존 Discovery 문서에 `대체됨` 또는 `후속 주기 참조` 필드를 새 문서 경로로 갱신한다.
21. Discovery 문서에서는 추론 가능한 플레이스홀더를 적극적으로 실제 내용으로 치환한다.
22. 추론 불가능하거나 사용자 확인이 필요한 항목만 플레이스홀더로 남긴다.
23. `새 Discovery 생성`인 경우에만 `docs/discovery/index.md` 전역 인덱스에 새 행을 추가한다.
24. `기존 Discovery 갱신`인 경우 전역 인덱스에 새 행을 추가하지 않는다.

# Global Index Rules

- `docs/discovery/index.md`가 없으면 아래 골격으로 새로 만든다.
- `## Discovery 목록`에는 새 행을 추가한다.
- 형식은 아래와 같다.

`| <DISCOVERY_ID> | <YYYYMMDD> | <ISSUE_NAME> | Discovery: ./<DISCOVERY_ID>.md | draft |`

- 테이블 구조 자체는 바꾸지 않는다.
- `기존 Discovery 갱신`으로 판정된 경우 `docs/discovery/index.md`에 새 행을 추가하지 않는다.
- 같은 `DISCOVERY_ID`가 이미 있으면 중복 추가하지 않는다.

# Output Expectations

작업이 끝나면 아래 내용을 보고할 수 있어야 한다.

- 판정 결과 (`기존 Discovery 갱신` 또는 `새 Discovery 생성`)
- 파라미터 없는 실행이면 저장소 상태 분류 (`no-history` | `active-cycle` | `ready-for-next-iteration`)
- `active-cycle` 상태였다면 자동 중단 사유 또는 병렬 Discovery 허용 사유
- 대상 `DISCOVERY_ID`
- 확인에 사용한 후보 Discovery 목록과 각 후보의 비교 근거
- 새 Discovery인 경우 생성한 파일 경로
- 기존 Discovery 갱신인 경우 갱신한 파일 경로
- 기존 Discovery와의 대체 또는 후속 참조 갱신 결과
- `docs/discovery/index.md` 갱신 결과 또는 미갱신 사유
- `docs/project-structure.md`, `docs/runtime-flows.md` baseline 상태와 Discovery 반영 결과
- 저장소 현황 탐색 결과
- 자동으로 채운 Discovery 핵심 섹션 요약
- 사용자 확인이 필요해 플레이스홀더로 남긴 항목 요약

# Validation

완료 전에 아래를 확인한다.

## Template fidelity check

When the user asks to follow the StagePilot template exactly, or when generating a Discovery from a repository-local template, validate template fidelity before final reporting.

- Compare the generated Discovery heading list against the resolved `stage-pilot/templates/discovery/discovery.md` heading list.
- Missing headings must be zero.
- Extra headings must be zero; do not add convenience headings such as `## 확정된 DECIDE` or `## 확정된 CONFIRM` unless the template itself contains them.
- Preserve the template's top-level and subsection ordering even when some sections have no unresolved items.
- Put explicit user decisions into the relevant body sections, requirements, assumptions, or Freeze rationale. Keep `# 10. 사용자 결정 필요 항목 요약` focused on unresolved `{{DECIDE_*}}`, `{{CONFIRM_*}}`, and `{{DATA_*}}` placeholders, or state that there are no remaining items without adding new headings.
- A quick deterministic check can read both files and compare all Markdown heading lines (`line.startswith('#')`) before finalizing.

- `새 Discovery 생성`이면 생성 경로가 `docs/discovery/<DISCOVERY_ID>.md` 형식을 만족하는지
- `새 Discovery 생성`이면 Discovery 문서가 생성되었는지
- `새 Discovery 생성`이면 `docs/discovery/index.md`가 신규 생성 또는 올바르게 갱신되었는지
- Discovery가 구조 또는 runtime baseline 갭을 다루면 `docs/project-structure.md`, `docs/runtime-flows.md` 갱신 요구가 문서 본문에 포함됐는지
- `기존 Discovery 갱신`이면 대상 Discovery 문서만 갱신되었는지
- `기존 Discovery 갱신`이면 새 `DISCOVERY_ID`와 불필요한 파일이 생성되지 않았는지
- 기존 Discovery 후보 탐색 결과와 판정 근거가 보고 가능한 형태로 정리되었는지
- 파라미터 없는 실행에서 `active-cycle` 상태라면 사용자 확인이나 명시적 신규 입력 없이 새 Discovery를 자동 생성하지 않았는지
- `active-cycle` 상태에서 명시적 신규 입력으로 새 Discovery를 생성한 경우, 기존 active unit와의 범위 충돌 여부와 판정 근거가 함께 정리됐는지
- 판정이 애매한 경우 사용자 확인 없이 새 폴더 생성이나 기존 문서 갱신을 진행하지 않았는지
- `대체됨`, `후속 주기 참조` 필드가 `없음` 또는 유효한 Discovery 경로로 채워졌는지
- 새 Discovery가 기존 Discovery의 대체 또는 후속 반복이라면 기존 Discovery의 참조 필드가 함께 갱신되었는지
- 추론 가능한 섹션은 실제 문장으로 채워졌는지
- 사용자 확인이 필요한 항목만 플레이스홀더로 남았는지