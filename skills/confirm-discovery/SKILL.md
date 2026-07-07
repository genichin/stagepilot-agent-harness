---
name: confirm-discovery
description: "Use when: running /confirm-discovery with dcy-xyz or a Discovery path, re-checking the current repository state against docs/discovery/*.md, filling AI-resolvable placeholders or inconsistencies, and promoting the Discovery to confirmed when it is ready for REQ drafting in the Requirements phase."
version: 0.9.1
author: Justin Ko
license: private
argument-hint: "예: dcy-001 또는 docs/discovery/dcy-001_20260424_krx-stock-picker-python-scaffold.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, discovery, approval, quality, sdlc]
    related_skills: [new-discovery, review-discovery, draft-req]
---

# Purpose

This skill revalidates an existing Discovery document against the current repository state, fills anything the AI can resolve from local evidence, and promotes the document to `confirmed` only when REQ drafting handoff has no remaining blockers.

이 skill의 결과는 아래 두 경우로 나뉜다.

- 확인 결과 승인 가능이면 대상 Discovery 문서를 `confirmed`로 전환하고 `docs/discovery/index.md`의 해당 행 상태를 함께 갱신한다.
- 승인까지는 불가하더라도 AI가 근거 있게 채울 수 있는 항목이 있으면 문서를 먼저 보강한다. 단, 이 경우 `confirmed` 전환과 REQ drafting 준비 플래그 변경은 하지 않는다.

# When to use

다음 상황에서 사용한다.

- `/confirm-discovery dcy-xyz` 형태로 기존 Discovery를 최종 확인해야 할 때
- `docs/discovery/` 아래 Discovery 초안 문서를 REQ 초안 작성 가능 상태로 승격해야 할 때
- 현재 저장소 구현 상태를 다시 확인해 Discovery 본문의 사실 관계를 정정하거나 보강해야 할 때
- 문서 안의 플레이스홀더 중 AI가 근거 있게 채울 수 있는 항목을 먼저 정리한 뒤 승인 가능 여부를 판정해야 할 때
- `docs/discovery/index.md`의 상태가 실제 Discovery 상태와 일치하는지 함께 맞춰야 할 때

다음 상황에는 이 skill을 기본 경로로 사용하지 않는다.

- Discovery 품질 점검, 누락 점검, OQ 후보 정리만 먼저 하고 싶을 때
  - 이 경우 `review-discovery`를 사용한다.
- 현재 문서가 사실상 새 Discovery 생성 또는 대규모 범위 재정의를 필요로 할 때
  - 이 경우 `new-discovery`로 새 주기를 시작하거나 기존 Discovery를 재작성해야 한다.
- 승인자 지정, 정책 확정, 외부 확인 결과처럼 사람 판단 또는 외부 근거가 먼저 필요한 상태일 때
  - 이 경우 confirm 없이 보류하고 필요한 결정을 먼저 해소한다.

# Inputs

이 skill은 아래 입력을 사용한다.

- Discovery 식별자
    - `dcy-001` 같은 축약 ID
    - `dcy-001_20260424_topic-slug` 같은 전체 Discovery ID
    - `docs/discovery/<DISCOVERY_ID>.md` 같은 직접 경로
- Discovery 문서 본문
- `docs/discovery/index.md`
- `docs/project-structure.md` (존재하는 경우)
- `docs/runtime-flows.md` (존재하는 경우)
- 현재 저장소 구현 상태
    - 관련 소스 파일
    - 설정 파일
    - 관련 문서
- 현재 시각 (KST)

# Core Rules

## 1. 입력 해석 규칙

- 입력이 `dcy-001`처럼 prefix만 주어지면 `docs/discovery/` 아래에서 해당 prefix로 시작하는 문서를 찾는다.
- 입력이 전체 Discovery ID면 `docs/discovery/<DISCOVERY_ID>.md`를 직접 찾는다.
- 입력이 파일 경로면 해당 경로를 그대로 사용한다.
- 매칭 결과가 0개면 자동 진행하지 않고 사용자에게 입력을 재확인하도록 알린다.
- 같은 prefix에 대해 여러 문서가 매칭되면 임의 선택하지 않고 후보 목록을 보여 준 뒤 사용자 확인을 요청한다.
- `.stage-pilot/` 경로는 탐색 대상에서 제외한다.

## 2. 현재 구현 상태 재확인 규칙

- 현재 구현 상태 확인은 요구사항이 이미 모두 구현되었는지 검사하는 절차가 아니다.
- 이 확인의 목적은 Discovery의 `현재 상태`, `영향 범위`, `성공 기준`, `체크 항목`, `사용자 결정 필요 항목`이 저장소 현실과 맞는지 검증하는 것이다.
- `docs/project-structure.md`, `docs/runtime-flows.md`가 존재하면 Discovery의 구조 설명, 영향 범위, runtime flow 설명이 baseline과 모순되지 않는지도 함께 확인한다.
- 구현 부재 자체는 차단 사유가 아니다. Discovery가 애초에 신규 작업을 정의하는 문서라면 코드가 없는 상태도 정상일 수 있다.
- 현재 코드/문서에 변경 대상 구현이 아직 남아 있는 것도, Discovery가 그 잔여물을 `현재 상태`와 `향후 구현 대상`으로 정확히 기록하고 있으면 차단 사유가 아니다.
- 차단이 되는 경우는 아래와 같다.
    - 문서가 이미 존재한다고 적은 구현이 실제 저장소에는 없어서 본문 사실 관계가 틀린 경우
    - 저장소 현실이 문서의 핵심 범위, 사용자 시나리오, 성공 기준을 다시 써야 할 정도로 바뀐 경우
    - 문서의 남은 결정 항목이 여전히 사람 판단을 필요로 하는데 승인 상태로 올리려는 경우

## 3. 승인 전 보강 규칙

승인 판정 전에 먼저 아래 보강 절차를 수행한다.

### 3-1. 일관성 검토

- 용어 혼용, 범위 충돌, 중복 서술, 번호 누락을 확인한다.
- `# 5. 요구사항 목록`, `# 6. 리스크/가정 목록`, `# 7. 초기 성공 기준`, `# 8. REQ로 넘기기 전 확인 체크`, `# 10. 사용자 결정 필요 항목 요약`, `# 11. Discovery Freeze`의 연결 관계를 확인한다.
- 문장만 다르고 같은 의미를 반복하는 부분은 간결하게 정리한다.
- 문법, 오타, 링크 형식, 체크리스트 표현을 함께 정리한다.

### 3-2. 증거 기반 보강

- Discovery 본문에서 이슈명, 핵심 변경 항목, FR/NFR, 범위 경계를 읽고 키워드를 추출한다.
- 키워드를 바탕으로 저장소에서 관련 파일, 설정, 문서를 탐색한다.
- 탐색 결과는 최소한 아래 판단으로 정리한다.
    - 이미 존재함
    - 일부 존재함
    - 아직 없음
    - 문서와 모순됨
- AI가 아래 근거로 확정 가능한 항목은 실제 문장으로 치환한다.
    - 같은 Discovery 문서 안 다른 섹션에 이미 답이 있는 항목
    - 현재 저장소 파일 구조, 설정, 문서에서 직접 확인 가능한 항목
    - 승인 행위 시각처럼 현재 실행 시점에 자동 확정 가능한 항목
- 아래 항목은 추론만으로 확정하지 않는다.
    - 정책 선택
    - 우선순위 승인
    - 외부 시스템 또는 외부 데이터 확인 결과
    - 승인자 지명처럼 사람 책임을 수반하는 결정
    - `Confirmed By`처럼 승인 책임 주체를 명시하는 값

### 3-3. 플레이스홀더 분류 기준

- A. 승인 시점 자동 채움
    - 예: `{{DATA_CONFIRMED_AT_KST:...}}`, `{{CONFIRMED_AT_KST:...}}`
    - 승인 성공 시 현재 시각으로 채운다.
- B. 증거 기반 해소 가능
    - 문서 다른 섹션, 저장소 구조, 이미 확정된 값으로 해소 가능한 플레이스홀더다.
    - 승인 성공 여부와 무관하게 먼저 채운다.
- C. 사람 결정 또는 외부 확인 필요
    - `{{DECIDE_*}}`, `{{CONFIRM_*}}`, `{{DATA_*}}` 중 아직 문서와 저장소 근거만으로 해소되지 않는 항목이다.
    - 승인 차단 대상이다.

### 3-4. 책임자 지정과 저장소 범위 DATA 처리 기준

- `REQ/검토 책임자 지정`, `구현/검토 책임자 지정`, `해소 책임자 지정`처럼 사람 책임 배정이 필요한 항목은 AI가 자동으로 채우지 않는다.
- 이런 항목이 Discovery의 범위/정책/성공 기준 자체를 결정하는 질문이 아니라 이후 REQ 또는 batch planning 단계의 담당자 할당 문제라면, `# 10. 사용자 결정 필요 항목 요약`에 남겨 Discovery confirm을 가로막는 질문으로 유지하지 말고 `# 8. REQ로 넘기기 전 확인 체크` 또는 `# 11. Discovery Freeze`의 보류 사유로 정리한다.
- 다만 사람이 이미 대화에서 승인자/책임자/범위 결정을 명시해 주었고, 그 값이 문서에 직접 반영 가능한 형태라면 AI는 그 사람 결정을 문서에 옮길 수 있다. 이 경우에도 AI가 새 값을 추정하면 안 되고, 사용자가 제공한 사람 이름/결정만 그대로 기록해야 한다.
- 저장소 내부에서 확인 가능한 DATA 항목은 repo-wide consumer 탐색으로 먼저 해소를 시도한다. 예를 들어 특정 명령의 응답 길이에 의존하는 호스트 도구/스크립트 목록이 필요한 경우, 관련 토큰(`VISIONCFG`, `visioncfg` 등)으로 코드/문서/QA 스크립트 전체를 검색해 in-repo 소비처를 먼저 열거한다.
- 측정 경로와 검증 방법은 저장소 근거로 이미 확정됐지만 실제 수치가 구현/운영 단계에서만 수집 가능한 경우, 그 DATA 항목이 REQ 초안 작성 자체를 막는지 분리해서 판단한다. 대표 검증셋, 범위, 성공 기준, 사람 승인자가 확정돼 있으면 runtime baseline 수치 같은 운영 데이터는 REQ 단계 계측 항목으로 넘기고 confirm을 진행할 수 있다.
- 이 과정에서 저장소 안에서 길이 의존 구현이 확인되지 않으면 `현 저장소 기준 확인된 소비처는 없음`처럼 범위를 한정해 정리할 수 있다. 단, 저장소 밖 배포 도구나 외부 시스템까지 없다고 확대 해석하지 않는다.

- 승인 판정 직전에는 A와 B만 남아 있어야 한다.
- B로 분류한 항목을 채운 뒤에도 `# 1`부터 `# 10` 사이에 C 유형 플레이스홀더가 남아 있으면 승인하지 않는다.
- 단, `DATA_*` 성격의 항목이 "REQ 또는 delivery 단계에서 계측·확정할 운영 데이터"임이 문서 안에 명시되고, Discovery 본문만으로도 FR/NFR, 범위, 성공 기준, 검증 시나리오를 REQ 초안으로 내리기에 충분하다면 confirm 차단 사유로 유지하지 않는다. 이런 경우에는 `# 8. REQ로 넘기기 전 확인 체크`와 `# 10. 사용자 결정 필요 항목 요약`에 "REQ 단계 계측/확정" 또는 동등한 표현으로 넘기고, Discovery Freeze rationale에도 비차단 운영 데이터라는 점을 적는다.

## 4. 최종 승인 게이트

아래 조건을 모두 만족해야 `confirmed`로 전환한다.

- 문서 상태가 아직 `confirmed`가 아니어야 한다.
- B 유형 보강 이후 C 유형 플레이스홀더가 0개여야 한다.
- `# 6. 리스크/가정 목록`의 오픈 질문에 `상태: Open` 항목이 없어야 한다.
- `# 8. REQ로 넘기기 전 확인 체크`에 남아 있는 미완료 항목이 있다면, 그 항목이 REQ 초안 작성을 막지 않는다고 문서에 명시되어 있어야 한다. 그렇지 않으면 차단한다.
- `# 10. 사용자 결정 필요 항목 요약`에 남은 항목이 모두 `없음`이거나, 문서 안에서 이미 답이 반영되어 제거 가능해야 한다.
- `# 11. Discovery Freeze`에 `Confirmed By`가 비어 있지 않아야 한다.
- 현재 저장소 상태가 Discovery의 핵심 범위나 요구사항을 다시 정의해야 할 정도로 모순되지 않아야 한다.
- runtime budget baseline, 허용 상한, 운영 계측값처럼 구현 전에는 원천적으로 확정되지 않는 수치가 남아 있더라도, 그 값이 REQ의 acceptance/verification에서 수집할 evidence로 이미 위치가 정리돼 있으면 confirm 차단 사유로 과도하게 남기지 않는다.

`Confirmed By` 관련 규칙:

- `Confirmed By`는 사람 승인자 또는 사람 책임 주체를 의미한다.
- AI는 `Confirmed By`를 새로 생성하거나 추정해서 채우지 않는다.
- 사용자가 `/confirm-discovery dcy-001 승인자 Justin` 또는 “승인자를 Justin으로 입력한 후 confirm”처럼 같은 요청 안에서 승인자 이름을 명시했다면, 그 값은 사람 제공 값으로 간주해 문서의 `Confirmed By`에 그대로 반영할 수 있다.
- `Confirmed By`가 비어 있고 사용자가 이번 요청이나 기존 문서에서 승인자를 명시하지 않았다면 승인 차단 사유로 유지한다.

다음 경우는 `confirmed` 전환 대신 보류한다.

- Discovery 초안이 아니라 사실상 새 Discovery 생성 또는 대규모 범위 재정의가 필요한 경우
- 확인 과정에서 FR/NFR, In Scope/Out of Scope, 성공 기준을 실질적으로 다시 써야 하는 경우
- 승인자 또는 필수 결정 사항이 여전히 문서 밖 사람 판단에 의존하는 경우

## 5. 허용되는 수정 범위

이 skill은 아래 수정만 수행한다.

- AI가 근거 있게 채울 수 있는 플레이스홀더 치환
- 현재 저장소 상태에 맞춘 사실 관계 보정
- 표현, 번호, 체크리스트, 링크의 일관성 정리
- 실제 문서 변경이 있었다면 `마지막 갱신 시각(KST)` 갱신
- 승인 가능 시 아래 상태 전환 수행
    - `# 0. 문서 상태`의 `상태`를 `confirmed`로 변경
    - `# 11. Discovery Freeze`의 `Handoff Decision`을 `승인`으로 변경
    - `# 11. Discovery Freeze`의 `Ready for REQ Drafting`을 `true`로 변경
    - `Confirmed At (KST)`를 현재 시각으로 채움
    - `docs/discovery/index.md`의 해당 Discovery 행 상태를 `confirmed`로 갱신

단, 아래 항목은 자동으로 채우지 않는다.

- `Confirmed By`
  - 사람 승인자 또는 사람 책임 주체가 이미 문서에 명시되어 있어야 한다.
  - 비어 있으면 승인 전환 없이 보류한다.

아래 상황이면 상태 전환 없이 보강만 하고 종료한다.

- C 유형 플레이스홀더가 남아 있는 경우
- 오픈 질문 또는 사용자 결정 항목이 남아 있는 경우
- 승인 자체보다 먼저 Discovery 내용 재정비가 필요한 경우

# Repository Exploration

현재 구현 상태를 다시 확인할 때는 아래 순서로 저장소를 탐색한다.

1. Discovery 문서에서 이슈명, 핵심 변경 항목, FR/NFR, 범위 경계 키워드를 뽑는다.
2. 키워드 기준으로 관련 소스, 설정, 문서를 찾는다.
   - `docs/project-structure.md`, `docs/runtime-flows.md`가 있으면 baseline 참조 문서로 함께 읽는다.
3. 아래 항목은 기본적으로 제외한다.
   - 테스트 파일
   - 의존성 잠금 파일
   - `.stage-pilot/` 하위 파일
4. 탐색 결과를 아래 형태로 정리한다.
   - 관련 파일 경로 목록
   - 이미 구현된 내용
   - 일부만 구현된 내용
   - 아직 없는 내용
   - 문서와 모순되는 내용
   - baseline 문서와 일치하는 내용 / 충돌하는 내용
5. 탐색 결과는 Discovery 보강과 승인 게이트 판단에만 사용한다.

# Execution Procedure

다음 순서대로 작업한다.

1. 입력에서 Discovery 문서 경로를 확정한다.
2. 대상 Discovery 문서와 `docs/discovery/index.md`를 읽는다.
3. Discovery의 핵심 범위, FR/NFR, 오픈 질문, 체크리스트, 사용자 결정 필요 항목을 추출한다.
4. 위 `Repository Exploration` 규칙에 따라 현재 저장소 상태를 확인한다.
5. 문서 전체를 검토해 일관성 오류와 플레이스홀더를 나열한다.
6. B 유형 플레이스홀더와 명백한 사실 관계 오류를 먼저 수정한다.
7. 문서 내용이 바뀌었다면 `마지막 갱신 시각(KST)`를 현재 시각으로 갱신한다.
8. 다시 한 번 `최종 승인 게이트`를 평가한다.
9. 게이트를 통과하면 A 유형 플레이스홀더를 채우고 문서를 `confirmed`로 전환한다.
    - confirm 실행 자체로 해소되는 `Freeze 승인자 확인 필요`, `Confirmed At (KST): TBD`, `Ready for REQ Drafting: false`, `Handoff Decision: 보류` 같은 항목은 같은 패치에서 함께 정리한다.
    - `# 8. REQ로 넘기기 전 확인 체크`, `# 10. 사용자 결정 필요 항목 요약`, `# 11. Discovery Freeze`가 서로 모순되지 않도록 체크박스/확인 문구/Freeze rationale을 동기화한다.
10. 게이트를 통과하면 `docs/discovery/index.md`의 해당 행 상태도 `confirmed`로 갱신한다.
11. `docs/discovery/index.md`에 해당 Discovery 행이 없으면 현재 문서 메타데이터를 기준으로 기존 register/header 형식과 열 순서를 유지한 채 행을 추가한다.
    - 최소한 Discovery ID, 제목/이슈명, 상태, 링크, 마지막 갱신 시각에 해당하는 값을 채운다.
    - 표가 아닌 다른 register 형식이면 그 형식을 그대로 따른다.
12. 게이트를 통과하지 못하면 상태는 유지하고, 보강된 내용과 남은 차단 항목만 보고한다.

# Output Expectations

작업이 끝나면 아래 내용을 보고할 수 있어야 한다.

- 대상 `DISCOVERY_ID`와 문서 경로
- 현재 저장소 상태 재확인 결과 요약
- AI가 자동으로 채운 항목 목록
- 남겨 둔 항목 목록과 남긴 이유
- 최종 판정
    - `confirmed 전환 완료`
    - `보강만 수행, 승인 보류`
    - `문서 변경 없이 승인 보류`
- `docs/discovery/index.md` 갱신 결과
- REQ 초안 작성으로 넘기기 전에 남은 작업 요약

# Common Pitfalls

1. 구현이 아직 없다는 이유만으로 승인 차단하기
   - 신규 작업을 정의하는 Discovery라면 구현 부재는 정상일 수 있다. 차단 사유는 문서와 저장소 사실 관계 모순 또는 사람 결정 미해소여야 한다.

2. `Confirmed By`를 AI가 추정해서 채우기
   - `Confirmed By`는 사람 승인자 또는 사람 책임 주체를 뜻한다. AI가 새로 만들거나 추정하면 안 된다.

3. 사실상 새 Discovery가 필요한 문서를 confirm으로 밀어 올리기
   - 확인 과정에서 FR/NFR, 범위 경계, 성공 기준을 다시 써야 한다면 confirm보다 재작성 또는 새 Discovery 판단이 우선이다.

4. `review-discovery`에서 할 품질 점검과 `confirm-discovery`의 승인 게이트를 혼동하기
   - 단순 누락 점검과 구조 품질 확인이 목적이면 먼저 `review-discovery`를 사용한다.

5. Discovery 본문만 바꾸고 index 또는 freeze 필드를 함께 확인하지 않기
   - 승인 완료 시 본문 상태, Freeze 필드, `docs/discovery/index.md` 상태가 함께 일치해야 한다.

# Verification Checklist

완료 전에 아래를 확인한다.

- [ ] 대상 경로가 `docs/discovery/<DISCOVERY_ID>.md` 형식을 만족하는지
- [ ] 대상 Discovery 문서가 실제로 존재하는지
- [ ] `docs/project-structure.md`, `docs/runtime-flows.md`가 있다면 필요한 baseline cross-check가 반영되었는지
- [ ] 보강 후에도 C 유형 플레이스홀더와 `상태: Open` 오픈 질문이 정확히 식별되었는지
- [ ] 승인 완료인 경우 `Confirmed By`가 사람에 의해 채워져 있고, 문서 상태와 `docs/discovery/index.md` 상태가 모두 `confirmed`인지
- [ ] 대상 Discovery 문서가 git 기준 untracked이면 `git diff`만으로 변경 내용을 검증하지 말고, `read_file`/문서 검색/작은 검증 스크립트로 본문 상태, Freeze 필드, 플레이스홀더 부재, index 행을 직접 확인했는지
- [ ] 승인 보류인 경우 `confirmed`, `승인`, `true` 같은 승인 전환 값이 잘못 들어가지 않았는지
- [ ] 문서 본문 보강이 새로운 요구사항 생성이나 범위 재정의로 번지지 않았는지
- [ ] 결과 보고에 자동 처리 항목과 차단 항목이 모두 포함되는지