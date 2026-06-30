import re

from app.constants.skill_mapping import (
    CANONICAL_SKILLS
)


class ResumeParser:

    EMAIL_PATTERN = (
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    )

    PHONE_PATTERN = (
        r'\+?\d{10,13}'
    )

    DEGREE_KEYWORDS = [
        "B.E", "B.E.", "BE",
        "B.TECH", "B.TECH.", "BTECH",
        "BACHELOR",
        "B.SC", "BSC",
        "B.A", "BA",
        "MCA",
        "M.TECH", "M.TECH.", "MTECH",
        "MASTER",
        "M.SC", "MSC",
        "M.A", "MA",
        "MBA",
        "PH.D", "PHD",
        "DIPLOMA",
        "HSC", "SSLC", "SSC",
    ]

    # Word-boundary version of DEGREE_KEYWORDS, used wherever we need to
    # avoid matching an abbreviation as a substring of an unrelated word
    # (e.g. "BA" inside "Global", "MA" inside "Mathematics"). Note:
    # multi-word phrases like "HIGHER SECONDARY" are deliberately
    # excluded -- they show up inside ordinary institution names (e.g.
    # "XYZ Higher Secondary School") and would falsely flag the
    # institution's own line as a separate degree entry.
    DEGREE_KEYWORD_PATTERN = re.compile(
        r'\b(?:' + '|'.join(
            re.escape(kw) for kw in sorted(
                [
                    "B.E", "B.E.", "BE", "B.TECH", "B.TECH.", "BTECH",
                    "BACHELOR", "B.SC", "BSC", "B.A", "BA", "MCA",
                    "M.TECH", "M.TECH.", "MTECH", "MASTER", "M.SC", "MSC",
                    "M.A", "MA", "MBA", "PH.D", "PHD", "DIPLOMA",
                    "HSC", "SSLC", "SSC",
                ],
                key=len,
                reverse=True
            )
        ) + r')\b',
        re.IGNORECASE
    )

    EXPERIENCE_TITLE_KEYWORDS = [
        "INTERN", "INTERNSHIP",
        "ENGINEER", "DEVELOPER", "ANALYST",
        "CONSULTANT", "MANAGER", "ARCHITECT",
        "ADMINISTRATOR", "DESIGNER", "LEAD",
        "SPECIALIST", "ASSOCIATE", "EXECUTIVE",
        "SCIENTIST", "PROGRAMMER", "TESTER",
        "TRAINEE",
    ]

    SECTION_HEADINGS = [
        "EDUCATION",
        "EXPERIENCE",
        "INTERNSHIP EXPERIENCE",
        "WORK EXPERIENCE",
        "PROJECTS",
        "SKILLS",
        "CERTIFICATIONS",
        "ACHIEVEMENTS",
        "SUMMARY",
        "OBJECTIVE",
        "PROFILE",
        "CONTACT",
    ]

    # Matches a wide range of "date range" formats found on resumes, e.g.:
    #   Jan 2021 - Mar 2022
    #   January 2021 to March 2022
    #   2021 - 2022
    #   06/2021 - 09/2022
    #   Jan 2021 - Present
    MONTH_NAME = (
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|'
        r'Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|'
        r'Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    )

    DATE_TOKEN = (
        r'(?:' + MONTH_NAME + r'\.?\s+\d{4}'
        r'|\d{1,2}/\d{4}'
        r'|\d{4})'
    )

    DATE_RANGE_PATTERN = re.compile(
        r'(' + DATE_TOKEN + r')\s*(?:-|–|—|to)\s*'
        r'(' + DATE_TOKEN + r'|Present|present|Current|current|Till Date|till date)',
        re.IGNORECASE
    )

    def get_section(
        self,
        text: str,
        section_name: str
    ):

        lines = text.splitlines()

        section_lines = []

        capture = False

        for line in lines:

            line = line.strip()

            # Heading lines are single-column (no right-hand date or
            # location), but check defensively against the left column
            # only in case a layout-aware extraction ever inserts a tab
            # on a heading line.
            heading_check_text, _ = self._split_columns(line)

            if not capture and self._is_heading_match(
                heading_check_text, section_name
            ):
                capture = True
                continue

            if capture:

                # Stop at the next major heading (any known section,
                # not just generic all-caps short lines, to avoid
                # accidentally swallowing unrelated content or stopping
                # too early on an all-caps job title).
                if self._is_any_known_heading(heading_check_text):
                    break

                section_lines.append(line)

        return section_lines

    def _is_heading_match(self, line: str, section_name: str) -> bool:
        """
        True if `line` looks like a section heading matching `section_name`,
        e.g. 'EDUCATION', 'Education:', '== EDUCATION =='.
        Avoids matching section_name when it merely appears as a substring
        inside an unrelated sentence.
        """

        if not line:
            return False

        stripped = re.sub(r'[^A-Za-z ]', ' ', line).strip().upper()

        if not stripped:
            return False

        # Heading lines are short (so we don't match a paragraph that
        # happens to contain the word, e.g. "...gained experience...").
        if len(stripped.split()) > 5:
            return False

        return section_name in stripped

    def _is_any_known_heading(self, line: str) -> bool:

        if not line:
            return False

        stripped = re.sub(r'[^A-Za-z ]', ' ', line).strip().upper()

        if not stripped:
            return False

        if len(stripped.split()) > 5:
            return False

        for heading in self.SECTION_HEADINGS:
            if heading in stripped:
                return True

        # Generic fallback: a SHORT (<=2 word) fully upper-case line that
        # isn't a known degree/title keyword line is probably a custom
        # section heading (covers names like "HONOURS" or "PROFILE").
        # Intentionally conservative:
        #  - <=2 words, not <=4: all-caps institution/company names on
        #    resumes are frequently 3+ words (e.g. "RATHINAM TECHNICAL
        #    CAMPUS"), and treating those as headings would prematurely
        #    cut off section capture.
        #  - no colon or digit allowed: lines like "CGPA: 9.43" or
        #    "Percentage: 88%" reduce to a single all-caps word once
        #    punctuation/digits are stripped (e.g. "CGPA"), but they are
        #    data lines, not section headings.
        if (
            line.strip().isupper()
            and len(line.split()) <= 2
            and ':' not in line
            and not re.search(r'\d', line)
            and not self.DEGREE_KEYWORD_PATTERN.search(line)
            and not any(
                kw in stripped for kw in self.EXPERIENCE_TITLE_KEYWORDS
            )
        ):
            return True

        return False

    def _extract_dates(self, line: str):
        """
        Returns (start_date, end_date) strings found in `line`, or
        (None, None) if no date range is present.
        """

        match = self.DATE_RANGE_PATTERN.search(line)

        if not match:
            return None, None

        return match.group(1).strip(), match.group(2).strip()

    def _split_columns(self, line: str):
        """
        Splits a line on a tab character, which marks a column boundary
        inserted by layout-aware PDF extraction (see
        extract_text_layout_aware in layout_extract.py). Returns
        (left, right) with both sides stripped. If there is no tab,
        returns (line, None).

        Resumes are frequently laid out with two columns -- e.g. a job
        title on the left and its date range on the right, or an
        institution name on the left and its city on the right. Plain
        PDF text extraction loses this visual pairing entirely (the
        right column often ends up dozens of lines away in the raw
        text). A layout-aware extractor preserves the pairing by
        emitting a tab where it detects a large horizontal gap between
        words, so this parser can split on it directly instead of
        guessing from a date/location regex search across distant lines.
        """

        if '\t' in line:
            left, _, right = line.partition('\t')
            return left.strip(), right.strip()

        return line.strip(), None

    def _strip_dates(self, line: str) -> str:
        """Removes a matched date range from a line, tidying punctuation."""

        cleaned = self.DATE_RANGE_PATTERN.sub('', line)
        cleaned = re.sub(r'[\(\)\[\]|,]+\s*$', '', cleaned)
        cleaned = re.sub(r'^\s*[\(\)\[\]|,-]+', '', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip(' -|,\t')

    def _looks_like_experience_entry(self, line: str) -> bool:
        """
        Heuristic to avoid treating ordinary resume sentences (e.g. bullet
        points describing responsibilities) as a new experience entry.
        A genuine title/company line is short and contains a recognizable
        job-title keyword, or contains a date range.
        """

        if not line:
            return False

        word_count = len(line.split())

        if word_count == 0 or word_count > 12:
            return False

        upper = line.upper()

        has_title_keyword = any(
            kw in upper for kw in self.EXPERIENCE_TITLE_KEYWORDS
        )

        has_date = bool(self.DATE_RANGE_PATTERN.search(line))

        # Bullet-point sentences usually start with a verb and end with a
        # period; genuine title/company lines rarely end with one.
        ends_like_sentence = line.strip().endswith('.')

        if ends_like_sentence and not has_date:
            return False

        return has_title_keyword or has_date

    def parse(self, text: str):

        # Fix PDF extraction artifacts
        cleaned_text = text.replace(" @", "@")
        cleaned_text = cleaned_text.replace("@ ", "@")

        # Emails
        emails = re.findall(
            self.EMAIL_PATTERN,
            cleaned_text
        )

        # Phones
        phones = re.findall(
            self.PHONE_PATTERN,
            cleaned_text
        )

        # Name
        lines = cleaned_text.splitlines()

        full_name = None

        for line in lines:

            line = line.strip()

            if line:
                full_name = line
                break

        # Skills
        skills = []

        text_lower = cleaned_text.lower()

        for keyword, canonical in CANONICAL_SKILLS.items():

            pattern = r'\b' + re.escape(keyword) + r'\b'

            if re.search(
                pattern,
                text_lower
            ):
                skills.append(canonical)

        # Location
        location = self._extract_location(cleaned_text, full_name)

        # ----------------------------------
        # EDUCATION EXTRACTION
        # ----------------------------------

        education = self._extract_education(cleaned_text)

        # ----------------------------------
        # EXPERIENCE EXTRACTION
        # ----------------------------------

        experience = self._extract_experience(cleaned_text)

        # ----------------------------------
        # HEADLINE
        # ----------------------------------

        headline = None

        if experience:
            headline = experience[0].get("title")

        return {
            "full_name": full_name,
            "emails": list(dict.fromkeys(emails)),
            "phones": list(dict.fromkeys(phones)),
            "skills": list(dict.fromkeys(skills)),
            "location": location,
            "education": education,
            "experience": experience,
            "headline": headline
        }

    def _extract_location(self, cleaned_text: str, full_name):
        """
        Looks for a "City, Region" style pattern in the resume header
        (the block of lines before the first recognized section heading,
        e.g. name / contact / address block). Restricting to the header
        avoids false positives such as "Business Analyst, Initech Corp"
        showing up inside an experience entry further down the page.
        """

        lines = cleaned_text.splitlines()

        location_pattern = re.compile(
            r'\b([A-Z][a-zA-Z]+)\s*,\s*([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\b'
        )

        header_lines = []

        for line in lines:

            stripped = line.strip()

            if stripped and self._is_any_known_heading(stripped):
                break

            header_lines.append(stripped)

        for stripped in header_lines:

            if not stripped:
                continue

            if full_name and stripped == full_name.strip():
                continue

            if re.search(self.EMAIL_PATTERN, stripped):
                continue

            if re.search(self.PHONE_PATTERN, stripped):
                continue

            # A genuine address/location line is short; long lines are
            # more likely to be a sentence that happens to contain a comma.
            if len(stripped.split()) > 6:
                continue

            match = location_pattern.search(stripped)

            if match:
                return {
                    "city": match.group(1),
                    "region": match.group(2),
                    "country": "India"
                }

        return None

    def _extract_education(self, cleaned_text: str):

        education = []

        education_section = self.get_section(
            cleaned_text,
            "EDUCATION"
        )

        location_only_pattern = re.compile(
            r'^\s*[A-Z][a-zA-Z]+\s*,\s*[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?\s*$'
        )

        for i, raw_line in enumerate(education_section):

            if not raw_line:
                continue

            left, right = self._split_columns(raw_line)

            if not self.DEGREE_KEYWORD_PATTERN.search(left):
                continue

            degree_line = left
            field = None
            institution = None

            # Find exactly where the degree abbreviation/word ends, so
            # we can treat whatever comes after it as the field --
            # this works even when there's NO separator at all, e.g.
            # "B.E.COMPUTER SCIENCE AND ENGINEERING (AI & ML)" (common
            # on Indian resumes where the degree and field run together
            # with just a period between them).
            degree_match = self.DEGREE_KEYWORD_PATTERN.search(degree_line)

            # `degree` in the output is cleaned down to just the
            # abbreviation/name (e.g. "B.E.", "MBA"), not the full raw
            # line with the field still attached. Defaults to the full
            # line if no keyword match is found (shouldn't happen here
            # since we already required a match above, but kept as a
            # safe fallback).
            degree = degree_line

            if degree_match:

                degree = degree_match.group().strip()

                remainder = degree_line[degree_match.end():]

                # Strip a leading separator if present: "in", ",", "-",
                # or "." (the lone connecting period in "B.E.COMPUTER...").
                remainder = re.sub(
                    r'^\s*(?:\bin\b|[,\-.])\s*', '', remainder
                )

                # "Bachelor of Engineering" / "Master of Science" etc:
                # "of" here is part of the degree's own name, not a
                # field separator, so don't peel it off as a field --
                # instead fold it into `degree` so the full degree name
                # is preserved (e.g. degree="Bachelor of Engineering",
                # not degree="Bachelor" with the rest discarded).
                is_bachelor_or_master_of = (
                    degree.upper() in ('BACHELOR', 'MASTER')
                    and re.match(r'^\s*of\b', remainder, re.IGNORECASE)
                )

                if is_bachelor_or_master_of:

                    of_match = re.match(
                        r'^\s*(of\s+\S+)', remainder, re.IGNORECASE
                    )

                    if of_match:
                        degree = f"{degree} {of_match.group(1).strip()}"
                        remainder = remainder[of_match.end():].strip()

                if (
                    remainder
                    and not self.DEGREE_KEYWORD_PATTERN.fullmatch(
                        remainder.strip()
                    )
                ):
                    field = remainder.strip()

            # If the degree's own line had a right-hand column (a date
            # range, from a layout-aware extraction), that's this
            # entry's date info; the institution is then expected on
            # the NEXT line's left-hand column.
            start_date, end_date = (None, None)

            if right:
                start_date, end_date = self._extract_dates(right)

            # Look at nearby lines (next, then previous, then two ahead)
            # for the institution name, skipping blank lines and lines
            # that are themselves degree lines or pure date ranges. We
            # only look at the LEFT column of each candidate line, since
            # the right column (if any) belongs to that candidate
            # line's own date or location, not to our institution
            # lookup -- but we do capture it separately as the
            # institution's location.
            institution_location = None

            for offset in (1, -1, 2):

                idx = i + offset

                if not (0 <= idx < len(education_section)):
                    continue

                candidate_left, candidate_right = self._split_columns(
                    education_section[idx]
                )

                candidate = candidate_left.strip()

                if not candidate:
                    continue

                if self.DEGREE_KEYWORD_PATTERN.search(candidate):
                    continue

                # Skip metadata "Label: value" lines (e.g. "CGPA: 9.43",
                # "Percentage: 88%", "HONOURS: Cybersecurity") -- these
                # describe the entry but aren't the institution name.
                if re.match(r'^[A-Za-z][A-Za-z .]*:\s*\S', candidate):
                    continue

                # Guard for plain-text (no column tab) input where a
                # bare "City, Region" line could appear on its own and
                # get mistaken for an institution name.
                if not candidate_right and location_only_pattern.match(
                    candidate
                ):
                    continue

                if self.DATE_RANGE_PATTERN.fullmatch(candidate.strip(' -|,')):
                    continue

                if self.DATE_RANGE_PATTERN.search(candidate):
                    candidate_clean = self._strip_dates(candidate)
                    if candidate_clean:
                        institution = candidate_clean
                        if candidate_right:
                            institution_location = candidate_right
                        break
                    continue

                institution = candidate

                if candidate_right:
                    institution_location = candidate_right

                break

            education.append(
                {
                    "institution": institution,
                    "degree": degree,
                    "field": field,
                    "start_date": start_date,
                    "end_date": end_date,
                    "location": institution_location
                }
            )

        return education

    def _extract_experience(self, cleaned_text: str):

        experience = []

        experience_section = []

        experience_section.extend(
            self.get_section(
                cleaned_text,
                "INTERNSHIP EXPERIENCE"
            )
        )

        experience_section.extend(
            self.get_section(
                cleaned_text,
                "WORK EXPERIENCE"
            )
        )

        experience_section.extend(
            self.get_section(
                cleaned_text,
                "EXPERIENCE"
            )
        )

        seen_lines = set()

        skip_indices = set()

        for idx, raw_line in enumerate(experience_section):

            if idx in skip_indices:
                continue

            if not raw_line.strip() or raw_line.strip() in seen_lines:
                continue

            left, right = self._split_columns(raw_line)

            stripped = left

            if not stripped or stripped in seen_lines:
                continue

            if not self._looks_like_experience_entry(stripped):
                continue

            seen_lines.add(raw_line.strip())

            # If a layout-aware extraction put the date range in this
            # line's right-hand column, that's the authoritative source.
            start_date, end_date = (None, None)

            if right:
                start_date, end_date = self._extract_dates(right)

            # Fall back to scanning the line itself (date inline with
            # the title, no column separator).
            if start_date is None:
                start_date, end_date = self._extract_dates(stripped)

            # Final fallback: resumes commonly place the date range on
            # its own line right after the title/company line, e.g.:
            #   Software Engineer Intern - TechCorp Solutions
            #   Jun 2022 - Aug 2022
            if start_date is None:

                next_idx = idx + 1

                if next_idx < len(experience_section):

                    next_left, _next_right = self._split_columns(
                        experience_section[next_idx]
                    )

                    next_start, next_end = self._extract_dates(next_left)

                    # Only treat the next line as a date line if, once the
                    # date range is removed, nothing meaningful is left —
                    # otherwise it's a normal description line that merely
                    # happens to contain a year.
                    if next_start is not None:

                        remainder = self._strip_dates(next_left)

                        if not remainder:
                            start_date, end_date = next_start, next_end
                            skip_indices.add(next_idx)

            without_dates = self._strip_dates(stripped)

            title = without_dates
            company = None

            if "-" in without_dates:

                parts = without_dates.split("-", 1)

                title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else None

            elif "," in without_dates:

                parts = without_dates.split(",", 1)

                title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else None

            elif " at " in without_dates.lower():

                at_idx = without_dates.lower().index(" at ")
                title = without_dates[:at_idx].strip()
                company = without_dates[at_idx + 4:].strip()

            if not title:
                continue

            experience.append(
                {
                    "company": company,
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "summary": "Extracted from resume"
                }
            )

        return experience