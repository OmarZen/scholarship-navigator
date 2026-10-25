"""
Scholarship Page Parser: Extracts deadlines, eligibility criteria, and required documents.
"""

import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup


DATE_PATTERNS = [
    r"(?:deadline|closing date|closes|applications close|apply by)\s*[:\-–]?\s*([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{4})",
    r"([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{4})",
    r"([0-9]{4}-[0-9]{2}-[0-9]{2})",
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{1,2}(?:st|nd|rd|th)?,?\s+[0-9]{4}"
]

REQUIREMENT_KEYWORDS = [
    "gpa", "bachelor", "master", "ielts", "toefl", "work experience",
    "years of experience", "nationality", "citizenship", "age limit",
    "transcript", "recommendation letter", "reference", "motivation letter",
    "statement of purpose", "curriculum vitae", "cv", "resume"
]


def extract_page_metadata(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag and desc_tag.get("content"):
        meta_desc = desc_tag["content"].strip()

    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if len(h.get_text(strip=True)) > 3]

    return {
        "url": url,
        "title": title,
        "description": meta_desc,
        "headings": headings[:10]
    }


def extract_deadlines(text: str) -> List[str]:
    found_dates = []
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0]
            m_clean = m.strip()
            if m_clean not in found_dates and len(m_clean) > 4:
                found_dates.append(m_clean)
    return found_dates[:5]


def extract_key_sections(soup: BeautifulSoup) -> Dict[str, List[str]]:
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    extracted_eligibility = []
    extracted_documents = []

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(k in line_lower for k in ["eligible", "eligibility", "criteria", "requirements", "who can apply"]):
            context = " ".join(lines[i:min(i + 5, len(lines))])
            if len(context) > 20 and context not in extracted_eligibility:
                extracted_eligibility.append(context)

        if any(k in line_lower for k in ["required documents", "supporting documents", "what to submit", "application documents"]):
            context = " ".join(lines[i:min(i + 5, len(lines))])
            if len(context) > 20 and context not in extracted_documents:
                extracted_documents.append(context)

    return {
        "eligibility_snippets": extracted_eligibility[:3],
        "document_snippets": extracted_documents[:3]
    }


def parse_scholarship_page(html_or_soup, url: str) -> Dict[str, Any]:
    if isinstance(html_or_soup, BeautifulSoup):
        soup = html_or_soup
    else:
        soup = BeautifulSoup(html_or_soup, "html.parser")

    # Remove script and style elements
    for s in soup(["script", "style", "noscript", "svg"]):
        s.extract()

    meta = extract_page_metadata(soup, url)
    full_text = soup.get_text(separator=" ", strip=True)
    deadlines = extract_deadlines(full_text)
    sections = extract_key_sections(soup)

    return {
        "metadata": meta,
        "detected_deadlines": deadlines,
        "eligibility_snippets": sections["eligibility_snippets"],
        "document_snippets": sections["document_snippets"],
        "word_count": len(full_text.split())
    }
