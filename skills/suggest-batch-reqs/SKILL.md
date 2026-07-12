---
name: suggest-batch-reqs
description: "Use when: recommending delivery batch groupings from approved requirements, running /suggest-batch-reqs with a Discovery ID or REQ list, assessing cohesion and delivery risk, or preparing input for /draft-batch without changing repository state."
version: 0.8.2
author: Justin Ko
license: private
argument-hint: "예: dcy-001 또는 req-001 req-002 req-003"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, requirements, planning, sdlc]
    related_skills: [draft-req, draft-batch, run-sdlc]
---

# Purpose

This skill recommends one or more candidate batch groupings from approved requirements and reports rationale, exclusions, risk, and confidence without modifying any files. 입력이 없으면 현재 저장소에서 아직 delivery 입력으로 소모되지 않은 Approved REQ를 찾아 이번 batch 후보를 추천한다. 기본 operating model에서는 이 추천의 primary consumer가 `delivery-runner`이며, runner는 approved scope 안에서 이 결과를 바탕으로 `draft-batch`를 이어서 진행할 수 있다.

# When to use

- Approved REQ가 여러 개 쌓여 어떤 묶음으로 delivery를 시작할지 추천이 필요할 때
- `/suggest-batch-reqs dcy-001` 또는 `/suggest-batch-reqs req-001 req-002`처럼 batch 후보안을 받아야 할 때
- `/suggest-batch-reqs`처럼 인자 없이 현재 저장소의 Approved REQ 중 아직 구현 완료 또는 기존 batch 편성이 끝나지 않은 후보만 추려 이번 batch 권장안을 보고 싶을 때
- `draft-batch` 실행 전에 포함/제외 REQ 근거를 미리 보고 싶을 때

## Do not use when

- 아직 `Approved`되지 않은 REQ를 먼저 승인해야 할 때 (`confirm-req`가 더 적절함)
- 포함할 REQ 집합이 이미 확정되어 바로 batch 문서를 생성하면 될 때 (`draft-batch`가 더 적절함)
- 단일 저위험 `Approved` REQ라 minor-change 또는 `batch-lite` 경로가 명확할 때 (`draft-batch`를 바로 고려할 수 있음)
- batch 추천이 아니라 현재 저장소의 전체 다음 SDLC 단계를 알고 싶을 때 (`run-sdlc`가 더 적절함)

# Inputs

- 선택 입력
  - `DISCOVERY_ID`, Discovery-level root state path, or Approved `REQ-ID` 목록
  - 입력이 없으면 `docs/srs/**/req-*.md`와 `docs/srs/index.md`를 읽어 Approved REQ를 찾는다.
  - 입력이 없으면 `docs/batches/index.md`도 함께 읽어 이미 batch에 편성된 REQ를 제외한다.
- 선택 입력
  - batch 최대 크기
  - Type, Priority, Owner 필터
  - 제외할 REQ 목록
  - 강제로 함께 고려할 REQ 목록

# Core Rules

- 이 skill은 추천만 수행하고 저장소 상태를 바꾸지 않는다.
- `Approved`가 아닌 REQ는 후보에서 제외한다.
- `Deprecated` REQ는 후보에서 제외한다.
- 입력이 없는 경우 `Implemented` 상태 REQ는 후보에서 제외한다.
- 입력이 없는 경우 `docs/batches/index.md` 기준으로 `draft`, `in-delivery`, `release-candidate`, `released` batch에 이미 포함된 REQ는 중복 추천하지 않는다.
- 상태가 REQ 본문과 index 사이에서 불일치하면, 추천 전에 그 불일치를 보고하고 기본적으로 후보에서 제외하거나 보류한다.
- 아래 조건을 많이 만족할수록 같은 batch 후보로 묶는다.
  - 같은 사용자 가치 또는 기능 흐름
  - 같은 모듈, 인터페이스, 런타임 경로
  - 같은 설계 전제와 환경 가정
  - 같은 iteration 안에서 구현과 검증 가능
  - acceptance criteria를 함께 검증하는 것이 효율적임
  - release 시 함께 배포해도 위험이 과도하지 않음
- 아래 조건이 있으면 같은 batch로 묶지 않는다.
  - 핵심 설계 전제 충돌
  - 완전히 다른 verification 흐름 필요
  - 독립 배포가 필요한 고위험 변경
  - 미해결 정책 결정이나 외부 의존성으로 planning이 불안정함

## Runner-driven selection rule

- 추천 결과 중 기본 채택 후보를 고르는 책임은 기본적으로 `delivery-runner`에 있다.
- Discovery-level root 입력에서는 이미 Implemented인 연결 REQ를 제외하고 remaining Approved REQ만 후보로 삼으며, 출력은 runner가 `batch-queue.json`에 옮길 수 있는 순서/의존성 근거를 포함해야 한다.
- 이 skill 자체는 저장소를 수정하지 않지만, runner는 이 결과를 근거로 `draft-batch`를 이어서 실행할 수 있다.
- 다만 후보 선택이 승인된 scope를 사실상 바꾸거나, priority/release policy 판단을 요구하거나, 사용자가 명시적으로 hold/defer를 걸어 둔 경우에는 runner가 lead로 escalate해야 한다.
- 후보 간 우열이 애매하면 `기본안` 1개와 `보수적 대안` 1개 이상을 함께 제시하고 trade-off를 설명한다.
- runner가 기본안을 고를 때 설명해야 하는 기준은 보통 다음 순서다.
  1. 이번 iteration 안에 끝낼 수 있는가
  2. 함께 검증할 때 verification cost가 실제로 줄어드는가
  3. release risk가 한 번에 묶어도 감당 가능한가
  4. 나중에 분리하면 오히려 재작업이 커지는가

## 후보별 batch profile 힌트

- `batch-lite`
  - 단일 REQ 또는 아주 작은 저위험 묶음
  - 구조/인터페이스/런타임 영향이 좁음
  - planning/design/verification 서술이 짧고 명확함
- `standard`
  - 다수 REQ 또는 상호작용이 있는 묶음
  - 구조/인터페이스/런타임 영향이 중간 이상임
  - planning/design/verification 근거를 분리해서 적는 편이 안전함
- 각 후보 출력에는 profile 이름만 적지 말고, 왜 그 profile이 맞는지 REQ 수, 변경 폭, verification 복잡도 기준으로 한 줄 이상 근거를 붙인다.

# Execution Procedure

1. 입력이 Discovery면 source Discovery의 `생성된 REQ 참조` 또는 명시된 연결 REQ를 우선 읽고, 입력이 REQ 목록이면 각 REQ 문서를 읽는다.
2. Discovery 입력인데 연결 REQ가 없거나 연결 REQ가 모두 `Approved`가 아니면 추천을 만들지 않고 그 사실을 보고한다.
3. 입력이 없으면 `docs/srs/**/req-*.md`, `docs/srs/index.md`, `docs/batches/index.md`를 읽어 Approved REQ 전체를 찾고, `Implemented` 상태 또는 기존 batch에 이미 포함된 REQ를 제외해 현재 후보군을 만든다.
4. 각 REQ의 상태, Type, Impacted Area, Acceptance Criteria를 요약한다.
5. 후보군에서 Approved REQ만 추린 뒤 응집도와 delivery risk 기준으로 후보안을 1개 이상 만든다.
6. 입력이 없는 스캔 결과 후보군이 비어 있으면 억지로 batch 후보를 만들지 않는다.
   - `Approved` REQ가 전혀 없거나
   - Approved REQ가 모두 기존 batch에 이미 포함돼 있거나
   - 남은 REQ가 전부 `Proposed`/`Implemented`/`Deprecated`라면
   `추천 가능한 신규 batch 없음`으로 보고한다.
   - 이 경우 스캔한 REQ와 제외 사유를 함께 정리하고, 필요하면 먼저 `confirm-req` 또는 기존 batch 진행 상태 점검을 권장한다.
   - 후보가 없는데도 형식상 `BAT-CANDIDATE-1`을 억지로 만들거나, 실제로 구성할 수 없는 `/draft-batch ...` 예시를 만들지 않는다.
7. 가능하면 최소 2개 후보를 제시한다.
   - 응집도 중심 기본안
   - 더 작은 묶음 또는 보수적 대안
8. 적절한 묶음이 없지만 단일 Approved REQ는 존재하면 `단일 REQ batch 권장`을 명시한다.
9. 각 후보에 대해 포함 REQ, 제외 REQ와 제외 이유, 추천 근거, 위험도, 신뢰도, 예상 batch profile(`standard` | `batch-lite`)을 정리한다.
10. 각 후보에 대해 profile 판단 근거(REQ 수, 구조/인터페이스/런타임 영향, verification 흐름 복잡도)를 함께 적는다.
11. 바로 사용할 수 있는 `/draft-batch ...` 입력 예시를 제시한다. 기본 operating model에서는 `delivery-runner`가 이 추천을 채택해 다음 단계로 넘길 수 있음을 함께 적고, 단 추천 가능한 후보가 없으면 `/draft-batch` 예시는 생략하고 그 이유를 쓴다.

# Output Expectations

- 후보 `BAT-CANDIDATE-N` 목록
- 입력이 없는 경우 스캔한 Approved REQ 목록
- 후보별 포함 REQ
- 후보별 제외 REQ와 제외 이유
- 후보별 추천 근거
- 후보별 위험도 (`Low|Medium|High`)
- 후보별 신뢰도 (`High|Medium|Low`)
- 후보별 예상 batch profile (`standard` | `batch-lite`)과 판단 근거
- Discovery-level root라면 권장 queue order와 각 queue item의 included REQ / dependency reason
- `draft-batch` 추천 명령 예시
- 기본 채택 주체가 `delivery-runner`이며 어떤 경우 lead escalation이 필요한지에 대한 안내
- 단, 추천 가능한 신규 batch가 없으면 아래 형식으로 대체 보고할 수 있다.
  - 스캔한 REQ 목록
  - 승인됨/제외됨/기존 batch 포함 상태 요약
  - `추천 가능한 신규 batch 없음` 결론
  - 먼저 필요한 선행 단계(`confirm-req`, 기존 batch 진행, release 정리 등)

# Common Pitfalls

1. `Approved`가 아닌 REQ를 후보에 섞는 실수
   - batch 추천은 delivery input이 확정된 REQ만 대상으로 해야 하므로 `Proposed`, `Implemented`, `Deprecated`를 구분해 제외한다.

2. 이미 다른 batch에 포함된 REQ를 다시 추천하는 실수
   - `docs/batches/index.md`를 읽고 중복 편성 여부를 먼저 확인한다.

3. 서로 다른 verification 흐름이 필요한 REQ를 단순 개수 맞추기로 한 batch에 묶는 실수
   - 응집도보다 검증 흐름 충돌이 크면 더 작은 보수적 대안을 함께 제시한다.

4. Discovery 입력을 받았지만 실제 연결 REQ 근거 없이 임의로 묶는 실수
   - source Discovery의 `생성된 REQ 참조` 또는 명시된 연결 REQ를 우선 근거로 삼는다.

5. 추천 후보를 무근거로 확정하거나, 반대로 아무 이유 없이 사람 선택만 기다리게 만드는 실수
   - 기본 채택은 `delivery-runner`가 할 수 있지만, 승인된 scope 밖으로 흐르거나 우선순위/릴리즈 정책 판단이 섞이면 lead로 escalate해야 한다.

6. 단일 저위험 REQ인데도 불필요하게 큰 batch 후보만 제시하는 실수
   - 필요하면 `단일 REQ batch 권장` 또는 `batch-lite` 대안을 함께 제시한다.

# Verification Checklist

- [ ] 후보에 `Approved`가 아닌 REQ가 포함되지 않았다.
- [ ] 입력이 없는 경우 `Implemented` 상태 REQ와 기존 batch 포함 REQ가 제외되었다.
- [ ] Discovery 입력이면 연결 REQ 근거가 명확하다.
- [ ] 상태 불일치 REQ는 보고되었고 무리하게 후보에 포함되지 않았다.
- [ ] 후보별 포함/제외 이유가 설명되어 있다.
- [ ] 가능하면 최소 1개의 보수적 대안 또는 `단일 REQ batch 권장`이 포함되어 있다.
- [ ] 후보별 예상 batch profile(`standard` | `batch-lite`)과 그 근거가 제시되었다.
- [ ] `/draft-batch` 예시 입력이 실제 후보 구성과 일치한다.
- [ ] 저장소 상태를 변경하지 않았다.
- [ ] 기본 채택 주체(`delivery-runner`)와 lead escalation 조건이 명시되어 있다.