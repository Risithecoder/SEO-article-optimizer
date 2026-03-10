"""
utils/deduplicator.py — Content deduplication utilities.

Uses fuzzy string matching to prevent duplicate keywords and articles
from entering the pipeline.
"""

import difflib
import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# Default similarity threshold (0.0–1.0)
SIMILARITY_THRESHOLD = 0.85


def deduplicate_keywords(
    new_keywords: List[Dict[str, str]],
    existing_keywords: Set[str],
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[Dict[str, str]]:
    """
    Remove keywords that are duplicates or near-duplicates of existing ones.

    Args:
        new_keywords:      List of keyword dicts with at least a 'keyword' key.
        existing_keywords: Set of already-stored keyword strings (lowercased).
        threshold:         Similarity ratio above which a keyword is a duplicate.

    Returns:
        Filtered list containing only genuinely new keywords.
    """
    unique: List[Dict[str, str]] = []
    seen: Set[str] = set(existing_keywords)

    for kw_dict in new_keywords:
        kw = kw_dict["keyword"].lower().strip()

        # Exact match
        if kw in seen:
            continue

        # Fuzzy match against all known keywords
        is_dup = False
        for existing in seen:
            ratio = difflib.SequenceMatcher(None, kw, existing).ratio()
            if ratio >= threshold:
                logger.debug("Duplicate detected: '%s' ≈ '%s' (%.2f)", kw, existing, ratio)
                is_dup = True
                break

        if not is_dup:
            unique.append(kw_dict)
            seen.add(kw)

    logger.info(
        "Deduplication: %d input → %d unique (removed %d)",
        len(new_keywords), len(unique), len(new_keywords) - len(unique),
    )
    return unique


def is_duplicate_article(
    title: str,
    existing_titles: List[str],
    threshold: float = SIMILARITY_THRESHOLD,
) -> bool:
    """
    Check whether an article title is too similar to existing titles.

    Args:
        title:           Proposed article title.
        existing_titles: List of existing article titles.
        threshold:       Similarity ratio above which it's a duplicate.

    Returns:
        True if the title is a near-duplicate of any existing title.
    """
    title_lower = title.lower().strip()
    for existing in existing_titles:
        ratio = difflib.SequenceMatcher(None, title_lower, existing.lower().strip()).ratio()
        if ratio >= threshold:
            logger.debug("Duplicate article: '%s' ≈ '%s' (%.2f)", title, existing, ratio)
            return True
    return False
