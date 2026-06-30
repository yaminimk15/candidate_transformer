"""
Merge Engine — pluggable per-field conflict-resolution strategies.

Strategies (selectable per-field in merge_config.json):
  priority_order     — highest source-trust wins (CSV > LinkedIn > resume > notes)
  majority_vote      — value agreed by 2+ sources wins; ties fall back to priority_order
  latest_wins        — value from the most recent experience/date entry wins
  highest_confidence — value with the highest provenance.confidence score wins

Fuzzy dedup:
  Candidates are first collapsed into groups representing the same real person.
  Match key (in order of precedence):
    1. Exact normalized email match
    2. Exact E.164 phone match
    3. rapidfuzz token_sort_ratio(name1, name2) >= threshold AND same company
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Optional

from rapidfuzz import fuzz

from app.models.candidate import Candidate, Provenance, Skill, Education, Experience, Location

logger = logging.getLogger(__name__)


# Source-trust ordering (higher = more trusted)
SOURCE_TRUST: dict[str, float] = {
    "ats":      1.00,
    "csv":      0.90,
    "linkedin": 0.85,
    "resume":   0.75,
    "notes":    0.50,
}

# Method-reliability multipliers
METHOD_RELIABILITY: dict[str, float] = {
    "column_mapping":    1.00,
    "linkedin_field":    0.90,
    "regex":             0.95,
    "education_section": 0.85,
    "experience_section":0.85,
    "location_regex":    0.80,
    "first_line":        0.70,
    "keyword_match":     0.75,
    "fuzzy":             0.60,
}

DEFAULT_MERGE_CONFIG: dict = {
    "field_strategies": {
        "full_name":  "priority_order",
        "emails":     "priority_order",
        "phones":     "priority_order",
        "location":   "priority_order",
        "headline":   "highest_confidence",
        "links":      "priority_order",
        "skills":     "majority_vote",
        "experience": "priority_order",
        "education":  "priority_order",
    },
    "dedup_threshold": 85,
    "default_strategy": "priority_order",
}


def _effective_confidence(prov: Provenance) -> float:
    trust = SOURCE_TRUST.get(prov.source, 0.70)
    reliability = METHOD_RELIABILITY.get(prov.method, 0.70)
    base = prov.confidence if prov.confidence > 0 else trust * reliability
    return round(base, 4)


class MergeEngine:
    """
    Merges a list of Candidate objects (from different sources) into a
    single canonical Candidate record.
    """

    def __init__(self, merge_config: Optional[dict] = None):
        self.config = merge_config or DEFAULT_MERGE_CONFIG

    # ─────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────────────

    def merge(self, candidates: list[Candidate]) -> Candidate:
        if not candidates:
            raise ValueError("Cannot merge an empty candidate list.")
        if len(candidates) == 1:
            return candidates[0]

        # Collapse fuzzy duplicates into groups
        groups = self._deduplicate(candidates)
        # Flatten group into a single ordered list (highest-trust sources first)
        ordered = sorted(
            groups,
            key=lambda c: SOURCE_TRUST.get(
                (c.provenance[0].source if c.provenance else "notes"), 0
            ),
            reverse=True,
        )

        strategies = self.config.get("field_strategies", {})
        default = self.config.get("default_strategy", "priority_order")

        trace: dict[str, str] = {}

        # ── Scalar fields ─────────────────────────────────────────────────────
        full_name, t = self._resolve_scalar(
            "full_name", ordered,
            [c.full_name for c in ordered],
            strategies.get("full_name", default),
        )
        trace["full_name"] = t

        headline, t = self._resolve_scalar(
            "headline", ordered,
            [c.headline for c in ordered],
            strategies.get("headline", default),
        )
        trace["headline"] = t

        # ── Location ──────────────────────────────────────────────────────────
        location, t = self._resolve_location(ordered, strategies.get("location", default))
        trace["location"] = t

        # ── List fields (union with dedup) ────────────────────────────────────
        emails = self._union_list([c.emails for c in ordered], key=lambda x: x.lower())
        phones = self._union_list([c.phones for c in ordered], key=lambda x: x)
        links  = self._union_list([c.links  for c in ordered], key=lambda x: x.lower())

        # ── Skills — merge with strategy ──────────────────────────────────────
        skills, t = self._resolve_skills(ordered, strategies.get("skills", default))
        trace["skills"] = t

        # ── Experience & Education — union ────────────────────────────────────
        experience = self._union_experience(ordered)
        education  = self._union_education(ordered)

        # ── Provenance — combine + annotate conflicts ─────────────────────────
        provenance = self._merge_provenance(ordered)

        return Candidate(
            candidate_id=(ordered[0].candidate_id if ordered[0].candidate_id
                          else None),
            full_name=full_name,
            emails=emails,
            phones=phones,
            location=location,
            headline=headline,
            links=links,
            skills=skills,
            experience=experience,
            education=education,
            provenance=provenance,
            merge_trace=trace,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Fuzzy deduplication
    # ─────────────────────────────────────────────────────────────────────────

    def _deduplicate(self, candidates: list[Candidate]) -> list[Candidate]:
        """
        Collapse candidates that represent the same person into a single group,
        then return the group (merging within each group recursively if needed).
        For now this pipeline typically has one candidate per source, so the
        function just confirms they are the same person or returns them as-is.
        """
        threshold = self.config.get("dedup_threshold", 85)
        groups: list[list[Candidate]] = []

        for cand in candidates:
            placed = False
            for group in groups:
                rep = group[0]
                if self._same_person(cand, rep, threshold):
                    group.append(cand)
                    placed = True
                    break
            if not placed:
                groups.append([cand])

        # Flatten: within each group every candidate represents the same real
        # person from a different source, so we want to keep them ALL and let
        # the main merge logic combine them. There is no recursion here because
        # the outer merge() already handles a list of Candidate objects.
        # We simply return the group members as-is, preserving multi-source data.
        merged: list[Candidate] = []
        for group in groups:
            merged.extend(group)
        return merged

    @staticmethod
    def _same_person(a: Candidate, b: Candidate, threshold: int) -> bool:
        # 1. Email exact match
        a_emails = {e.lower() for e in a.emails}
        b_emails = {e.lower() for e in b.emails}
        if a_emails & b_emails:
            return True

        # 2. Phone exact match
        if set(a.phones) & set(b.phones):
            return True

        # 3. Fuzzy name + same company
        if a.full_name and b.full_name:
            name_score = fuzz.token_sort_ratio(a.full_name, b.full_name)
            if name_score >= threshold:
                a_companies = {
                    e.company.lower() for e in a.experience if e.company
                }
                b_companies = {
                    e.company.lower() for e in b.experience if e.company
                }
                if a_companies & b_companies:
                    return True
                # If neither has a company, name similarity alone is enough
                if not a_companies and not b_companies and name_score >= 95:
                    return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy dispatchers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_scalar(
        self,
        field_name: str,
        candidates: list[Candidate],
        values: list[Any],
        strategy: str,
    ) -> tuple[Any, str]:
        """Resolve a single scalar field using the chosen strategy."""

        # Pair each value with its candidate for provenance lookup
        pairs = [
            (val, cand)
            for val, cand in zip(values, candidates)
            if val is not None
        ]

        if not pairs:
            return None, f"{field_name}: no value found in any source — null."

        if strategy == "priority_order":
            return self._priority_order(field_name, pairs)
        elif strategy == "majority_vote":
            return self._majority_vote(field_name, pairs)
        elif strategy == "latest_wins":
            return self._latest_wins(field_name, pairs)
        elif strategy == "highest_confidence":
            return self._highest_confidence(field_name, pairs)
        else:
            logger.warning("Unknown strategy '%s' for field '%s'; using priority_order", strategy, field_name)
            return self._priority_order(field_name, pairs)

    def _resolve_location(
        self, candidates: list[Candidate], strategy: str
    ) -> tuple[Optional[Location], str]:
        pairs = [
            (c.location, c)
            for c in candidates
            if c.location is not None
        ]
        if not pairs:
            return None, "location: no value found — null."
        val, reason = self._priority_order("location", pairs)
        return val, reason

    def _resolve_skills(
        self, candidates: list[Candidate], strategy: str
    ) -> tuple[list[Skill], str]:
        """
        For skills (a list field), gather all unique skill names and determine
        per-skill confidence from source agreement.
        """
        skill_sources: dict[str, list[tuple[float, str]]] = defaultdict(list)

        for cand in candidates:
            src = cand.provenance[0].source if cand.provenance else "notes"
            trust = SOURCE_TRUST.get(src, 0.70)
            for sk in cand.skills:
                skill_sources[sk.name].append((sk.confidence or trust, src))

        merged_skills: list[Skill] = []
        for name, source_list in skill_sources.items():
            sources = [s for _, s in source_list]
            confidences = [c for c, _ in source_list]
            # Agreement bonus
            if len(set(sources)) >= 2:
                avg_conf = min(1.0, sum(confidences) / len(confidences) * 1.15)
                agreed = True
            else:
                avg_conf = confidences[0]
                agreed = False

            merged_skills.append(Skill(
                name=name,
                confidence=round(avg_conf, 4),
                sources=list(set(sources)),
            ))

        n_agreed = sum(1 for sk in merged_skills if len(sk.sources) >= 2)
        return merged_skills, (
            f"skills: {len(merged_skills)} skills merged from "
            f"{len(candidates)} sources; {n_agreed} confirmed by 2+ sources."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Individual strategy implementations
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _priority_order(
        field_name: str, pairs: list[tuple[Any, Candidate]]
    ) -> tuple[Any, str]:
        """Highest source-trust wins."""
        best_val, best_cand = max(
            pairs,
            key=lambda p: SOURCE_TRUST.get(
                p[1].provenance[0].source if p[1].provenance else "notes", 0
            ),
        )
        src = best_cand.provenance[0].source if best_cand.provenance else "notes"
        trust = SOURCE_TRUST.get(src, 0.70)
        reason = (
            f"{field_name} from {src} ({trust:.2f}): "
            "highest source trust (priority_order)."
        )
        if len(pairs) > 1:
            others = [
                f"{p[1].provenance[0].source if p[1].provenance else 'notes'}"
                for p in pairs
                if p[1] is not best_cand
            ]
            reason += f" Discarded: {', '.join(others)}."
        return best_val, reason

    @staticmethod
    def _majority_vote(
        field_name: str, pairs: list[tuple[Any, Candidate]]
    ) -> tuple[Any, str]:
        """Value agreed by the most sources wins; tie breaks via priority_order."""
        vote_count: dict[str, int] = defaultdict(int)
        vote_val: dict[str, Any] = {}

        for val, _ in pairs:
            key = str(val).lower().strip() if val else ""
            vote_count[key] += 1
            vote_val[key] = val

        max_votes = max(vote_count.values())
        winners = [k for k, v in vote_count.items() if v == max_votes]

        if len(winners) == 1:
            chosen = vote_val[winners[0]]
            reason = (
                f"{field_name}: majority_vote winner '{chosen}' "
                f"({max_votes}/{len(pairs)} sources agree)."
            )
            return chosen, reason

        # Tie — fall back to priority_order among tied winners
        tied_pairs = [p for p in pairs if str(p[0]).lower().strip() in winners]
        return MergeEngine._priority_order(field_name, tied_pairs)

    @staticmethod
    def _latest_wins(
        field_name: str, pairs: list[tuple[Any, Candidate]]
    ) -> tuple[Any, str]:
        """
        Choose the value from the candidate whose most recent experience
        end-date is latest. Falls back to priority_order if dates are absent.
        """
        def _latest_date(cand: Candidate) -> str:
            dates = []
            for exp in cand.experience:
                if exp.end and exp.end.lower() not in ("present", "current"):
                    dates.append(exp.end)
                elif exp.start:
                    dates.append(exp.start)
            return max(dates) if dates else ""

        dated = [(val, cand, _latest_date(cand)) for val, cand in pairs]
        best = max(dated, key=lambda x: x[2])
        val, cand, date = best
        src = cand.provenance[0].source if cand.provenance else "notes"
        reason = (
            f"{field_name} from {src} (latest date: {date or 'N/A'}): "
            "latest_wins strategy."
        )
        return val, reason

    @staticmethod
    def _highest_confidence(
        field_name: str, pairs: list[tuple[Any, Candidate]]
    ) -> tuple[Any, str]:
        """Value with the highest provenance confidence wins."""
        def _field_conf(cand: Candidate) -> float:
            relevant = [
                p for p in cand.provenance
                if p.field == field_name
            ]
            if relevant:
                return max(_effective_confidence(p) for p in relevant)
            # Fall back to source trust if no field-specific provenance
            src = cand.provenance[0].source if cand.provenance else "notes"
            return SOURCE_TRUST.get(src, 0.70)

        best_val, best_cand = max(pairs, key=lambda p: _field_conf(p[1]))
        conf = _field_conf(best_cand)
        src = best_cand.provenance[0].source if best_cand.provenance else "notes"
        reason = (
            f"{field_name} from {src} ({conf:.4f}): "
            "highest_confidence strategy."
        )
        return best_val, reason

    # ─────────────────────────────────────────────────────────────────────────
    # List helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _union_list(lists: list[list[Any]], key=None) -> list[Any]:
        seen: set = set()
        result: list = []
        for lst in lists:
            for item in lst:
                k = key(item) if key else item
                if k not in seen:
                    seen.add(k)
                    result.append(item)
        return result

    @staticmethod
    def _union_experience(candidates: list[Candidate]) -> list[Experience]:
        seen: set = set()
        result: list[Experience] = []
        for cand in candidates:
            for exp in cand.experience:
                k = (
                    (exp.company or "").lower().strip(),
                    exp.title.lower().strip(),
                )
                if k not in seen:
                    seen.add(k)
                    result.append(exp)
        return result

    @staticmethod
    def _union_education(candidates: list[Candidate]) -> list[Education]:
        seen: set = set()
        result: list[Education] = []
        for cand in candidates:
            for edu in cand.education:
                k = (
                    (edu.institution or "").lower().strip(),
                    (edu.degree or "").lower().strip(),
                )
                if k not in seen:
                    seen.add(k)
                    result.append(edu)
        return result

    @staticmethod
    def _merge_provenance(candidates: list[Candidate]) -> list[Provenance]:
        """
        Combine provenance from all candidates.
        Flag fields where different sources gave different values (conflict).
        """
        # Group by field name
        field_vals: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for cand in candidates:
            src = cand.provenance[0].source if cand.provenance else "notes"
            for p in cand.provenance:
                field_vals[p.field].append((str(p.value or "").lower(), p.source))

        # Determine which fields have genuine conflicts
        conflicted: set[str] = set()
        for field, pairs in field_vals.items():
            unique_vals = {v for v, _ in pairs}
            if len(unique_vals) > 1:
                conflicted.add(field)

        combined: list[Provenance] = []
        for cand in candidates:
            for p in cand.provenance:
                combined.append(Provenance(
                    field=p.field,
                    value=p.value,
                    raw_value=p.raw_value,
                    source=p.source,
                    method=p.method,
                    confidence=_effective_confidence(p),
                    conflict=(p.field in conflicted),
                ))

        return combined