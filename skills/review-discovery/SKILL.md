---
name: review-discovery
description: "Use when: reviewing an existing Discovery document for missing content, additional OQ candidates, internal consistency, duplication, unnecessary content, placeholder residue, and REQ handoff readiness without changing lifecycle state."
version: 0.8.0
author: Justin Ko
license: private
argument-hint: "예: dcy-001 또는 docs/discovery/dcy-001_20260424_topic.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, discovery, review, quality, sdlc]
    related_skills: [new-discovery, confirm-discovery, draft-req]
---

# Purpose

This skill reviews an existing Discovery document as a non-gating quality check before `confirm-discovery` or before human review. It looks for missing content, candidate open questions, internal inconsistencies, duplicated statements, unnecessary text, placeholder residue, and weak handoff readiness.

이 skill은 별도 lifecycle stage를 만들지 않는다. 기본 목적은 Discovery 품질을 점검하고 수정 우선순위를 정리하는 것이며, 문서 상태 전환이나 index 갱신은 수행하지 않는다.

# When to use

- `/review-discovery dcy-xyz` 형태로 Discovery 문서를 먼저 점검하고 싶을 때
- `confirm-discovery` 전에 누락, 중복, OQ 후보, 표현 불일치를 빠르게 정리하고 싶을 때
- Discovery 문서가 길어지면서 같은 내용이 여러 섹션에 흩어졌는지 확인해야 할 때
- 템플릿 잔여 문구, 불필요한 상세 구현 설명, 근거 없는 확정 표현이 남아 있는지 보고 싶을 때
- 사람이 수정할 항목과 AI가 바로 정리할 수 있는 항목을 분리해서 보고 싶을 때

# Inputs

- Discovery 식별자
  - `dcy-001` 같은 prefix
  - `dcy-001_20260424_topic-slug` 같은 전체 ID
  - `docs/discovery/<DISCOVERY_ID>.md` 같은 직접 경로
- 대상 Discovery 문서 본문
- 필요 시 관련 저장소 문맥
  - 현재 저장소의 관련 파일, 문서, 설정
  - `docs/discovery/index.md`
  - `docs/project-structure.md`, `docs/runtime-flows.md`
- 현재 시각 (KST)

# Core Rules

## 1. 역할 경계

- 이 skill은 review helper이며, active SDLC 단계로 취급하지 않는다.
- 아래 항목은 수정하지 않는다.
  - `# 0. 문서 상태`의 `상태`
  - `# 11. Discovery Freeze`의 `Handoff Decision`, `Ready for REQ Drafting`, `Confirmed By`, `Confirmed At (KST)`
  - `docs/discovery/index.md`
- 이 skill은 REQ 생성, 승인, 상태 승격을 하지 않는다.
- 사실 관계를 바꾸는 추정성 수정은 하지 않는다. 근거 없는 항목은 finding 또는 OQ 후보로 남긴다.
- 사용자가 단순 검토만 요청한 경우 결과는 findings-first로 보고한다.
- 사용자가 `정리`, `수정`, `보강`, `반영`까지 명시한 경우에만 의미 변화가 없는 경미한 편집을 수행할 수 있다.

## 2. 기본 검토 축

반드시 아래 항목을 검토한다.

### 2-1. 누락 항목

- 템플릿 기준으로 필요한 섹션과 핵심 내용이 빠지지 않았는지 확인한다.
- 빈 bullet, `TBD`, `{{...}}`, `필요 없으면 삭제` 잔여 문구를 누락 또는 미정리 항목으로 본다.
- 아래 핵심 정보가 약하거나 비어 있으면 finding으로 기록한다.
  - 문제의 현재 상태와 기대 상태
  - 핵심 변경 항목과 영향 범위
  - FR/NFR와 범위 경계
  - 리스크, 가정, 성공 기준
  - REQ handoff 전 확인 기준
- 단, `# 2. 요구사항 판정 결과`가 `완전 중복`이면 템플릿 가이드에 따라 이후 섹션 축약을 허용한다. 이 경우 `# 9. 파일 처리 결과`까지의 중복 판정 근거와 참조만 충분한지 본다.

### 2-2. 추가 OQ 후보

- 아래 조건이면 새 OQ 후보를 제안한다.
  - 범위 경계가 모호해 In Scope/Out of Scope가 흔들리는 경우
  - 성공 기준은 있는데 측정 방식이나 데이터 출처가 없는 경우
  - 리스크 완화 책임자나 판단 주체가 비어 있는 경우
  - 외부 정책, 외부 시스템, 운영 절차, 승인자 결정이 필요한데 본문에 근거가 없는 경우
  - 서로 다른 섹션이 충돌해서 사람 판단 없이는 확정할 수 없는 경우
- 이미 다른 섹션에서 답이 있는 질문은 OQ로 늘리지 말고, answered cleanup 대상으로 분류한다.
- 사소한 문장 다듬기나 서식 문제는 OQ로 만들지 않는다.

### 2-3. 문서 일관성

- 이슈명, 핵심 변경, FR/NFR, 범위 경계, 성공 기준, Freeze rationale 사이의 용어와 범위가 일치하는지 확인한다.
- `# 4. 이번에 정의할 변경`, `# 5. 요구사항 목록`, `# 6. 리스크/가정 목록`, `# 7. 초기 성공 기준`, `# 8. REQ로 넘기기 전 확인 체크`, `# 10. 사용자 결정 필요 항목 요약`, `# 11. Discovery Freeze`의 연결 관계를 본다.
- `Open` OQ가 남아 있는데 Freeze가 사실상 진행 가능처럼 읽히는지 확인한다.
- 문서 안에서 같은 개념을 서로 다른 이름으로 부르는 경우 정규화 필요 finding으로 기록한다.

### 2-4. 중복 제거 대상

- 같은 사실이나 요구를 여러 섹션에서 반복하는지 찾는다.
- 중복은 아래 세 종류로 분류한다.
  - 완전 중복: 문장만 다르지만 의미가 같은 경우
  - 부분 중복: 핵심은 같고 세부만 다른 경우
  - 잘못된 재기술: 상위 요약과 하위 상세가 서로 다른 말을 하는 경우
- 중복이 있으면 어떤 섹션을 source of truth로 둘지 함께 제안한다.

### 2-5. 불필요한 내용

- Discovery 단계에 필요 없는 구현 디테일, 과도한 알고리즘 설계, 배포 절차 상세, 이미 결정된 이력 서술을 찾는다.
- 현재 반복의 문제 정의와 성공 기준에 기여하지 않는 배경 설명은 삭제 또는 압축 후보로 본다.
- 템플릿 가이드 문구, 예시 텍스트, 삭제 예정 placeholder 설명이 본문에 남아 있으면 제거 대상으로 본다.

## 3. 추가 검토 항목

사용자 요청 외에도 아래를 함께 본다.

### 3-1. 근거와 사실 일치성

- 문서가 현재 저장소 상태를 서술하는 경우, 그 주장에 직접 관련된 파일이나 문서와 모순이 없는지 확인한다.
- 저장소 확인은 문서의 핵심 주장과 직접 연결된 범위만 탐색한다. 구현 전체를 감사하지는 않는다.
- 저장소 근거와 충돌하는 서술은 높은 우선순위 finding으로 기록한다.

### 3-2. 실행 가능성과 측정 가능성

- FR/NFR, 성공 기준, 체크 항목이 다음 단계에서 실제 REQ/검증 항목으로 이어질 정도로 구체적인지 본다.
- `개선한다`, `지원한다`, `정리한다`처럼 모호한 동사만 있고 판정 기준이 없으면 구체화 필요 finding으로 기록한다.
- 성공 기준은 가능한 한 측정 방식과 데이터 출처에 연결되어야 한다.

### 3-3. 플레이스홀더 위생

- 사용자 결정이 필요한 placeholder와 단순 미정리 placeholder를 구분한다.
- 같은 의미의 placeholder가 본문과 `# 10. 사용자 결정 필요 항목 요약`에 중복으로 남아 있으면 정리 대상으로 본다.
- 이미 문서 근거로 해소 가능한 placeholder는 unresolved로 방치하지 않는다.

## 4. 허용되는 편집 범위

사용자가 수정까지 요청한 경우에만 아래 경미한 편집을 허용한다.

- 중복 문장 삭제 또는 압축
- 템플릿 잔여 문구 제거
- 번호, 체크리스트, 링크, 용어 표기 일관성 정리
- 답이 이미 문서 안에 있는 OQ를 본문 반영 후 resolved cleanup으로 정리
- 의미 변화 없는 섹션 재배치
- review finding을 근거로 새 OQ 후보, 리스크, 가정, REQ handoff 전 확인 기준, verification evidence 요구를 보강
- 실제 내용이 바뀌었을 때 `마지막 갱신 시각(KST)` 갱신

아래는 이 skill로 수정하지 않는다.

- 정책을 임의로 확정하거나 사용자의 추가 결정을 대신 내리는 변경
- 승인자 지정 또는 승인 시각 확정
- 상태 전환과 index 갱신
+
### 4-1. review 결과를 문서에 반영할 때의 Freeze 경계

사용자가 “review-discovery로 검토한 내용 적용/반영”을 요청하더라도 `# 11. Discovery Freeze`의 lifecycle flag는 보존한다.

- 보존 대상: `Handoff Decision`, `Ready for REQ Drafting`, `Confirmed By`, `Confirmed At (KST)` 원문 값
- 허용 대상: 본문 섹션(`# 6` 리스크/가정, `# 8` 체크, `# 10` 사용자 결정 필요 항목)에 “승인자 후보”, “confirm-discovery에서 확정 필요”, “Open OQ가 남아 있어 handoff 보류”처럼 Freeze 모순을 해소하는 보강 문장 추가
- 금지 대상: `Confirmed By: Justin`을 `TBD`로 바꾸거나, `Confirmed At`을 채우거나, `Ready for REQ Drafting`을 true/false로 재판정하는 것
- 필요한 경우 최종 보고에서 “Freeze flag는 review-discovery 역할 경계상 변경하지 않았다”고 명시한다.

### 4-2. 사용자 결정이 내려진 OQ/placeholder 반영 규칙

사용자가 Discovery 문서의 OQ, DECIDE, CONFIRM 항목에 대해 실제 결정을 내려 주면, 단순히 해당 bullet 하나만 닫지 말고 문서 전반에 파급 반영한다.

- 최소 반영 대상:
  - `# 0. 문서 상태`의 `마지막 갱신 시각(KST)`
  - `# 5. 요구사항 목록`의 In Scope / Out of Scope placeholder와 범위 경계 문장
  - `# 6. 리스크/가정 목록`의 해당 OQ 상태(`Open` → `Answered`)와 결정 근거/결정 반영
  - `# 7. 초기 성공 기준` 및 `측정 방식 및 데이터 출처`에서 결정으로 인해 추가/분리된 acceptance 또는 confidence check
  - `# 8. REQ로 넘기기 전 확인 체크`의 기준 문구
  - `# 10. 사용자 결정 필요 항목 요약`의 DECIDE / CONFIRM 체크 상태
  - `# 11. Discovery Freeze`의 rationale 문구(단, lifecycle flag 값 자체는 바꾸지 않음)
- 실무 규칙:
  - 실통합 스모크를 “권장 검증”으로 내리면 Out of Scope에는 “필수 게이트로 승격하는 것”을 적고, 성공 기준에는 별도 confidence check 항목을 추가해 acceptance와 권장 검증을 분리한다.
  - 실행 정책 필드처럼 채택 여부가 범위를 바꾸는 결정은 In Scope 문장과 사용자 결정 요약을 함께 갱신한다.
  - `intent_id` 규칙, 멱등 키 구성, 거래일 컴포넌트 유지 여부처럼 요구사항 본문(FR/NFR)에 직접 닿는 결정은 `# 10`의 체크만 닫지 말고 해당 FR 문장과 OQ 본문까지 같이 업데이트한다. 기존 placeholder(`{{CONFIRM_*}}`)는 그대로 남기지 말고 checked bullet로 치환한다.
  - 사용자가 새 결정을 내려 기존 OQ 집합에 없던 독립 판단 축이 생기면(예: OQ-1~3 외에 intent_id 규칙을 별도 추적해야 하는 경우) 문서 본문 `## 오픈 질문`에 새 OQ 번호를 추가하고, `# 8`/`# 10`/Freeze rationale의 OQ 개수 언급도 함께 맞춘다.
  - `Open` OQ가 줄어들면 Freeze rationale과 REQ handoff readiness 문구도 함께 정리해, 남은 확인 항목이 무엇인지 한눈에 드러나게 한다.

# Review Heuristics By Section

섹션별로 최소한 아래를 점검한다.

- `# 0. 문서 상태`
  - 문서 ID, 이슈명, 시각 정보, 참조 필드가 자기모순 없는지 확인한다.
- `# 1. 계획 상태 요약`
  - 현재 작성 배경과 이번 Discovery의 핵심 판단 포인트가 2줄 요약으로 드러나는지 본다.
- `# 2. 요구사항 판정 결과`
  - 신규/유사/중복 판정과 근거가 실제 본문 범위와 맞는지 본다.
- `# 3. 문제점의 요약`
  - 현재 상태, 기대 상태, 이해관계자, 시나리오가 왜 이 Discovery가 필요한지를 설명하는지 본다.
- `# 4. 이번에 정의할 변경`
  - 변경 항목과 영향 범위가 `# 5` 요구사항과 연결되는지 본다.
- `# 5. 요구사항 목록`
  - FR/NFR가 구분되어 있고 범위 경계가 충돌하지 않는지 본다.
- `# 6. 리스크/가정 목록`
  - 리스크, 가정, OQ가 각각 역할에 맞게 쓰였는지 본다.
- `# 7. 초기 성공 기준`
  - 측정 대상, 방식, 데이터 출처가 요구사항과 연결되는지 본다.
- `# 8. REQ로 넘기기 전 확인 체크`
  - 체크 항목이 선언만 있고 판단 기준이 없는지 본다.
- `# 9. 파일 처리 결과`
  - 참조 문서가 실제 검토 근거를 반영하는지 본다.
- `# 10. 사용자 결정 필요 항목 요약`
  - DECIDE, CONFIRM, DATA가 실제 unresolved 항목과 맞는지 본다.
- `# 11. Discovery Freeze`
  - review 결과와 무관하게 상태 전환 없이, 본문과 논리적 충돌만 점검한다.

# Execution Procedure

1. 입력에서 Discovery 문서 경로를 확정한다.
2. 대상 Discovery 문서를 읽고, 필요 시 `docs/discovery/index.md`와 직접 관련된 저장소 문맥을 읽는다.
3. 문서를 `중복 판정으로 축약 가능한 문서`인지 `정상 Discovery 검토 대상`인지 먼저 분류한다.
4. 위 `기본 검토 축`과 `추가 검토 항목` 기준으로 findings를 수집한다.
5. findings를 아래 우선순위로 분류한다.
   - `blocking`: REQ handoff 또는 사실 관계에 직접 문제를 만드는 항목
   - `major`: 지금 고치는 편이 좋은 구조/일관성/측정 가능성 문제
   - `minor`: 표현, 중복, 서식, 경미한 cleanup 문제
6. 추가 OQ 후보가 있으면 기존 OQ와 중복 여부를 제거한 뒤 후보 목록으로 정리한다.
7. 사용자가 수정까지 요청한 경우에만 `허용되는 편집 범위` 안에서 경미한 cleanup을 수행한다.
8. 편집을 수행한 경우 `마지막 갱신 시각(KST)`만 갱신하고, 상태 전환 없이 종료한다.
9. 최종적으로 findings, OQ 후보, auto-fix 결과, 다음 추천 행동을 보고한다.

# Output Expectations

작업이 끝나면 아래 내용을 보고할 수 있어야 한다.

- 대상 `DISCOVERY_ID`와 문서 경로
- 전체 판정
  - `양호, 바로 confirm-discovery 검토 가능`
  - `경미한 정리 필요`
  - `추가 보강 필요`
  - `문서 구조 또는 사실 관계 재정비 필요`
- severity별 findings 목록
- 새 OQ 후보 목록
- 중복/불필요 내용 정리 제안
- 자동 정리한 항목 목록(수정 요청이 있었을 때만)
- 다음 추천 행동
  - `confirm-discovery` 진행
  - Discovery 문서 추가 수정 후 재검토
  - 범위가 바뀌어 `new-discovery` 또는 `change-req` 판단 필요

# Validation

완료 전에 아래를 확인한다.

- 대상 경로가 실제 Discovery 문서를 가리키는지 확인한다.
- `완전 중복` 예외를 제외하고, 누락 판단이 템플릿 구조와 충돌하지 않는지 확인한다.
- 제안한 OQ가 이미 본문이나 다른 섹션에서 답을 가진 항목이 아닌지 확인한다.
- 같은 finding을 누락/중복/불필요 항목에 중복 보고하지 않았는지 확인한다.
- 수정이 있었다면 상태 전환 값과 `docs/discovery/index.md`가 바뀌지 않았는지 확인한다.
- 저장소 사실 관계와의 충돌을 지적했다면 최소 한 개 이상의 직접 근거가 있는지 확인한다.