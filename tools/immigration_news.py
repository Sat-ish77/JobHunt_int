"""
Immigration news fetcher — Federal Register API + USCIS/DHS/NAFSA RSS.
Only official government and recognised organisation sources.
Filters for F-1 / OPT / STEM / H-1B relevance only.
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

# ── Relevance filter keywords ──────────────────────────────
# An article must contain at least one of these in title OR summary
# to be considered relevant to international students.
RELEVANCE_KEYWORDS = [
    "f-1", "f1 visa", "f-1 visa",
    "opt", "optional practical training",
    "stem opt", "stem extension",
    "h-1b", "h1b", "h-1b cap", "specialty occupation",
    "cpt", "curricular practical training",
    "international student", "foreign student",
    "student visa", "nonimmigrant student",
    "work authorization", "employment authorization",
    "i-20", "sevis", "cap-gap",
    "grace period", "post-completion",
    "nafsa", "designated school official", "dso",
    "visa rule", "visa policy", "immigration rule",
    "uscis update", "dhs update",
]

# RSS fallback URLs
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

RSS_HEADERS = {"User-Agent": "Mozilla/5.0"}


# ── Helpers ────────────────────────────────────────────────

def _is_official_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in OFFICIAL_DOMAINS)


def _is_relevant(article: dict) -> bool:
    """
    Return True only if the article is relevant to F-1/OPT/H-1B/STEM students.
    Checks title + summary for any relevance keyword.
    DHS and Federal Register publish a lot of unrelated content —
    this filter drops everything that has no student-visa signal.
    """
    text = (
        (article.get("title") or "") + " " +
        (article.get("summary") or "")
    ).lower()
    return any(kw in text for kw in RELEVANCE_KEYWORDS)


def _make_news_dict(
    title: str,
    summary: str,
    url: str,
    source: str,
    category: str = "Policy",
    published_at: str = None,
) -> dict:
    return {
        "title": (title or "")[:120],
        "summary": (summary or "")[:300],
        "url": url or "",
        "source": source,
        "category": category,
        "is_official": True,
        "published_at": published_at or datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Federal Register API ───────────────────────────────────

async def _fetch_fr_keyword(client: httpx.AsyncClient, keyword: str) -> list:
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
        articles = []
        for r in data.get("results", []):
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
    # Use highly specific F-1/OPT/H-1B keywords so Federal Register
    # results are already pre-filtered at the API level.
    keywords = [
        "F-1 visa international student OPT",
        "Optional Practical Training STEM extension",
        "H-1B specialty occupation cap rule",
        "SEVIS student visa nonimmigrant",
    ]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            batches = await asyncio.gather(
                *[_fetch_fr_keyword(client, kw) for kw in keywords],
                return_exceptions=True,
            )
        articles, seen = [], set()
        for batch in batches:
            if isinstance(batch, list):
                for a in batch:
                    if a["url"] and a["url"] not in seen:
                        seen.add(a["url"])
                        articles.append(a)
        return articles
    except Exception as e:
        print(f"[fetch_federal_register] Error: {e}")
        return []


# ── RSS feeds ──────────────────────────────────────────────

def _parse_rss(feed_urls: list, source: str) -> list:
    """Try each URL in feed_urls until one returns entries."""
    for url in feed_urls:
        try:
            feed = feedparser.parse(url, request_headers=RSS_HEADERS)
            if not feed.entries:
                continue
            articles = []
            for entry in feed.entries[:10]:  # fetch more, filter later
                articles.append(
                    _make_news_dict(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", ""),
                        url=entry.get("link", ""),
                        source=source,
                        published_at=entry.get("published", ""),
                    )
                )
            return articles
        except Exception as e:
            print(f"[_parse_rss] Error for {url}: {e}")
            continue
    return []


def fetch_uscis_rss() -> list:
    return _parse_rss(USCIS_FEEDS, "USCIS")


def fetch_dhs_rss() -> list:
    # DHS publishes everything — coast guard, drug codes, personnel.
    # We fetch more entries and rely on _is_relevant() to filter.
    return _parse_rss(DHS_FEEDS, "DHS")


def fetch_nafsa_rss() -> list:
    return _parse_rss(NAFSA_FEEDS, "NAFSA")


# ── Category detection ─────────────────────────────────────

def detect_category(title: str) -> str:
    t = (title or "").lower()
    if "stem" in t:
        return "STEM OPT"
    if "opt" in t or "practical training" in t:
        return "OPT"
    if "h-1b" in t or "h1b" in t:
        return "H1B"
    if "f-1" in t or "f1" in t or "student visa" in t or "sevis" in t:
        return "F-1"
    if "cpt" in t or "curricular" in t:
        return "CPT"
    return "Policy"


# ── Main aggregator ────────────────────────────────────────

def get_all_immigration_news() -> list:
    """
    Return immigration news relevant to F-1/OPT/H-1B students.
    Uses 6-hour Supabase cache to avoid hammering RSS feeds.
    """
    try:
        last_fetch = get_last_news_fetch_time()
        now = datetime.now(timezone.utc)

        if last_fetch:
            if last_fetch.tzinfo is None:
                last_fetch = last_fetch.replace(tzinfo=timezone.utc)
            if (now - last_fetch) < timedelta(hours=6):
                cached = get_immigration_news(limit=8)
                if cached:
                    return cached

        # Fetch from all sources
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

        all_articles = (
            fr_articles
            + fetch_uscis_rss()
            + fetch_dhs_rss()
            + fetch_nafsa_rss()
        )

        # Step 1: Official domain filter
        official = [a for a in all_articles if _is_official_url(a.get("url", ""))]

        # Step 2: Relevance filter — F-1/OPT/H-1B/STEM signal required
        relevant = [a for a in official if _is_relevant(a)]

        # Step 3: Deduplicate by URL
        seen, unique = set(), []
        for article in relevant:
            url = article.get("url", "")
            if url and url not in seen:
                seen.add(url)
                article["category"] = detect_category(article.get("title", ""))
                unique.append(article)

        # Step 4: Sort newest first
        unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        # Step 5: Cache to Supabase (non-blocking on failure)
        if unique:
            try:
                save_immigration_news(unique)
            except Exception as e:
                print(f"[get_all_immigration_news] Cache save failed: {e}")

        # Fallback: if nothing relevant found, return cached
        if not unique:
            print("[get_all_immigration_news] No relevant articles found, using cache.")
            try:
                return get_immigration_news(limit=8)
            except Exception:
                return []

        return unique[:8]

    except Exception as e:
        print(f"[get_all_immigration_news] Error: {e}")
        try:
            return get_immigration_news(limit=8)
        except Exception:
            return []