"""
Crawlee Adapter: Modern, concurrent web crawler for crawling scholarship catalogues and university lists.
Uses Crawlee for Python (BeautifulSoupCrawler / ParselCrawler).
"""

import asyncio
from typing import List, Dict, Any
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext


async def crawl_scholarship_pages_crawlee(start_urls: List[str], max_requests: int = 10) -> List[Dict[str, Any]]:
    results = []

    crawler = BeautifulSoupCrawler(
        max_requests_per_crawl=max_requests,
    )

    @crawler.router.default_handler
    async def request_handler(context: BeautifulSoupCrawlingContext) -> None:
        title = context.soup.title.string.strip() if context.soup.title and context.soup.title.string else ""
        headings = [h.get_text(strip=True) for h in context.soup.find_all(["h1", "h2"])][:5]

        # Extract potential scholarship links on page
        links = []
        for a in context.soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True).lower()
            if any(k in text or k in href.lower() for k in ["scholarship", "bursary", "funding", "apply", "grants"]):
                links.append({"title": a.get_text(strip=True), "href": href})

        results.append({
            "url": context.request.url,
            "title": title,
            "headings": headings,
            "found_links_count": len(links),
            "sample_links": links[:5]
        })

    await crawler.run(start_urls)
    return results


def run_crawlee_sync(start_urls: List[str], max_requests: int = 5) -> List[Dict[str, Any]]:
    return asyncio.run(crawl_scholarship_pages_crawlee(start_urls, max_requests=max_requests))

