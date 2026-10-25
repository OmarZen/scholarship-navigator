"""
Crawl4AI Adapter: LLM-friendly web crawler for extracting markdown, structured scholarship data, and media.
"""

import asyncio
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


async def crawl_with_crawl4ai(url: str) -> Dict[str, Any]:
    browser_cfg = BrowserConfig(
        headless=True,
        verbose=False
    )
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        remove_overlay_elements=True
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)
        return {
            "tool": "crawl4ai",
            "url": url,
            "success": result.success,
            "status_code": result.status_code,
            "markdown_length": len(result.markdown or ""),
            "markdown_snippet": (result.markdown or "")[:1500],
            "title": result.metadata.get("title", "") if result.metadata else ""
        }


def run_crawl4ai_sync(url: str) -> Dict[str, Any]:
    return asyncio.run(crawl_with_crawl4ai(url))

