"""
article_generator.py — Generate full-length SEO/AEO optimised articles.

Produces 1500–2000 word Markdown articles structured for both search
engines and AI answer engines. Includes direct answer summaries,
question-based headings, tables, bullet lists, and FAQ sections.
"""

import concurrent.futures
import json
import logging
from typing import Any, Dict

from .config import config
from .utils.openai_client import chat_completion

logger = logging.getLogger(__name__)


def generate_article(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a full article from a blueprint.

    Args:
        blueprint: Blueprint dict from blueprint_generator with title,
                   slug, meta_description, outline, faq_questions,
                   semantic_keywords, and snippet_answers.

    Returns:
        Article dict with: blueprint_id, title, slug, content (Markdown),
        meta_description, status.
    """
    outline_text = _format_outline(blueprint.get("outline", []))
    faqs_text = "\n".join(f"- {q}" for q in blueprint.get("faq_questions", []))
    semantics_text = ", ".join(blueprint.get("semantic_keywords", []))
    snippets_text = json.dumps(blueprint.get("snippet_answers", []), indent=2)

    system_prompt = (
        "You are an expert content writer for Oliveboard, a leading Indian exam "
        "preparation platform. You write authoritative, reader-friendly articles "
        "that rank in Google search, AI Overviews, People Also Ask, and AI answer "
        "engines like ChatGPT and Perplexity.\n\n"
        "WRITING RULES:\n"
        "1. Write 1500–2000 words in Markdown format\n"
        "2. Start with a DIRECT ANSWER SUMMARY (40–60 words) immediately after the title. "
        "This summary should directly answer the core question in a way that AI engines can extract\n"
        "3. Use clear H1 (# ), H2 (## ), and H3 (### ) heading hierarchy\n"
        "4. Use QUESTION-BASED HEADINGS where appropriate (e.g., ## What is ...?)\n"
        "5. Include DEFINITION BOXES using blockquotes (> **Definition:** ...)\n"
        "6. Add STEP-BY-STEP sections with numbered lists\n"
        "7. Include BULLET POINT lists for tips, features, and advantages\n"
        "8. Add at least one MARKDOWN TABLE for comparisons or structured data\n"
        "9. Include practical EXAM PREPARATION TIPS, study plans, and strategies\n"
        "10. Write a FAQ SECTION with 5–8 questions and concise (2–3 sentence) answers\n"
        "11. Each FAQ answer must be self-contained and suitable for AI extraction\n"
        "12. Use the semantic keywords naturally throughout the article\n"
        "13. Write in an authoritative but approachable tone\n"
        "14. Include actionable advice, not generic AI filler\n"
        "15. End with a CONCLUSION that summarises key takeaways\n\n"
        "AEO OPTIMISATION RULES:\n"
        "- Structure content so AI answer engines can extract clean answers\n"
        "- Use concise paragraphs (3-4 sentences max)\n"
        "- Put the most important information first in each section\n"
        "- Use explicit question-answer patterns\n"
        "- Ensure every H2 section could standalone as an answer\n\n"
        "FORMAT: Output ONLY the Markdown article. Do not include any preamble or explanation."
    )

    user_prompt = (
        f"ARTICLE TITLE: {blueprint['title']}\n\n"
        f"META DESCRIPTION: {blueprint.get('meta_description', '')}\n\n"
        f"ARTICLE OUTLINE:\n{outline_text}\n\n"
        f"FAQ QUESTIONS TO ANSWER:\n{faqs_text}\n\n"
        f"SEMANTIC KEYWORDS TO INCLUDE: {semantics_text}\n\n"
        f"FEATURED SNIPPET CANDIDATES:\n{snippets_text}\n\n"
        f"TARGET WORD COUNT: {blueprint.get('word_count', 1800)} words\n\n"
        "Write the complete article now."
    )

    try:
        content = chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=config.openai_max_tokens,
        )

        if not content or len(content.split()) < 500:
            logger.warning(
                "Article too short for '%s' (%d words), regenerating...",
                blueprint["title"], len(content.split()) if content else 0,
            )
            content = chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt + "\n\nIMPORTANT: Write at least 1500 words.",
                temperature=0.8,
                max_tokens=config.openai_max_tokens,
            )

        article = {
            "blueprint_id": blueprint.get("id", 0),
            "title": blueprint["title"],
            "slug": blueprint["slug"],
            "content": content,
            "meta_description": blueprint.get("meta_description", ""),
            "status": "draft",
        }

        word_count = len(content.split()) if content else 0
        logger.info("Article generated: '%s' (%d words)", blueprint["title"], word_count)
        return article

    except Exception as exc:
        logger.error("Article generation failed for '%s': %s", blueprint["title"], exc)
        return {
            "blueprint_id": blueprint.get("id", 0),
            "title": blueprint["title"],
            "slug": blueprint["slug"],
            "content": "",
            "meta_description": blueprint.get("meta_description", ""),
            "status": "failed",
        }


def generate_articles(blueprints: list, cancel_check=None) -> list:
    """
    Generate articles for a list of blueprints.

    Args:
        blueprints: List of blueprint dicts.

    Returns:
        List of article dicts.
    """
    articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(generate_article, bp): bp for bp in blueprints}
        for future in concurrent.futures.as_completed(futures):
            if cancel_check and cancel_check():
                for f in futures:
                    f.cancel()
                break
            article = future.result()
            if article.get("status") != "failed":
                articles.append(article)
                
    logger.info("Generated %d articles from %d blueprints", len(articles), len(blueprints))
    return articles


def _format_outline(outline: list) -> str:
    """Format blueprint outline into readable text."""
    lines = []
    for item in outline:
        if isinstance(item, dict):
            level = item.get("level", "h2")
            text = item.get("text", "")
            indent = "  " * (int(level.replace("h", "")) - 2) if level != "h1" else ""
            lines.append(f"{indent}- [{level.upper()}] {text}")
        elif isinstance(item, str):
            lines.append(f"- {item}")
    return "\n".join(lines) if lines else "No outline provided"
