# Bright Data SDK wrapper — SERP, Web Scraper, Scraping Browser, Web Unlocker routing
import httpx
from app.config.source_tiers import assign_tier


class BrightDataClient:
    def __init__(self, api_key: str, serp_zone: str, scraper_zone: str) -> None:
        pass

    async def serp_search(self, query: str, num_results: int = 10):
        pass

    async def scrape_page(self, url: str):
        pass

    async def scrape_job_page(self, url: str):
        pass
