"""
Resilient Web Scraping Engine with modern HTTP/2 support, custom headers, and caching.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}


class ScrapeEngine:
    def __init__(self, cache_dir: Optional[Path] = None, timeout: float = 15.0):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.client = httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=self.timeout,
            follow_redirects=True,
            verify=True
        )

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    def fetch(self, url: str, use_cache: bool = True, max_cache_age_days: int = 7) -> str:
        cache_file = self._get_cache_path(url)
        if use_cache and cache_file.exists():
            age_days = (time.time() - cache_file.stat().st_mtime) / (24 * 3600)
            if age_days < max_cache_age_days:
                return cache_file.read_text(encoding="utf-8")

        response = self.client.get(url)
        response.raise_for_status()
        html = response.text

        if use_cache:
            cache_file.write_text(html, encoding="utf-8")
        return html

    def get_soup(self, url: str, use_cache: bool = True) -> BeautifulSoup:
        html = self.fetch(url, use_cache=use_cache)
        return BeautifulSoup(html, "html.parser")

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
