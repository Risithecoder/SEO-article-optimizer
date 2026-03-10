"""
publisher.py — WordPress REST API publisher.

Publishes articles to WordPress via the WP REST API, supporting
title, slug, HTML content (with schema markup), excerpt, and
status (draft or publish). Logs results to the database.
"""

import json
import logging
from typing import Any, Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

from .config import config

logger = logging.getLogger(__name__)


def publish_article(
    article: Dict[str, Any],
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Publish a single article to WordPress.

    Args:
        article: Article dict with title, slug, html_content,
                 meta_description, schema_markup.
        status:  Override publish status ('draft' or 'publish').

    Returns:
        Result dict with 'success', 'post_id', 'url', 'error'.
    """
    wp_url = config.wp_url.rstrip("/")
    endpoint = f"{wp_url}/wp-json/wp/v2/posts"
    publish_status = status or config.wp_publish_status

    # Build the post payload
    html_content = article.get("html_content", article.get("content", ""))

    payload = {
        "title": article.get("title", ""),
        "slug": article.get("slug", ""),
        "content": html_content,
        "excerpt": article.get("meta_description", ""),
        "status": publish_status,
    }

    # Add Yoast SEO meta if available (via custom fields)
    meta_fields = {}
    if article.get("meta_description"):
        meta_fields["_yoast_wpseo_metadesc"] = article["meta_description"]
    if article.get("title"):
        meta_fields["_yoast_wpseo_title"] = article["title"]
    if meta_fields:
        payload["meta"] = meta_fields

    try:
        response = requests.post(
            endpoint,
            json=payload,
            auth=HTTPBasicAuth(config.wp_username, config.wp_app_password),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code in (200, 201):
            data = response.json()
            result = {
                "success": True,
                "post_id": data.get("id"),
                "url": data.get("link", ""),
                "error": "",
            }
            logger.info(
                "Published '%s' → %s (ID: %s)",
                article.get("title"), result["url"], result["post_id"],
            )
            return result
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
            logger.error("Publish failed for '%s': %s", article.get("title"), error_msg)
            return {
                "success": False,
                "post_id": None,
                "url": "",
                "error": error_msg,
            }

    except requests.exceptions.Timeout:
        error_msg = "Request timed out"
        logger.error("Publish timeout for '%s'", article.get("title"))
        return {"success": False, "post_id": None, "url": "", "error": error_msg}

    except requests.exceptions.ConnectionError as exc:
        error_msg = f"Connection error: {exc}"
        logger.error("Publish connection error for '%s': %s", article.get("title"), exc)
        return {"success": False, "post_id": None, "url": "", "error": error_msg}

    except Exception as exc:
        error_msg = f"Unexpected error: {exc}"
        logger.error("Publish error for '%s': %s", article.get("title"), exc)
        return {"success": False, "post_id": None, "url": "", "error": error_msg}


def publish_articles(
    articles: list,
    db=None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Publish a batch of articles to WordPress.

    Args:
        articles: List of article dicts.
        db:       Optional Database instance for logging.
        status:   Override publish status.

    Returns:
        Summary dict with 'published', 'failed', 'results'.
    """
    published = 0
    failed = 0
    results = []

    for article in articles:
        result = publish_article(article, status=status)
        results.append(result)

        article_id = article.get("id")

        if result["success"]:
            published += 1
            # Update article in DB if db is provided
            if db and article_id:
                db.update_article(article_id, {
                    "status": "published",
                    "published_url": result["url"],
                })
                db.log_publish(article_id, "success", json.dumps(result))
        else:
            failed += 1
            if db and article_id:
                db.log_publish(article_id, "failed", result["error"])

    summary = {
        "published": published,
        "failed": failed,
        "total": len(articles),
        "results": results,
    }

    logger.info(
        "Publishing complete: %d published, %d failed, %d total",
        published, failed, len(articles),
    )
    return summary
