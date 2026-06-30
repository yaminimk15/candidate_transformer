import uuid
from pydantic import BaseModel, model_validator
from typing import List, Optional, Dict


class Location(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class Skill(BaseModel):
    name: str
    confidence: float = 0.75
    sources: List[str] = []


class Experience(BaseModel):
    company: Optional[str] = None
    title: str
    start: Optional[str] = None
    end: Optional[str] = None
    summary: Optional[str] = None


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Provenance(BaseModel):
    field: str
    value: Optional[str] = None
    raw_value: Optional[str] = None   # original un-normalized value kept for audit
    source: str
    method: str
    confidence: float = 0.0
    conflict: bool = False            # True when this field had conflicting values across sources


class Candidate(BaseModel):
    candidate_id: Optional[str] = None

    full_name: Optional[str] = None

    emails: List[str] = []

    phones: List[str] = []

    location: Optional[Location] = None

    headline: Optional[str] = None

    links: List[str] = []

    years_experience: Optional[float] = None

    skills: List[Skill] = []

    experience: List[Experience] = []

    education: List[Education] = []

    provenance: List[Provenance] = []

    overall_confidence: float = 0.0

    # Per-field human-readable merge trace, e.g.:
    # {"full_name": "full_name from csv (1.0) over resume (0.80): higher source trust"}
    merge_trace: Dict[str, str] = {}

    @model_validator(mode="after")
    def assign_candidate_id(self) -> "Candidate":
        """
        Generate a deterministic UUID5 candidate_id seeded on the
        lowest-alphabetical normalized email. This makes the ID stable
        across re-runs so long as the primary email is the same.
        """
        if self.candidate_id:
            return self
        if self.emails:
            seed_email = sorted(e.lower().strip() for e in self.emails)[0]
            self.candidate_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"candidate:{seed_email}")
            )
        return self