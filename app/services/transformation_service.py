"""
Transformation Service

Orchestrates the full pipeline:
  detect → extract → normalize → dedupe/merge → confidence & provenance
  → project (config) → validate → emit

Each source is wrapped in a try/except so a corrupt or missing file
causes that source to be skipped gracefully (logged, confidence reduced)
rather than crashing the entire run.

Per-source extraction results are cached by file path + mtime so re-runs
over the same inputs are fast and deterministic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Optional

from app.extractors.csv_extractor import CSVExtractor
from app.extractors.resume_extractor import ResumeExtractor
from app.extractors.resume_parser import ResumeParser
from app.extractors.linkedin_extractor import LinkedInExtractor

from app.services.candidate_builder import CandidateBuilder

from app.merger.merge_engine import MergeEngine, DEFAULT_MERGE_CONFIG

from app.confidence.confidence_engine import ConfidenceEngine

from app.projection.projection_engine import ProjectionEngine

from app.validators.schema_validator import SchemaValidator

from app.reporting.quality_report import QualityReporter

logger = logging.getLogger(__name__)

# Simple file-based cache directory
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "output", ".cache")


def _cache_key(file_path: str) -> str:
    """Stable cache key = SHA256 of (absolute path + file mtime + file size)."""
    abs_path = os.path.abspath(file_path)
    try:
        stat = os.stat(abs_path)
        raw = f"{abs_path}:{stat.st_mtime}:{stat.st_size}"
    except OSError:
        raw = abs_path
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_load(key: str):
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(_CACHE_DIR, f"{key}.json")
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _cache_save(key: str, data) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(_CACHE_DIR, f"{key}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Could not write cache: %s", exc)


class TransformationService:

    def transform(
        self,
        csv_path: str,
        resume_path: str,
        config_path: str,
        linkedin_path: Optional[str] = None,
        merge_config_path: Optional[str] = None,
        schema_path: Optional[str] = None,
    ) -> dict:
        """
        Run the full pipeline and return a result dict with three keys:
          canonical_profile  — the merged Candidate as a dict
          projected_output   — the config-driven projected output dict
          data_quality_report — run-level observability summary

        Args:
            csv_path:           Path to the recruiter CSV file.
            resume_path:        Path to the candidate resume PDF.
            config_path:        Path to the projection config JSON.
            linkedin_path:      Optional path to the LinkedIn stub JSON.
            merge_config_path:  Optional path to the merge strategy config JSON.
            schema_path:        Optional path to the output JSON Schema.
        """
        sources_attempted: list[str] = []
        sources_failed: list[str] = []
        candidates = []

        # ── Step 1: Load merge config ─────────────────────────────────────────
        merge_config = DEFAULT_MERGE_CONFIG
        if merge_config_path and os.path.isfile(merge_config_path):
            try:
                with open(merge_config_path, "r", encoding="utf-8") as f:
                    merge_config = json.load(f)
            except Exception as exc:
                logger.warning("Could not load merge config: %s — using defaults.", exc)

        # ── Step 2: Extract CSV (only if a real path was provided) ──────────────
        if csv_path and os.path.isfile(csv_path):
            sources_attempted.append("csv")
            try:
                ckey = _cache_key(csv_path)
                cached = _cache_load(ckey)
                if cached:
                    logger.info("CSV: loaded from cache.")
                    csv_records = cached
                else:
                    csv_records = CSVExtractor().extract(csv_path)
                    _cache_save(ckey, csv_records)

                for record in csv_records:
                    candidates.append(CandidateBuilder.from_csv(record))

            except Exception as exc:
                logger.error("CSV extraction failed: %s", exc)
                sources_failed.append("csv")
        else:
            logger.info("CSV path not provided — skipping CSV source.")

        # ── Step 3: Extract Resume (only if a real path was provided) ───────────
        if resume_path and os.path.isfile(resume_path):
            sources_attempted.append("resume")
            try:
                ckey = _cache_key(resume_path)
                cached = _cache_load(ckey)
                if cached:
                    logger.info("Resume: loaded from cache.")
                    parsed_resume = cached
                else:
                    resume_text = ResumeExtractor().extract(resume_path)
                    parsed_resume = ResumeParser().parse(resume_text)
                    _cache_save(ckey, parsed_resume)

                candidates.append(CandidateBuilder.from_resume(parsed_resume))

            except Exception as exc:
                logger.error("Resume extraction failed: %s", exc)
                sources_failed.append("resume")
        else:
            logger.info("Resume path not provided — skipping resume source.")

        # ── Step 4: Extract LinkedIn (optional) ───────────────────────────────
        if linkedin_path:
            sources_attempted.append("linkedin")
            try:
                ckey = _cache_key(linkedin_path)
                cached = _cache_load(ckey)
                if cached:
                    logger.info("LinkedIn: loaded from cache.")
                    linkedin_data = cached
                else:
                    linkedin_data = LinkedInExtractor().extract(linkedin_path)
                    _cache_save(ckey, linkedin_data)

                candidates.append(CandidateBuilder.from_linkedin(linkedin_data))

            except Exception as exc:
                logger.error("LinkedIn extraction failed: %s", exc)
                sources_failed.append("linkedin")

        if not candidates:
            raise RuntimeError(
                "All sources failed to extract. Cannot produce a candidate profile."
            )

        # ── Step 5: Merge ─────────────────────────────────────────────────────
        engine = MergeEngine(merge_config=merge_config)
        merged_candidate = engine.merge(candidates)

        # ── Step 6: Confidence ────────────────────────────────────────────────
        merged_candidate = ConfidenceEngine.calculate(merged_candidate)

        # ── Step 7: Soft validation ───────────────────────────────────────────
        merged_candidate = SchemaValidator.validate(merged_candidate)

        # ── Step 8: Projection ────────────────────────────────────────────────
        with open(config_path, "r", encoding="utf-8") as f:
            proj_config = json.load(f)

        projected = ProjectionEngine.project(merged_candidate, proj_config)

        # ── Step 9: JSON Schema validation of projected output ────────────────
        schema_warnings = SchemaValidator.validate_projected(
            projected, schema_path=schema_path
        )

        # ── Step 10: Data Quality Report ──────────────────────────────────────
        quality_report = QualityReporter.generate(
            candidate=merged_candidate,
            sources_attempted=sources_attempted,
            sources_failed=sources_failed,
            schema_warnings=schema_warnings,
        )

        return {
            "canonical_profile":   merged_candidate.model_dump(),
            "projected_output":    projected,
            "data_quality_report": quality_report,
        }