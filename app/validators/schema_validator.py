"""
Schema Validator

Validates the projected output dict against a JSON Schema.
Missing required fields are logged as warnings (not hard errors),
so the pipeline never crashes on missing data — consistent with the
spec's "missing field → null, never invented; logged, not fatal" rule.
"""

import json
import logging
import os
from typing import Optional

import jsonschema
from jsonschema import ValidationError

from app.models.candidate import Candidate

logger = logging.getLogger(__name__)

_DEFAULT_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "output_schema.json"
)


class SchemaValidator:
    """
    Two-stage validation:
      1. Soft checks on the canonical Candidate object (log warnings, don't raise).
      2. JSON Schema validation on the projected output dict (raises on hard errors
         only if configured to do so via missing_value_policy).
    """

    @staticmethod
    def validate(candidate: Candidate) -> Candidate:
        """
        Soft-validate the canonical Candidate. Log warnings for missing
        important fields; adjust confidence if critical fields are absent.
        Never raises.
        """
        if not candidate.full_name:
            logger.warning(
                "Candidate has no full_name. overall_confidence reduced."
            )
            candidate.overall_confidence = max(
                0.0, candidate.overall_confidence - 0.10
            )

        if not candidate.emails:
            logger.warning(
                "Candidate has no email address. overall_confidence reduced."
            )
            candidate.overall_confidence = max(
                0.0, candidate.overall_confidence - 0.10
            )

        if not candidate.phones:
            logger.info("Candidate has no phone number — acceptable.")

        return candidate

    @staticmethod
    def validate_projected(
        projected: dict,
        schema_path: Optional[str] = None,
    ) -> list[str]:
        """
        Validate the projected output dict against the JSON Schema.

        Returns:
            A list of validation error messages (empty = valid).
            Does NOT raise — callers decide what to do with errors.
        """
        path = schema_path or _DEFAULT_SCHEMA_PATH
        if not os.path.isfile(path):
            logger.warning("Output schema not found at '%s'; skipping validation.", path)
            return []

        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        errors: list[str] = []
        validator = jsonschema.Draft7Validator(schema)
        for error in validator.iter_errors(projected):
            msg = f"{' -> '.join(str(p) for p in error.absolute_path)}: {error.message}"
            errors.append(msg)
            logger.warning("Schema validation error: %s", msg)

        return errors