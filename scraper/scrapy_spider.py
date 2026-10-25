"""
Scrapy Spider: Battle-tested framework for high-throughput crawling of scholarship catalogues.
"""

from typing import List, Dict, Any
import scrapy
from scrapy.crawler import CrawlerProcess


class ScholarshipSpider(scrapy.Spider):
    name = "scholarship_spider"

    def __init__(self, start_urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or ["https://stipendiumhungaricum.hu/"]
        self.extracted_items = []

    def parse(self, response):
        title = response.css("title::text").get(default="").strip()
        h1s = response.css("h1::text").getall()

        # Find paragraphs mentioning deadline or scholarship
        relevant_text = []
        for p in response.css("p, li"):
            text = " ".join(p.css("::text").getall()).strip()
            if any(k in text.lower() for k in ["deadline", "apply", "scholarship", "eligibility"]):
                if len(text) < 400 and text not in relevant_text:
                    relevant_text.append(text)

        item = {
            "url": response.url,
            "title": title,
            "headings": [h.strip() for h in h1s if h.strip()],
            "snippets": relevant_text[:5]
        }
        self.extracted_items.append(item)
        yield item


def run_scrapy_crawler(urls: List[str]) -> List[Dict[str, Any]]:
    process = CrawlerProcess(
        settings={
            "LOG_LEVEL": "WARNING",
            "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "ROBOTSTXT_OBEY": False,
            "DOWNLOAD_TIMEOUT": 15
        }
    )
    spider = ScholarshipSpider
    process.crawl(spider, start_urls=urls)
    process.start()
    return []

