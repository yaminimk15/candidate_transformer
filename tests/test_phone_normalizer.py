import pytest
from app.normalizers.phone_normalizer import PhoneNormalizer


@pytest.mark.parametrize("raw, expected", [
    ("9342880954",   "+919342880954"),
    ("+919342880954","+919342880954"),
    ("09342880954",  "+919342880954"),
    ("not_a_phone",  None),
    ("",             None),
])
def test_phone_normalizer(raw, expected):
    assert PhoneNormalizer.normalize(raw) == expected


def test_phone_normalizer_never_raises():
    """Must return None for any unparseable input, never raise."""
    assert PhoneNormalizer.normalize("!!!!!!") is None
    assert PhoneNormalizer.normalize(None) is None