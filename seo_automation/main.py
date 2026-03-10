"""
main.py — Pipeline orchestrator for the SEO/AEO content automation system.

Runs the full pipeline:
1. Fetch trending keywords (broad, then filter by relevance)
2. Deduplicate keywords
3. Expand keywords into long-tail queries
4. Cluster keywords into topics
5. Generate article blueprints
6. Generate full articles
7. Optimise for SEO/AEO
8. Insert internal links
9. Publish articles

CLI flags:
  --dry-run          Validate pipeline without external API calls
  --step <name>      Run only a specific step
  --limit <N>        Limit the number of articles to generate
  --skip-publish     Run everything except publishing
  --skip-scraping    Skip Playwright-based scraping
"""

import argparse
import logging
import sys
from typing import List

from .config import config
from .database import Database
from .trend_fetcher import fetch_trending_keywords
from .keyword_expander import expand_keywords
from .keyword_cluster import cluster_keywords
from .blueprint_generator import generate_blueprints
from .article_generator import generate_articles
from .seo_optimizer import optimize_articles
from .internal_linker import add_internal_links_batch
from .publisher import publish_articles
from .utils.deduplicator import deduplicate_keywords

# ── Logging setup ───────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seo_automation")


# ── Pipeline Steps ──────────────────────────────────────────

STEPS = [
    "trend_fetch",
    "expand",
    "cluster",
    "blueprint",
    "generate",
    "optimize",
    "link",
    "publish",
]


def run_pipeline(
    dry_run: bool = False,
    step: str = "",
    limit: int = 0,
    skip_publish: bool = False,
    skip_scraping: bool = False,
) -> None:
    """
    Execute the full SEO/AEO content pipeline.

    Args:
        dry_run:        If True, skip external API calls and use mock data.
        step:           If set, run only this specific step.
        limit:          Max number of articles to generate (0 = use config default).
        skip_publish:   Skip the publishing step.
        skip_scraping:  Skip Playwright-based scraping.
    """
    if not dry_run:
        errors = config.validate()
        if errors:
            for err in errors:
                logger.error("Config error: %s", err)
            logger.error("Fix configuration issues before running. See .env.example")
            sys.exit(1)

    max_articles = limit if limit > 0 else config.articles_per_day

    logger.info("=" * 60)
    logger.info("SEO/AEO Content Pipeline Starting")
    logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")
    logger.info("Article limit: %d", max_articles)
    logger.info("=" * 60)

    with Database() as db:
        should_run = lambda s: (not step) or (step == s)

        # ── Step 1: Fetch Trending Keywords ─────────────────
        if should_run("trend_fetch"):
            logger.info("━" * 50)
            logger.info("STEP 1: Fetching trending keywords...")

            if dry_run:
                raw_keywords = _mock_keywords()
                logger.info("[DRY RUN] Using %d mock keywords", len(raw_keywords))
            else:
                raw_keywords = fetch_trending_keywords(skip_scraping=skip_scraping)

            # Deduplicate against existing DB keywords
            existing = {kw["keyword"] for kw in db.get_all_keywords()}
            unique_keywords = deduplicate_keywords(raw_keywords, existing)

            inserted = db.save_keywords(unique_keywords)
            logger.info("Saved %d new keywords to database", inserted)

        # ── Step 2: Expand Keywords ─────────────────────────
        if should_run("expand"):
            logger.info("━" * 50)
            logger.info("STEP 2: Expanding keywords into long-tail queries...")

            unexpanded = db.get_unexpanded_keywords()
            if not unexpanded:
                logger.info("No unexpanded keywords found. Skipping.")
            else:
                if dry_run:
                    expanded = _mock_expanded(unexpanded)
                else:
                    expanded = expand_keywords(unexpanded)

                inserted = db.save_keywords(expanded)
                logger.info("Saved %d expanded keywords", inserted)

                # Mark originals as expanded
                db.mark_keywords_expanded([kw["id"] for kw in unexpanded])

        # ── Step 3: Cluster Keywords ────────────────────────
        if should_run("cluster"):
            logger.info("━" * 50)
            logger.info("STEP 3: Clustering keywords into topics...")

            all_keywords = db.get_all_keywords()
            unclustered = [kw for kw in all_keywords if not kw.get("cluster_id")]

            if not unclustered:
                logger.info("All keywords already clustered. Skipping.")
            else:
                if dry_run:
                    clusters = _mock_clusters(unclustered)
                else:
                    clusters = cluster_keywords(unclustered)

                for cluster in clusters:
                    cluster_id = db.save_cluster(cluster)
                    cluster["id"] = cluster_id

                logger.info("Created %d keyword clusters", len(clusters))

        # ── Step 4: Generate Blueprints ─────────────────────
        if should_run("blueprint"):
            logger.info("━" * 50)
            logger.info("STEP 4: Generating article blueprints...")

            all_clusters = db.get_all_clusters()
            # Only generate blueprints for clusters without existing blueprints
            existing_bp_cluster_ids = {
                bp["cluster_id"] for bp in db.get_all_blueprints()
            }
            new_clusters = [
                c for c in all_clusters if c["id"] not in existing_bp_cluster_ids
            ]

            if not new_clusters:
                logger.info("All clusters already have blueprints. Skipping.")
            else:
                new_clusters = new_clusters[:max_articles]

                if dry_run:
                    blueprints = _mock_blueprints(new_clusters)
                else:
                    blueprints = generate_blueprints(new_clusters)

                for bp in blueprints:
                    bp_id = db.save_blueprint(bp)
                    bp["id"] = bp_id

                logger.info("Created %d blueprints", len(blueprints))

        # ── Step 5: Generate Articles ───────────────────────
        if should_run("generate"):
            logger.info("━" * 50)
            logger.info("STEP 5: Generating articles...")

            pending_blueprints = db.get_blueprints_without_articles()
            pending_blueprints = pending_blueprints[:max_articles]

            if not pending_blueprints:
                logger.info("No pending blueprints. Skipping.")
            else:
                if dry_run:
                    articles = _mock_articles(pending_blueprints)
                else:
                    articles = generate_articles(pending_blueprints)

                for article in articles:
                    article_id = db.save_article(article)
                    article["id"] = article_id

                logger.info("Generated %d articles", len(articles))

        # ── Step 6: SEO/AEO Optimisation ────────────────────
        if should_run("optimize"):
            logger.info("━" * 50)
            logger.info("STEP 6: Optimising articles for SEO/AEO...")

            draft_articles = db.get_unpublished_articles()
            if not draft_articles:
                logger.info("No articles to optimise. Skipping.")
            else:
                all_blueprints = db.get_all_blueprints()
                optimised = optimize_articles(draft_articles, all_blueprints)

                for article in optimised:
                    if article.get("id"):
                        db.update_article(article["id"], {
                            "html_content": article.get("html_content", ""),
                            "schema_markup": article.get("schema_markup", {}),
                            "status": "optimized",
                        })

                logger.info("Optimised %d articles", len(optimised))

        # ── Step 7: Internal Linking ────────────────────────
        if should_run("link"):
            logger.info("━" * 50)
            logger.info("STEP 7: Adding internal links...")

            optimised_articles = [
                a for a in db.get_all_articles() if a.get("status") == "optimized"
            ]
            published_articles = db.get_published_articles()
            all_clusters = db.get_all_clusters()

            if not optimised_articles:
                logger.info("No articles to link. Skipping.")
            else:
                linked = add_internal_links_batch(
                    optimised_articles, published_articles, all_clusters,
                    site_url=config.wp_url,
                )

                for article in linked:
                    if article.get("id"):
                        db.update_article(article["id"], {
                            "html_content": article.get("html_content", ""),
                        })

                logger.info("Added internal links to %d articles", len(linked))

        # ── Step 8: Publish ─────────────────────────────────
        if should_run("publish") and not skip_publish:
            logger.info("━" * 50)
            logger.info("STEP 8: Publishing articles...")

            if dry_run:
                logger.info("[DRY RUN] Skipping actual publishing")
                ready = db.get_unpublished_articles()
                logger.info("[DRY RUN] %d articles would be published", len(ready))
            else:
                ready = db.get_unpublished_articles()
                if not ready:
                    logger.info("No articles ready for publishing. Skipping.")
                else:
                    result = publish_articles(ready, db=db)
                    logger.info(
                        "Published: %d | Failed: %d | Total: %d",
                        result["published"], result["failed"], result["total"],
                    )

    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info("=" * 60)


# ────────────────────────────────────────────────────────────
# Mock data for dry-run mode
# ────────────────────────────────────────────────────────────

def _mock_keywords() -> List[dict]:
    """Generate mock keywords for dry-run testing."""
    return [
        {"keyword": "upsc preparation strategy 2026", "source": "mock", "timestamp": ""},
        {"keyword": "ssc cgl exam pattern", "source": "mock", "timestamp": ""},
        {"keyword": "banking exam current affairs", "source": "mock", "timestamp": ""},
        {"keyword": "study tips for competitive exams", "source": "mock", "timestamp": ""},
        {"keyword": "how to improve reasoning ability", "source": "mock", "timestamp": ""},
        {"keyword": "government job interview preparation", "source": "mock", "timestamp": ""},
        {"keyword": "best mock test platforms india", "source": "mock", "timestamp": ""},
        {"keyword": "student productivity techniques", "source": "mock", "timestamp": ""},
    ]


def _mock_expanded(keywords: list) -> List[dict]:
    return [
        {"keyword": f"how to {kw['keyword']} for beginners", "source": "mock_expanded", "timestamp": ""}
        for kw in keywords[:5]
    ]


def _mock_clusters(keywords: list) -> List[dict]:
    return [{
        "cluster_name": "Exam Preparation Strategy",
        "primary_keyword": keywords[0]["keyword"] if keywords else "exam preparation",
        "supporting_keywords": [kw["keyword"] for kw in keywords[1:4]],
    }]


def _mock_blueprints(clusters: list) -> List[dict]:
    return [{
        "cluster_id": c.get("id", 0),
        "title": f"Complete Guide to {c['cluster_name']}",
        "slug": c["primary_keyword"].replace(" ", "-"),
        "meta_description": f"Learn everything about {c['primary_keyword']}.",
        "outline": [
            {"level": "h2", "text": f"What is {c['primary_keyword']}?"},
            {"level": "h2", "text": "Key Tips and Strategies"},
            {"level": "h2", "text": "FAQ"},
        ],
        "word_count": 1800,
        "faq_questions": [f"What is {c['primary_keyword']}?"],
        "semantic_keywords": c.get("supporting_keywords", []),
        "snippet_answers": [],
    } for c in clusters]


def _mock_articles(blueprints: list) -> List[dict]:
    return [{
        "blueprint_id": bp.get("id", 0),
        "title": bp["title"],
        "slug": bp["slug"],
        "content": f"# {bp['title']}\n\n[DRY RUN] Mock article content for testing.",
        "meta_description": bp.get("meta_description", ""),
        "status": "draft",
    } for bp in blueprints]


# ────────────────────────────────────────────────────────────
# CLI entry point
# ────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SEO/AEO Content Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate pipeline without external API calls",
    )
    parser.add_argument(
        "--step", type=str, choices=STEPS, default="",
        help="Run only a specific pipeline step",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Maximum number of articles to generate (0 = config default)",
    )
    parser.add_argument(
        "--skip-publish", action="store_true",
        help="Run everything except publishing",
    )
    parser.add_argument(
        "--skip-scraping", action="store_true",
        help="Skip Playwright-based scraping (faster, less keywords)",
    )

    args = parser.parse_args()

    run_pipeline(
        dry_run=args.dry_run,
        step=args.step,
        limit=args.limit,
        skip_publish=args.skip_publish,
        skip_scraping=args.skip_scraping,
    )


if __name__ == "__main__":
    main()
