# tests/test_provenance.py

from app.services.candidate_builder import CandidateBuilder

resume_data = {
    "full_name": "YAMINI M K",
    "emails": ["yamini.0954@gmail.com"],
    "phones": ["9342880954"]
}

candidate = CandidateBuilder.from_resume(resume_data)

print(candidate.model_dump())