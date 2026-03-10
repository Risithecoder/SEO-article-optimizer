"""
trend_fetcher.py — Fetch trending keywords from multiple sources.

Discovers broadly trending keywords from Google Trends, Google Autocomplete,
People Also Ask, Related Searches, and Reddit. Then filters them by
relevance to Oliveboard's domain (exams, career, study, etc.).

Returns structured data: keyword, source, timestamp.
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import quote_plus

import requests

from .config import config
from .utils.openai_client import chat_completion_json

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Source: Google Trends (via pytrends)
# ────────────────────────────────────────────────────────────

def fetch_google_trends() -> List[Dict[str, str]]:
    """
    Fetch trending searches from Google Trends (India).
    Uses the pytrends library for daily trending searches.
    """
    results: List[Dict[str, str]] = []
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl=config.trends_language, tz=330)

        # Daily trending searches (broad, not exam-specific)
        trending = pytrends.trending_searches(pn=config.trends_region)
        for keyword in trending[0].tolist():
            results.append({
                "keyword": keyword.strip(),
                "source": "google_trends",
                "timestamp": _now(),
            })

        # Also fetch related queries for each seed keyword
        for seed in config.seed_keywords[:5]:  # limit to avoid rate limits
            try:
                pytrends.build_payload([seed], cat=0, timeframe="now 7-d", geo="IN")
                related = pytrends.related_queries()
                if seed in related and related[seed]["rising"] is not None:
                    for _, row in related[seed]["rising"].iterrows():
                        results.append({
                            "keyword": row["query"].strip(),
                            "source": "google_trends_related",
                            "timestamp": _now(),
                        })
                time.sleep(1)  # rate limit
            except Exception as exc:
                logger.warning("Trends related query failed for '%s': %s", seed, exc)

    except ImportError:
        logger.warning("pytrends not installed — skipping Google Trends")
    except Exception as exc:
        logger.error("Google Trends fetch failed: %s", exc)

    logger.info("Google Trends: fetched %d keywords", len(results))
    return results


# ────────────────────────────────────────────────────────────
# Source: Google Autocomplete
# ────────────────────────────────────────────────────────────

def fetch_google_autocomplete() -> List[Dict[str, str]]:
    """
    Fetch autocomplete suggestions from Google for seed keywords.
    Uses the undocumented suggestqueries API.
    """
    results: List[Dict[str, str]] = []
    base_url = "http://suggestqueries.google.com/complete/search"

    for seed in config.seed_keywords:
        try:
            params = {
                "client": "firefox",
                "q": seed,
                "hl": "en",
                "gl": "in",
            }
            resp = requests.get(base_url, params=params, timeout=10)
            if resp.status_code == 200:
                suggestions = resp.json()
                if len(suggestions) > 1 and isinstance(suggestions[1], list):
                    for suggestion in suggestions[1]:
                        results.append({
                            "keyword": suggestion.strip(),
                            "source": "google_autocomplete",
                            "timestamp": _now(),
                        })
            time.sleep(0.5)
        except Exception as exc:
            logger.warning("Autocomplete failed for '%s': %s", seed, exc)

    logger.info("Google Autocomplete: fetched %d keywords", len(results))
    return results


# ────────────────────────────────────────────────────────────
# Source: People Also Ask (via Playwright)
# ────────────────────────────────────────────────────────────

def fetch_people_also_ask() -> List[Dict[str, str]]:
    """
    Scrape People Also Ask boxes from Google Search using Playwright.
    Searches a subset of seed keywords.
    """
    results: List[Dict[str, str]] = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            for seed in config.seed_keywords[:8]:
                try:
                    url = f"https://www.google.com/search?q={quote_plus(seed)}&hl=en&gl=in"
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)

                    # PAA questions
                    paa_elements = page.query_selector_all(
                        'div[data-sgrd] span, div.related-question-pair span'
                    )
                    for el in paa_elements:
                        text = el.inner_text().strip()
                        if text and "?" in text and len(text) > 10:
                            results.append({
                                "keyword": text,
                                "source": "people_also_ask",
                                "timestamp": _now(),
                            })

                    # Related searches
                    related_elements = page.query_selector_all(
                        'div.s75CSd a, div#brs a'
                    )
                    for el in related_elements:
                        text = el.inner_text().strip()
                        if text and len(text) > 3:
                            results.append({
                                "keyword": text,
                                "source": "google_related_searches",
                                "timestamp": _now(),
                            })

                    time.sleep(1)
                except Exception as exc:
                    logger.warning("PAA scrape failed for '%s': %s", seed, exc)

            browser.close()

    except ImportError:
        logger.warning("Playwright not installed — skipping PAA scraping")
    except Exception as exc:
        logger.error("PAA fetch failed: %s", exc)

    logger.info("People Also Ask / Related: fetched %d keywords", len(results))
    return results


# ────────────────────────────────────────────────────────────
# Source: Reddit
# ────────────────────────────────────────────────────────────

def fetch_reddit_keywords() -> List[Dict[str, str]]:
    """
    Fetch hot post titles from relevant subreddits via Reddit JSON API.
    """
    results: List[Dict[str, str]] = []

    headers = {"User-Agent": config.reddit_user_agent}

    for subreddit in config.reddit_subreddits:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    title = post["data"]["title"].strip()
                    if len(title) > 10:
                        results.append({
                            "keyword": title,
                            "source": f"reddit_r/{subreddit}",
                            "timestamp": _now(),
                        })
            time.sleep(1)
        except Exception as exc:
            logger.warning("Reddit fetch failed for r/%s: %s", subreddit, exc)

    logger.info("Reddit: fetched %d keywords", len(results))
    return results


# ────────────────────────────────────────────────────────────
# Relevance Filter (uses OpenAI)
# ────────────────────────────────────────────────────────────

def filter_relevant_keywords(keywords: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Filter a list of broadly-fetched keywords by relevance to
    Oliveboard's domain using OpenAI. Processes in batches.

    Relevant domains include: competitive exams, government job preparation,
    study techniques, career guidance, learning productivity, exam notifications,
    current affairs, interview preparation, mock tests, skill building,
    student productivity.
    """
    if not keywords:
        return []

    domains_str = ", ".join(config.relevant_domains)
    batch_size = 50
    relevant: List[Dict[str, str]] = []

    for i in range(0, len(keywords), batch_size):
        batch = keywords[i : i + batch_size]
        keyword_list = [kw["keyword"] for kw in batch]

        system_prompt = (
            "You are a keyword relevance classifier for an education platform "
            "(Oliveboard) that covers competitive exams, government job preparation, "
            "study techniques, career guidance, and related educational topics.\n\n"
            "Given a list of keywords, return ONLY the keywords that are relevant to "
            "the following domains:\n"
            f"{domains_str}\n\n"
            "Be inclusive — if a keyword could reasonably be useful to students "
            "preparing for exams or building careers, include it.\n\n"
            "Return your answer as a JSON object with a single key 'relevant' "
            "containing a list of the relevant keyword strings."
        )

        user_prompt = f"Keywords to classify:\n{json.dumps(keyword_list, indent=2)}"

        try:
            result = chat_completion_json(system_prompt, user_prompt)
            relevant_keywords = result.get("relevant", [])

            # Map back to the original dicts
            relevant_set = {kw.lower().strip() for kw in relevant_keywords}
            for kw_dict in batch:
                if kw_dict["keyword"].lower().strip() in relevant_set:
                    relevant.append(kw_dict)

        except Exception as exc:
            logger.error("Relevance filtering failed for batch %d: %s", i, exc)
            # On failure, include all — better to have noise than miss keywords
            relevant.extend(batch)

    logger.info(
        "Relevance filter: %d input → %d relevant",
        len(keywords), len(relevant),
    )
    return relevant


# ────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────

def fetch_trending_keywords(skip_scraping: bool = False) -> List[Dict[str, str]]:
    """
    Fetch trending keywords from all sources, then filter by domain relevance.

    Args:
        skip_scraping: If True, skip Playwright-based scraping (for dry-run mode).

    Returns:
        List of relevant keyword dicts with 'keyword', 'source', 'timestamp'.
    """
    all_keywords: List[Dict[str, str]] = []

    # Fetch from all sources
    logger.info("Fetching from Google Trends...")
    all_keywords.extend(fetch_google_trends())

    logger.info("Fetching from Google Autocomplete...")
    all_keywords.extend(fetch_google_autocomplete())

    if not skip_scraping:
        logger.info("Fetching from People Also Ask & Related Searches...")
        all_keywords.extend(fetch_people_also_ask())

    logger.info("Fetching from Reddit...")
    all_keywords.extend(fetch_reddit_keywords())

    logger.info("Total raw keywords fetched: %d", len(all_keywords))

    # Filter by relevance to Oliveboard's domain
    relevant_keywords = filter_relevant_keywords(all_keywords)

    return relevant_keywords


# ── Helpers ─────────────────────────────────────────────────

def _now() -> str:
    """Current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()
