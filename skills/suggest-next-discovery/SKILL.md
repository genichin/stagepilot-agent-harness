---
name: suggest-next-discovery
description: "Use when: recommending the next Discovery candidate from release feedback, pending requirements, baseline gaps, or recent doctor reports, running /suggest-next-discovery with or without a REL ID, or deciding whether feedback should become a new Discovery or a change-req instead."
version: 0.6.0
author: Justin Ko
license: private
argument-hint: "예: rel-001 또는 인자 없이 /suggest-next-discovery"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, discovery, prioritization, planning, sdlc]
    related_skills: [capture-release-feedback, new-discovery, run-sdlc, stagepilot-doctor-ops]
---

# Purpose

This skill analyzes release feedback, pending REQs, baseline gaps, and recent delivery signals to recommend the next improvement loop. It reports ranked candidates and tells the user whether to start a new Discovery or route work into `change-req` instead.

# When to use

- `/suggest-next-discovery`처럼 다음 반복 주제를 추천받고 싶을 때
- `feedback-captured` release 이후 어떤 후속 Discovery를 열지 정해야 할 때
- release feedback에 기존 REQ 수정과 신규 Discovery 후보가 섞여 있어 triage가 필요할 때
- `stagepilot-doctor --report ...` 결과와 release feedback를 함께 보고 다음 개선 루프를 정하고 싶을 때

# Inputs

- 선택 입력
  - `REL-ID` prefix 또는 release 경로
  - 입력이 없으면 `docs/releases/*.md`, `docs/srs/index.md`, `docs/project-structure.md`, `docs/runtime-flows.md`를 읽어 후보를 찾는다.
- 선택 입력
  - `stagepilot-doctor` Markdown report 경로
- 관련 release 문서의 `Feedback Handoff`
- `docs/srs/index.md`와 미구현/변경 대기 REQ 상태
- `docs/project-structure.md`, `docs/runtime-flows.md` (존재하는 경우)

# Core Rules

- 이 skill은 추천만 수행하고 저장소 상태를 바꾸지 않는다.
- release feedback의 후보는 아래 셋 중 하나로 분류한다.
  - `new-discovery`
  - `change-req`
  - `no-action`
- 기존 REQ의 수정으로 닫히는 항목은 새 Discovery보다 `change-req`를 우선 추천한다.
- 서로 다른 가치 흐름이나 이해관계자를 가지는 후보는 별도 Discovery로 분리한다.
- 추천에는 가치, 위험, 노력의 상대 평가를 포함한다.

# Execution Procedure

1. 입력 release가 있으면 해당 문서를, 없으면 최근 release 문서들을 읽는다.
2. `Feedback Handoff`에서 Discovery Input, REQ Input, Change Request Input을 추린다.
3. `docs/srs/index.md`와 관련 REQ 상태를 읽어 기존 REQ 수정으로 해결 가능한지 판정한다.
4. baseline 문서 gap, 미구현 REQ, doctor report의 경고/오류가 후속 반복 후보인지 함께 판단한다.
5. 후보를 `new-discovery` 또는 `change-req`로 분류하고 가치/위험/노력 점수를 매긴다.
6. 우선순위 순으로 추천 목록과 바로 실행할 명령 예시를 제시한다.

# Output Expectations

- 후보 목록 (`CANDIDATE-1`, `CANDIDATE-2`, ...)
- 각 후보의 분류 (`new-discovery` | `change-req` | `no-action`)
- 근거 release 또는 REQ
- 가치/위험/노력 (`High|Medium|Low`)
- 추천 이유
- 다음 명령 예시 (`/new-discovery ...` 또는 `/change-req ...`)

# Validation

- 동일 후보를 `new-discovery`와 `change-req`에 중복 배치하지 않았는지 확인한다.
- release feedback 근거가 없는 임의 후보를 만들지 않았는지 확인한다.
- 기존 REQ 수정으로 닫히는 항목을 새 Discovery로 과도하게 승격하지 않았는지 확인한다.