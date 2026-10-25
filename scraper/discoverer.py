"""
Dynamic Scholarship Discovery and Extraction Engine.
Uses Scrapling, Crawl4AI, and Crawlee to scrape, extract, and append new scholarship programs.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from .engine import ScrapeEngine
from .parser import parse_scholarship_page
from .scrapling_fetcher import extract_scholarship_with_scrapling
from .crawlee_crawler import run_crawlee_sync


SEED_PORTALS = {
    "erasmus": "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en",
    "chevening": "https://www.chevening.org/scholarships/",
    "daad": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
    "hungary": "https://stipendiumhungaricum.hu/",
    "campusfrance": "https://www.campusfrance.org/en/bursaries-foreign-students",
    "studyinsweden": "https://studyinsweden.se/scholarships/",
    "studyinfinland": "https://www.studyinfinland.fi/scholarships",
    "newzealand": "https://www.nzscholarships.govt.nz/",
    "austria": "https://grants.at/en/",
    "carolina_spain": "https://www.fundacioncarolina.es/formacion/becas-de-postgrado-y-doctorado/"
}


def discover_and_extract_from_url(url: str, engine: str = "scrapling") -> Dict[str, Any]:
    """
    Extract structured scholarship data from a live target portal.
    """
    if engine == "scrapling":
        try:
            return extract_scholarship_with_scrapling(url)
        except Exception:
            pass

    # Default to ScrapeEngine with BeautifulSoup
    with ScrapeEngine() as eng:
        soup = eng.get_soup(url)
        parsed = parse_scholarship_page(soup, url)
        return parsed


def save_discovered_scholarship(scholarship_data: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    """
    Append newly discovered scholarship to custom_scholarships.json
    """
    if output_path is None:
        output_path = Path(__file__).parent.parent / "data" / "custom_scholarships.json"

    existing = []
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # Check for duplicate by ID or name
    s_id = scholarship_data.get("id") or scholarship_data.get("title", "").lower().replace(" ", "-")[:30]
    scholarship_data["id"] = s_id

    existing = [s for s in existing if s.get("id") != s_id]
    existing.append(scholarship_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return str(output_path.resolve())
