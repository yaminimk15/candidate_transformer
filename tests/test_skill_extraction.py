import pytest
from app.normalizers.skill_normalizer import SkillNormalizer


@pytest.mark.parametrize("raw, expected", [
    ("python",       "Python"),
    ("Python",       "Python"),
    ("JS",           "JavaScript"),
    ("javascript",   "JavaScript"),
    ("node",         "Node.js"),
    ("node.js",      "Node.js"),
    ("ML",           "Machine Learning"),
    ("aws",          "AWS"),
    ("PostgreSQL",   "PostgreSQL"),
    ("postgres",     "PostgreSQL"),
    ("k8s",          "Kubernetes"),
    ("react.js",     "React"),
    ("TF",           "TensorFlow"),
])
def test_skill_normalizer_exact_aliases(raw, expected):
    assert SkillNormalizer.normalize(raw) == expected


def test_skill_normalizer_empty():
    assert SkillNormalizer.normalize("") == ""
    assert SkillNormalizer.normalize(None) == ""


def test_skill_normalizer_deduplication():
    raw = ["Python", "python", "py", "Flask", "flask"]
    result = SkillNormalizer.normalize_list(raw)
    # All Python aliases should collapse to one "Python"
    assert result.count("Python") == 1
    assert result.count("Flask") == 1
    assert len(result) == 2


def test_skill_normalizer_fuzzy_fallback():
    """Slightly misspelled skills should still match via fuzzy."""
    result = SkillNormalizer.normalize("Pythn")
    assert result == "Python"