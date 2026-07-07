---
name: confirm-batch-verification
description: "Use when: approving a batch verification result, running /confirm-batch-verification with a BAT ID, promoting docs/batches/<BAT_ID> to release-candidate, or updating docs/batches/index.md after verification passes."
version: 0.8.0
author: Justin Ko
license: private
argument-hint: "예: bat-001 또는 docs/batches/bat-001_20260424_scaffold"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, verification, approval, sdlc]
    related_skills: [draft-batch-verification, confirm-req-implemented, draft-release, stagepilot-doctor-ops]
---

# Purpose

This skill checks whether a batch verification document has enough evidence to release the batch and, if so, promotes the batch to `release-candidate`.

# Inputs

- `BAT-ID` 또는 batch 경로
- `docs/batches/<BAT_ID>/verification.md`
- 포함된 REQ 문서들
- `docs/batches/index.md`

# Core Rules

- verification에 미해결 blocker가 있으면 승인하지 않는다.
- verification에 미해결 blocker가 있으면 승인하지 않는다.
- 단, verification 문서에 명시적 `Human Approval Memo`가 있고 승인자, 승인 시각, 스킵/수용 범위, 잔여 리스크, 승인 근거가 모두 적혀 있으면 그 메모가 명시적으로 수용한 blocker는 residual risk로 보고 승인할 수 있다. 이 경우 승인 결과에는 사람이 수용한 예외 범위를 함께 요약한다.
- 포함된 REQ의 acceptance criteria가 evidence와 연결돼야 한다.
- `batch-lite`는 design 문서 없이도 승인할 수 있지만, planning의 `Design Gate`가 design 불필요를 명시하고 verification이 구조 영향 없음 또는 baseline 영향 없음을 확인해야 한다.
- 승인 성공 시 batch status는 `release-candidate`가 된다.

# Execution Procedure

1. batch와 verification 문서를 읽는다.
2. 필요하면 planning과 design을 함께 읽어 profile과 구조 영향 여부를 확인한다.
3. Acceptance Mapping, Evidence, Blocking Issues를 점검한다.
4. 승인 가능하면 verification 상태와 batch index 상태를 갱신한다.
5. 승인과 함께 포함 REQ들의 구현 완료를 확인해야 하는 흐름이면 `confirm-req-implemented`도 이어서 적용하여 REQ 문서와 `docs/srs/index.md`를 `Implemented`로 동기화한다. 특히 `stagepilot-doctor`의 `approved-req-no-release-candidate-batch` warning은 batch 승격 전에는 정상일 수 있으므로, batch를 `release-candidate`로 승격하고 REQ 상태를 동기화한 뒤 반드시 doctor를 다시 실행해 warning이 해당 batch 범위에서 해소됐는지 확인한다.
6. 승인 불가면 상태는 유지하고 blocker를 보고한다.
7. verification에 `Human Approval Memo`가 있으면, 메모가 수용한 blocker와 여전히 승인 불가한 blocker를 분리해서 판단한다. 사람이 수용한 항목만 남아 있다면 verification을 `approved`로 올리고 batch를 `release-candidate`로 승격할 수 있다.

# Validation

- 승인 성공인 경우 batch index 상태가 `release-candidate`인지 확인한다.
- 승인 성공 후 포함 REQ를 `Implemented`로 동기화했다면 `stagepilot-doctor`를 재실행하고 traceability matrix에서 해당 REQ들이 `implemented`, 해당 batch가 `Release-Ready Batch`로 표시되며 batch 범위 warning/flags가 사라졌는지 확인한다. 남은 warning이 다른 discovery/batch 범위라면 verification 문서에 out-of-scope non-blocker로 기록한다.
- `draft-batch-verification` 단계에서 doctor warning을 "expected until confirmation"으로 기록했다면, confirmation 후 재실행 결과를 `verification.md`에 다시 반영한다. 성공 시 pre-confirmation warning 문구를 현재 blocker처럼 남겨두지 말고 `Post-confirmation doctor: no issues found`와 traceability matrix 요약을 추가/갱신한다.
- 최종 보고 전 targeted status check를 실행해 다음을 한 번에 확인한다: batch `index.md` Status, `verification.md` Status/Ready for Release, `docs/batches/index.md` row, 포함 REQ 문서 및 `docs/srs/index.md`의 `Implemented` 상태.
- 승인 보류인 경우 blocker가 명시됐는지 확인한다.
- `batch-lite` 승인 성공인 경우 design 부재가 검증 근거와 모순되지 않는지 확인한다.