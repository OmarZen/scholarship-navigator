"""
Live Portal Verifier: Checks health, redirects, and updates of official scholarship portals.
"""

from typing import List, Dict, Any
from pathlib import Path
import json
import httpx
from .engine import ScrapeEngine
from .parser import parse_scholarship_page


def verify_scholarship_portals(scholarships_path: Path = None, limit: int = None) -> List[Dict[str, Any]]:
    if scholarships_path is None:
        scholarships_path = Path(__file__).parent.parent / "data" / "scholarships.json"

    with open(scholarships_path, "r", encoding="utf-8") as f:
        scholarships = json.load(f)

    if limit:
        scholarships = scholarships[:limit]

    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }

    with httpx.Client(headers=headers, timeout=12.0, follow_redirects=True) as client:
        for s in scholarships:
            url = s["official_portal"]
            entry = {
                "id": s["id"],
                "name": s["name"],
                "country": s["country"],
                "url": url,
                "status_code": None,
                "is_online": False,
                "error": None
            }
            try:
                resp = client.get(url)
                entry["status_code"] = resp.status_code
                entry["is_online"] = resp.status_code < 400
                entry["final_url"] = str(resp.url)
            except Exception as e:
                entry["error"] = str(e)
                entry["is_online"] = False

            results.append(entry)

    return results


def scrape_scholarship_url(url: str) -> Dict[str, Any]:
    with ScrapeEngine() as engine:
        soup = engine.get_soup(url)
        parsed = parse_scholarship_page(soup, url)
        return parsed
