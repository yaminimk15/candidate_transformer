"""
Shared pytest fixtures for the Candidate Data Transformer test suite.
"""
import pytest
from app.models.candidate import Candidate, Provenance, Skill, Education, Experience, Location


@pytest.fixture
def sample_candidate():
    return Candidate(
        full_name="Yamini M K",
        emails=["yamini.0954@gmail.com"],
        phones=["+919342880954"],
        location=Location(city="Coimbatore", region="Tamil Nadu", country="India"),
        headline="Web Development Intern",
        skills=[
            Skill(name="Python",     confidence=0.75, sources=["resume"]),
            Skill(name="Flask",      confidence=0.75, sources=["resume"]),
            Skill(name="JavaScript", confidence=0.75, sources=["resume"]),
        ],
        experience=[
            Experience(
                company="CodeBind Technologies",
                title="Web Development Intern",
                start="2024-01",
                end="2024-06",
            )
        ],
        education=[
            Education(
                institution="Rathinam Technical Campus",
                degree="B.E.",
                field="Computer Science and Engineering",
            )
        ],
        provenance=[
            Provenance(field="email",     value="yamini.0954@gmail.com", source="csv",    method="column_mapping",   confidence=0.90),
            Provenance(field="email",     value="yamini.0954@gmail.com", source="resume", method="regex",            confidence=0.7125),
            Provenance(field="full_name", value="Yamini M K",             source="csv",    method="column_mapping",   confidence=0.90),
            Provenance(field="phone",     value="+919342880954",           source="resume", method="regex",            confidence=0.7125),
        ],
    )


@pytest.fixture
def sample_csv_record():
    return {
        "name":            "Yamini M K",
        "email":           "yamini.0954@gmail.com",
        "phone":           "9342880954",
        "current_company": "CodeBind Technologies",
        "title":           "Web Development Intern",
    }


@pytest.fixture
def sample_linkedin_record():
    return {
        "full_name": "Yamini M K",
        "headline":  "Web Development Intern | Python | React | Flask",
        "emails":    ["yamini.0954@gmail.com"],
        "phones":    [],
        "location":  {"city": "Coimbatore", "region": "Tamil Nadu", "country": "India"},
        "links":     ["https://linkedin.com/in/yamini-mk"],
        "skills":    ["Python", "Flask", "React", "JavaScript", "HTML", "CSS", "MySQL"],
        "experience": [
            {
                "company":    "CodeBind Technologies",
                "title":      "Web Development Intern",
                "start_date": "Jan 2024",
                "end_date":   "Jun 2024",
                "summary":    "Built full-stack web apps.",
            }
        ],
        "education": [
            {
                "institution": "Rathinam Technical Campus",
                "degree":      "B.E.",
                "field":       "Computer Science and Engineering",
                "start_date":  "2021",
                "end_date":    "2025",
            }
        ],
    }
