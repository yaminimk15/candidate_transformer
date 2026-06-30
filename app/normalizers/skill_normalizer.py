from typing import Optional
from rapidfuzz import process as fuzz_process, fuzz

from app.constants.skill_mapping import CANONICAL_SKILLS

# Pre-built set of unique canonical values for fuzzy fallback
_CANONICAL_VALUES: list[str] = list(dict.fromkeys(CANONICAL_SKILLS.values()))

# Fuzzy match score threshold (0–100). Values below this are discarded.
FUZZY_THRESHOLD = 80


class SkillNormalizer:
    """
    Normalizes raw skill strings to their canonical display names.

    Strategy:
      1. Exact lowercase dict lookup (fastest path).
      2. rapidfuzz fuzzy match against canonical values at threshold ≥ FUZZY_THRESHOLD.
      3. If no match, return the original string title-cased as a best-effort.

    Example:
      "JS"        → "JavaScript"
      "node.js"   → "Node.js"
      "ML"        → "Machine Learning"
      "Pythn"     → "Python"   (fuzzy)
      "Yoga"      → "Yoga"     (no match, pass-through)
    """

    @classmethod
    def normalize(cls, raw: Optional[str]) -> str:
        if not raw:
            return ""

        cleaned = raw.strip()
        key = cleaned.lower()

        # 1. Exact alias match
        if key in CANONICAL_SKILLS:
            return CANONICAL_SKILLS[key]

        # 2. Fuzzy match against canonical display values
        result = fuzz_process.extractOne(
            cleaned,
            _CANONICAL_VALUES,
            scorer=fuzz.WRatio,
            score_cutoff=FUZZY_THRESHOLD,
        )
        if result:
            return result[0]

        # 3. Pass-through (title-case for consistency)
        return cleaned.title()

    @classmethod
    def normalize_list(cls, raw_skills: list[str]) -> list[str]:
        """Normalize a list of skills, deduplicating canonicalized names."""
        seen: set[str] = set()
        result: list[str] = []
        for raw in raw_skills:
            canonical = cls.normalize(raw)
            if canonical and canonical not in seen:
                seen.add(canonical)
                result.append(canonical)
        return result
