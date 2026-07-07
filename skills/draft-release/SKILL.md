---
name: draft-release
description: "Use when: creating a release document from one or more release-candidate batches, running /draft-release with BAT IDs, generating docs/releases/rel-XXX_YYYYMMDD_<slug>.md, or updating docs/releases/index.md before release approval."
version: 0.8.1
author: Justin Ko
license: private
argument-hint: "예: bat-001 또는 bat-001 bat-002"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, release, drafting, documentation, sdlc]
    related_skills: [confirm-batch-verification, confirm-release, capture-release-feedback]
---

# Purpose

This skill creates a profile-aware release document from one or more verified batches and registers it in the release index.

# Inputs

- `BAT-ID` 목록
- `docs/batches/index.md`
- 각 batch의 `verification.md`
- `docs/releases/index.md`
- 템플릿의 논리 경로
  - `stage-pilot/templates/releases/release.md`
  - `stage-pilot/templates/releases/index.md`

## Template path resolution

- 템플릿은 하나의 물리 경로만 고정하지 말고 `stage-pilot/templates/...`를 논리 경로로 취급한다.
- 물리 경로는 다음 순서로 해석한다.
  1. `.stage-pilot/templates/...`
  2. `~/.stage-pilot/templates/...`
- 여러 후보가 동시에 존재하면 가장 우선순위가 높은 한 곳만 사용하고, 서로 다른 설치 위치의 템플릿을 섞지 않는다.
- 템플릿 source path와 생성 target path를 혼동하지 않는다.
  - source: `stage-pilot/templates/...`
  - target: `docs/releases/rel-XXX_YYYYMMDD_<slug>.md`, `docs/releases/index.md`

# Core Rules

- `release-candidate`가 아닌 batch는 release에 포함하지 않는다.
- 새 release 경로는 `docs/releases/rel-XXX_YYYYMMDD_<slug>.md` 형식을 사용한다.
- release는 `docs-only`, `tooling`, `app-service` profile 중 하나를 가진다.
- release profile은 포함 batch의 운영 부담 중 가장 무거운 것을 따른다. 기본 우선순위는 `app-service` > `tooling` > `docs-only`다.
- `docs-only`는 문서, 가이드, 템플릿, 정적 산출물 변경에 사용한다.
- `tooling`은 bootstrap, 스크립트, CLI, 자동화, 패키지 동작 검증이 필요한 변경에 사용한다.
- `app-service`는 실제 서비스 배포, runtime health, 로그, 운영 확인이 필요한 변경에 사용한다.
- release 문서 생성 시 Included Batch, Profile, Scope, Rollout Plan, Rollback Plan, Verification Checklist를 채운다.

# Execution Procedure

1. 입력 batch들의 상태와 verification 결과를 확인한다.
2. 포함 batch의 변경 성격과 검증 evidence를 기준으로 release profile을 결정한다.
3. 다음 `REL-ID`를 계산하고 제목/slug를 정한다.
4. 필요한 release 논리 템플릿 경로를 현재 환경의 물리 경로로 해석한 뒤 release 문서를 생성한다.
5. `docs/releases/index.md`가 없으면 `stage-pilot/templates/releases/index.md`에 해당하는 실제 template source를 해석한 뒤 생성하고, 이미 있으면 register 행을 추가한다.

# Validation

- 포함 batch가 모두 `release-candidate`인지 확인한다.
- release 문서에 `Profile`이 있고 profile별 검증 항목이 비어 있지 않은지 확인한다.
- release 문서와 index register 행이 함께 생성됐는지 확인한다.