---
name: run-batch-delivery
description: "Use when: orchestrating the full delivery chain for an existing batch, running /run-batch-delivery with a BAT ID, resuming an in-progress batch from the first incomplete delivery stage, or chaining planning, design, implementation, verification drafting, verification approval, and REQ implementation sync for one selected batch."
version: 0.7.2
author: Justin Ko
license: private
argument-hint: "예: bat-002 또는 docs/batches/bat-002_20260522_visioncfg-32-contract-migration"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, batch, delivery, orchestration, execution, sdlc]
    related_skills: [draft-batch-planning, draft-batch-design, run-batch-implementation, draft-batch-verification, confirm-batch-verification, confirm-req-implemented, draft-release, stagepilot-agent-harness, stagepilot-doctor-ops]
---

# Purpose

This skill orchestrates the Delivery phase for one already-created batch by chaining the batch-level skills in order until the batch reaches `release-candidate` and its included REQs are synchronized to `Implemented` where evidence exists.

이 skill은 새 batch를 만들지 않는다. 이미 존재하는 `docs/batches/<BAT_ID>/`를 기준으로 현재 delivery 진행 상태를 읽고, 아래 6단계를 순서대로 이어 붙이는 orchestration entrypoint다.

1. `draft-batch-planning`
2. `draft-batch-design`
3. `run-batch-implementation`
4. `draft-batch-verification`
5. `confirm-batch-verification`
6. `confirm-req-implemented`

# When to use

- `/run-batch-delivery bat-002`처럼 특정 batch를 delivery phase 끝까지 밀고 싶을 때
- 이미 `draft-batch`까지 끝난 batch를 planning/design/implementation/verification/REQ 상태 동기화까지 이어서 처리할 때
- 기존 batch가 어느 delivery 단계에서 멈췄는지 확인하고, 첫 incomplete stage부터 재개하고 싶을 때
- `delivery-runner`가 REQ 묶음을 확정했고 batch도 생성했으므로, 이제 batch 내부 delivery chain만 집중 실행해야 할 때

## Do not use when

- 아직 batch가 생성되지 않았고 포함 REQ 집합 선택도 끝나지 않았을 때 (`suggest-batch-reqs`, `draft-batch`가 더 적절함)
- 단순히 batch의 planning만 채우거나 design만 보강하려는 단일 단계 작업일 때 (해당 개별 skill이 더 적절함)
- verification 승인 이후 release 문서까지 자동으로 이어 가고 싶을 때 (`draft-release`는 별도 단계로 남겨 둔다)
- batch가 아니라 저장소 전체의 다음 SDLC 단계를 판단하려는 상황일 때 (`run-sdlc`가 더 적절함)

# Inputs

- `BAT-ID` prefix 또는 batch 경로
- `docs/batches/<BAT_ID>/index.md`
- `docs/batches/<BAT_ID>/planning.md`
- `docs/batches/<BAT_ID>/design.md` (존재하는 경우)
- `docs/batches/<BAT_ID>/implementation.md` (존재하는 경우)
- `docs/batches/<BAT_ID>/verification.md` (존재하는 경우)
- 포함된 REQ 문서들
- `docs/batches/index.md`
- `docs/srs/index.md`

# Core Rules

## 0. Delivery profile first

- Select and persist `delivery_profile` (`fast`, `standard`, `guarded`) before selecting the chain; canonical policy is [docs/delivery-profiles.md](../../docs/delivery-profiles.md).
- `fast` is only for one small local low-risk change and replaces the six-stage chain with runner → impl → targeted validation; record validation, QC waiver reason, and residual risk in root state.
- `standard` retains this chain when its stages are justified, but QC/supervision are risk-triggered rather than automatic.
- `guarded` requires the complete chain and full supervised independent review.

## 1. 배치 단위 orchestration

- 이 skill은 정확히 하나의 batch를 대상으로 한다.
- 입력 batch가 유일하게 확정되지 않으면 진행하지 않는다.
- batch 밖의 다른 REQ나 다른 batch를 임의로 끌어오지 않는다.

## 2. 6단계 delivery chain 유지

- 기본 chain은 아래 순서를 따른다.
  1. `draft-batch-planning`
  2. `draft-batch-design`
  3. `run-batch-implementation`
  4. `draft-batch-verification`
  5. `confirm-batch-verification`
  6. `confirm-req-implemented`
- 앞 단계 결과가 다음 단계 입력 전제를 만족하지 않으면 그 지점에서 멈추고 blocker를 보고한다.
- `confirm-batch-verification`과 `confirm-req-implemented`는 승인 게이트이므로 evidence 부족 상태를 억지로 통과시키지 않는다.

## 3. design 생략 규칙

- batch profile이 `batch-lite`이고 planning의 `Design Gate`가 `no`이며 구조/인터페이스/런타임 영향이 실제로 없을 때만 `draft-batch-design`을 생략할 수 있다.
- 그 외에는 design 단계를 delivery chain에 포함한다.
- 생략 여부는 planning 문서와 batch index 근거로 설명되어야 한다.

## 4. 중복 실행보다 불완전 단계 우선

- 이미 충분히 채워진 단계는 다시 덮어쓰는 것이 목적이 아니다.
- 각 단계는 먼저 현재 batch 문서를 읽고, 실제로 비어 있거나 draft 수준인 stage부터 시작한다.
- 다만 앞 단계 산출물이 뒤 단계 전제를 만족하지 못하면 필요한 범위 내에서 보강할 수 있다.

## 4a. 중간 commit 요청은 scope 전환으로 처리

- delivery chain 도중 사용자가 `commit`, `커밋해줘`처럼 커밋만 요청하면, 그 요청을 현재 턴의 active scope로 취급한다.
- 이때 남은 implementation/verification/REQ sync 단계를 임의로 계속 진행하지 않는다.
- 현재 dirty tree를 확인하고, 이미 생성/수정된 batch 산출물에 맞는 최소 검증을 실행한 뒤 의도된 파일만 stage/commit한다.
- 최종 보고에는 커밋 hash/message, 실행한 검증, batch delivery에서 아직 남은 단계(`implementation`, `verification`, `confirm-batch-verification`, `confirm-req-implemented` 등)를 명확히 분리해서 적는다.

## 5. 사람 결정과 승인 게이트 존중

- verification evidence가 부족하거나 blocker가 있으면 `confirm-batch-verification`에서 멈춘다.
- 기본 경로에서는 `confirm-batch-verification` 전에 `delivery-runner -> dev-qc` 독립 검토를 거친다.
- 단일 저위험 `batch-lite`만 예외적으로 QC handoff를 생략할 수 있고, 이 경우 생략 사유와 residual risk를 verification 문서에 남긴다.
- 동일 acceptance scope에 대한 QC verdict는 최대 3회(초기 QC 1회 + 재작업 후 재검토 2회)까지만 허용한다.
- 같은 QC gap이 3번째 verdict에서도 unresolved이면 `delivery-runner -> lead` escalation을 강제하고, impl↔QC 루프를 계속 돌리지 않는다.
- REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, 또는 runner authority 밖 판단이 원인이면 retry budget을 쓰지 말고 즉시 escalation한다.
- harness runtime을 사용할 수 있는 `standard`/`guarded` delivery에서는 `scripts/run_qc_rework_loop.py`로 QC FAIL → fresh impl rework → required validation → fresh QC를 실행한다. 임의 launcher 재호출로 verdict count, canonical QC verdict artifact, fresh review, terminal escalation을 우회하지 않는다.
- REQ acceptance criteria와 evidence 연결이 불충분하면 `confirm-req-implemented`에서 멈춘다.
- release 문서 생성과 release 승인까지 자동으로 넘기지 않는다. 이 skill의 종료점은 delivery phase 완료 직전 또는 완료 직후 상태 보고다.

## 6. child skill 규칙 상속

- 이 skill은 하위 skill들을 대체하지 않는다.
- 각 단계에서는 해당 skill의 prerequisite, validation, blocker 규칙을 그대로 따른다.
- 특히 baseline 문서(`docs/project-structure.md`, `docs/runtime-flows.md`) 영향 여부는 design/verification 단계 child skill 규칙을 따라 점검한다.

# Execution Procedure

1. 입력에서 `BAT-ID` 또는 batch 경로를 유일하게 확정한다.
2. batch `index.md`, `planning.md`, `design.md`, `implementation.md`, `verification.md`, 포함 REQ, `docs/batches/index.md`, `docs/srs/index.md`를 읽어 현재 delivery 상태를 요약한다.
3. 아래 기준으로 첫 incomplete stage를 판정한다.
   - `planning.md`가 비어 있거나 draft 수준이면 `draft-batch-planning`
   - design이 필요하지만 `design.md`가 비어 있거나 부족하면 `draft-batch-design`
   - 구현 로그/변경/검증 기록이 부족하면 `run-batch-implementation`
   - verification mapping/evidence 초안이 부족하면 `draft-batch-verification`
   - verification evidence는 있으나 batch가 아직 `release-candidate`가 아니면 `confirm-batch-verification`
   - batch가 `release-candidate` 또는 `released`인데 포함 REQ 중 `Approved`가 남아 있으면 `confirm-req-implemented`
4. 첫 incomplete stage부터 시작해, blocker가 생길 때까지 다음 stage로 순차 진행한다.
5. `draft-batch-planning`이 실행되면 범위, dependency, milestone, Design Gate가 채워졌는지 확인한다.
6. `draft-batch-design`이 필요하면 architecture summary, changed areas, key decisions, architecture impact가 채워졌는지 확인한다.
7. Before `run-batch-implementation`, verify that the batch/impl handoff is patch-ready: target files, edit anchors, service seams, return shape, render insertion point, test assertions, forbidden data exposure, allowed search budget, validation commands, and first-progress expectations are explicit. If not, stop and improve/escalate the batch document rather than launching `dev-impl`.
8. `run-batch-implementation` 후에는 구현 변경, execution log, validation, remaining risks가 기록됐는지 확인한다.
8. `draft-batch-verification` 후에는 REQ acceptance criteria와 evidence mapping, blocking issues, baseline 동기화 evidence가 필요한 경우 그 항목이 채워졌는지 확인한다.
9. 기본 경로라면 `confirm-batch-verification` 전에 `delivery-runner -> dev-qc` handoff를 수행하고 QC verdict를 반영한다. 단일 저위험 `batch-lite` 예외만 QC 생략 사유와 residual risk를 남긴 뒤 다음 단계로 간다.
10. QC가 gap을 반환하면 먼저 원인을 `implementation defect` / `evidence gap` / `REQ ambiguity or governance issue`로 분류한다. harness runtime이 있는 `standard`/`guarded` delivery이면 `scripts/run_qc_rework_loop.py`에 acceptance scope, impl handoff/context, QC handoff, validation command를 제공해 loop를 실행한다. 구현 결함과 evidence gap만 재작업 대상으로 돌리고, governance/REQ 문제는 즉시 `lead`로 escalate한다.
11. controller가 terminal PASS 또는 blocked 상태를 state에 기록할 때까지 기다리고, 같은 acceptance scope의 QC verdict가 3번째에도 실패하면 `Stopped at verification` + mandatory escalation으로 보고한다. 추가 재작업 루프를 직접 실행하지 않는다.
12. `confirm-batch-verification` 성공 시 batch가 `release-candidate`로 전환됐는지 확인한다. 실패 시 blocker를 보고하고 멈춘다.
13. `confirm-req-implemented`를 실행해 포함 REQ 중 evidence가 충분한 항목만 `Implemented`로 동기화한다. 부족한 항목은 blocker와 함께 남긴다.
14. delivery chain 종료 후 결과를 아래 중 하나로 보고한다.
    - `Stopped at <stage>` + blocker
    - `Delivery chain complete through REQ sync`
15. delivery chain이 성공적으로 끝났으면 다음 단계로 `draft-release`를 추천하되, 자동 실행하지는 않는다.

# Output Expectations

- 대상 batch 경로
- 시작 시점 batch 상태 요약
- 실제로 실행한 stage 목록
- 생략한 stage와 생략 근거 (`batch-lite` design 생략 등)
- 각 stage 결과 요약
- 중단 지점과 blocker 또는 완료 결과
- batch 최종 상태 (`draft` | `in-delivery` | `release-candidate` 등)
- 포함 REQ 중 `Implemented` 전환 성공 목록 / 보류 목록
- 다음 권장 단계 (`draft-release` 또는 blocker 해소)

# Common Pitfalls

1. `draft-batch` 전 batch를 바로 delivery chain에 넣는 실수
   - 이 skill은 이미 생성된 batch가 전제다. REQ 묶음 선택이나 batch 생성은 먼저 끝나 있어야 한다.

2. `draft-batch-verification`을 건너뛰고 바로 `confirm-batch-verification`으로 가는 실수
   - verification 초안과 evidence mapping이 먼저 있어야 approval gate를 제대로 통과시킬 수 있다.

3. `batch-lite`라는 이유만으로 design을 자동 생략하는 실수
   - planning의 `Design Gate`가 `no`여야 하고 실제 구조 영향도 없어야 한다.

4. verification blocker가 있는데도 REQ를 `Implemented`로 올리는 실수
   - `confirm-req-implemented`는 batch verification evidence를 근거로 해야 하므로 blocker가 남아 있으면 보류해야 한다.

5. child skill이 이미 만든 문서를 읽지 않고 매번 처음부터 다시 쓰는 실수
   - 현재 batch 문서를 먼저 읽고, 첫 incomplete stage부터 이어 가야 한다.

6. release까지 자동으로 계속 진행하는 실수
   - 이 skill의 역할은 delivery chain orchestration이다. release 문서 생성/승인은 별도 stage다.

# Verification Checklist

- [ ] 대상 batch가 유일하게 확정되었다.
- [ ] batch 생성 단계가 이미 완료된 상태다.
- [ ] planning -> design -> implementation -> verification drafting -> verification approval -> REQ sync 순서가 유지되었다.
- [ ] `batch-lite` design 생략은 `Design Gate`와 실제 영향 근거로 설명된다.
- [ ] 기본 경로에서는 `confirm-batch-verification` 전에 QC handoff와 verdict가 반영되었다.
- [ ] QC handoff를 생략한 경우 단일 저위험 `batch-lite` 예외이며 생략 사유와 residual risk가 기록되었다.
- [ ] 같은 acceptance scope에서 QC verdict가 3회를 넘기지 않았고, 3번째 unresolved verdict는 lead escalation으로 전환되었다.
- [ ] REQ ambiguity / scope mismatch / release-risk posture 문제는 retry budget 소비 대신 즉시 escalation되었다.
- [ ] `confirm-batch-verification`은 blocker 없는 evidence 상태에서만 통과했다.
- [ ] `confirm-req-implemented`는 evidence가 연결된 REQ만 전환했다.
- [ ] stage별 실행 결과와 중단/완료 상태가 보고되었다.
- [ ] release 단계는 자동으로 진행하지 않고 별도 추천으로 남겼다.


### Supervised worker lifecycle integrity

- Runner-owned supervised impl/QC calls should launch in background/tmux mode by default; foreground supervised execution is an explicit short-runtime exception only when the caller timeout is safely above the child max runtime.
- The runner must poll the launcher `exit_file`, worker log, and supervisor `final-result.json`. If `final-result.json` is missing or has `result_class=supervisor_interrupted`, classify it as `supervisor_integrity_failure` / harness execution failure, not as implementation acceptance failure.
- Child logs, diffs, and progress artifacts may be used as secondary evidence, but they do not replace the canonical supervisor final result.
- If a completed implementation has a simple same-scope implementation-context mismatch (for example visible label or CTA wording), the runner may create a fresh bounded rework handoff without lead escalation. Escalate only when the contract itself is ambiguous, scope changes, or governance/product authority is needed.
- Implementation contexts with user-visible copy requirements should include machine-checkable assertions such as required visible strings, forbidden visible strings, and required metric labels before QC handoff.
