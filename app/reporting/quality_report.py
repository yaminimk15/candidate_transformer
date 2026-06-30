"""
Data Quality Reporter

Emits a run-level meta-summary alongside the candidate profile, providing
production-style observability over what happened during a pipeline run.

Report structure:
{
  "sources_attempted": ["csv", "resume", "linkedin"],
  "sources_processed": ["csv", "resume", "linkedin"],
  "sources_failed":    [],
  "fields_missing":    ["phones"],
  "fields_conflicted": ["headline"],
  "overall_confidence": 0.83,
  "skill_count":       12,
  "experience_count":  2,
  "education_count":   1,
  "merge_trace":       { ... },
  "schema_warnings":   []
}
"""

from __future__ import annotations

from app.models.candidate import Candidate


class QualityReporter:
    """
    Generates a run-level data quality report from a merged Candidate
    and pipeline metadata.
    """

    @staticmethod
    def generate(
        candidate: Candidate,
        sources_attempted: list[str],
        sources_failed: list[str],
        schema_warnings: list[str] | None = None,
    ) -> dict:
        """
        Args:
            candidate:          The merged canonical Candidate object.
            sources_attempted:  All source names tried (e.g. ["csv", "resume"]).
            sources_failed:     Sources that failed to extract (graceful failures).
            schema_warnings:    Validation warnings from SchemaValidator.

        Returns:
            A plain dict suitable for JSON serialisation.
        """
        sources_processed = [
            s for s in sources_attempted if s not in sources_failed
        ]

        # Fields that are None / empty in the canonical record
        fields_missing: list[str] = []
        if not candidate.full_name:
            fields_missing.append("full_name")
        if not candidate.emails:
            fields_missing.append("emails")
        if not candidate.phones:
            fields_missing.append("phones")
        if not candidate.location:
            fields_missing.append("location")
        if not candidate.headline:
            fields_missing.append("headline")
        if not candidate.skills:
            fields_missing.append("skills")
        if not candidate.experience:
            fields_missing.append("experience")
        if not candidate.education:
            fields_missing.append("education")

        # Fields that had conflicts across sources
        fields_conflicted: list[str] = list({
            p.field for p in candidate.provenance if p.conflict
        })

        return {
            "sources_attempted":  sources_attempted,
            "sources_processed":  sources_processed,
            "sources_failed":     sources_failed,
            "fields_missing":     fields_missing,
            "fields_conflicted":  fields_conflicted,
            "overall_confidence": candidate.overall_confidence,
            "candidate_id":       candidate.candidate_id,
            "skill_count":        len(candidate.skills),
            "experience_count":   len(candidate.experience),
            "education_count":    len(candidate.education),
            "merge_trace":        candidate.merge_trace,
            "schema_warnings":    schema_warnings or [],
        }
