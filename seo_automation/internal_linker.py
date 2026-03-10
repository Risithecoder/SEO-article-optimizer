"""
internal_linker.py — Automatic internal linking engine.

Links each article to 3 related cluster articles and 1 pillar article
using keyword matching and cluster relationships. Inserts natural
<a> tags into the HTML content.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def add_internal_links(
    article: Dict[str, Any],
    all_articles: List[Dict[str, Any]],
    clusters: List[Dict[str, Any]],
    site_url: str = "",
    related_count: int = 3,
    pillar_count: int = 1,
) -> Dict[str, Any]:
    """
    Insert internal links into an article's HTML content.

    Links to:
    - `related_count` articles from related clusters
    - `pillar_count` pillar articles (most comprehensive/broad articles)

    Args:
        article:       The article to add links to.
        all_articles:  All published articles from the database.
        clusters:      All clusters for keyword overlap analysis.
        site_url:      Base site URL for constructing links.
        related_count: Number of related article links (default 3).
        pillar_count:  Number of pillar article links (default 1).

    Returns:
        Updated article dict with internal links in html_content.
    """
    html_content = article.get("html_content", "")
    if not html_content or not all_articles:
        return article

    current_slug = article.get("slug", "")

    # Exclude current article from candidates
    candidates = [a for a in all_articles if a.get("slug") != current_slug]
    if not candidates:
        return article

    # Score candidates by relevance
    scored = _score_candidates(article, candidates, clusters)

    # Select top related + pillar articles
    related_articles = scored[:related_count]
    pillar = _find_pillar_articles(candidates, pillar_count)

    # Combine, removing duplicates
    link_targets: List[Dict[str, Any]] = []
    seen_slugs = set()

    for target in related_articles + pillar:
        slug = target.get("slug", "")
        if slug and slug not in seen_slugs:
            link_targets.append(target)
            seen_slugs.add(slug)

    # Insert links into HTML
    for target in link_targets:
        html_content = _insert_link(
            html_content,
            target_title=target.get("title", ""),
            target_url=_build_url(site_url, target.get("slug", "")),
            published_url=target.get("published_url", ""),
        )

    # Add a "Related Articles" section at the end if needed
    if link_targets:
        related_section = _build_related_section(link_targets, site_url)
        html_content += "\n" + related_section

    article["html_content"] = html_content
    logger.info(
        "Internal links added to '%s': %d links",
        article.get("title"), len(link_targets),
    )
    return article


def add_internal_links_batch(
    articles: List[Dict[str, Any]],
    all_published: List[Dict[str, Any]],
    clusters: List[Dict[str, Any]],
    site_url: str = "",
) -> List[Dict[str, Any]]:
    """Add internal links to a batch of articles."""
    # Combine published + current batch for cross-linking
    all_available = all_published + articles

    linked = []
    for article in articles:
        linked_article = add_internal_links(
            article, all_available, clusters, site_url
        )
        linked.append(linked_article)
    return linked


# ────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────

def _score_candidates(
    article: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    clusters: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Score candidate articles by relevance to the current article.
    Uses title word overlap and cluster proximity.
    """
    current_words = set(article.get("title", "").lower().split())
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for candidate in candidates:
        candidate_words = set(candidate.get("title", "").lower().split())
        # Word overlap score
        overlap = len(current_words & candidate_words)
        # Bonus if same cluster
        if (
            article.get("blueprint_id")
            and candidate.get("blueprint_id")
            and article.get("blueprint_id") == candidate.get("blueprint_id")
        ):
            overlap += 3

        scored.append((overlap, candidate))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored]


def _find_pillar_articles(
    candidates: List[Dict[str, Any]], count: int
) -> List[Dict[str, Any]]:
    """
    Find pillar articles — the most comprehensive/broad articles.
    Uses content length as a proxy for comprehensiveness.
    """
    sorted_by_length = sorted(
        candidates,
        key=lambda a: len(a.get("html_content", "") or a.get("content", "")),
        reverse=True,
    )
    return sorted_by_length[:count]


def _insert_link(
    html: str,
    target_title: str,
    target_url: str,
    published_url: str = "",
) -> str:
    """
    Insert an <a> tag into the HTML content at a natural position.
    Finds a paragraph mentioning related terms and adds a contextual link.
    """
    url = published_url if published_url else target_url
    if not url or not target_title:
        return html

    # Find a good keyword from the target title to anchor the link
    title_words = target_title.lower().split()
    # Use 2-3 word phrases from the title as anchor candidates
    for phrase_len in (3, 2, 1):
        for i in range(len(title_words) - phrase_len + 1):
            phrase = " ".join(title_words[i : i + phrase_len])
            if len(phrase) < 4:
                continue

            # Look for the phrase in a paragraph (case-insensitive)
            pattern = re.compile(
                rf"(<p>(?:(?!</p>).)*?)({re.escape(phrase)})((?:(?!</p>).)*</p>)",
                re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(html)
            if match:
                # Only link the first occurrence
                link_tag = f'<a href="{url}" title="{target_title}">{match.group(2)}</a>'
                html = html[: match.start(2)] + link_tag + html[match.end(2) :]
                return html

    return html


def _build_url(site_url: str, slug: str) -> str:
    """Build a full URL from site URL and slug."""
    if not site_url:
        return f"/{slug}/"
    base = site_url.rstrip("/")
    return f"{base}/{slug}/"


def _build_related_section(
    targets: List[Dict[str, Any]], site_url: str
) -> str:
    """Build an HTML 'Related Articles' section."""
    links_html = ""
    for target in targets:
        url = target.get("published_url") or _build_url(site_url, target.get("slug", ""))
        title = target.get("title", "Related Article")
        links_html += f'  <li><a href="{url}">{title}</a></li>\n'

    return (
        '<div class="related-articles">\n'
        "  <h3>Related Articles</h3>\n"
        "  <ul>\n"
        f"{links_html}"
        "  </ul>\n"
        "</div>"
    )
