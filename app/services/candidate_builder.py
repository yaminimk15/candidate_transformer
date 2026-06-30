import uuid
from app.models.candidate import (
    Candidate,
    Provenance,
    Skill,
    Education,
    Experience,
    Location,
)

from app.normalizers.phone_normalizer import PhoneNormalizer
from app.normalizers.date_normalizer import DateNormalizer
from app.normalizers.skill_normalizer import SkillNormalizer


def _make_candidate_id(emails: list[str]) -> str | None:
    """Deterministic UUID5 from the lowest-alphabetical email."""
    if not emails:
        return None
    seed = sorted(e.lower().strip() for e in emails)[0]
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"candidate:{seed}"))


class CandidateBuilder:
    """
    Converts raw parsed dicts from any source adapter into canonical
    Candidate objects. Adapters never write directly to the schema —
    all normalization (phones → E.164, dates → YYYY-MM, skills →
    canonical names) happens here.
    """

    # ── Source trust weights (used by ConfidenceEngine) ──────────────────────
    SOURCE_TRUST = {
        "linkedin": 0.85,
        "csv":      0.90,
        "resume":   0.75,
        "notes":    0.50,
    }

    # ── Method reliability weights ────────────────────────────────────────────
    METHOD_RELIABILITY = {
        "column_mapping":   1.00,
        "linkedin_field":   0.90,
        "regex":            0.95,
        "education_section": 0.85,
        "experience_section": 0.85,
        "location_regex":   0.80,
        "first_line":       0.70,
        "keyword_match":    0.75,
        "fuzzy":            0.60,
    }

    @staticmethod
    def _base_confidence(source: str, method: str) -> float:
        trust = CandidateBuilder.SOURCE_TRUST.get(source, 0.70)
        reliability = CandidateBuilder.METHOD_RELIABILITY.get(method, 0.70)
        return round(trust * reliability, 4)

    # ─────────────────────────────────────────────────────────────────────────
    # Resume
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def from_resume(parsed_data: dict) -> Candidate:
        source = "resume"

        # ── Phones → E.164 ────────────────────────────────────────────────────
        normalized_phones = []
        for phone in parsed_data.get("phones", []):
            raw = str(phone).strip()
            normalized = PhoneNormalizer.normalize(raw)
            if normalized:
                normalized_phones.append(normalized)

        # ── Skills → canonical names ──────────────────────────────────────────
        raw_skills = parsed_data.get("skills", [])
        canonical_skills_list = SkillNormalizer.normalize_list(raw_skills)
        candidate_skills = [
            Skill(
                name=skill,
                confidence=CandidateBuilder._base_confidence(source, "keyword_match"),
                sources=[source],
            )
            for skill in canonical_skills_list
        ]

        # ── Education (with date normalization) ───────────────────────────────
        education_objects = []
        for edu in parsed_data.get("education", []):
            education_objects.append(
                Education(
                    institution=edu.get("institution"),
                    degree=edu.get("degree"),
                    field=edu.get("field"),
                    start_date=DateNormalizer.normalize(edu.get("start_date")),
                    end_date=DateNormalizer.normalize(edu.get("end_date")),
                )
            )

        # ── Experience (with date normalization) ──────────────────────────────
        experience_objects = []
        for exp in parsed_data.get("experience", []):
            experience_objects.append(
                Experience(
                    company=exp.get("company"),
                    title=exp.get("title", ""),
                    start=DateNormalizer.normalize(exp.get("start_date")),
                    end=DateNormalizer.normalize(exp.get("end_date")),
                    summary=exp.get("summary"),
                )
            )

        # ── Location ──────────────────────────────────────────────────────────
        loc_data = parsed_data.get("location")
        location = Location(**loc_data) if loc_data else None

        emails = parsed_data.get("emails", [])

        # ── Provenance ────────────────────────────────────────────────────────
        provenance = []

        if parsed_data.get("full_name"):
            provenance.append(Provenance(
                field="full_name", value=parsed_data["full_name"],
                source=source, method="first_line",
                confidence=CandidateBuilder._base_confidence(source, "first_line"),
            ))

        for email in emails:
            provenance.append(Provenance(
                field="email", value=email,
                source=source, method="regex",
                confidence=CandidateBuilder._base_confidence(source, "regex"),
            ))

        for raw_phone, norm_phone in zip(
            parsed_data.get("phones", []), normalized_phones
        ):
            provenance.append(Provenance(
                field="phone", value=norm_phone,
                raw_value=raw_phone if raw_phone != norm_phone else None,
                source=source, method="regex",
                confidence=CandidateBuilder._base_confidence(source, "regex"),
            ))

        if loc_data:
            provenance.append(Provenance(
                field="location",
                value=f"{loc_data.get('city')}, {loc_data.get('region')}",
                source=source, method="location_regex",
                confidence=CandidateBuilder._base_confidence(source, "location_regex"),
            ))

        for skill in canonical_skills_list:
            provenance.append(Provenance(
                field="skill", value=skill,
                source=source, method="keyword_match",
                confidence=CandidateBuilder._base_confidence(source, "keyword_match"),
            ))

        for edu in parsed_data.get("education", []):
            if edu.get("institution"):
                provenance.append(Provenance(
                    field="education", value=edu["institution"],
                    source=source, method="education_section",
                    confidence=CandidateBuilder._base_confidence(source, "education_section"),
                ))

        for exp in parsed_data.get("experience", []):
            if exp.get("company"):
                provenance.append(Provenance(
                    field="experience", value=exp["company"],
                    source=source, method="experience_section",
                    confidence=CandidateBuilder._base_confidence(source, "experience_section"),
                ))

        return Candidate(
            candidate_id=_make_candidate_id(emails),
            full_name=parsed_data.get("full_name"),
            emails=emails,
            phones=normalized_phones,
            location=location,
            headline=parsed_data.get("headline"),
            skills=candidate_skills,
            education=education_objects,
            experience=experience_objects,
            provenance=provenance,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CSV
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def from_csv(record: dict) -> Candidate:
        source = "csv"
        emails = []
        phones = []
        provenance = []
        skills = []
        experience_objects = []

        if record.get("name"):
            provenance.append(Provenance(
                field="full_name", value=str(record["name"]),
                source=source, method="column_mapping",
                confidence=CandidateBuilder._base_confidence(source, "column_mapping"),
            ))

        if record.get("email"):
            email = str(record["email"]).strip().lower()
            emails.append(email)
            provenance.append(Provenance(
                field="email", value=email,
                source=source, method="column_mapping",
                confidence=CandidateBuilder._base_confidence(source, "column_mapping"),
            ))

        if record.get("phone"):
            raw = str(record["phone"]).strip()
            normalized = PhoneNormalizer.normalize(raw)
            if normalized:
                phones.append(normalized)
                provenance.append(Provenance(
                    field="phone", value=normalized,
                    raw_value=raw if raw != normalized else None,
                    source=source, method="column_mapping",
                    confidence=CandidateBuilder._base_confidence(source, "column_mapping"),
                ))

        # CSV may contain title / company columns
        title = record.get("title") or record.get("job_title") or record.get("position")
        company = record.get("current_company") or record.get("company")
        if title or company:
            experience_objects.append(
                Experience(
                    company=str(company) if company else None,
                    title=str(title) if title else "",
                )
            )
            if company:
                provenance.append(Provenance(
                    field="experience", value=str(company),
                    source=source, method="column_mapping",
                    confidence=CandidateBuilder._base_confidence(source, "column_mapping"),
                ))

        # CSV may contain a skills column (comma-separated)
        if record.get("skills"):
            raw_skills = [s.strip() for s in str(record["skills"]).split(",") if s.strip()]
            canonical = SkillNormalizer.normalize_list(raw_skills)
            for sk in canonical:
                skills.append(Skill(
                    name=sk,
                    confidence=CandidateBuilder._base_confidence(source, "column_mapping"),
                    sources=[source],
                ))
                provenance.append(Provenance(
                    field="skill", value=sk,
                    source=source, method="column_mapping",
                    confidence=CandidateBuilder._base_confidence(source, "column_mapping"),
                ))

        return Candidate(
            candidate_id=_make_candidate_id(emails),
            full_name=str(record["name"]) if record.get("name") else None,
            emails=emails,
            phones=phones,
            skills=skills,
            experience=experience_objects,
            provenance=provenance,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # LinkedIn (stub)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def from_linkedin(parsed_data: dict) -> Candidate:
        source = "linkedin"

        phones = []
        for phone in parsed_data.get("phones", []):
            normalized = PhoneNormalizer.normalize(str(phone))
            if normalized:
                phones.append(normalized)

        raw_skills = parsed_data.get("skills", [])
        canonical_skills_list = SkillNormalizer.normalize_list(raw_skills)
        candidate_skills = [
            Skill(
                name=sk,
                confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
                sources=[source],
            )
            for sk in canonical_skills_list
        ]

        education_objects = []
        for edu in parsed_data.get("education", []):
            education_objects.append(Education(
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                field=edu.get("field"),
                start_date=DateNormalizer.normalize(edu.get("start_date")),
                end_date=DateNormalizer.normalize(edu.get("end_date")),
            ))

        experience_objects = []
        for exp in parsed_data.get("experience", []):
            experience_objects.append(Experience(
                company=exp.get("company"),
                title=exp.get("title", ""),
                start=DateNormalizer.normalize(exp.get("start_date")),
                end=DateNormalizer.normalize(exp.get("end_date")),
                summary=exp.get("summary"),
            ))

        loc_data = parsed_data.get("location")
        location = Location(**loc_data) if loc_data else None
        emails = parsed_data.get("emails", [])
        links = parsed_data.get("links", [])

        provenance = []

        if parsed_data.get("full_name"):
            provenance.append(Provenance(
                field="full_name", value=parsed_data["full_name"],
                source=source, method="linkedin_field",
                confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
            ))

        for email in emails:
            provenance.append(Provenance(
                field="email", value=email,
                source=source, method="linkedin_field",
                confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
            ))

        if loc_data:
            provenance.append(Provenance(
                field="location",
                value=f"{loc_data.get('city')}, {loc_data.get('region')}",
                source=source, method="linkedin_field",
                confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
            ))

        for sk in canonical_skills_list:
            provenance.append(Provenance(
                field="skill", value=sk,
                source=source, method="linkedin_field",
                confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
            ))

        for edu in parsed_data.get("education", []):
            if edu.get("institution"):
                provenance.append(Provenance(
                    field="education", value=edu["institution"],
                    source=source, method="linkedin_field",
                    confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
                ))

        for exp in parsed_data.get("experience", []):
            if exp.get("company"):
                provenance.append(Provenance(
                    field="experience", value=exp["company"],
                    source=source, method="linkedin_field",
                    confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
                ))

        for link in links:
            provenance.append(Provenance(
                field="link", value=link,
                source=source, method="linkedin_field",
                confidence=CandidateBuilder._base_confidence(source, "linkedin_field"),
            ))

        return Candidate(
            candidate_id=_make_candidate_id(emails),
            full_name=parsed_data.get("full_name"),
            emails=emails,
            phones=phones,
            location=location,
            headline=parsed_data.get("headline"),
            links=links,
            skills=candidate_skills,
            education=education_objects,
            experience=experience_objects,
            provenance=provenance,
        )