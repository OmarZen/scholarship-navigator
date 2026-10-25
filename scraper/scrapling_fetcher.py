"""
Scrapling Adapter: Ultra-fast, anti-detection page fetching and parsing.
Leverages Scrapling's Fetcher and Adaptor for resilient DOM queries.
"""

from typing import Dict, Any, Optional
from scrapling.parser import Selector
import httpx


def fetch_with_scrapling(url: str, stealthy: bool = True) -> Selector:
    """
    Fetch a page and return a Scrapling Selector with CSS/XPath capabilities.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        page = Selector(resp.text)
        return page


def extract_scholarship_with_scrapling(url: str) -> Dict[str, Any]:
    """
    Extract headings, deadlines, and key requirements using Scrapling selector queries.
    """
    page = fetch_with_scrapling(url)

    # Scrapling clean text and selectors
    title = page.css("title::text").first or ""
    h1 = page.css("h1::text").get_all()
    h2 = page.css("h2::text").get_all()
    headings = [h.strip() for h in (h1 + h2) if len(h.strip()) > 3]

    # Find paragraphs containing deadline or eligibility keywords
    paragraphs = page.css("p, li, div").get_all()
    deadline_snippets = []
    eligibility_snippets = []

    for p in paragraphs:
        p_clean = " ".join(p.split())
        p_lower = p_clean.lower()
        if any(w in p_lower for w in ["deadline", "closing date", "apply by", "due date"]) and len(p_clean) < 300:
            if p_clean not in deadline_snippets:
                deadline_snippets.append(p_clean)
        if any(w in p_lower for w in ["eligibility", "criteria", "requirements", "minimum gpa", "ielts"]) and len(p_clean) < 400:
            if p_clean not in eligibility_snippets:
                eligibility_snippets.append(p_clean)

    return {
        "tool": "scrapling",
        "url": url,
        "title": title.strip(),
        "headings": headings[:8],
        "deadline_snippets": deadline_snippets[:4],
        "eligibility_snippets": eligibility_snippets[:4]
    }

