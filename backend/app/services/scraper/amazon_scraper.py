# this file handles amazon scraping for products and reviews
import asyncio
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from playwright.async_api import Browser, Page, async_playwright

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedReview:
    # this object stores parsed review data from one review block
    review_id: Optional[str]
    title: Optional[str]
    content: str
    rating: Optional[float]
    review_date: Optional[str]
    verified_purchase: Optional[bool]
    helpful_votes: Optional[int]
    raw_payload: dict = field(default_factory=dict)


@dataclass
class ScrapedProduct:
    # this object stores parsed product data and nested reviews
    asin: str
    title: str
    url: str
    category: Optional[str]
    size: Optional[str]
    price: Optional[float]
    list_price: Optional[float]
    discount_percent: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    reviews: list[ScrapedReview] = field(default_factory=list)


def _extract_asin(url: str) -> Optional[str]:
    # this function extracts asin from multiple amazon url styles
    patterns = [r"/dp/([A-Z0-9]{10})", r"/gp/product/([A-Z0-9]{10})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _clean_text(value: Optional[str]) -> str:
    # this function normalizes text values
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _parse_price(raw: Optional[str]) -> Optional[float]:
    # this function parses inr price text into float
    if not raw:
        return None
    numbers = re.sub(r"[^0-9.]", "", raw)
    if not numbers:
        return None
    try:
        return round(float(numbers), 2)
    except ValueError:
        return None


def _parse_discount(price: Optional[float], list_price: Optional[float], text_discount: Optional[str]) -> Optional[float]:
    # this function computes discount percentage from available fields
    if text_discount:
        match = re.search(r"(\d{1,2})\s?%", text_discount)
        if match:
            return float(match.group(1))
    if price and list_price and list_price > 0 and list_price > price:
        return round((list_price - price) * 100 / list_price, 2)
    return None


def _parse_rating(raw: Optional[str]) -> Optional[float]:
    # this function extracts rating numeric value
    if not raw:
        return None
    match = re.search(r"([0-9.]+)\s*out of", raw.lower())
    if match:
        return float(match.group(1))
    match = re.search(r"([0-9.]+)", raw)
    if match:
        return float(match.group(1))
    return None


def _parse_review_count(raw: Optional[str]) -> Optional[int]:
    # this function parses review count text
    if not raw:
        return None
    match = re.search(r"([0-9,]+)", raw)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _parse_helpful_votes(raw: Optional[str]) -> Optional[int]:
    # this function parses helpful vote statement
    if not raw:
        return None
    lowered = raw.lower()
    if "one person" in lowered:
        return 1
    match = re.search(r"([0-9,]+)", raw)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def _parse_review_date(raw: Optional[str]) -> Optional[str]:
    # this function parses review date into iso date string
    if not raw:
        return None
    cleaned = raw.replace("Reviewed in India on", "").strip()
    try:
        parsed = date_parser.parse(cleaned, dayfirst=True)
        return parsed.date().isoformat()
    except Exception:
        return None


class AmazonScraper:
    # this class manages browser lifecycle and scraping steps
    def __init__(self) -> None:
        # this method loads scraper configs
        self.settings = get_settings()

    async def scrape_brand(self, brand_name: str, products_limit: int, reviews_limit: int) -> dict:
        # this function scrapes products and reviews for one brand
        search_url = f"https://www.amazon.in/s?k={quote_plus(brand_name + ' luggage')}&rh=n%3A1571271031"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.settings.scraper_headless)
            try:
                page = await browser.new_page()
                await page.goto(search_url, wait_until="domcontentloaded", timeout=self.settings.scraper_timeout_seconds * 1000)
                await asyncio.sleep(self.settings.scraper_delay_ms / 1000)

                product_urls = await self._extract_product_urls(page, products_limit)
                products: list[ScrapedProduct] = []

                for product_url in product_urls:
                    try:
                        product = await self._scrape_product(browser, product_url, reviews_limit)
                        if product:
                            products.append(product)
                    except Exception as exc:
                        logger.warning("product scrape failed for %s error %s", product_url, exc)

                    await asyncio.sleep(self.settings.scraper_delay_ms / 1000)

                return {
                    "brand": brand_name,
                    "search_url": search_url,
                    "products": [asdict(p) for p in products],
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            finally:
                await browser.close()

    async def _extract_product_urls(self, page: Page, limit: int) -> list[str]:
        # this function extracts product links from search result page
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        links = []
        seen = set()

        for node in soup.select("a.a-link-normal.s-no-outline"):
            href = node.get("href")
            if not href:
                continue
            full = href if href.startswith("http") else f"https://www.amazon.in{href}"
            asin = _extract_asin(full)
            if not asin or asin in seen:
                continue
            seen.add(asin)
            links.append(full.split("?")[0])
            if len(links) >= limit:
                break

        # this fallback helps when selector changes
        if len(links) < limit:
            for node in soup.select("a[href*='/dp/']"):
                href = node.get("href")
                if not href:
                    continue
                full = href if href.startswith("http") else f"https://www.amazon.in{href}"
                asin = _extract_asin(full)
                if not asin or asin in seen:
                    continue
                seen.add(asin)
                links.append(full.split("?")[0])
                if len(links) >= limit:
                    break

        return links[:limit]

    async def _scrape_product(self, browser: Browser, product_url: str, reviews_limit: int) -> Optional[ScrapedProduct]:
        # this function extracts one product page and related reviews
        page = await browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=self.settings.scraper_timeout_seconds * 1000)
            await asyncio.sleep(self.settings.scraper_delay_ms / 1000)
            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            asin = _extract_asin(product_url)
            if not asin:
                return None

            title = _clean_text((soup.select_one("#productTitle") or {}).get_text() if soup.select_one("#productTitle") else "")
            if not title:
                return None

            price_text = _clean_text((soup.select_one("span.a-price span.a-offscreen") or {}).get_text() if soup.select_one("span.a-price span.a-offscreen") else "")
            list_price_text = _clean_text((soup.select_one("span.a-price.a-text-price span.a-offscreen") or {}).get_text() if soup.select_one("span.a-price.a-text-price span.a-offscreen") else "")
            discount_text = _clean_text((soup.select_one("span.savingsPercentage") or {}).get_text() if soup.select_one("span.savingsPercentage") else "")

            rating_text = ""
            rating_node = soup.select_one("#acrPopover")
            if rating_node:
                rating_text = _clean_text(rating_node.get("title"))

            review_count_text = _clean_text((soup.select_one("#acrCustomerReviewText") or {}).get_text() if soup.select_one("#acrCustomerReviewText") else "")

            category = _clean_text(" > ".join([node.get_text(strip=True) for node in soup.select("#wayfinding-breadcrumbs_feature_div ul li a")]))
            size = _clean_text((soup.select_one("#variation_size_name .selection") or {}).get_text() if soup.select_one("#variation_size_name .selection") else "")

            price = _parse_price(price_text)
            list_price = _parse_price(list_price_text)

            product = ScrapedProduct(
                asin=asin,
                title=title,
                url=product_url.split("?")[0],
                category=category or None,
                size=size or None,
                price=price,
                list_price=list_price,
                discount_percent=_parse_discount(price, list_price, discount_text),
                rating=_parse_rating(rating_text),
                review_count=_parse_review_count(review_count_text),
                reviews=[],
            )

            product.reviews = await self._scrape_reviews(browser, asin, reviews_limit)
            return product
        finally:
            await page.close()

    async def _scrape_reviews(self, browser: Browser, asin: str, reviews_limit: int) -> list[ScrapedReview]:
        # this function scrapes paginated review pages for one asin
        collected: list[ScrapedReview] = []
        page_number = 1

        while len(collected) < reviews_limit and page_number <= 10:
            reviews_url = f"https://www.amazon.in/product-reviews/{asin}/?pageNumber={page_number}&sortBy=recent"
            page = await browser.new_page()
            try:
                await page.goto(reviews_url, wait_until="domcontentloaded", timeout=self.settings.scraper_timeout_seconds * 1000)
                await asyncio.sleep(self.settings.scraper_delay_ms / 1000)

                html = await page.content()
                soup = BeautifulSoup(html, "lxml")
                blocks = soup.select("div[data-hook='review']")
                if not blocks:
                    break

                for block in blocks:
                    review = self._parse_review_block(block)
                    if review:
                        collected.append(review)
                    if len(collected) >= reviews_limit:
                        break
            finally:
                await page.close()

            page_number += 1

        return collected[:reviews_limit]

    def _parse_review_block(self, block) -> Optional[ScrapedReview]:
        # this function parses one review dom block
        review_id = block.get("id")
        title = _clean_text(block.select_one("a[data-hook='review-title']").get_text(" ", strip=True) if block.select_one("a[data-hook='review-title']") else "")
        content = _clean_text(block.select_one("span[data-hook='review-body']").get_text(" ", strip=True) if block.select_one("span[data-hook='review-body']") else "")
        if not content:
            return None

        rating_text = _clean_text(block.select_one("i[data-hook='review-star-rating'] span").get_text() if block.select_one("i[data-hook='review-star-rating'] span") else "")
        date_text = _clean_text(block.select_one("span[data-hook='review-date']").get_text() if block.select_one("span[data-hook='review-date']") else "")
        vp_text = _clean_text(block.select_one("span[data-hook='avp-badge']").get_text() if block.select_one("span[data-hook='avp-badge']") else "")
        helpful_text = _clean_text(block.select_one("span[data-hook='helpful-vote-statement']").get_text() if block.select_one("span[data-hook='helpful-vote-statement']") else "")

        return ScrapedReview(
            review_id=review_id,
            title=title or None,
            content=content,
            rating=_parse_rating(rating_text),
            review_date=_parse_review_date(date_text),
            verified_purchase=True if "verified purchase" in vp_text.lower() else None,
            helpful_votes=_parse_helpful_votes(helpful_text),
            raw_payload={
                "rating_text": rating_text,
                "date_text": date_text,
                "verified_text": vp_text,
                "helpful_text": helpful_text,
            },
        )
