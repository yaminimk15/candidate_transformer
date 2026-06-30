import pytest
from app.normalizers.date_normalizer import DateNormalizer


@pytest.mark.parametrize("raw, expected", [
    ("Jan 2021",       "2021-01"),
    ("January 2021",   "2021-01"),
    ("Jun 2022",       "2022-06"),
    ("2021",           "2021"),
    ("06/2021",        "2021-06"),
    ("Present",        "Present"),
    ("present",        "Present"),
    ("current",        "Present"),
    ("till date",      "Present"),
    (None,             None),
    ("",               None),
    ("not a date",     None),
])
def test_date_normalizer(raw, expected):
    assert DateNormalizer.normalize(raw) == expected


def test_date_normalizer_never_raises():
    """DateNormalizer must always return None instead of raising."""
    assert DateNormalizer.normalize("!!!") is None
    assert DateNormalizer.normalize("99/9999") is None
