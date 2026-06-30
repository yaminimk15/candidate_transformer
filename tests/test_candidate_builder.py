import pytest
from app.services.candidate_builder import CandidateBuilder


def test_from_csv_basic(sample_csv_record):
    c = CandidateBuilder.from_csv(sample_csv_record)
    assert c.full_name == "Yamini M K"
    assert "yamini.0954@gmail.com" in c.emails
    assert "+919342880954" in c.phones


def test_from_csv_phone_normalized(sample_csv_record):
    """Raw phone 9342880954 should become E.164 +919342880954."""
    c = CandidateBuilder.from_csv(sample_csv_record)
    assert all(p.startswith("+") for p in c.phones)


def test_from_csv_experience_mapped(sample_csv_record):
    c = CandidateBuilder.from_csv(sample_csv_record)
    assert len(c.experience) == 1
    exp = c.experience[0]
    assert exp.company == "CodeBind Technologies"
    assert exp.title == "Web Development Intern"


def test_from_csv_provenance_populated(sample_csv_record):
    c = CandidateBuilder.from_csv(sample_csv_record)
    fields = {p.field for p in c.provenance}
    assert "full_name" in fields
    assert "email" in fields


def test_from_linkedin_basic(sample_linkedin_record):
    c = CandidateBuilder.from_linkedin(sample_linkedin_record)
    assert c.full_name == "Yamini M K"
    assert len(c.links) == 1
    assert len(c.skills) > 0


def test_from_linkedin_skills_normalized(sample_linkedin_record):
    c = CandidateBuilder.from_linkedin(sample_linkedin_record)
    skill_names = {sk.name for sk in c.skills}
    assert "Python" in skill_names
    assert "JavaScript" in skill_names


def test_from_linkedin_dates_normalized(sample_linkedin_record):
    c = CandidateBuilder.from_linkedin(sample_linkedin_record)
    for exp in c.experience:
        if exp.start:
            # Should be YYYY-MM format or None
            assert exp.start == "Present" or len(exp.start) in (4, 7, 10)


def test_candidate_id_deterministic(sample_csv_record):
    c1 = CandidateBuilder.from_csv(sample_csv_record)
    c2 = CandidateBuilder.from_csv(sample_csv_record)
    assert c1.candidate_id == c2.candidate_id
    assert c1.candidate_id is not None