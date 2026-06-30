import pytest
from app.services.transformation_service import TransformationService


SAMPLE_CSV    = "data/recruiter.csv"
SAMPLE_RESUME = "data/sample_resume.pdf"
SAMPLE_CONFIG = "config/projection_config.json"
SAMPLE_LINKEDIN = "data/linkedin_stub.json"
MERGE_CONFIG  = "config/merge_config.json"


def test_transform_two_sources():
    """Full pipeline with CSV + Resume should produce a valid result dict."""
    svc = TransformationService()
    result = svc.transform(
        csv_path=SAMPLE_CSV,
        resume_path=SAMPLE_RESUME,
        config_path=SAMPLE_CONFIG,
        merge_config_path=MERGE_CONFIG,
    )
    assert "canonical_profile" in result
    assert "projected_output" in result
    assert "data_quality_report" in result


def test_transform_three_sources():
    """Pipeline with CSV + Resume + LinkedIn should process all three."""
    svc = TransformationService()
    result = svc.transform(
        csv_path=SAMPLE_CSV,
        resume_path=SAMPLE_RESUME,
        config_path=SAMPLE_CONFIG,
        linkedin_path=SAMPLE_LINKEDIN,
        merge_config_path=MERGE_CONFIG,
    )
    report = result["data_quality_report"]
    assert "linkedin" in report["sources_processed"]


def test_transform_canonical_has_required_fields():
    svc = TransformationService()
    result = svc.transform(
        csv_path=SAMPLE_CSV,
        resume_path=SAMPLE_RESUME,
        config_path=SAMPLE_CONFIG,
    )
    profile = result["canonical_profile"]
    assert profile.get("full_name")
    assert len(profile.get("emails", [])) > 0
    assert profile.get("overall_confidence", 0) > 0


def test_transform_candidate_id_stable():
    """Same inputs should always produce the same candidate_id."""
    svc = TransformationService()
    r1 = svc.transform(SAMPLE_CSV, SAMPLE_RESUME, SAMPLE_CONFIG)
    r2 = svc.transform(SAMPLE_CSV, SAMPLE_RESUME, SAMPLE_CONFIG)
    assert r1["canonical_profile"]["candidate_id"] == r2["canonical_profile"]["candidate_id"]


def test_transform_merge_trace_present():
    svc = TransformationService()
    result = svc.transform(SAMPLE_CSV, SAMPLE_RESUME, SAMPLE_CONFIG)
    trace = result["canonical_profile"].get("merge_trace", {})
    assert isinstance(trace, dict)
    assert len(trace) > 0


def test_transform_quality_report_structure():
    svc = TransformationService()
    result = svc.transform(SAMPLE_CSV, SAMPLE_RESUME, SAMPLE_CONFIG)
    report = result["data_quality_report"]
    for key in ["sources_attempted", "sources_processed", "sources_failed",
                "fields_missing", "fields_conflicted", "overall_confidence"]:
        assert key in report, f"Missing key in quality report: {key}"