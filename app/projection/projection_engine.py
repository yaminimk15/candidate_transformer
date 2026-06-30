"""
Projection Engine

Transforms the internal canonical Candidate record into a caller-defined
output shape, driven entirely by config. Zero code changes are needed
when the output schema or field mapping changes.

Config format:
{
  "fields": [
    {"path": "candidate_name", "from": "full_name"},
    {"path": "primary_email",  "from": "emails[0]"},
    {"path": "city",           "from": "location.city"},
    {"path": "top_skill",      "from": "skills[0].name"}
  ],
  "include_provenance": false,
  "include_confidence": true,
  "missing_value_policy": "null",      // "null" | "omit" | "error"
  "normalizations": {
    "primary_email": "lowercase",      // "lowercase" | "uppercase" | "strip"
    "candidate_name": "strip"
  }
}
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProjectionEngine:
    """
    Projects a canonical Candidate dict into a caller-defined output dict.
    """

    @staticmethod
    def project(candidate_obj, config: dict) -> dict:
        """
        Args:
            candidate_obj: A Candidate pydantic model instance.
            config:        Projection config dict (see module docstring).

        Returns:
            A plain dict with the projected fields.

        Raises:
            ValueError: if missing_value_policy is "error" and a field is None.
        """
        data = candidate_obj.model_dump()
        policy = config.get("missing_value_policy", "null")
        normalizations = config.get("normalizations", {})
        output: dict[str, Any] = {}

        for field_spec in config.get("fields", []):
            target_path = field_spec["path"]
            source_expr = field_spec["from"]

            value = ProjectionEngine._resolve_source(data, source_expr)

            # Apply missing-value policy
            if value is None:
                if policy == "omit":
                    continue
                elif policy == "error":
                    raise ValueError(
                        f"Projection field '{target_path}' (from '{source_expr}') "
                        "is None but missing_value_policy is 'error'."
                    )
                else:  # "null"
                    output[target_path] = None
                    continue

            # Apply per-field normalization override
            norm = normalizations.get(target_path)
            if norm and isinstance(value, str):
                if norm == "lowercase":
                    value = value.lower()
                elif norm == "uppercase":
                    value = value.upper()
                elif norm == "strip":
                    value = value.strip()

            output[target_path] = value

        # Optional toggles
        if config.get("include_confidence", False):
            output["overall_confidence"] = data.get("overall_confidence", 0.0)

        if config.get("include_provenance", False):
            output["provenance"] = data.get("provenance", [])

        if config.get("include_merge_trace", False):
            output["merge_trace"] = data.get("merge_trace", {})

        return output

    @staticmethod
    def _resolve_source(data: dict, expr: str) -> Any:
        """
        Resolve a source expression against the canonical dict.

        Supported expressions:
          "full_name"              — top-level key
          "emails[0]"             — first element of a list
          "location.city"         — nested dict key
          "skills[0].name"        — first element of a list, then nested key
          "experience[0].company" — etc.
        """
        # Handle list index: "emails[0]" or "skills[0].name"
        import re
        index_match = re.match(r"^(\w+)\[(\d+)\](?:\.(.+))?$", expr)
        if index_match:
            key       = index_match.group(1)
            idx       = int(index_match.group(2))
            sub_key   = index_match.group(3)
            lst       = data.get(key, [])
            if not lst or idx >= len(lst):
                return None
            item = lst[idx]
            if sub_key:
                return ProjectionEngine._deep_get(item, sub_key)
            return item

        # Handle nested key: "location.city"
        if "." in expr:
            return ProjectionEngine._deep_get(data, expr)

        # Simple top-level key
        return data.get(expr)

    @staticmethod
    def _deep_get(obj: Any, path: str) -> Any:
        """Traverse a dot-separated path through nested dicts."""
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            if current is None:
                return None
        return current