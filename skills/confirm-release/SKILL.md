---
name: confirm-release
description: "Use when: approving a release plan, running /confirm-release with a REL ID or release path, promoting docs/releases/rel-XXX_*.md from draft to confirmed, or validating rollout and rollback readiness before deployment."
version: 0.8.0
author: Justin Ko
license: private
argument-hint: "예: rel-001 또는 docs/releases/rel-001_20260424_scaffold.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, release, approval, quality, sdlc]
    related_skills: [draft-release, capture-release-feedback, suggest-next-discovery]
---

# Purpose

This skill validates a release document and promotes it to `confirmed` only when rollout, rollback, and verification checks are ready.

# Inputs

- `REL-ID` 또는 release 경로
- 대상 release 문서
- `docs/releases/index.md`
- 포함 batch 문서들

# Core Rules

- Included Batch가 모두 release-candidate여야 한다.
- Rollout Plan, Rollback Plan, Verification Checklist가 비어 있으면 승인하지 않는다.
- release profile에 맞는 검증 항목이 비어 있으면 승인하지 않는다.
- `docs-only`는 링크/렌더링/패키징 검증으로 충분하며 health endpoint를 요구하지 않는다.
- `tooling`은 설치/업데이트/CLI 또는 스크립트 smoke 결과가 있어야 한다.
- `app-service`는 health, 로그, smoke 또는 동등한 운영 확인 근거가 있어야 한다.
- 승인 성공 시 release 상태를 `confirmed`로 바꾸고 index를 갱신한다.

# Execution Procedure

1. release 문서와 포함 batch 상태를 확인한다.
2. rollout, rollback, verification 준비도와 release profile의 필수 검증 항목을 점검한다.
3. 게이트 통과 시 release 상태와 index를 `confirmed`로 갱신한다.
4. 미통과 시 상태는 유지하고 blocker를 보고한다.

# Validation

- 승인 성공인 경우 release 문서와 index 상태가 모두 `confirmed`인지 확인한다.
- 승인 보류인 경우 누락 항목이 명시됐는지 확인한다.
- profile별 검증 항목이 release 문서의 선택된 profile과 모순되지 않는지 확인한다.