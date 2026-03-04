"""
Immigration news fetcher — Federal Register API + USCIS/DHS/NAFSA RSS.
Only official government and recognised organisation sources.
"""

import asyncio
from datetime import datetime, timezone, timedelta

import feedparser
import httpx

from database.supabase_client import (
    get_immigration_news,
    get_last_news_fetch_time,
    save_immigration_news,
)

OFFICIAL_DOMAINS = [
    "uscis.gov",
    "dhs.gov",
    "dol.gov",
    "federalregister.gov",
    "ice.gov",
    "travel.state.gov",
    "nafsa.org",
]

# FIX 4 — fallback URLs for each RSS source
USCIS_FEEDS = [
    "https://www.uscis.gov/feeds/all-news-and-updates",
    "https://www.uscis.gov/newsroom/news-releases/feed",
]
DHS_FEEDS = [
    "https://www.dhs.gov/rss.xml",
    "https://www.dhs.gov/news/rss.xml",
]
NAFSA_FEEDS = [
    "https://www.nafsa.org/rss.xml",
    "https://www.nafsa.org/about/about-nafsa/newsroom/rss",
]

# FIX 4 — user-agent header to avoid bot-blocking
RSS_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _is_official_url(url: str) -> bool:
    """Check if a URL belongs to one of the official domains."""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in OFFICIAL_DOMAINS)


def _make_news_dict(
    title: str,
    summary: str,
    url: str,
    source: str,
    category: str = "Policy",
    published_at: str = None,
) -> dict:
    """Create a standardised news article dict."""
    return {
        "title": (title or "")[:120],
        "summary": (summary or "")[:300],
        "url": url or "",
        "source": source,
        "category": category,
        "is_official": True,
        "published_at": published_at or datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),  # FIX 5
    }


# ─────────────────────────────────────────────────────────
# Federal Register API (async, 4 concurrent keyword searches)
# ─────────────────────────────────────────────────────────

async def _fetch_fr_keyword(client: httpx.AsyncClient, keyword: str) -> list:
    """Fetch articles from Federal Register for a single keyword."""
    try:
        resp = await client.get(
            "https://www.federalregister.gov/api/v1/articles",
            params={
                "conditions[term]": keyword,
                "order": "newest",
                "per_page": 5,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        articles = []
        for r in results:
            articles.append(
                _make_news_dict(
                    title=r.get("title", ""),
                    summary=r.get("abstract", ""),
                    url=r.get("html_url", ""),
                    source="Federal Register",
                    published_at=r.get("publication_date", ""),
                )
            )
        return articles
    except Exception as e:
        print(f"[fetch_federal_register] Error for '{keyword}': {e}")
        return []


async def fetch_federal_register() -> list:
    """Fetch immigration-related articles from the Federal Register API."""
    keywords = [
        "F-1 visa international student",
        "Optional Practical Training OPT",
        "H-1B specialty occupation cap",
        "STEM OPT extension",
    ]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tasks = [_fetch_fr_keyword(client, kw) for kw in keywords]
            batches = await asyncio.gather(*tasks, return_exceptions=True)

        articles = []
        seen_urls = set()
        for batch in batches:
            if isinstance(batch, list):
                for article in batch:
                    if article["url"] and article["url"] not in seen_urls:
                        seen_urls.add(article["url"])
                        articles.append(article)
        return articles
    except Exception as e:
        print(f"[fetch_federal_register] Error: {e}")
        return []


# ─────────────────────────────────────────────────────────
# RSS feeds (synchronous via feedparser)
# ─────────────────────────────────────────────────────────

def fetch_uscis_rss() -> list:
    """Fetch latest entries from USCIS RSS — tries primary then fallback URL."""
    for url in USCIS_FEEDS:                                          # FIX 4
        try:
            feed = feedparser.parse(url, request_headers=RSS_HEADERS)
            if not feed.entries:
                continue
            articles = []
            for entry in feed.entries[:5]:
                articles.append(
                    _make_news_dict(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", ""),
                        url=entry.get("link", ""),
                        source="USCIS",
                        published_at=entry.get("published", ""),
                    )
                )
            return articles
        except Exception as e:
            print(f"[fetch_uscis_rss] Error for {url}: {e}")
            continue
    return []


def fetch_dhs_rss() -> list:
    """Fetch latest entries from DHS RSS — tries primary then fallback URL."""
    for url in DHS_FEEDS:                                            # FIX 4
        try:
            feed = feedparser.parse(url, request_headers=RSS_HEADERS)
            if not feed.entries:
                continue
            articles = []
            for entry in feed.entries[:5]:
                articles.append(
                    _make_news_dict(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", ""),
                        url=entry.get("link", ""),
                        source="DHS",
                        published_at=entry.get("published", ""),
                    )
                )
            return articles
        except Exception as e:
            print(f"[fetch_dhs_rss] Error for {url}: {e}")
            continue
    return []


def fetch_nafsa_rss() -> list:
    """Fetch latest entries from NAFSA RSS — tries primary then fallback URL."""
    for url in NAFSA_FEEDS:                                          # FIX 4
        try:
            feed = feedparser.parse(url, request_headers=RSS_HEADERS)
            if not feed.entries:
                continue
            articles = []
            for entry in feed.entries[:5]:
                articles.append(
                    _make_news_dict(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", ""),
                        url=entry.get("link", ""),
                        source="NAFSA",
                        published_at=entry.get("published", ""),
                    )
                )
            return articles
        except Exception as e:
            print(f"[fetch_nafsa_rss] Error for {url}: {e}")
            continue
    return []


# ─────────────────────────────────────────────────────────
# Category detection
# ─────────────────────────────────────────────────────────

def detect_category(title: str) -> str:
    """Detect news category from the article title."""
    try:
        t = (title or "").lower()
        if "opt" in t or "practical training" in t:
            return "OPT"
        if "h-1b" in t or "h1b" in t:
            return "H1B"
        if "f-1" in t or "f1" in t or "student visa" in t:
            return "F-1"
        if "stem" in t:
            return "STEM OPT"
        return "Policy"
    except Exception:
        return "Policy"


# ─────────────────────────────────────────────────────────
# Main aggregator
# ─────────────────────────────────────────────────────────

def get_all_immigration_news() -> list:
    """
    Return immigration news from cache if fresh (< 6 hours),
    otherwise fetch from all sources, filter, save, and return.
    """
    try:
        last_fetch = get_last_news_fetch_time()
        now = datetime.now(timezone.utc)

        if last_fetch:
            # Make last_fetch timezone-aware if it isn't
            if last_fetch.tzinfo is None:
                last_fetch = last_fetch.replace(tzinfo=timezone.utc)
            if (now - last_fetch) < timedelta(hours=6):
                cached = get_immigration_news(limit=8)
                if cached:
                    return cached

        # Fetch from all sources
        # Federal Register is async; RSS feeds are sync
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    fr_articles = pool.submit(
                        asyncio.run, fetch_federal_register()
                    ).result()
            else:
                fr_articles = asyncio.run(fetch_federal_register())
        except RuntimeError:
            fr_articles = asyncio.run(fetch_federal_register())

        uscis_articles = fetch_uscis_rss()
        dhs_articles = fetch_dhs_rss()
        nafsa_articles = fetch_nafsa_rss()

        all_articles = fr_articles + uscis_articles + dhs_articles + nafsa_articles

        # Filter: only keep items whose URL contains an official domain
        filtered = [a for a in all_articles if _is_official_url(a.get("url", ""))]

        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for article in filtered:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                article["category"] = detect_category(article.get("title", ""))
                unique.append(article)

        # Sort by published_at desc
        unique.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True,
        )

        # FIX 3 — save failure no longer blocks returning freshly fetched articles
        if unique:
            try:
                save_immigration_news(unique)
            except Exception as e:
                print(f"[get_all_immigration_news] Cache save failed (RLS?): {e}")

        return unique[:8]

    except Exception as e:
        print(f"[get_all_immigration_news] Error: {e}")
        # Fall back to cached data
        try:
            return get_immigration_news(limit=8)
        except Exception:
            return []