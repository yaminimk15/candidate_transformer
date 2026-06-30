"""
LinkedIn Extractor — HTTP scraper for public LinkedIn profile pages.

Fetches the publicly visible portion of a LinkedIn profile URL and
extracts: name, headline, location, about, experience, education, skills.

Limitations:
  - Only data visible WITHOUT login is extracted (public view).
  - LinkedIn may return a login-wall for some profiles; the extractor
    handles this gracefully and returns whatever it could parse.
  - For full data access, use the LinkedIn Official Partner API.
"""

import re
import time
import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Rotate a realistic browser UA to reduce bot-blocking
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}


def _clean(text: Optional[str]) -> Optional[str]:
    """Strip and collapse whitespace; return None for empty strings."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned or None


def _is_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


class LinkedInExtractor:
    """
    Fetches and parses a LinkedIn public profile page.
    Falls back to an empty profile dict on any network / parse error.
    """

    def extract(self, file_path: Optional[str] = None) -> dict:
        """
        Args:
            file_path: LinkedIn profile URL (https://linkedin.com/in/username)
                       OR path to a local LinkedIn JSON stub file.

        Returns:
            dict with keys: full_name, emails, phones, location, links,
                            skills, experience, education, headline, about.
        """
        if not file_path:
            return self._empty()

        # If it's a local JSON file, read it directly
        import os, json
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "full_name":  data.get("full_name"),
                    "emails":     data.get("emails", []),
                    "phones":     data.get("phones", []),
                    "location":   data.get("location"),
                    "links":      data.get("links", []),
                    "skills":     data.get("skills", []),
                    "experience": data.get("experience", []),
                    "education":  data.get("education", []),
                    "headline":   data.get("headline"),
                    "about":      data.get("about"),
                }
            except Exception as exc:
                logger.warning("Failed to read local LinkedIn JSON: %s", exc)
                return self._empty()

        # Otherwise treat as URL
        if not _is_url(file_path):
            logger.warning("linkedin_path '%s' is neither a file nor a URL.", file_path)
            return self._empty()

        return self._fetch_and_parse(file_path)

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _empty(self) -> dict:
        return {
            "full_name": None, "emails": [], "phones": [],
            "location": None, "links": [], "skills": [],
            "experience": [], "education": [], "headline": None, "about": None,
        }

    def _fetch_and_parse(self, url: str) -> dict:
        """Download the public profile page and extract fields."""
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15, allow_redirects=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("LinkedIn fetch failed for '%s': %s", url, exc)
            return self._empty()

        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Detect login-wall
        if self._is_login_wall(soup, html):
            logger.warning(
                "LinkedIn returned a login-wall for '%s'. "
                "Only limited data may be available.", url
            )

        result = self._empty()
        result["links"] = [url]

        # ── Name ──────────────────────────────────────────────────────────────
        name = (
            self._meta(soup, "og:title")
            or self._text(soup, "h1")
            or self._text(soup, '[class*="top-card__title"]')
            or self._text(soup, '[class*="profile-header__name"]')
        )
        # og:title format: "Full Name - Role at Company | LinkedIn"
        # Strip everything from the first dash/pipe that isn't the name
        if name:
            # Remove " | LinkedIn" or " - LinkedIn" tail
            name = re.sub(r"\s*[|]\s*(LinkedIn|linkedin\.com).*$", "", name, flags=re.I)
            # Remove " - Title at Company" part if present (keep only the name portion)
            name = re.sub(r"\s+-\s+.{5,}$", "", name).strip()
        result["full_name"] = _clean(name)

        # ── Headline ──────────────────────────────────────────────────────────
        headline = (
            self._text(soup, '[class*="top-card__subline-item"]')
            or self._text(soup, '[class*="profile-header__headline"]')
            or self._text(soup, "h2")
            or self._meta(soup, "og:description")
        )
        # Strip mojibake chars; truncate to first clause
        if headline:
            headline = re.sub(r"[\ufffd\u00e2\u0080\u0093-\u0099]+", "", headline)
            headline = re.split(r"[.·|]", headline)[0][:120].strip()
        result["headline"] = _clean(headline)

        # ── Location ──────────────────────────────────────────────────────────
        location = (
            self._text(soup, '[class*="top-card__subline-item"]:last-child')
            or self._text(soup, '[class*="location"]')
        )
        result["location"] = _clean(location)

        # ── About / summary ───────────────────────────────────────────────────
        about = self._text(soup, '[class*="summary"]') or self._text(soup, '[class*="about"]')
        result["about"] = _clean(about)

        # ── Skills ────────────────────────────────────────────────────────────
        skills_raw = soup.find_all(
            attrs={"class": re.compile(r"skill|endorsement", re.I)}
        )
        skills = []
        for s in skills_raw:
            t = _clean(s.get_text())
            if t and len(t) < 60 and t not in skills:
                skills.append(t)
        result["skills"] = skills[:30]

        # ── Experience ────────────────────────────────────────────────────────
        exp_section = soup.find(attrs={"class": re.compile(r"experience", re.I)})
        experience = []
        if exp_section:
            items = exp_section.find_all("li")
            for item in items[:6]:
                # Try multiple selectors for title
                title_el   = (item.find(attrs={"class": re.compile(r"title|position|role", re.I)})
                              or item.find("h3") or item.find("h4"))
                company_el = (item.find(attrs={"class": re.compile(r"company|org|employer", re.I)})
                              or item.find("h4") or item.find("span"))
                date_el    = item.find(attrs={"class": re.compile(r"date|duration|period", re.I)})
                title   = _clean(title_el.get_text())   if title_el   else None
                company = _clean(company_el.get_text()) if company_el else None
                dates   = _clean(date_el.get_text())    if date_el    else None
                # Avoid duplicating title text into company
                if company and title and company.strip() == title.strip():
                    company = None
                if title or company:
                    entry = {"title": title or "N/A", "company": company or "N/A"}
                    if dates:
                        parts = re.split(r"\s*[\u2013\u2014\-–—]\s*", dates, maxsplit=1)
                        entry["start"] = parts[0].strip() if parts else None
                        entry["end"]   = parts[1].strip() if len(parts) > 1 else "Present"
                    experience.append(entry)
        result["experience"] = experience

        # ── Education ─────────────────────────────────────────────────────────
        edu_section = soup.find(attrs={"class": re.compile(r"education", re.I)})
        education = []
        if edu_section:
            items = edu_section.find_all("li")
            for item in items[:4]:
                institution = _clean(item.find(attrs={"class": re.compile(r"school|institution|org", re.I)}) and
                                      item.find(attrs={"class": re.compile(r"school|institution|org", re.I)}).get_text())
                degree      = _clean(item.find(attrs={"class": re.compile(r"degree|field", re.I)}) and
                                      item.find(attrs={"class": re.compile(r"degree|field", re.I)}).get_text())
                if institution or degree:
                    education.append({"institution": institution or "N/A", "degree": degree or "N/A"})
        result["education"] = education

        # ── Email fallback — LinkedIn rarely exposes these in public HTML ──────
        emails_found = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
        result["emails"] = list(dict.fromkeys(emails_found))[:5]  # deduplicated

        logger.info(
            "LinkedIn extracted: name=%s headline=%s skills=%d exp=%d edu=%d",
            result["full_name"], result["headline"],
            len(result["skills"]), len(result["experience"]), len(result["education"]),
        )
        return result

    # ──────────────────────────────────────────────────────────────────────────
    def _text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """CSS-select first element and return its stripped text."""
        try:
            el = soup.select_one(selector)
            return el.get_text(separator=" ") if el else None
        except Exception:
            return None

    def _meta(self, soup: BeautifulSoup, prop: str) -> Optional[str]:
        """Read an og: / name= meta tag."""
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return tag.get("content") if tag else None

    def _is_login_wall(self, soup: BeautifulSoup, html: str) -> bool:
        """Heuristic: detect LinkedIn's auth-redirect page."""
        return (
            "authwall" in html.lower()
            or "join now" in html.lower()
            or soup.find("form", id="join-form") is not None
        )
