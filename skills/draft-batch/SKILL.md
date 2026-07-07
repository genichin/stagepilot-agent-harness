---
name: draft-batch
description: "Use when: creating a new batch from approved REQ IDs, running /draft-batch with one or more req IDs, scaffolding docs/batches/<BAT_ID>/ files, or updating docs/batches/index.md for a new delivery unit."
version: 0.9.3
author: Justin Ko
license: private
argument-hint: "예: req-001 req-002 req-003"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, planning, documentation, sdlc]
    related_skills: [suggest-batch-reqs, draft-batch-planning, draft-batch-design, draft-batch-verification, run-batch-delivery, stagepilot-doctor-ops]
---

# Purpose

This skill creates a new batch delivery unit from already-selected approved requirements, chooses the right delivery profile, scaffolds its folder and documents, and updates the batch register.

# When to use

- 포함할 `Approved` REQ 집합이 이미 확정되어 새 batch를 실제로 생성해야 할 때
- `/draft-batch req-001 req-002`처럼 batch 문서 scaffold와 register entry가 필요할 때
- `/draft-batch dcy-002`처럼 confirmed Discovery 기준으로 승인된 REQ 묶음을 찾아 batch를 만들어야 할 때
- 단일 저위험 `Approved` REQ를 `minor-change` fast path로 바로 batch-lite batch로 시작할 때
- `suggest-batch-reqs` 결과에서 사람이 후보를 선택한 뒤 실제 batch 문서를 만들 차례일 때

## Do not use when

- 아직 REQ가 `Approved`되지 않아 먼저 승인 절차가 필요할 때 (`confirm-req`가 더 적절함)
- 어떤 REQ를 함께 묶을지 아직 사람 선택이 끝나지 않았을 때 (`suggest-batch-reqs`가 더 적절함)
- 이미 존재하는 batch의 planning/design/verification 내용을 채우는 단계일 때 (`draft-batch-planning`, `draft-batch-design`, `draft-batch-verification`이 더 적절함)
- 현재 저장소의 전체 다음 SDLC 단계를 알고 싶은 상황일 때 (`run-sdlc`가 더 적절함)

# Inputs

- `Approved` `REQ-ID` 목록
- 또는 confirmed Discovery 식별자 (`dcy-002` 같은 ID, full discovery slug, 또는 discovery 문서 경로)
  - Discovery 입력이면 `docs/srs/**/req-*.md`와 `docs/srs/index.md`를 기준으로 해당 Discovery에서 생성된 `Approved` REQ들을 역추적해 batch 입력 집합으로 확정한다.
- 선택 입력
  - batch profile 힌트 (`standard` | `batch-lite` | `minor-change`)
- `docs/srs/index.md`
- 대상 REQ 문서들
- `docs/batches/index.md`
- 배치 템플릿의 논리 경로
  - `stage-pilot/templates/batches/batch-index.md`
  - `stage-pilot/templates/batches/planning.md`
  - `stage-pilot/templates/batches/design.md`
  - `stage-pilot/templates/batches/implementation.md`
  - `stage-pilot/templates/batches/verification.md`
  - `stage-pilot/templates/batches/index.md` (`docs/batches/index.md` register 템플릿/기준)

## Template path resolution

- 배치 템플릿은 하나의 물리 경로만 고정하지 말고 `stage-pilot/templates/batches/...`를 논리 경로로 취급한다.
- 물리 경로는 다음 순서로 해석한다.
  1. `.stage-pilot/templates/batches/...`
  2. `~/.stage-pilot/templates/batches/...`
- 여러 후보가 동시에 존재하면 가장 우선순위가 높은 한 곳만 사용하고, 서로 다른 설치 위치의 템플릿을 섞지 않는다.
- 이 resolution rule은 SKILL.md 본문에 그대로 적어 두는 편이 좋다. 배치 템플릿이 실제로 존재하는 현재 머신의 경로만 적어 두면 다른 PC나 다른 agent install shape에서 portability가 떨어진다.
- 템플릿 source path와 생성 target path를 혼동하지 않는다.
  - source: `stage-pilot/templates/batches/...`
  - target: `docs/batches/<BAT_ID>/...`, `docs/batches/index.md`

# Core Rules

- 이 skill은 사람이 선택을 마친 REQ 집합을 batch 문서로 구체화하는 단계다.
- `Approved` 상태가 아닌 REQ는 batch에 포함하지 않는다.
- 새 batch 폴더는 `docs/batches/bat-XXX_YYYYMMDD_scope/` 형식을 사용한다.
- 새 batch의 persisted profile은 `standard` 또는 `batch-lite` 중 하나다.
- `minor-change`는 profile 자체가 아니라 단일 저위험 REQ를 빠르게 `batch-lite`로 판단하는 입력 fast path다.
- 입력이 정확히 1개의 `Approved` REQ이고 범위가 국소적이며 구조/인터페이스/런타임 흐름 변경이 없으면 `minor-change` fast path를 사용할 수 있다. 이 경우 최종 batch profile은 `batch-lite`로 기록한다.
- `standard` batch는 생성 시 아래 파일을 함께 만든다.
  - `index.md` ← `stage-pilot/templates/batches/batch-index.md`
  - `planning.md` ← `stage-pilot/templates/batches/planning.md`
  - `design.md` ← `stage-pilot/templates/batches/design.md`
  - `implementation.md` ← `stage-pilot/templates/batches/implementation.md`
  - `verification.md` ← `stage-pilot/templates/batches/verification.md`
- `batch-lite`는 생성 시 아래 파일만 먼저 만든다.
  - `index.md` ← `stage-pilot/templates/batches/batch-index.md`
  - `planning.md` ← `stage-pilot/templates/batches/planning.md`
- `batch-lite`의 `implementation.md`와 `verification.md`는 해당 단계 진입 시 생성한다.
- `batch-lite`라도 구조/인터페이스/흐름 영향이 생기면 `design.md`를 추가하고 사실상 standard depth로 다룬다.
- REQ 묶음 선택이 아직 불안정하거나 대안 비교가 필요하면 batch를 생성하지 말고 먼저 `suggest-batch-reqs`로 되돌린다.
- `docs/batches/index.md`의 register는 새 batch 생성과 함께 반드시 갱신한다.
- register 행에는 최소한 `BAT ID`, `Profile`, `Status`, `Included REQ`, `Discovery`, `Folder`를 채운다.
- source discovery는 포함 REQ에서 역추적해 채운다. source가 하나면 그대로 기록하고, 여러 source discovery가 섞이면 축약 표기와 함께 batch 문서 Notes에 설명한다.
- 사용자가 `dcy-XXX`처럼 Discovery ID만 주면 임의로 REQ를 추측하지 않는다. 먼저 해당 Discovery가 confirmed인지 확인하고, `docs/srs/**/req-*.md`에서 `Source Discovery`, `Notes`, 또는 `docs/srs/index.md` register를 통해 연결된 `Approved` REQ 목록을 수집한다. 연결 REQ가 없거나 일부만 `Approved`면 batch 생성 전에 blocker로 보고한다.

# Execution Procedure

1. 입력이 REQ 목록인지 Discovery 식별자인지 해석한다.
   - REQ 목록이면 각 REQ 경로와 상태를 확인하고 모두 `Approved`인지 검증한다.
   - Discovery 식별자이면 해당 Discovery 문서를 찾고 `confirmed`/handoff 상태를 확인한 뒤, 그 Discovery에서 생성된 `Approved` REQ를 `docs/srs/**/req-*.md`와 `docs/srs/index.md`에서 역추적해 대상 REQ 목록으로 변환한다.
2. 입력된 REQ 묶음이 이미 사람에 의해 선택된 집합인지 확인한다. Discovery 식별자 입력은 사람이 “이 Discovery의 승인 REQ들을 batch로 만들라”고 선택한 것으로 간주하되, 연결된 Approved REQ 집합이 명확할 때만 진행한다.
3. 필요한 템플릿의 논리 경로를 현재 환경의 물리 경로로 해석하고, 어떤 위치를 사용할지 확정한다.
4. 현재 저장소의 기존 batch 문서(`docs/batches/index.md`, 가능하면 가장 최근 batch의 `index.md`/`planning.md`)를 먼저 읽어 로컬 heading, register 표기, 문체를 확인한다. 템플릿은 scaffold source이고, target 문서는 저장소 로컬 형식을 우선한다.
5. REQ 수, 영향 범위, 구조/인터페이스/런타임 영향 여부를 기준으로 `standard` 또는 `batch-lite` profile을 결정한다.
   - 특히 같은 Discovery에서 나온 REQ 묶음이 (a) runtime 또는 interface 구조 변경, (b) 성능/운영 budget 같은 Non-Functional 기준, (c) baseline 문서 정렬을 함께 포함하면 기본값은 `standard`로 본다. 이런 조합은 planning만으로 끝나지 않고 design, implementation, verification 문서를 같은 턴에 scaffold하는 편이 drift와 재작업을 줄인다.
6. 단일 저위험 REQ면 `minor-change` fast path를 검토하되 최종 기록 profile은 `batch-lite`로 남긴다.
7. 배치 제목과 slug를 결정하고 다음 `BAT-ID`를 계산한다.
8. profile에 맞는 템플릿으로 batch 폴더와 문서를 생성하되, placeholder를 그대로 두지 말고 이번 REQ 집합 기준의 구체적 초안 내용을 즉시 채운다.
9. `index.md`에 `Profile`, Included REQ, Excluded REQ, Source Discovery, Scope, Documents, Notes를 채운다.
10. 포함 REQ의 source discovery를 수집해 `index.md`와 register에 반영한다. source가 복수면 Notes에 혼합 배경을 설명한다. Discovery 식별자로 시작한 경우, batch 문서에 해당 Discovery ID와 포함 REQ 목록이 모두 일치하는지 명시적으로 검증한다.
11. `planning.md`에 `Design Gate`를 기록해 design이 즉시 필요한지 여부와 근거를 남긴다.
12. `docs/batches/index.md`에 새 register 행을 추가하고 `BAT ID`, `Profile`, `Status`, `Included REQ`, `Discovery`, `Folder`를 실제 생성 결과와 일치하게 채운다. 이때 register의 헤더/구분선/행 순서는 현재 저장소 로컬 형식을 유지한다.
13. 생성된 문서 집합과 register가 profile 판단 및 입력 REQ 집합과 일치하는지 검증한다.
14. 검증 시 `stagepilot-doctor`를 실행하고 traceability matrix에서 입력 REQ가 새 `bat-XXX`에 연결되는지 확인한다. 새 batch가 아직 `draft` 상태라면 `approved-req-no-release-candidate-batch` warning은 정상적인 중간 상태로 보고, error나 batch 연결 누락만 blocker로 다룬다.
15. `git diff --stat`만으로 결과를 판단하지 않는다. 새 batch 폴더는 untracked라 diff stat에 빠질 수 있으므로 `git status --short`와 생성 대상 폴더 파일 목록을 함께 확인한다.

# Common Pitfalls

1. `Approved`가 아닌 REQ를 섞는 실수
   - batch 생성은 delivery 입력이 확정된 REQ만 대상으로 해야 하므로 상태를 먼저 검증한다.

2. 아직 사람 선택이 끝나지 않았는데 곧바로 batch를 만드는 실수
   - 여러 후보안 중 선택이 남아 있으면 먼저 `suggest-batch-reqs`에서 멈춘다.

3. `minor-change`를 최종 profile 값처럼 기록하는 실수
   - `minor-change`는 fast path 이름일 뿐이고, persisted profile은 `batch-lite`다.

4. `stage-pilot/templates/batches/index.md`와 `docs/batches/index.md`를 혼동하는 실수
   - 전자는 register template/source이고 후자는 실제 저장소 target 파일이다.

5. `batch-lite`인데 구조 영향이 생겼는데도 design 문서를 만들지 않는 실수
   - planning의 `Design Gate`를 다시 보고 필요하면 `design.md`를 추가한다.

6. 템플릿 경로를 한 설치 형태에만 고정하는 실수
   - `.stage-pilot`, `~/.stage-pilot` 순서의 resolution rule을 따른다.

7. pack-level 문서를 빼먹는 실수
   - 외부 skill pack의 SKILL.md를 실제 수정해 버전이 바뀌면 `README.md` inventory와 `CHANGELOG.md`도 같은 턴에 함께 갱신한다.

8. 템플릿 문구를 저장소 로컬 형식보다 우선해 그대로 덮어쓰는 실수
   - 템플릿은 scaffold source일 뿐이다. 실제 생성 시에는 현재 저장소의 기존 batch 문서 형식과 register 배치를 먼저 보고, target 문서는 그 로컬 형식에 맞춰 채운다.

9. 템플릿 placeholder만 복사하고 batch 초안 내용을 비워 두는 실수
   - `draft-batch` 단계에서는 최소한 포함/제외 REQ, source discovery, scope, Design Gate, 핵심 리스크까지 즉시 채워 넣어 다음 stage가 바로 이어질 수 있게 한다.

10. Discovery ID 입력을 단순 batch slug 힌트로만 쓰고 REQ 역추적을 생략하는 실수
   - `/draft-batch dcy-002` 같은 요청은 먼저 confirmed Discovery와 연결된 Approved REQ 집합을 찾아야 한다. `docs/srs/index.md`만 보지 말고 각 REQ 문서의 `Source Discovery`/Notes도 확인해 register 누락이나 문서 불일치를 잡는다.

# Verification Checklist

- [ ] 포함 REQ가 모두 `Approved` 상태다.
- [ ] 새 `BAT-ID`와 folder명이 기존 register와 충돌하지 않는다.
- [ ] 사용한 템플릿 물리 경로가 resolution rule과 일치한다.
- [ ] template source path와 generated target path를 혼동하지 않았다.
- [ ] `standard`면 5개 문서가 모두 생성되었다.
- [ ] `batch-lite`면 최소 `index.md`, `planning.md`가 생성되었고 profile이 `batch-lite`로 기록되었다.
- [ ] `planning.md`의 `Design Gate`가 현재 profile과 구조 영향 판단을 설명한다.
- [ ] `docs/batches/index.md` register 행이 실제 batch folder, profile, included REQ, discovery와 일치한다.
- [ ] source discovery가 단일/복수 여부에 맞게 기록되었다.
- [ ] 아직 사람 선택이 필요한 상태를 batch 생성으로 건너뛰지 않았다.
