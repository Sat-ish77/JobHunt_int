"""
Job fetcher — searches Greenhouse, Lever, JSearch, and Tavily concurrently.
All jobs are normalised to a standard dict and enriched with sponsorship data.
"""

import asyncio
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from tavily import TavilyClient

from utils.sponsorship_checker import check_sponsorship_history

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def _standard_job(
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    source: str,
    posted_at: str = "",
) -> dict:
    """Create a standard job dict.

    We intentionally keep this minimal; quality/tier labels are added later
    in :func:`search_all_jobs` once we know which source the job came from and
    whether the employer exists in the H1B CSV.  This keeps the individual
    fetchers simple and avoids duplication of sponsorship logic.
    """
    return {
        "title": (title or "")[:200],
        "company": (company or "")[:200],
        "location": (location or "")[:200],
        "description": (description or "")[:3000],
        "url": (url or ""),
        "source": source,
        "posted_at": posted_at or "",
        "h1b_sponsor_history": False,
        "h1b_approvals_count": 0,
        "opt_friendly": False,
        "cpt_friendly": False,
        "explicitly_sponsors": False,
        # tier_label and tier are set later
        "tier_label": "",
        "tier": 0,
    }


# ═══════════════════════════════════════════════════════════
# GREENHOUSE — dynamic board discovery
# ═══════════════════════════════════════════════════════════

async def _fetch_greenhouse_board(
    client: httpx.AsyncClient, token: str, role: str, location: str
) -> list:
    """Fetch jobs from a single Greenhouse board and filter by role/location."""
    try:
        resp = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
            params={"content": "true"},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs_list = data.get("jobs", [])
        role_lower = role.lower()
        location_lower = location.lower()
        results = []
        for j in jobs_list:
            title = j.get("title", "")
            loc = ""
            if j.get("location", {}).get("name"):
                loc = j["location"]["name"]
            # Filter by role keyword
            if role_lower not in title.lower():
                continue
            # Filter by location
            if location_lower and "remote" not in location_lower:
                if (
                    location_lower not in loc.lower()
                    and "remote" not in loc.lower()
                ):
                    continue
            desc_raw = j.get("content", "") or ""
            url = j.get("absolute_url", "")
            company_name = data.get("name", token)
            posted = j.get("updated_at", "")
            results.append(
                _standard_job(
                    title=title,
                    company=company_name,
                    location=loc,
                    description=desc_raw,
                    url=url,
                    source="greenhouse",
                    posted_at=posted,
                )
            )
        return results
    except Exception:
        return []


async def fetch_greenhouse_all(role: str, location: str) -> list:
    """Discover all Greenhouse boards and fetch matching jobs concurrently."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Step 1: get all boards
            resp = await client.get(
                "https://boards-api.greenhouse.io/v1/boards"
            )
            if resp.status_code != 200:
                return []
            boards = resp.json()
            # boards can be a list or dict with key
            if isinstance(boards, dict):
                boards = boards.get("boards", boards.get("data", []))
            if not isinstance(boards, list):
                return []

            # Cap at 300 companies to avoid timeout
            tokens = []
            for b in boards[:300]:
                token = b.get("token") or b.get("id") or b.get("slug")
                if token:
                    tokens.append(str(token))

            # Step 2: concurrently fetch jobs from each board
            tasks = [
                _fetch_greenhouse_board(client, token, role, location)
                for token in tokens
            ]
            batches = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for batch in batches:
            if isinstance(batch, list):
                all_jobs.extend(batch)
        return all_jobs
    except Exception as e:
        print(f"[fetch_greenhouse_all] Error: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# LEVER — known company slugs
# ═══════════════════════════════════════════════════════════

LEVER_SLUGS = [
    "netflix", "dropbox", "spotify", "twilio", "segment",
    "intercom", "airtable", "benchling", "carta", "figma",
    "notion", "linear", "vercel", "ramp", "brex", "plaid",
    "gusto", "mercury", "anthropic", "openai", "cohere",
    "scale-ai", "huggingface", "mistral",
]


async def _fetch_lever_company(
    client: httpx.AsyncClient, slug: str, role: str, location: str
) -> list:
    """Fetch jobs from a single Lever company page."""
    try:
        resp = await client.get(
            f"https://api.lever.co/v0/postings/{slug}",
            params={"mode": "json"},
        )
        if resp.status_code != 200:
            return []
        postings = resp.json()
        if not isinstance(postings, list):
            return []
        role_lower = role.lower()
        location_lower = location.lower()
        results = []
        for p in postings:
            title = p.get("text", "")
            categories = p.get("categories", {})
            loc = categories.get("location", "") or ""
            if role_lower not in title.lower():
                continue
            if location_lower and "remote" not in location_lower:
                if (
                    location_lower not in loc.lower()
                    and "remote" not in loc.lower()
                ):
                    continue
            desc_plain = p.get("descriptionPlain", "") or ""
            lists_text = ""
            for lst in p.get("lists", []):
                lists_text += lst.get("text", "") + " "
                lists_text += " ".join(
                    item.get("text", "") for item in lst.get("content", "")
                    if isinstance(item, dict)
                ) + " "
            full_desc = (desc_plain + " " + lists_text).strip()
            url = p.get("hostedUrl", "") or p.get("applyUrl", "")
            company = slug.replace("-", " ").title()
            posted = p.get("createdAt", "")
            if isinstance(posted, int):
                posted = datetime.fromtimestamp(
                    posted / 1000, tz=timezone.utc
                ).isoformat()
            results.append(
                _standard_job(
                    title=title,
                    company=company,
                    location=loc,
                    description=full_desc,
                    url=url,
                    source="lever",
                    posted_at=str(posted),
                )
            )
        return results
    except Exception:
        return []


async def fetch_lever_all(role: str, location: str) -> list:
    """Fetch matching jobs from all known Lever company pages."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tasks = [
                _fetch_lever_company(client, slug, role, location)
                for slug in LEVER_SLUGS
            ]
            batches = await asyncio.gather(*tasks, return_exceptions=True)
        all_jobs = []
        for batch in batches:
            if isinstance(batch, list):
                all_jobs.extend(batch)
        return all_jobs
    except Exception as e:
        print(f"[fetch_lever_all] Error: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# JSEARCH via RapidAPI
# ═══════════════════════════════════════════════════════════

async def fetch_jsearch(role: str, location: str) -> list:
    """Fetch jobs from JSearch API via RapidAPI."""
    try:
        if not RAPIDAPI_KEY:
            print("[fetch_jsearch] RAPIDAPI_KEY not set, skipping.")
            return []
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
                params={
                    "query": f"{role} in {location}",
                    "num_pages": "3",
                    "date_posted": "week",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        jobs_data = data.get("data", [])
        results = []
        for j in jobs_data:
            results.append(
                _standard_job(
                    title=j.get("job_title", ""),
                    company=j.get("employer_name", ""),
                    location=(
                        f"{j.get('job_city', '')}, "
                        f"{j.get('job_state', '')}"
                    ).strip(", "),
                    description=j.get("job_description", ""),
                    url=j.get("job_apply_link", "")
                       or j.get("job_google_link", ""),
                    source="jsearch",
                    posted_at=j.get("job_posted_at_datetime_utc", ""),
                )
            )
        return results
    except Exception as e:
        print(f"[fetch_jsearch] Error: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# TAVILY AI search (sync)
# ═══════════════════════════════════════════════════════════

def fetch_tavily_jobs(role: str, location: str) -> list:
    """Fetch jobs using Tavily AI search across career sites."""
    try:
        if not TAVILY_API_KEY:
            print("[fetch_tavily_jobs] TAVILY_API_KEY not set, skipping.")
            return []
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        queries = [
            f"{role} jobs {location} site:myworkdayjobs.com",
            f"{role} internship {location} site:jobs.ashbyhq.com",
            f"{role} {location} hiring 2025 careers",
        ]
        results = []
        seen_urls = set()
        for query in queries:
            try:
                resp = tavily.search(
                    query=query,
                    max_results=5,
                    search_depth="advanced",
                )
                for r in resp.get("results", []):
                    url = r.get("url", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    results.append(
                        _standard_job(
                            title=r.get("title", ""),
                            company=_extract_company_from_url(url),
                            location=location,
                            description=r.get("content", ""),
                            url=url,
                            source="tavily",
                        )
                    )
            except Exception as e:
                print(f"[fetch_tavily_jobs] Query error: {e}")
                continue
        return results
    except Exception as e:
        print(f"[fetch_tavily_jobs] Error: {e}")
        return []


def _extract_company_from_url(url: str) -> str:
    """Try to extract a company name from a job URL."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        # Remove www. and common suffixes
        domain = domain.replace("www.", "")
        parts = domain.split(".")
        if parts:
            name = parts[0]
            # Clean up common job board prefixes
            for prefix in ["jobs-", "careers-", "jobs.", "careers."]:
                name = name.replace(prefix, "")
            return name.replace("-", " ").title()
        return ""
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════
# Sponsorship detection
# ═══════════════════════════════════════════════════════════

def check_explicitly_sponsors(description: str) -> bool:
    """Check if a job description explicitly mentions sponsorship."""
    try:
        description_lower = (description or "").lower()
        keywords = [
            "sponsor", "h1b", "h-1b", "opt",
            "visa", "work authorization", "will sponsor",
        ]
        return any(kw in description_lower for kw in keywords)
    except Exception:
        return False


def assign_tier(job: dict) -> dict:
    """Compute ``tier`` and ``tier_label`` for a single job dict.

    This encapsulates the tier logic so that both :func:`search_all_jobs` and
    any other consumer (e.g. the UI) can call it and stay in sync.
    The function mutates the input dict and also returns it for convenience.
    """
    src = job.get("source", "").lower()
    # make sure sponsorship status is known; the caller may have already set it
    from utils.sponsorship_checker import check_sponsorship_history

    if src in ("greenhouse", "lever"):
        job["tier_label"] = "✅ Verified"
        job["tier"] = 1
    else:
        # if not already computed, run the H1B lookup now
        if not job.get("h1b_sponsor_history"):
            sponsor = check_sponsorship_history(job.get("company", ""))
            job["h1b_sponsor_history"] = sponsor.get("has_history", False)
            job["h1b_approvals_count"] = sponsor.get("approvals", 0)
        if job.get("h1b_sponsor_history"):
            job["tier_label"] = "⚪ H1B Verified Company"
            job["tier"] = 2
        else:
            job["tier_label"] = "⚠️ Unverified"
            job["tier"] = 3
    return job


# ═══════════════════════════════════════════════════════════
# MAIN AGGREGATOR
# ═══════════════════════════════════════════════════════════

def search_all_jobs(role: str, location: str) -> list:
    """
    Search all job sources concurrently, combine, deduplicate,
    and enrich with sponsorship data.

    This function also applies the "tiered" quality scheme requested by the
    `Friend 1 Task` design note:

    * **Tier 1** – Jobs discovered via the Greenhouse or Lever public APIs.  These
      are labelled ``✅ Verified`` since they come directly from employer
      career pages and are guaranteed to be live.
    * **Tier 2** – Jobs from the RapidAPI/JSearch or Tavily engines where the
      company name can be found in the H1B sponsor CSV.  These are marked
      ``⚪ H1B Verified Company``.
    * **Tier 3** – Any remaining jobs from those sources that do not match the
      CSV, labelled ``⚠️ Unverified``.

    The CSV cross‑check is performed using ``check_sponsorship_history`` and
    its result is stored in the job dict as ``h1b_sponsor_history`` and
    ``tier_label``.  Downstream code in ``app.py`` reads ``tier_label`` when
    rendering each job.
    """
    try:
        # 1. Run async sources concurrently
        async def _run_async():
            return await asyncio.gather(
                fetch_greenhouse_all(role, location),
                fetch_lever_all(role, location),
                fetch_jsearch(role, location),
                return_exceptions=True,
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    async_results = pool.submit(
                        asyncio.run, _run_async()
                    ).result()
            else:
                async_results = asyncio.run(_run_async())
        except RuntimeError:
            async_results = asyncio.run(_run_async())

        all_jobs = []
        for batch in async_results:
            if isinstance(batch, list):
                all_jobs.extend(batch)

        # 2. Run Tavily (sync)
        tavily_jobs = fetch_tavily_jobs(role, location)
        all_jobs.extend(tavily_jobs)

        # 3. Deduplicate by URL (keep first occurrence)
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            url = job.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            unique_jobs.append(job)

        # 4. Enrich with sponsorship data
        for job in unique_jobs:
            company = job.get("company", "")
            if company:
                sponsorship = check_sponsorship_history(company)
                job["h1b_sponsor_history"] = sponsorship["has_history"]
                job["h1b_approvals_count"] = sponsorship["approvals"]
            # record whether the description itself mentions sponsorship
            job["explicitly_sponsors"] = check_explicitly_sponsors(
                job.get("description", "")
            )

            # delegate tier/label assignment to helper
            assign_tier(job)

        return unique_jobs

    except Exception as e:
        print(f"[search_all_jobs] Error: {e}")
        return []

