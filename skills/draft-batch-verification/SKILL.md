---
name: draft-batch-verification
description: "Use when: drafting verification evidence for a batch, running /draft-batch-verification with a BAT ID, filling docs/batches/<BAT_ID>/verification.md, mapping REQ acceptance criteria to evidence before release approval, or verifying sync with docs/project-structure.md and docs/runtime-flows.md."
version: 0.8.1
author: Justin Ko
license: private
argument-hint: "예: bat-001 또는 docs/batches/bat-001_20260424_scaffold"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, verification, testing, sdlc]
    related_skills: [draft-batch, run-batch-implementation, confirm-batch-verification, stagepilot-doctor-ops]
---

# Purpose

This skill drafts the verification document for a batch by mapping included REQ acceptance criteria to available evidence and identifying remaining blockers.

batch design 또는 REQ가 baseline 문서 생성/갱신 또는 구조/흐름 영향이 있음을 나타내면, verification은 `docs/project-structure.md`와 `docs/runtime-flows.md`가 코드와 설계에 맞게 동기화되었는지도 확인해야 한다.

# Inputs

- `BAT-ID` 또는 batch 경로
- 포함된 REQ 문서들
- `docs/batches/<BAT_ID>/design.md` (존재하는 경우)
- `docs/batches/<BAT_ID>/planning.md`
- `docs/batches/<BAT_ID>/implementation.md`
- `docs/batches/<BAT_ID>/verification.md`
- `docs/project-structure.md` (존재하는 경우)
- `docs/runtime-flows.md` (존재하는 경우)

# Core Rules

- verification은 Discovery 성공 기준이 아니라 REQ acceptance criteria에 직접 연결한다.
- evidence가 없는 항목은 통과로 간주하지 않는다.
- 기본 경로에서는 `confirm-batch-verification` 전에 `delivery-runner -> dev-qc` 독립 검토가 이어질 수 있도록 verification target, evidence bundle, suspicious areas를 명시적으로 정리한다.
- 단일 저위험 `batch-lite`에서 QC handoff를 생략하려면 verification에 skip reason과 residual risk를 명시하고, confirm 단계가 그 예외를 읽을 수 있게 남긴다.
- stateful runtime/PYDEBUG binding 검증에서는 같은 입력을 연속 호출해도 내부 상태가 누적될 수 있음을 먼저 확인한다. REQ가 deterministic candidate/order evidence를 요구하면 '같은 입력 + 같은 초기 상태'를 보장하는 reset hook, 재초기화 step, 또는 동등한 통제 절차를 verification evidence에 포함한다.
- 확인되지 않은 항목은 `Blocking Issues`에 명시한다.
- `batch-lite`에서 design 문서가 없다면 planning의 `Design Gate`와 implementation 결과를 기준으로 구조 영향이 실제로 없었는지 확인해야 한다.
- design의 Architecture Impact가 `none`이 아니거나 baseline 문서 생성/갱신이 batch 범위에 있으면, baseline 문서 동기화 evidence를 verification에 포함해야 한다.
- baseline 문서 동기화가 필요한데 evidence가 없으면 release-ready로 간주하지 않는다.
- hardware/manual 검증이 남아 있는 상태에서 코드/문서 구현만 끝났다면 `Ready for Release: false`를 유지하고, 누락된 실장치 증거를 `Missing evidence`와 `Blocking Issues`에 명시해 confirm 단계로 성급히 올리지 않는다.
- 설정 persistence를 실장치로 검증할 때는 장치가 노출하는 실제 제어 경로를 먼저 확인한다. CTSP 설정의 재부팅 persistence를 확인하는 목적이면 가능할 때 CTSP `REBOOT`/`RESET` 명령으로 재부팅하고, 재부팅 전후 동일 CTSP readback(`DATE`, 대상 설정 명령 등)으로 복귀와 설정 유지 여부를 캡처한다. 테스트 중 설정을 바꿨다면 verification evidence를 수집한 뒤 baseline 값을 다시 써서 원복 여부도 함께 남긴다.
- CTSP 기반 실장치 검증에서는 먼저 비파괴 명령(예: `DATE`, 읽기 전용 `VISIONCFG`)으로 연결과 응답 형식을 확인한 뒤 쓰기/재부팅 테스트로 넘어간다. `VISIONCFG`처럼 값 목록이 단일 payload 안에 `/`로 직렬화되는 명령은 raw response, 분해 후 값 개수, slot별 해석(예: ratio 27번째, trailing reserved 28~32번째)을 함께 기록해야 한다.
- 업그레이드/migration 검증에서는 업그레이드 직전 legacy readback 원문과 기대 26개 값을 먼저 고정하고, 업그레이드 직후 첫 current 32값 readback의 1~26 슬롯을 그 legacy 캡처와 직접 대조해야 한다. ratio=`10`, trailing reserved=`0xFFFFFFFF`만 맞고 1~26 슬롯이 업그레이드 전 값과 다르면 migration 성공으로 간주하지 말고, 설정 영역 보존 실패/플래시 경로 문제/fixture 주입 실패 가능성을 blocker로 기록한다.
- 업그레이드 직후 boot log에 `current revision size mismatch (...)` 뒤 `vision config default`가 보이면, 이는 rev0 migration 성공 증거가 아니라 "current revision으로 해석된 저장본의 binary schema/길이가 현 코드와 다름"을 뜻한다. 이런 경우에는 downgrade 후 legacy `VISIONCFG` readback을 다시 캡처해 기존 26개 값이 되살아나는지 확인하고, 값이 복원되면 storage erase보다 revision-schema drift 또는 current-loader incompatibility를 우선 원인 후보로 기록한다.
- 업그레이드 경로 진단에서는 image slot과 `storage_partition`을 분리해서 해석한다. firmware loader가 image slot만 erase/write하는 구조라면, migration 실패 후 default current 값이 보였더라도 곧바로 "설정이 지워졌다"고 결론내리지 말고, downgrade/legacy readback 또는 raw property dump로 storage 보존 여부를 먼저 구분한다.
- verification에 사람이 명시적으로 잔여 리스크를 수용하기로 했다면 `Human Approval Memo` 섹션을 추가해 승인 결정, 승인자, 승인 시각, 스킵/수용 범위, 잔여 리스크, 승인 근거를 구조적으로 남긴다. 이후 confirm 단계에서는 이 메모가 수용한 blocker와 미수용 blocker를 분리해서 판단할 수 있어야 한다.
- 재부팅 persistence를 자동 검증할 때는 가능하면 ext-proto reboot보다 CTSP `REBOOT`/`RESET`처럼 실제 설정 검증 경로와 같은 제어면을 우선 사용하고, 재부팅 전후 `DATE`와 대상 설정 readback을 같이 캡처한다.

# Execution Procedure

1. batch와 포함 REQ를 확정한다.
2. REQ acceptance criteria를 목록화한다.
3. design 문서가 있으면 Architecture Impact와 Reference Doc Update Plan을 읽고, 없으면 planning의 `Design Gate`를 읽는다.
4. implementation 결과와 테스트 로그를 근거로 evidence를 연결한다.
5. baseline 문서 동기화가 필요하면 `docs/project-structure.md`와 `docs/runtime-flows.md`의 생성/갱신 여부를 evidence에 포함한다.
6. `batch-lite`에서 design이 없었다면 verification에 `no architecture impact confirmed` 여부를 남긴다.
7. `verification.md`의 Acceptance Mapping, Evidence, Result를 채운다.
8. 기본 경로라면 이후 `delivery-runner -> dev-qc` handoff에 바로 사용할 수 있게 verification target, evidence bundle, suspicious areas 또는 열린 risk를 요약한다.
9. QC handoff를 생략하는 저위험 `batch-lite` 예외라면 verification 문서에 skip reason과 residual risk를 남긴다.
10. 재부팅 persistence나 CTSP contract 계열 실장치 검증을 수행했다면 `references/opspro-visioncfg-hardware-verification.md` 같은 session note를 남겨, 실제로 성공한 명령/응답/원복 순서를 future batch verification에 재사용할 수 있게 한다. OpsPro `VISIONCFG` 작업에서는 current 32값 round-trip, legacy 26값 호환, invalid ratio reject, reboot persistence, migration failure signature(`current revision size mismatch`)뿐 아니라, 순수 legacy device에서의 성공한 first-boot migration / post-reboot current direct-load evidence와 downgrade/re-upgrade schema-drift exclusion rule까지 그 reference에 누적한다.

# Validation

- 포함 REQ마다 acceptance mapping이 존재하는지 확인한다.
- evidence 없는 항목이 있으면 Result에 blocker로 반영했는지 확인한다.
- 같은 source-of-truth/policy-boundary 계열 배치가 연속으로 실행되어 나중 배치가 이전 배치의 보존 범위를 의도적으로 더 좁힌 경우(예: calendar local vault 제거 후 todo local vault도 별도 배치에서 제거), verification은 이전 wording을 기계적으로 blocker로 처리하지 말고 최신 approved/implemented batch chain을 확인해 `superseding batch note`로 명시한다. 단, 원래 batch의 핵심 acceptance boundary가 여전히 만족되는지(예: 제거 대상 type이 재도입되지 않았는지, 남겨야 할 범위가 최소한으로 유지되는지)는 runtime/schema evidence로 검증한다.
- local vault type 제거 또는 destructive data cleanup verification에는 가능하면 다음 evidence를 함께 남긴다: runtime/schema enum import 결과, 제거된 helper/schema 파일 absence, generic `vault_*` 호출의 제거 type rejection과 postcondition(삭제된 documents path가 재생성되지 않음), active-profile data path absence, residual search 분류(활성 지원 vs negative/historical/test), StagePilot doctor warning의 pre-confirmation 여부.
- Architecture Impact가 있는 batch라면 baseline 문서 동기화 evidence 또는 blocker가 명시됐는지 확인한다.
- `batch-lite`에서 design이 없는 경우 planning과 implementation을 기준으로 구조 영향 없음 또는 design 누락 blocker 중 하나가 명시됐는지 확인한다.
- 실장치/manual evidence가 필요한 REQ인데 코드 diff나 빌드 결과만 있는 경우, `Ready for Release`가 false로 유지되고 confirm 단계 보류 사유가 적혀 있는지 확인한다.