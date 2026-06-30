import pytest
from app.models.candidate import Candidate, Provenance
from app.reporting.quality_report import QualityReporter


def test_quality_report_basic(sample_candidate):
    report = QualityReporter.generate(
        candidate=sample_candidate,
        sources_attempted=["csv", "resume"],
        sources_failed=[],
    )
    assert "csv" in report["sources_processed"]
    assert "resume" in report["sources_processed"]
    assert report["sources_failed"] == []
    assert report["skill_count"] == 3
    assert isinstance(report["overall_confidence"], float)


def test_quality_report_missing_fields():
    c = Candidate()  # all fields empty
    report = QualityReporter.generate(
        candidate=c,
        sources_attempted=["csv"],
        sources_failed=[],
    )
    assert "full_name" in report["fields_missing"]
    assert "emails" in report["fields_missing"]
    assert "phones" in report["fields_missing"]


def test_quality_report_failed_source():
    c = Candidate(full_name="X", emails=["x@x.com"])
    report = QualityReporter.generate(
        candidate=c,
        sources_attempted=["csv", "resume"],
        sources_failed=["resume"],
    )
    assert "resume" in report["sources_failed"]
    assert "resume" not in report["sources_processed"]


def test_quality_report_conflicted_fields():
    c = Candidate(
        full_name="X",
        emails=["x@x.com"],
        provenance=[
            Provenance(field="email", value="x@x.com",  source="csv",    method="column_mapping", conflict=True),
            Provenance(field="email", value="y@y.com",  source="resume", method="regex",           conflict=True),
        ],
    )
    report = QualityReporter.generate(
        candidate=c,
        sources_attempted=["csv", "resume"],
        sources_failed=[],
    )
    assert "email" in report["fields_conflicted"]
