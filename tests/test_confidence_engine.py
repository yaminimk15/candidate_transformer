import pytest
from app.models.candidate import Candidate, Provenance
from app.confidence.confidence_engine import ConfidenceEngine


def test_confidence_empty_provenance():
    c = Candidate(full_name="Alice", emails=["alice@example.com"])
    c = ConfidenceEngine.calculate(c)
    assert c.overall_confidence == 0.0


def test_confidence_single_source():
    c = Candidate(
        full_name="Alice",
        emails=["alice@example.com"],
        provenance=[
            Provenance(field="email",     value="alice@example.com", source="csv", method="column_mapping", confidence=0.90),
            Provenance(field="full_name", value="Alice",             source="csv", method="column_mapping", confidence=0.90),
        ],
    )
    c = ConfidenceEngine.calculate(c)
    assert 0.0 < c.overall_confidence <= 1.0


def test_confidence_agreement_boosts():
    """Two sources agreeing on the same value should raise confidence vs. one source."""
    single = Candidate(
        full_name="Bob",
        emails=["bob@example.com"],
        provenance=[
            Provenance(field="email", value="bob@example.com", source="resume", method="regex", confidence=0.7125),
        ],
    )
    ConfidenceEngine.calculate(single)

    multi = Candidate(
        full_name="Bob",
        emails=["bob@example.com"],
        provenance=[
            Provenance(field="email", value="bob@example.com", source="csv",    method="column_mapping", confidence=0.90),
            Provenance(field="email", value="bob@example.com", source="resume", method="regex",           confidence=0.7125),
        ],
    )
    ConfidenceEngine.calculate(multi)
    assert multi.overall_confidence > single.overall_confidence


def test_confidence_conflict_lowers():
    """Different values from two sources should lower confidence vs. agreement."""
    agreed = Candidate(
        full_name="Carol",
        emails=["carol@example.com"],
        provenance=[
            Provenance(field="email", value="carol@example.com", source="csv",    method="column_mapping", confidence=0.90),
            Provenance(field="email", value="carol@example.com", source="resume", method="regex",           confidence=0.7125),
        ],
    )
    ConfidenceEngine.calculate(agreed)

    conflicted = Candidate(
        full_name="Carol",
        emails=["carol@example.com"],
        provenance=[
            Provenance(field="email", value="carol@example.com",  source="csv",    method="column_mapping", confidence=0.90),
            Provenance(field="email", value="carol2@example.com", source="resume", method="regex",           confidence=0.7125),
        ],
    )
    ConfidenceEngine.calculate(conflicted)
    assert conflicted.overall_confidence < agreed.overall_confidence


def test_confidence_bounded():
    c = Candidate(
        full_name="Dave",
        emails=["dave@example.com"],
        provenance=[
            Provenance(field="email",     value="dave@example.com", source="ats", method="column_mapping", confidence=1.0),
            Provenance(field="full_name", value="Dave",             source="ats", method="column_mapping", confidence=1.0),
        ],
    )
    ConfidenceEngine.calculate(c)
    assert 0.0 <= c.overall_confidence <= 1.0