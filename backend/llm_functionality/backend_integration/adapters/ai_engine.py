from __future__ import annotations

import re

from ai_engine.agents.ai_clerk import generate_case_node
from ai_engine.agents.ai_judge import judge_verdict_node
from ai_engine.agents.defense import defense_turn_node
from ai_engine.agents.prosecutor import prosecutor_turn_node
from ai_engine.models.schemas import Argument, CaseContext, Evidence as AIEngineEvidence

from backend_integration.models.actors import ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, CaseSummary, EvidenceCard, EvidenceRole
from backend_integration.models.match import MatchRuntimeState
from backend_integration.models.turns import TurnRecord, VerdictRecord
from backend_integration.ports.ai_runner import AIRunnerJudgeResult, AIRunnerPort, AIRunnerTurnResult


class AIEngineAdapter(AIRunnerPort):
    def generate_case(self, *, user_prompt: str, allow_evidence_reuse: bool) -> CaseFileBundle:
        state_update = generate_case_node(
            {
                "user_prompt": user_prompt,
                "allow_evidence_reuse": allow_evidence_reuse,
            }
        )
        return CaseFileBundle(
            summary=_from_ai_case_summary(state_update["case_summary"]),
            prosecution_evidence=[
                _from_ai_evidence(evidence, EvidenceRole.PROSECUTION)
                for evidence in state_update["prosecution_evidence"]
            ],
            defense_evidence=[
                _from_ai_evidence(evidence, EvidenceRole.DEFENSE)
                for evidence in state_update["defense_evidence"]
            ],
        )

    def run_actor_turn(self, *, state: MatchRuntimeState, actor_role: ActorRole) -> AIRunnerTurnResult:
        ai_state = _to_ai_state(state)
        previous_event_count = len(ai_state.get("system_events", []))

        if actor_role == ActorRole.PROSECUTION:
            state_update = prosecutor_turn_node(ai_state)
        elif actor_role == ActorRole.DEFENSE:
            state_update = defense_turn_node(ai_state)
        else:
            raise ValueError(f"Unsupported actor role for debate turn: {actor_role}")

        merged_messages = state_update["messages"]
        latest_message: Argument = merged_messages[-1]
        new_system_events = state_update.get("system_events", ai_state.get("system_events", []))[previous_event_count:]

        updated_case_file = state.case_file.model_copy(
            update={
                "prosecution_evidence": (
                    [_from_ai_evidence(evidence, EvidenceRole.PROSECUTION) for evidence in state_update.get("prosecution_evidence", ai_state["prosecution_evidence"])]
                ),
                "defense_evidence": (
                    [_from_ai_evidence(evidence, EvidenceRole.DEFENSE) for evidence in state_update.get("defense_evidence", ai_state["defense_evidence"])]
                ),
            }
        )

        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=actor_role,
            controller=ActorController.AI,
            text=latest_message.text,
            attached_evidence_ids=latest_message.attached_evidence_ids,
            skipped=latest_message.text.startswith("[TURN MISSED]"),
            system_note=new_system_events[-1] if new_system_events else None,
        )
        return AIRunnerTurnResult(
            turn=turn,
            updated_case_file=updated_case_file,
            system_events=new_system_events,
        )

    def run_judge_turn(self, *, state: MatchRuntimeState) -> AIRunnerJudgeResult:
        ai_state = _to_ai_state(state)
        previous_event_count = len(ai_state.get("system_events", []))
        state_update = judge_verdict_node(ai_state)

        latest_message: Argument = state_update["messages"][-1]
        new_system_events = state_update.get("system_events", ai_state.get("system_events", []))[previous_event_count:]
        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=ActorRole.JUDGE,
            controller=ActorController.AI,
            text=latest_message.text,
            attached_evidence_ids=[],
            skipped=False,
            system_note=new_system_events[-1] if new_system_events else None,
        )
        verdict = _parse_verdict_text(latest_message.text)
        return AIRunnerJudgeResult(
            turn=turn,
            verdict=verdict,
            system_events=new_system_events,
        )


def _to_ai_state(state: MatchRuntimeState) -> dict:
    return {
        "user_prompt": state.config.user_prompt,
        "allow_evidence_reuse": state.config.allow_evidence_reuse,
        "case_summary": _to_ai_case_summary(state.case_file.summary),
        "defense_evidence": [_to_ai_evidence(evidence) for evidence in state.case_file.defense_evidence],
        "prosecution_evidence": [_to_ai_evidence(evidence) for evidence in state.case_file.prosecution_evidence],
        "messages": _build_message_history(state),
        "round_number": state.current_cycle,
        "system_events": list(state.system_events),
    }


def _build_message_history(state: MatchRuntimeState) -> list[Argument]:
    all_cards = (
        state.case_file.prosecution_evidence
        + state.case_file.defense_evidence
        + state.case_file.shared_evidence
    )
    evidence_by_code = {card.code: card for card in all_cards}

    messages = []
    for turn in state.transcript:
        if turn.actor_role == ActorRole.JUDGE:
            continue
        arg = _to_ai_argument(turn)
        if turn.attached_evidence_ids:
            evidence_notes = []
            for code in turn.attached_evidence_ids:
                card = evidence_by_code.get(code)
                if card:
                    evidence_notes.append(
                        f"[Evidence submitted: {card.title} — {card.description}]"
                    )
            if evidence_notes:
                arg = arg.model_copy(
                    update={"text": arg.text + "\n" + "\n".join(evidence_notes)}
                )
        messages.append(arg)
        if turn.system_note == "[OBJECTION RAISED]":
            messages.append(Argument(
                speaker="System",
                text=(
                    "[COURT NOTICE — OBJECTION] The opposing counsel has formally challenged "
                    "the preceding argument as irrelevant or misleading. "
                    "In your next argument you MUST directly address and rebut this objection "
                    "before presenting any new points."
                ),
                attached_evidence_ids=[],
            ))
    return messages


def _to_ai_case_summary(summary: CaseSummary) -> CaseContext:
    return CaseContext(
        crime=summary.crime,
        charges=list(summary.charges),
        background_story=summary.background_story,
    )


def _from_ai_case_summary(summary: CaseContext) -> CaseSummary:
    return CaseSummary(
        crime=summary.crime,
        charges=list(summary.charges),
        background_story=summary.background_story,
    )


def _to_ai_evidence(evidence: EvidenceCard) -> AIEngineEvidence:
    return AIEngineEvidence(
        id=evidence.code,
        title=evidence.title,
        description=evidence.description,
        type=evidence.evidence_type,
        is_used=evidence.is_used,
    )


def _from_ai_evidence(evidence: AIEngineEvidence, role: EvidenceRole) -> EvidenceCard:
    return EvidenceCard(
        code=evidence.id,
        title=evidence.title,
        description=evidence.description,
        evidence_type=evidence.type,
        assigned_role=role,
        backend_id=None,
        is_used=evidence.is_used,
    )


def _to_ai_argument(turn: TurnRecord) -> Argument:
    speaker = {
        ActorRole.PROSECUTION: "Prosecutor",
        ActorRole.DEFENSE: "Defense",
        ActorRole.JUDGE: "Judge",
    }[turn.actor_role]
    return Argument(
        speaker=speaker,
        text=turn.text,
        attached_evidence_ids=list(turn.attached_evidence_ids),
    )


def _parse_verdict_text(text: str) -> VerdictRecord:
    normalized_text = text.strip()
    guilty_match = re.search(r"VERDICT:\s*(GUILTY|NOT GUILTY)", normalized_text, flags=re.IGNORECASE)
    reasoning_match = re.search(r"Reasoning:\s*(.*?)(?:\nScores\s*-|$)", normalized_text, flags=re.IGNORECASE | re.DOTALL)
    scores_match = re.search(
        r"Scores\s*-\s*Prosecution:\s*(\d+)/10,\s*Defense:\s*(\d+)/10",
        normalized_text,
        flags=re.IGNORECASE,
    )

    guilty_value = None
    if guilty_match:
        guilty_value = guilty_match.group(1).upper() == "GUILTY"

    reasoning_value = reasoning_match.group(1).strip() if reasoning_match else normalized_text
    prosecution_score = int(scores_match.group(1)) if scores_match else None
    defense_score = int(scores_match.group(2)) if scores_match else None

    return VerdictRecord(
        guilty=guilty_value,
        reasoning=reasoning_value,
        prosecution_score=prosecution_score,
        defense_score=defense_score,
        verdict_text=normalized_text,
    )
