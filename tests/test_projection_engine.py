import json
import pytest
from app.models.candidate import Candidate, Location
from app.projection.projection_engine import ProjectionEngine


@pytest.fixture
def sample_proj_candidate():
    return Candidate(
        full_name="Yamini M K",
        emails=["yamini.0954@gmail.com"],
        phones=["+919342880954"],
        location=Location(city="Coimbatore", region="Tamil Nadu", country="India"),
        headline="Web Dev Intern",
        overall_confidence=0.82,
    )


def test_projection_basic(sample_proj_candidate):
    config = {
        "fields": [
            {"path": "candidate_name", "from": "full_name"},
            {"path": "primary_email",  "from": "emails[0]"},
        ]
    }
    out = ProjectionEngine.project(sample_proj_candidate, config)
    assert out["candidate_name"] == "Yamini M K"
    assert out["primary_email"] == "yamini.0954@gmail.com"


def test_projection_nested_path(sample_proj_candidate):
    config = {
        "fields": [
            {"path": "city",   "from": "location.city"},
            {"path": "region", "from": "location.region"},
        ]
    }
    out = ProjectionEngine.project(sample_proj_candidate, config)
    assert out["city"] == "Coimbatore"
    assert out["region"] == "Tamil Nadu"


def test_projection_normalization(sample_proj_candidate):
    config = {
        "fields": [{"path": "email_lower", "from": "emails[0]"}],
        "normalizations": {"email_lower": "lowercase"},
    }
    out = ProjectionEngine.project(sample_proj_candidate, config)
    assert out["email_lower"] == out["email_lower"].lower()


def test_projection_missing_null_policy(sample_proj_candidate):
    config = {
        "fields": [{"path": "missing_field", "from": "nonexistent"}],
        "missing_value_policy": "null",
    }
    out = ProjectionEngine.project(sample_proj_candidate, config)
    assert out["missing_field"] is None


def test_projection_missing_omit_policy(sample_proj_candidate):
    config = {
        "fields": [{"path": "missing_field", "from": "nonexistent"}],
        "missing_value_policy": "omit",
    }
    out = ProjectionEngine.project(sample_proj_candidate, config)
    assert "missing_field" not in out


def test_projection_missing_error_policy(sample_proj_candidate):
    config = {
        "fields": [{"path": "missing_field", "from": "nonexistent"}],
        "missing_value_policy": "error",
    }
    with pytest.raises(ValueError, match="missing_value_policy is 'error'"):
        ProjectionEngine.project(sample_proj_candidate, config)


def test_projection_include_confidence(sample_proj_candidate):
    config = {
        "fields": [],
        "include_confidence": True,
    }
    out = ProjectionEngine.project(sample_proj_candidate, config)
    assert "overall_confidence" in out
    assert isinstance(out["overall_confidence"], float)