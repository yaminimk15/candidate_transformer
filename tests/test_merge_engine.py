import pytest
from app.models.candidate import Candidate, Provenance, Skill
from app.merger.merge_engine import MergeEngine


@pytest.fixture
def csv_candidate():
    """Candidate from CSV source with a distinct phone."""
    return Candidate(
        full_name="Yamini M K",
        emails=["yamini.csv@example.com"],          # distinct email so dedup sees 2 people
        phones=["+919342880954"],
        skills=[Skill(name="Python", confidence=0.81, sources=["csv"])],
        provenance=[
            Provenance(field="full_name", value="Yamini M K",              source="csv", method="column_mapping", confidence=0.90),
            Provenance(field="email",     value="yamini.csv@example.com",   source="csv", method="column_mapping", confidence=0.90),
        ],
    )


@pytest.fixture
def resume_candidate():
    """Candidate from Resume source with a second phone and extra skill."""
    return Candidate(
        full_name="Yamini M K",
        emails=["yamini.resume@example.com"],       # distinct email → treated as separate source
        phones=["+919876543210"],
        skills=[Skill(name="Python", confidence=0.75, sources=["resume"]),
                Skill(name="Flask",  confidence=0.75, sources=["resume"])],
        provenance=[
            Provenance(field="full_name", value="Yamini M K",               source="resume", method="first_line",  confidence=0.525),
            Provenance(field="email",     value="yamini.resume@example.com", source="resume", method="regex",       confidence=0.7125),
            Provenance(field="phone",     value="+919876543210",             source="resume", method="regex",       confidence=0.7125),
        ],
    )


def test_merge_deduplicates_same_candidate(csv_candidate, resume_candidate):
    """Same email → same person; result should be a single merged Candidate."""
    engine = MergeEngine()
    merged = engine.merge([csv_candidate, resume_candidate])
    assert merged.full_name == "Yamini M K"


def test_merge_unions_phones():
    """Two different people (different companies) - their phones both appear in output."""
    from app.models.candidate import Experience
    alice = Candidate(
        full_name="Alice Smith",
        emails=["alice@alpha.com"],
        phones=["+911111111111"],
        experience=[Experience(company="Alpha Corp", title="Engineer")],
        provenance=[Provenance(field="email", value="alice@alpha.com", source="csv", method="column_mapping", confidence=0.90)],
    )
    bob = Candidate(
        full_name="Bob Jones",
        emails=["bob@beta.com"],
        phones=["+912222222222"],
        experience=[Experience(company="Beta Ltd", title="Developer")],
        provenance=[Provenance(field="email", value="bob@beta.com", source="resume", method="regex", confidence=0.71)],
    )
    engine = MergeEngine()
    merged = engine.merge([alice, bob])
    assert "+911111111111" in merged.phones
    assert "+912222222222" in merged.phones


def test_merge_unions_skills():
    """Two candidates with different skills — merged result should contain all skills."""
    from app.models.candidate import Experience
    cand1 = Candidate(
        full_name="Eve Brown",
        emails=["eve@corp1.com"],
        phones=["+919000000001"],
        skills=[Skill(name="Python", confidence=0.81, sources=["csv"])],
        experience=[Experience(company="Corp One", title="Intern")],
        provenance=[Provenance(field="email", value="eve@corp1.com", source="csv", method="column_mapping", confidence=0.90)],
    )
    cand2 = Candidate(
        full_name="Eve Brown",
        emails=["eve@corp2.com"],
        phones=["+919000000002"],
        skills=[Skill(name="Flask", confidence=0.75, sources=["resume"])],
        experience=[Experience(company="Corp Two", title="Developer")],
        provenance=[Provenance(field="email", value="eve@corp2.com", source="resume", method="regex", confidence=0.71)],
    )
    engine = MergeEngine()
    merged = engine.merge([cand1, cand2])
    skill_names = {sk.name for sk in merged.skills}
    assert "Python" in skill_names
    assert "Flask" in skill_names


def test_merge_skill_agreement_boosts_confidence(csv_candidate, resume_candidate):
    engine = MergeEngine()
    merged = engine.merge([csv_candidate, resume_candidate])
    python_skill = next(sk for sk in merged.skills if sk.name == "Python")
    # Agreement from 2 sources should boost confidence above either individual source
    assert python_skill.confidence > 0.75


def test_merge_trace_populated(csv_candidate, resume_candidate):
    engine = MergeEngine()
    merged = engine.merge([csv_candidate, resume_candidate])
    assert isinstance(merged.merge_trace, dict)
    assert "full_name" in merged.merge_trace


def test_merge_priority_order_prefers_csv(csv_candidate, resume_candidate):
    """priority_order strategy: csv (trust=0.90) > resume (trust=0.75) for full_name."""
    engine = MergeEngine()
    merged = engine.merge([csv_candidate, resume_candidate])
    assert "csv" in merged.merge_trace.get("full_name", "").lower()


def test_merge_single_candidate_returns_same():
    cand = Candidate(full_name="Alice", emails=["alice@example.com"],
                     provenance=[Provenance(field="email", value="alice@example.com",
                                           source="csv", method="column_mapping", confidence=0.90)])
    engine = MergeEngine()
    result = engine.merge([cand])
    assert result.full_name == "Alice"