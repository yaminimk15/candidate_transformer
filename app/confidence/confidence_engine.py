"""
Confidence Engine

Computes overall_confidence as a weighted blend of three factors:

  field_score = source_trust × method_reliability × agreement_factor

  overall_confidence = weighted_mean(field_scores, weights=FIELD_IMPORTANCE)

Where:
  source_trust       — how trustworthy the originating source is
  method_reliability — how reliable the extraction method is
  agreement_factor   — bonus if ≥2 sources agree, penalty if they conflict
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.models.candidate import Candidate, Provenance

logger = logging.getLogger(__name__)


# ── Source trust ─────────────────────────────────────────────────────────────
SOURCE_TRUST: dict[str, float] = {
    "ats":      1.00,
    "csv":      0.90,
    "linkedin": 0.85,
    "resume":   0.75,
    "notes":    0.50,
}

# ── Extraction-method reliability ────────────────────────────────────────────
METHOD_RELIABILITY: dict[str, float] = {
    "column_mapping":     1.00,
    "linkedin_field":     0.90,
    "regex":              0.95,
    "education_section":  0.85,
    "experience_section": 0.85,
    "location_regex":     0.80,
    "first_line":         0.70,
    "keyword_match":      0.75,
    "fuzzy":              0.60,
}

# ── Field importance weights for the overall score ───────────────────────────
FIELD_IMPORTANCE: dict[str, float] = {
    "email":      1.00,
    "full_name":  0.90,
    "phone":      0.85,
    "experience": 0.80,
    "education":  0.75,
    "skill":      0.70,
    "location":   0.65,
    "headline":   0.50,
    "link":       0.40,
}

# Cross-source agreement bonus / conflict penalty
AGREEMENT_BONUS   = 1.15   # capped at 1.0
CONFLICT_PENALTY  = 0.80


class ConfidenceEngine:
    """
    Calculates and attaches overall_confidence to a Candidate object.
    Uses weighted field-level scores derived from source trust,
    method reliability, and cross-source agreement.
    """

    @staticmethod
    def calculate(candidate: Candidate) -> Candidate:
        if not candidate.provenance:
            candidate.overall_confidence = 0.0
            return candidate

        # Group provenance entries by field name
        by_field: dict[str, list[Provenance]] = defaultdict(list)
        for p in candidate.provenance:
            by_field[p.field].append(p)

        weighted_sum = 0.0
        total_weight = 0.0

        for field, provs in by_field.items():
            weight = FIELD_IMPORTANCE.get(field, 0.50)

            # Compute base score per provenance entry
            scores = []
            for p in provs:
                trust       = SOURCE_TRUST.get(p.source, 0.70)
                reliability = METHOD_RELIABILITY.get(p.method, 0.70)
                base        = trust * reliability
                scores.append(base)

            avg_base = sum(scores) / len(scores)

            # Agreement / conflict factor
            sources        = {p.source for p in provs}
            unique_vals    = {str(p.value or "").strip().lower() for p in provs}
            n_sources      = len(sources)
            n_unique_vals  = len(unique_vals)

            if n_sources >= 2 and n_unique_vals == 1:
                # All sources agree — boost
                factor = AGREEMENT_BONUS
            elif n_sources >= 2 and n_unique_vals > 1:
                # Sources conflict — penalize
                factor = CONFLICT_PENALTY
                logger.debug(
                    "Conflict on field '%s': values %s from sources %s",
                    field, unique_vals, sources,
                )
            else:
                factor = 1.0

            field_score = min(1.0, avg_base * factor)

            weighted_sum  += field_score * weight
            total_weight  += weight

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0
        candidate.overall_confidence = round(overall, 4)
        return candidate