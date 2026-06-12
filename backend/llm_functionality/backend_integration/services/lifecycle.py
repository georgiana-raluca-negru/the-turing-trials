from __future__ import annotations

from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, EvidenceCard
from backend_integration.models.match import (
    MatchConfig,
    MatchProgressResult,
    MatchRuntimeState,
    MatchStatus,
    ProgressAction,
)
from backend_integration.models.turns import HumanJudgeVerdictInput, HumanTurnInput, TurnRecord, VerdictRecord
from backend_integration.ports.ai_runner import AIRunnerPort


def create_match_state(
    *,
    config: MatchConfig,
    actors: ActorConfiguration,
    case_file: CaseFileBundle | None = None,
    ai_runner: AIRunnerPort | None = None,
) -> MatchRuntimeState:
    if case_file is None:
        runner = ai_runner or _get_default_ai_runner()
        resolved_case_file = runner.generate_case(
            user_prompt=config.user_prompt,
            allow_evidence_reuse=config.allow_evidence_reuse,
        )
    else:
        resolved_case_file = case_file

    state = MatchRuntimeState(
        config=config,
        actors=actors,
        case_file=resolved_case_file,
        status=MatchStatus.IN_PROGRESS,
        current_cycle=1,
        next_actor=ActorRole.PROSECUTION,
        transcript=[],
        system_events=[],
    )
    return _refresh_wait_status(state)


def progress_match_state(
    *,
    state: MatchRuntimeState,
    ai_runner: AIRunnerPort | None = None,
    human_turn: HumanTurnInput | None = None,
    human_verdict: HumanJudgeVerdictInput | None = None,
) -> MatchProgressResult:
    if human_turn is not None and human_verdict is not None:
        raise ValueError("Provide either human_turn or human_verdict, not both.")

    if state.status == MatchStatus.QUIT:
        return MatchProgressResult(
            state=state,
            action=ProgressAction.MATCH_QUIT,
            message=state.quit_reason or "Match was quit.",
        )

    if state.status == MatchStatus.COMPLETED:
        return MatchProgressResult(
            state=state,
            action=ProgressAction.MATCH_COMPLETED,
            latest_turn=state.transcript[-1] if state.transcript else None,
            message="Match is already completed.",
        )

    if state.next_actor == ActorRole.JUDGE:
        if human_turn is not None:
            raise ValueError("Judge step does not accept human_turn. Use human_verdict instead.")
        return _progress_judge_step(state=state, ai_runner=ai_runner, human_verdict=human_verdict)

    if human_verdict is not None:
        raise ValueError("human_verdict can only be submitted when the next actor is judge.")

    controller = state.actors.controller_for(state.next_actor)
    if controller == ActorController.HUMAN:
        if human_turn is None:
            awaiting_state = _refresh_wait_status(state)
            return MatchProgressResult(
                state=awaiting_state,
                action=ProgressAction.AWAITING_HUMAN_TURN,
                waiting_for_actor=awaiting_state.next_actor,
                message=f"Waiting for human {awaiting_state.next_actor.value} turn.",
            )
        return _apply_human_turn(state=state, human_turn=human_turn)

    if human_turn is not None:
        raise ValueError("human_turn was provided while the next actor is configured as AI.")

    runner = ai_runner or _get_default_ai_runner()
    ai_result = runner.run_actor_turn(state=state, actor_role=state.next_actor)

    # Hard enforcement: max 1 evidence per AI turn, no reuse
    ai_turn = ai_result.turn
    if ai_turn.attached_evidence_ids:
        available_codes = {card.code for card in get_available_evidence_for_role(state, ai_turn.actor_role)}
        valid_ids = [c for c in ai_turn.attached_evidence_ids if c in available_codes][:1]
        if valid_ids != list(ai_turn.attached_evidence_ids):
            enforced_case_file = _mark_evidence_used_for_human_turn(
                case_file=state.case_file,
                actor_role=ai_turn.actor_role,
                evidence_ids=valid_ids,
                turn_index=ai_turn.turn_index,
            )
            ai_turn = ai_turn.model_copy(update={"attached_evidence_ids": valid_ids})
            enforced_updated_case_file = enforced_case_file
        else:
            enforced_updated_case_file = ai_result.updated_case_file
    else:
        enforced_updated_case_file = ai_result.updated_case_file

    updated_state = state.model_copy(
        update={
            "case_file": enforced_updated_case_file,
            "transcript": state.transcript + [ai_turn],
            "system_events": state.system_events + ai_result.system_events,
        }
    )
    updated_state = _advance_after_turn(updated_state, ai_turn.actor_role)
    updated_state = _refresh_wait_status(updated_state)
    return MatchProgressResult(
        state=updated_state,
        action=(
            ProgressAction.MATCH_COMPLETED
            if updated_state.status == MatchStatus.COMPLETED
            else ProgressAction.AI_TURN_COMPLETED
        ),
        latest_turn=ai_turn,
        waiting_for_actor=updated_state.next_actor if updated_state.status != MatchStatus.COMPLETED else None,
        message=f"AI {ai_turn.actor_role.value} turn completed.",
    )


def progress_until_pause_or_completion(
    *,
    state: MatchRuntimeState,
    ai_runner: AIRunnerPort | None = None,
) -> MatchProgressResult:
    current_state = state
    latest_result: MatchProgressResult | None = None

    while True:
        latest_result = progress_match_state(state=current_state, ai_runner=ai_runner)
        current_state = latest_result.state
        if latest_result.action in {
            ProgressAction.AWAITING_HUMAN_TURN,
            ProgressAction.AWAITING_HUMAN_VERDICT,
            ProgressAction.MATCH_COMPLETED,
            ProgressAction.MATCH_QUIT,
        }:
            return latest_result


def quit_match_state(
    *,
    state: MatchRuntimeState,
    actor_role: ActorRole | None = None,
    reason: str = "Quit requested.",
) -> MatchProgressResult:
    if state.status == MatchStatus.COMPLETED:
        return MatchProgressResult(
            state=state,
            action=ProgressAction.MATCH_COMPLETED,
            latest_turn=state.transcript[-1] if state.transcript else None,
            message="Completed matches cannot be quit.",
        )

    if state.status == MatchStatus.QUIT:
        return MatchProgressResult(
            state=state,
            action=ProgressAction.MATCH_QUIT,
            latest_turn=state.transcript[-1] if state.transcript else None,
            message=state.quit_reason or reason,
        )

    quit_state = state.model_copy(
        update={
            "status": MatchStatus.QUIT,
            "quit_reason": reason,
            "quit_actor": actor_role,
        }
    )
    return MatchProgressResult(
        state=quit_state,
        action=ProgressAction.MATCH_QUIT,
        message=reason,
    )


def get_match_snapshot_state(state: MatchRuntimeState) -> MatchRuntimeState:
    return state.model_copy(deep=True)


def get_available_evidence_for_role(state: MatchRuntimeState, role: ActorRole) -> list[EvidenceCard]:
    if role == ActorRole.PROSECUTION:
        evidence = state.case_file.prosecution_evidence
    elif role == ActorRole.DEFENSE:
        evidence = state.case_file.defense_evidence
    else:
        evidence = state.case_file.shared_evidence

    if state.config.allow_evidence_reuse:
        return [item.model_copy(deep=True) for item in evidence]

    return [item.model_copy(deep=True) for item in evidence if not item.is_used]


def _progress_judge_step(
    *,
    state: MatchRuntimeState,
    ai_runner: AIRunnerPort | None,
    human_verdict: HumanJudgeVerdictInput | None,
) -> MatchProgressResult:
    judge_controller = state.actors.controller_for(ActorRole.JUDGE)

    if judge_controller == ActorController.HUMAN:
        if human_verdict is None:
            waiting_state = state.model_copy(update={"status": MatchStatus.AWAITING_HUMAN_VERDICT})
            return MatchProgressResult(
                state=waiting_state,
                action=ProgressAction.AWAITING_HUMAN_VERDICT,
                waiting_for_actor=ActorRole.JUDGE,
                message="Waiting for human judge verdict.",
            )

        verdict = VerdictRecord(
            guilty=human_verdict.guilty,
            reasoning=human_verdict.reasoning,
            prosecution_score=human_verdict.prosecution_score,
            defense_score=human_verdict.defense_score,
            verdict_text=(
                f"VERDICT: {'GUILTY' if human_verdict.guilty else 'NOT GUILTY'}\n"
                f"Reasoning: {human_verdict.reasoning}"
            ),
        )
        judge_turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=ActorRole.JUDGE,
            controller=ActorController.HUMAN,
            text=verdict.verdict_text,
            attached_evidence_ids=[],
        )
        completed_state = state.model_copy(
            update={
                "status": MatchStatus.COMPLETED,
                "transcript": state.transcript + [judge_turn],
                "verdict": verdict,
            }
        )
        return MatchProgressResult(
            state=completed_state,
            action=ProgressAction.MATCH_COMPLETED,
            latest_turn=judge_turn,
            message="Human judge verdict submitted.",
        )

    runner = ai_runner or _get_default_ai_runner()
    judge_result = runner.run_judge_turn(state=state)
    completed_state = state.model_copy(
        update={
            "status": MatchStatus.COMPLETED,
            "transcript": state.transcript + [judge_result.turn],
            "verdict": judge_result.verdict,
            "system_events": state.system_events + judge_result.system_events,
        }
    )
    return MatchProgressResult(
        state=completed_state,
        action=ProgressAction.MATCH_COMPLETED,
        latest_turn=judge_result.turn,
        message="AI judge verdict completed.",
    )


def _apply_human_turn(*, state: MatchRuntimeState, human_turn: HumanTurnInput) -> MatchProgressResult:
    if human_turn.actor_role != state.next_actor:
        raise ValueError(
            f"Expected human turn for {state.next_actor.value}, got {human_turn.actor_role.value}."
        )

    if human_turn.actor_role == ActorRole.JUDGE:
        raise ValueError("Human judge input must use submit_human_verdict().")

    if state.actors.controller_for(human_turn.actor_role) != ActorController.HUMAN:
        raise ValueError(f"{human_turn.actor_role.value} is not configured as a human actor.")

    validated_evidence_ids = _validate_human_evidence_selection(
        state=state,
        actor_role=human_turn.actor_role,
        attached_evidence_ids=human_turn.attached_evidence_ids,
    )

    turn = TurnRecord(
        turn_index=len(state.transcript) + 1,
        cycle_number=state.current_cycle,
        actor_role=human_turn.actor_role,
        controller=ActorController.HUMAN,
        text=human_turn.text,
        attached_evidence_ids=validated_evidence_ids,
    )
    updated_case_file = _mark_evidence_used_for_human_turn(
        case_file=state.case_file,
        actor_role=human_turn.actor_role,
        evidence_ids=validated_evidence_ids,
        turn_index=turn.turn_index,
    )
    updated_state = state.model_copy(
        update={
            "case_file": updated_case_file,
            "transcript": state.transcript + [turn],
        }
    )
    updated_state = _advance_after_turn(updated_state, human_turn.actor_role)
    updated_state = _refresh_wait_status(updated_state)
    if updated_state.status == MatchStatus.AWAITING_HUMAN_TURN:
        action = ProgressAction.AWAITING_HUMAN_TURN
    elif updated_state.status == MatchStatus.AWAITING_HUMAN_VERDICT:
        action = ProgressAction.AWAITING_HUMAN_VERDICT
    elif updated_state.status == MatchStatus.COMPLETED:
        action = ProgressAction.MATCH_COMPLETED
    else:
        action = ProgressAction.HUMAN_TURN_COMPLETED
    return MatchProgressResult(
        state=updated_state,
        action=action,
        latest_turn=turn,
        waiting_for_actor=updated_state.next_actor if updated_state.status != MatchStatus.COMPLETED else None,
        message=f"Human {human_turn.actor_role.value} turn submitted.",
    )


def _validate_human_evidence_selection(
    *,
    state: MatchRuntimeState,
    actor_role: ActorRole,
    attached_evidence_ids: list[str],
) -> list[str]:
    deduped_ids = list(dict.fromkeys(attached_evidence_ids))
    if len(deduped_ids) > 1:
        raise ValueError("At most 1 evidence item may be attached to a turn.")

    allowed_ids = {item.code for item in get_available_evidence_for_role(state, actor_role)}
    invalid_ids = [item for item in deduped_ids if item not in allowed_ids]
    if invalid_ids:
        raise ValueError(f"Invalid evidence IDs for {actor_role.value}: {invalid_ids}")
    return deduped_ids


def _mark_evidence_used_for_human_turn(
    *,
    case_file: CaseFileBundle,
    actor_role: ActorRole,
    evidence_ids: list[str],
    turn_index: int,
) -> CaseFileBundle:
    if not evidence_ids:
        return case_file.model_copy(deep=True)

    role_mapping = {
        ActorRole.PROSECUTION: "prosecution_evidence",
        ActorRole.DEFENSE: "defense_evidence",
    }
    list_name = role_mapping[actor_role]
    updated_case_file = case_file.model_copy(deep=True)
    evidence_list = getattr(updated_case_file, list_name)

    new_evidence_list = []
    selected_ids = set(evidence_ids)
    for evidence in evidence_list:
        if evidence.code in selected_ids:
            new_evidence_list.append(
                evidence.model_copy(update={"is_used": True, "used_in_turn_index": turn_index})
            )
        else:
            new_evidence_list.append(evidence)
    setattr(updated_case_file, list_name, new_evidence_list)
    return updated_case_file


def _advance_after_turn(state: MatchRuntimeState, actor_role: ActorRole) -> MatchRuntimeState:
    if actor_role == ActorRole.PROSECUTION:
        return state.model_copy(update={"next_actor": ActorRole.DEFENSE, "status": MatchStatus.IN_PROGRESS})

    if actor_role == ActorRole.DEFENSE:
        if state.current_cycle >= state.config.max_rounds:
            return state.model_copy(update={"next_actor": ActorRole.JUDGE, "status": MatchStatus.IN_PROGRESS})
        return state.model_copy(
            update={
                "current_cycle": state.current_cycle + 1,
                "next_actor": ActorRole.PROSECUTION,
                "status": MatchStatus.IN_PROGRESS,
            }
        )

    return state.model_copy(update={"status": MatchStatus.COMPLETED})


def _refresh_wait_status(state: MatchRuntimeState) -> MatchRuntimeState:
    if state.status in {MatchStatus.COMPLETED, MatchStatus.QUIT}:
        return state

    if state.next_actor == ActorRole.JUDGE and state.actors.controller_for(ActorRole.JUDGE) == ActorController.HUMAN:
        return state.model_copy(update={"status": MatchStatus.AWAITING_HUMAN_VERDICT})

    if state.actors.controller_for(state.next_actor) == ActorController.HUMAN:
        return state.model_copy(update={"status": MatchStatus.AWAITING_HUMAN_TURN})

    return state.model_copy(update={"status": MatchStatus.IN_PROGRESS})


def _get_default_ai_runner() -> AIRunnerPort:
    from backend_integration.adapters.ai_engine import AIEngineAdapter

    return AIEngineAdapter()
