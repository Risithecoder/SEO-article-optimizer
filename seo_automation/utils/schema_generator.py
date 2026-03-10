"""
utils/schema_generator.py — JSON-LD structured data generators.

Produces Article, FAQ, and HowTo schema markup for SEO/AEO optimisation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List


def generate_article_schema(
    title: str,
    description: str,
    author: str = "Exam Prep Team",
    date_published: str = "",
    url: str = "",
    image_url: str = "",
) -> Dict[str, Any]:
    """
    Generate JSON-LD Article schema.

    Args:
        title:           Article headline.
        description:     Short description / meta description.
        author:          Author name.
        date_published:  ISO-8601 date string (defaults to now).
        url:             Canonical URL of the article.
        image_url:       Optional hero image URL.

    Returns:
        JSON-LD dict ready for embedding in <script type="application/ld+json">.
    """
    if not date_published:
        date_published = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    schema: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {
            "@type": "Person",
            "name": author,
        },
        "datePublished": date_published,
        "dateModified": date_published,
    }

    if url:
        schema["url"] = url
        schema["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
    if image_url:
        schema["image"] = image_url

    return schema


def generate_faq_schema(faq_list: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Generate JSON-LD FAQPage schema.

    Args:
        faq_list: list of dicts with 'question' and 'answer' keys.

    Returns:
        JSON-LD dict for FAQPage.
    """
    entities = []
    for faq in faq_list:
        entities.append({
            "@type": "Question",
            "name": faq["question"],
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq["answer"],
            },
        })

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }


def generate_howto_schema(
    name: str,
    description: str,
    steps: List[str],
    total_time: str = "",
) -> Dict[str, Any]:
    """
    Generate JSON-LD HowTo schema.

    Args:
        name:        Title of the how-to guide.
        description: Brief description.
        steps:       List of step description strings.
        total_time:  Optional ISO-8601 duration (e.g. "PT2H").

    Returns:
        JSON-LD dict for HowTo.
    """
    step_entities = []
    for i, step_text in enumerate(steps, 1):
        step_entities.append({
            "@type": "HowToStep",
            "position": i,
            "text": step_text,
        })

    schema: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": name,
        "description": description,
        "step": step_entities,
    }

    if total_time:
        schema["totalTime"] = total_time

    return schema
