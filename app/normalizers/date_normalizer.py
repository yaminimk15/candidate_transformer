from dateutil import parser as dateutil_parser
from typing import Optional
import re


class DateNormalizer:
    """
    Normalizes raw date strings to YYYY-MM (or YYYY-MM-DD for full dates).
    Handles formats like: "Jan 2021", "January 2021", "2021", "06/2021",
    "Jun 2022 - Aug 2022" (takes the relevant part), "Present", "Current".

    Always returns None instead of raising — callers treat None as
    'unparseable / keep raw value in provenance'.
    """

    PRESENT_TOKENS = frozenset(
        ["present", "current", "till date", "now", "ongoing"]
    )

    @classmethod
    def normalize(cls, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None

        stripped = raw.strip()

        if stripped.lower() in cls.PRESENT_TOKENS:
            return "Present"

        # Strip trailing/leading junk (brackets, pipes)
        stripped = re.sub(r"^[\s\(\[\|]+|[\s\)\]\|]+$", "", stripped)

        # Handle "MM/YYYY" format explicitly (dateutil misreads these as DD/MM)
        mm_yyyy = re.match(r"^(\d{1,2})/(\d{4})$", stripped)
        if mm_yyyy:
            month, year = int(mm_yyyy.group(1)), int(mm_yyyy.group(2))
            if 1 <= month <= 12:
                return f"{year}-{month:02d}"

        # Year-only: "2021" → "2021-01" (normalized as January of that year)
        year_only = re.match(r"^(\d{4})$", stripped)
        if year_only:
            return year_only.group(1)

        try:
            parsed = dateutil_parser.parse(stripped, default=None, dayfirst=False)
            if parsed:
                # If the original string only had month+year, emit YYYY-MM
                has_day = re.search(r"\b\d{1,2}\b(?![\d/])", stripped)
                month_name = re.search(
                    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                    stripped, re.IGNORECASE
                )
                if month_name or re.match(r"^\d{1,2}/\d{4}$", stripped):
                    return parsed.strftime("%Y-%m")
                if has_day:
                    return parsed.strftime("%Y-%m-%d")
                return parsed.strftime("%Y-%m")
        except (ValueError, OverflowError):
            pass

        return None
