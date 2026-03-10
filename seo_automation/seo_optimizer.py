"""
seo_optimizer.py — SEO/AEO post-processing for generated articles.

Converts Markdown to HTML, injects JSON-LD schema markup, validates
keyword density, and ensures all SEO best practices are met.
"""

import json
import logging
import re
from typing import Any, Dict, List, Tuple

import markdown

from .config import config
from .utils.schema_generator import (
    generate_article_schema,
    generate_faq_schema,
    generate_howto_schema,
)

logger = logging.getLogger(__name__)


def optimize_article(article: Dict[str, Any], blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process an article for SEO and AEO optimisation.

    Steps:
    1. Convert Markdown content to HTML
    2. Verify keyword placement (title, first paragraph, H2s, meta)
    3. Generate JSON-LD schema markup (Article + FAQ + optional HowTo)
    4. Validate keyword density
    5. Return the enriched article

    Args:
        article:   Article dict with 'content' (Markdown), 'title', 'slug', etc.
        blueprint: Original blueprint dict with FAQ data.

    Returns:
        Updated article dict with 'html_content', 'schema_markup', status='optimized'.
    """
    md_content = article.get("content", "")
    title = article.get("title", "")
    primary_keyword = _extract_primary_keyword(blueprint)

    # ── 1. Markdown → HTML ──────────────────────────────────
    html_content = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "toc", "attr_list"],
    )

    # ── 2. Keyword placement checks ────────────────────────
    issues = _check_keyword_placement(html_content, title, primary_keyword)
    if issues:
        logger.warning("SEO issues for '%s': %s", title, "; ".join(issues))

    # ── 3. Schema markup ───────────────────────────────────
    schemas = _build_schemas(article, blueprint)

    # ── 4. Keyword density ─────────────────────────────────
    density = _calculate_keyword_density(md_content, primary_keyword)
    if density < 0.5:
        logger.warning("Low keyword density (%.1f%%) for '%s'", density, title)
    elif density > 3.0:
        logger.warning("High keyword density (%.1f%%) for '%s' — risking keyword stuffing", density, title)

    # ── 5. Inject schema into HTML ─────────────────────────
    schema_script = _schemas_to_script_tags(schemas)
    html_with_schema = schema_script + "\n" + html_content

    # ── Update article ─────────────────────────────────────
    article["html_content"] = html_with_schema
    article["schema_markup"] = schemas
    article["status"] = "optimized"

    logger.info(
        "Optimised: '%s' (density: %.1f%%, schemas: %d)",
        title, density, len(schemas),
    )
    return article


def optimize_articles(
    articles: List[Dict[str, Any]],
    blueprints: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Optimise a list of articles against their blueprints.

    Matches articles to blueprints by blueprint_id.
    """
    bp_map = {bp.get("id", bp.get("cluster_id", i)): bp for i, bp in enumerate(blueprints)}
    optimised = []
    for article in articles:
        bp = bp_map.get(article.get("blueprint_id"), {})
        optimised.append(optimize_article(article, bp))
    return optimised


# ────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────

def _extract_primary_keyword(blueprint: Dict[str, Any]) -> str:
    """Extract the primary keyword from a blueprint or cluster."""
    if "primary_keyword" in blueprint:
        return blueprint["primary_keyword"]
    if "semantic_keywords" in blueprint and blueprint["semantic_keywords"]:
        return blueprint["semantic_keywords"][0]
    return ""


def _check_keyword_placement(
    html: str, title: str, keyword: str
) -> List[str]:
    """Check that the primary keyword appears in key positions."""
    issues = []
    kw_lower = keyword.lower()

    if not kw_lower:
        return issues

    if kw_lower not in title.lower():
        issues.append(f"Primary keyword '{keyword}' missing from title")

    # Check first paragraph
    first_p_match = re.search(r"<p>(.*?)</p>", html, re.DOTALL)
    if first_p_match:
        if kw_lower not in first_p_match.group(1).lower():
            issues.append(f"Primary keyword '{keyword}' missing from first paragraph")

    # Check H2 headings
    h2_matches = re.findall(r"<h2>(.*?)</h2>", html, re.IGNORECASE)
    h2_has_kw = any(kw_lower in h.lower() for h in h2_matches)
    if not h2_has_kw and h2_matches:
        issues.append(f"Primary keyword '{keyword}' not found in any H2 heading")

    return issues


def _calculate_keyword_density(text: str, keyword: str) -> float:
    """Calculate keyword density as a percentage."""
    if not keyword or not text:
        return 0.0
    words = text.lower().split()
    total = len(words)
    if total == 0:
        return 0.0
    kw_words = keyword.lower().split()
    kw_len = len(kw_words)
    occurrences = 0
    for i in range(len(words) - kw_len + 1):
        if words[i : i + kw_len] == kw_words:
            occurrences += 1
    return (occurrences * kw_len / total) * 100


def _build_schemas(
    article: Dict[str, Any], blueprint: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build all applicable JSON-LD schemas for the article."""
    schemas: List[Dict[str, Any]] = []

    # Article schema
    schemas.append(
        generate_article_schema(
            title=article.get("title", ""),
            description=article.get("meta_description", ""),
        )
    )

    # FAQ schema (from blueprint FAQ questions + answers in content)
    faq_list = _extract_faq_pairs(
        article.get("content", ""),
        blueprint.get("faq_questions", []),
    )
    if faq_list:
        schemas.append(generate_faq_schema(faq_list))

    # HowTo schema (if article contains step-by-step content)
    steps = _extract_howto_steps(article.get("content", ""))
    if steps:
        schemas.append(
            generate_howto_schema(
                name=article.get("title", ""),
                description=article.get("meta_description", ""),
                steps=steps,
            )
        )

    return schemas


def _extract_faq_pairs(
    content: str, questions: List[str]
) -> List[Dict[str, str]]:
    """
    Extract FAQ question-answer pairs from article content.
    Looks for question headings followed by paragraph text.
    """
    pairs: List[Dict[str, str]] = []

    # Try to find the FAQ section
    faq_section = ""
    faq_match = re.search(
        r"(?:#{1,3}\s*(?:FAQ|Frequently Asked Questions).*?\n)(.*)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    if faq_match:
        faq_section = faq_match.group(1)

    # Extract Q&A pairs from FAQ section
    if faq_section:
        # Pattern: ### Question?\nAnswer text
        qa_pattern = re.findall(
            r"#{2,4}\s*(.+?\?)\s*\n+((?:(?!#{2,4}).+\n?)+)",
            faq_section,
        )
        for question, answer in qa_pattern:
            answer_clean = answer.strip()
            if answer_clean:
                pairs.append({
                    "question": question.strip(),
                    "answer": answer_clean[:500],  # cap length
                })

    # If we didn't find pairs in FAQ section, use blueprint questions
    if not pairs and questions:
        for q in questions[:5]:
            pairs.append({
                "question": q,
                "answer": f"Refer to our detailed guide above for a comprehensive answer to: {q}",
            })

    return pairs


def _extract_howto_steps(content: str) -> List[str]:
    """
    Extract step-by-step instructions from article content.
    Returns list of step descriptions, or empty list if none found.
    """
    steps: List[str] = []

    # Look for "Step N:" or numbered list patterns
    step_pattern = re.findall(
        r"(?:Step\s*\d+[:.]\s*|^\d+\.\s+\*\*)(.*?)(?:\*\*|\n)",
        content,
        re.MULTILINE,
    )
    for step in step_pattern:
        clean = step.strip().rstrip("*")
        if clean and len(clean) > 5:
            steps.append(clean)

    return steps[:10]  # max 10 steps


def _schemas_to_script_tags(schemas: List[Dict[str, Any]]) -> str:
    """Convert a list of schema dicts into HTML script tags."""
    tags = []
    for schema in schemas:
        tag = (
            '<script type="application/ld+json">\n'
            f"{json.dumps(schema, indent=2)}\n"
            "</script>"
        )
        tags.append(tag)
    return "\n".join(tags)
