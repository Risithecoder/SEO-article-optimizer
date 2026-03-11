"""
blueprint_generator.py — Generate structured article blueprints.

Creates detailed blueprints for each keyword cluster, including
SEO title, slug, meta description, article outline, FAQ questions,
semantic keywords, and featured snippet candidate answers.
"""

import concurrent.futures
import json
import logging
import re
from typing import Any, Dict, List

from .config import config
from .utils.openai_client import chat_completion_json

logger = logging.getLogger(__name__)


def generate_blueprint(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an article blueprint from a keyword cluster.

    Args:
        cluster: Dict with 'id', 'cluster_name', 'primary_keyword',
                 and 'supporting_keywords'.

    Returns:
        Blueprint dict with:
        - cluster_id, title, slug, meta_description
        - outline (list of H1/H2/H3 headings)
        - word_count
        - faq_questions (list of strings)
        - semantic_keywords (list of strings)
        - snippet_answers (list of dicts with 'question' and 'answer')
    """
    supporting = ", ".join(cluster.get("supporting_keywords", []))

    system_prompt = (
        "You are an expert SEO content strategist for an Indian exam preparation "
        "platform (Oliveboard). Your job is to create detailed article blueprints "
        "that rank well in Google search, AI Overviews, and answer engines.\n\n"
        "Create a comprehensive article blueprint for the given keyword cluster.\n\n"
        "Return a JSON object with these fields:\n"
        "- title: SEO-optimized article title (50–65 characters)\n"
        "- slug: URL-friendly slug\n"
        "- meta_description: Compelling meta description (150–160 characters)\n"
        "- outline: Array of heading objects [{level: 'h2', text: '...'}]\n"
        "  Include h2 and h3 headings. Use question-based headings where possible.\n"
        "- word_count: Recommended word count (1500–2000)\n"
        "- faq_questions: Array of 5–8 FAQ questions users would ask\n"
        "- semantic_keywords: Array of 8–12 LSI/semantic keywords to include\n"
        "- snippet_answers: Array of objects [{question: '...', answer: '...'}] "
        "with 2–3 featured snippet candidate answers (40–60 words each)\n\n"
        "The article should be structured for AI extraction with clear, "
        "direct answers and well-organized sections."
    )

    user_prompt = (
        f"Keyword Cluster: {cluster['cluster_name']}\n"
        f"Primary Keyword: {cluster['primary_keyword']}\n"
        f"Supporting Keywords: {supporting}\n\n"
        "Generate the article blueprint."
    )

    try:
        result = chat_completion_json(system_prompt, user_prompt, max_tokens=2048)

        blueprint = {
            "cluster_id": cluster.get("id", 0),
            "title": result.get("title", cluster["cluster_name"]),
            "slug": result.get("slug", _slugify(cluster["primary_keyword"])),
            "meta_description": result.get("meta_description", ""),
            "outline": result.get("outline", []),
            "word_count": result.get("word_count", 1800),
            "faq_questions": result.get("faq_questions", []),
            "semantic_keywords": result.get("semantic_keywords", []),
            "snippet_answers": result.get("snippet_answers", []),
        }

        logger.info("Blueprint generated: %s", blueprint["title"])
        return blueprint

    except Exception as exc:
        logger.error(
            "Blueprint generation failed for cluster '%s': %s",
            cluster.get("cluster_name"), exc,
        )
        return _fallback_blueprint(cluster)


def generate_blueprints(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate blueprints for a list of keyword clusters.

    Args:
        clusters: List of cluster dicts from the database.

    Returns:
        List of blueprint dicts.
    """
    blueprints: List[Dict[str, Any]] = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(generate_blueprint, cluster): cluster for cluster in clusters}
        for future in concurrent.futures.as_completed(futures):
            bp = future.result()
            if bp:
                blueprints.append(bp)
                
    logger.info("Generated %d blueprints from %d clusters", len(blueprints), len(clusters))
    return blueprints


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _fallback_blueprint(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Create a minimal blueprint when OpenAI fails."""
    return {
        "cluster_id": cluster.get("id", 0),
        "title": cluster["cluster_name"],
        "slug": _slugify(cluster["primary_keyword"]),
        "meta_description": f"Learn about {cluster['primary_keyword']} with expert tips and strategies.",
        "outline": [
            {"level": "h2", "text": f"What is {cluster['primary_keyword']}?"},
            {"level": "h2", "text": "Key Strategies and Tips"},
            {"level": "h2", "text": "Step-by-Step Guide"},
            {"level": "h2", "text": "Common Mistakes to Avoid"},
            {"level": "h2", "text": "Frequently Asked Questions"},
        ],
        "word_count": 1800,
        "faq_questions": [
            f"What is {cluster['primary_keyword']}?",
            f"How to get started with {cluster['primary_keyword']}?",
        ],
        "semantic_keywords": cluster.get("supporting_keywords", []),
        "snippet_answers": [],
    }
