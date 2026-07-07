---
name: capture-release-feedback
description: "Use when: recording post-release observations, running /capture-release-feedback with a REL ID, appending feedback and follow-up inputs to docs/releases/rel-XXX_*.md, or marking included batches as released after deployment feedback is captured."
version: 0.6.0
author: Justin Ko
license: private
argument-hint: "예: rel-001 또는 docs/releases/rel-001_20260424_scaffold.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, release, feedback, retrospective, sdlc]
    related_skills: [draft-release, confirm-release, suggest-next-discovery]
---

# Purpose

This skill records post-release observations, converts them into follow-up Discovery or REQ inputs, and closes the release with captured feedback.

# Inputs

- `REL-ID` 또는 release 경로
- 운영 관찰 결과
- 대상 release 문서
- 포함 batch 목록
- `docs/releases/index.md`
- `docs/batches/index.md`

# Core Rules

- 운영 관찰 결과는 사실과 후속 입력으로 분리해 기록한다.
- 후속 입력은 `Discovery Input`, `REQ Input`, `Change Request Input`으로 구분한다.
- release feedback을 남긴 뒤 release 상태는 `feedback-captured`로 전환할 수 있다.
- 포함 batch 상태는 필요하면 `released`로 갱신한다.

# Execution Procedure

1. release 문서와 포함 batch를 읽는다.
2. 운영 관찰 결과를 release 문서의 Feedback Handoff 섹션에 반영한다.
3. 후속 Discovery 입력, 신규 REQ 입력, 기존 REQ 변경 후보를 분리해 기록한다.
4. release index 상태를 `feedback-captured`로 갱신하고, 포함 batch 상태를 `released`로 조정한다.

# Validation

- release 문서에 운영 관찰 결과와 `Discovery Input`, `REQ Input`, `Change Request Input`이 모두 남았는지 확인한다.
- release index 상태와 batch index 상태가 문서 본문과 일치하는지 확인한다.