# this file handles amazon scraping for products and reviews
import asyncio
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from playwright.async_api import Page, async_playwright

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
    parsed = urlparse(url)
    if parsed.query:
        query = parse_qs(parsed.query)
        encoded_url = query.get("url", [])
        if encoded_url:
            decoded = unquote(encoded_url[0])
            nested = _extract_asin(decoded)
            if nested:
                return nested

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
        search_urls = self._build_search_urls(brand_name)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.settings.scraper_headless)
            try:
                context = await browser.new_context(
                    locale="en-IN",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1366, "height": 768},
                )
                product_urls: list[str] = []
                products: list[ScrapedProduct] = []
                warnings: list[str] = []
                attempted_search_urls: list[dict] = []

                for search_url in search_urls:
                    page = await context.new_page()
                    try:
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=self.settings.scraper_timeout_seconds * 1000)
                        await asyncio.sleep(self.settings.scraper_delay_ms / 1000)

                        discovered_urls, discovery_info = await self._extract_product_urls(page, products_limit)
                        attempted_search_urls.append(
                            {
                                "search_url": search_url,
                                "discovered_count": len(discovered_urls),
                                "page_title": discovery_info.get("page_title"),
                                "blocked": discovery_info.get("blocked"),
                                "no_results": discovery_info.get("no_results"),
                            }
                        )

                        for url in discovered_urls:
                            if url not in product_urls:
                                product_urls.append(url)
                            if len(product_urls) >= products_limit:
                                break
                    finally:
                        await page.close()

                    if len(product_urls) >= products_limit:
                        break

                for product_url in product_urls:
                    try:
                        product = await self._scrape_product(context, product_url, reviews_limit)
                        if product:
                            products.append(product)
                    except Exception as exc:
                        logger.warning("product scrape failed for %s error %s", product_url, exc)

                    await asyncio.sleep(self.settings.scraper_delay_ms / 1000)

                if not product_urls:
                    warnings.append("no product links were found on amazon search pages for this run.")
                if products and all(len(item.reviews) == 0 for item in products):
                    warnings.append("no reviews captured from review pages. amazon may have blocked review endpoints for this run.")

                return {
                    "brand": brand_name,
                    "search_url": search_urls[0],
                    "attempted_search_urls": attempted_search_urls,
                    "products": [asdict(p) for p in products],
                    "warnings": warnings,
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            finally:
                await browser.close()

    def _build_search_urls(self, brand_name: str) -> list[str]:
        # this helper prepares multiple amazon search variants for resilience
        queries = [
            f"{brand_name} luggage",
            f"{brand_name} trolley bag",
            brand_name,
        ]
        urls = [
            f"https://www.amazon.in/s?k={quote_plus(queries[0])}&rh=n%3A1571271031",
            f"https://www.amazon.in/s?k={quote_plus(queries[1])}",
            f"https://www.amazon.in/s?k={quote_plus(queries[2])}",
        ]
        return urls

    async def _extract_product_urls(self, page: Page, limit: int) -> tuple[list[str], dict]:
        # this function extracts product links from search result page
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")
        page_title = await page.title()

        links: list[str] = []
        seen: set[str] = set()

        blocked = self._looks_blocked(html)
        no_results = "no results for" in html.lower()

        # this path uses the stable search result cards amazon renders with data-asin
        result_cards = soup.select("div[data-component-type='s-search-result'][data-asin]")
        for card in result_cards:
            asin = (card.get("data-asin") or "").strip()
            if not asin or asin in seen:
                continue

            link_node = card.select_one("h2 a")
            href = link_node.get("href") if link_node else None
            if href:
                full = href if href.startswith("http") else f"https://www.amazon.in{href}"
            else:
                full = f"https://www.amazon.in/dp/{asin}"

            normalized_url = full.split("?")[0]
            seen.add(asin)
            links.append(normalized_url)
            if len(links) >= limit:
                break

        if len(links) < limit:
            # this fallback keeps older selectors for pages that still use them
            for node in soup.select("a.a-link-normal.s-no-outline, a[href*='/dp/'], a[href*='/gp/product/']"):
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

        return links[:limit], {
            "page_title": page_title,
            "blocked": blocked,
            "no_results": no_results,
        }

    async def _scrape_product(self, context, product_url: str, reviews_limit: int) -> Optional[ScrapedProduct]:
        # this function extracts one product page and related reviews
        page = await context.new_page()
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

            seeded_reviews = self._extract_reviews_from_soup(soup, reviews_limit, product_url)
            product.reviews = await self._scrape_reviews(context, asin, reviews_limit, seeded_reviews=seeded_reviews)
            return product
        finally:
            await page.close()

    def _looks_blocked(self, html: str) -> bool:
        # this helper detects captcha or anti bot pages
        lowered = html.lower()
        blocked_tokens = ["enter the characters you see below", "sorry, we just need to make sure", "captcha"]
        return any(token in lowered for token in blocked_tokens)

    def _merge_reviews(self, reviews: list[ScrapedReview], limit: int) -> list[ScrapedReview]:
        # this helper keeps unique reviews and preserves original order
        unique: list[ScrapedReview] = []
        seen: set[str] = set()

        for review in reviews:
            review_key = review.review_id or f"{review.title or ''}|{review.content[:80]}"
            if review_key in seen:
                continue
            seen.add(review_key)
            unique.append(review)
            if len(unique) >= limit:
                break

        return unique

    def _extract_reviews_from_soup(self, soup: BeautifulSoup, limit: int, page_url: str) -> list[ScrapedReview]:
        # this helper parses review blocks already visible on product page
        blocks = soup.select("#cm-cr-dp-review-list li.review, #cm-cr-dp-review-list [data-hook='review']")
        reviews: list[ScrapedReview] = []
        for block in blocks:
            review = self._parse_review_block(block, page_url)
            if review:
                reviews.append(review)
            if len(reviews) >= limit:
                break
        return self._merge_reviews(reviews, limit)

    async def _scrape_reviews(
        self,
        context,
        asin: str,
        reviews_limit: int,
        seeded_reviews: Optional[list[ScrapedReview]] = None,
    ) -> list[ScrapedReview]:
        # this function scrapes paginated review pages for one asin
        collected: list[ScrapedReview] = list(seeded_reviews or [])
        page_number = 1

        if len(collected) >= reviews_limit:
            return self._merge_reviews(collected, reviews_limit)

        while len(collected) < reviews_limit and page_number <= 10:
            reviews_url = f"https://www.amazon.in/product-reviews/{asin}/?pageNumber={page_number}&sortBy=recent"
            page = await context.new_page()
            try:
                await page.goto(reviews_url, wait_until="domcontentloaded", timeout=self.settings.scraper_timeout_seconds * 1000)
                await asyncio.sleep(self.settings.scraper_delay_ms / 1000)

                html = await page.content()
                if self._looks_blocked(html):
                    logger.warning("review scrape blocked for asin %s page %s", asin, page_number)
                    break
                soup = BeautifulSoup(html, "lxml")
                blocks = soup.select("div[data-hook='review'], div.review")
                if not blocks:
                    break

                for block in blocks:
                    review = self._parse_review_block(block, reviews_url)
                    if review:
                        collected.append(review)
                    if len(self._merge_reviews(collected, reviews_limit)) >= reviews_limit:
                        break
            finally:
                await page.close()

            page_number += 1

        return self._merge_reviews(collected, reviews_limit)

    def _parse_review_block(self, block, reviews_url: str) -> Optional[ScrapedReview]:
        # this function parses one review dom block
        review_id = block.get("id")
        title_node = block.select_one("a[data-hook='review-title'], span[data-hook='review-title']")
        title = ""
        if title_node:
            title_parts = []
            for node in title_node.select("span"):
                text = _clean_text(node.get_text(" ", strip=True))
                if not text or "out of 5 stars" in text.lower():
                    continue
                title_parts.append(text)
            title = _clean_text(" ".join(title_parts)) or _clean_text(title_node.get_text(" ", strip=True))

        content_node = (
            block.select_one("[data-hook='review-collapsed']")
            or block.select_one(".review-text-content span")
            or block.select_one("span[data-hook='review-body']")
        )
        content = _clean_text(content_node.get_text(" ", strip=True) if content_node else "")
        if not content:
            return None

        rating_text = _clean_text(
            block.select_one("i[data-hook='review-star-rating'] span").get_text()
            if block.select_one("i[data-hook='review-star-rating'] span")
            else block.select_one("i[data-hook='cmps-review-star-rating'] span").get_text()
            if block.select_one("i[data-hook='cmps-review-star-rating'] span")
            else ""
        )
        date_text = _clean_text(block.select_one("span[data-hook='review-date']").get_text() if block.select_one("span[data-hook='review-date']") else "")
        vp_text = _clean_text(block.select_one("span[data-hook='avp-badge']").get_text() if block.select_one("span[data-hook='avp-badge']") else "")
        helpful_text = _clean_text(block.select_one("span[data-hook='helpful-vote-statement']").get_text() if block.select_one("span[data-hook='helpful-vote-statement']") else "")
        review_href = title_node.get("href") if title_node else None
        review_url = urljoin("https://www.amazon.in", review_href) if review_href else reviews_url

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
                "source_url": review_url,
                "reviews_page_url": reviews_url,
            },
        )
