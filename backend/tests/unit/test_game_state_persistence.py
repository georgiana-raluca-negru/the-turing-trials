from types import SimpleNamespace

from app.models.match import Verdict
from app.services.game_service import (
    _build_persisted_case_summary,
    _build_persisted_verdict,
    _enrich_persisted_evidence,
    _load_persisted_legal_sources,
    _load_persisted_transcript,
)


def test_persisted_verdict_has_same_shape_as_live_verdict() -> None:
    match = SimpleNamespace(
        verdict=Verdict.GUILTY,
        verdict_reasoning="The charge was proven [LAW_2].",
    )
    transcript = [
        {
            "actor": "judge",
            "text": "VERDICT: GUILTY\nScores - Prosecution: 8/10, Defense: 5/10",
            "legal_citation_ids": ["LAW_2"],
        }
    ]

    verdict = _build_persisted_verdict(match, transcript)

    assert verdict == {
        "guilty": True,
        "reasoning": "The charge was proven [LAW_2].",
        "prosecution_score": 8,
        "defense_score": 5,
        "verdict_text": "VERDICT: GUILTY\nScores - Prosecution: 8/10, Defense: 5/10",
        "legal_citation_ids": ["LAW_2"],
    }


def test_pending_persisted_verdict_without_reasoning_is_not_rendered() -> None:
    match = SimpleNamespace(verdict=Verdict.PENDING, verdict_reasoning=None)

    assert _build_persisted_verdict(match, []) is None


def test_persisted_case_summary_uses_structured_case_file() -> None:
    case_file = {
        "summary": {
            "crime": "Vehicle theft",
            "charges": ["Theft", "Driving without a licence"],
            "background_story": "A parked vehicle was taken.",
        }
    }

    assert _build_persisted_case_summary(case_file, "legacy summary") == {
        "crime": "Vehicle theft",
        "charges": ["Theft", "Driving without a licence"],
        "background_story": "A parked vehicle was taken.",
    }


def test_persisted_transcript_normalizes_legacy_missing_fields() -> None:
    transcript = _load_persisted_transcript('[{"actor":"judge"}, null]')

    assert transcript == [
        {
            "actor": "judge",
            "text": "",
            "evidence_ids": [],
            "legal_citation_ids": [],
            "skipped": False,
            "system_note": None,
        }
    ]


def test_persisted_transcript_restores_evidence_card_details() -> None:
    transcript = [{"evidence_ids": ["Camera footage"]}]
    case_file = {
        "prosecution_evidence": [
            {
                "code": "P1",
                "title": "Camera footage",
                "description": "The recording shows the vehicle leaving.",
            }
        ]
    }

    _enrich_persisted_evidence(transcript, case_file)

    assert transcript[0]["evidence_used"] == [
        {
            "title": "Camera footage",
            "desc": "The recording shows the vehicle leaving.",
        }
    ]


def test_malformed_persisted_legal_sources_are_skipped_individually() -> None:
    sources = _load_persisted_legal_sources(
        [
            {"law": "Codul penal", "text": "Articol valid", "source_url": "https://legislatie.just.ro/valid"},
            {"law": "Codul penal", "source_url": "https://legislatie.just.ro/missing-text"},
        ]
    )

    assert len(sources) == 1
    assert sources[0].law == "Codul penal"
