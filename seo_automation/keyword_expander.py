"""
keyword_expander.py — Expand seed keywords into long-tail search queries.

Uses OpenAI to generate 5–10 long-tail variations per keyword,
targeting questions and phrases real users type into search engines.
"""

import concurrent.futures
import json
import logging
from typing import Any, Dict, List

from .config import config
from .utils.openai_client import chat_completion_json

logger = logging.getLogger(__name__)


def expand_keywords(keywords: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Expand a list of base keywords into long-tail search queries.

    Args:
        keywords: List of keyword dicts with at least 'keyword' and 'id' keys.

    Returns:
        List of expanded keyword dicts:
        [{"keyword": "...", "source": "expanded:<parent>", "timestamp": "..."}]
    """
    expanded: List[Dict[str, str]] = []
    batch_size = 10

    batches = [keywords[i : i + batch_size] for i in range(0, len(keywords), batch_size)]

    def process_batch(batch, batch_index):
        keyword_list = [kw["keyword"] for kw in batch]

        system_prompt = (
            "You are an SEO keyword research expert specialising in the Indian "
            "education and exam preparation space.\n\n"
            "Given a list of seed keywords, generate 5–8 long-tail keyword variations "
            "for EACH seed keyword. The variations should be:\n"
            "- Natural search queries that real users type into Google\n"
            "- Question-based when appropriate (how, what, why, when)\n"
            "- Specific and actionable\n"
            "- Relevant to exam preparation, study strategies, career guidance, "
            "or competitive exams in India\n\n"
            "Return a JSON object where each key is the original seed keyword and "
            "the value is a list of long-tail variations.\n\n"
            "Example:\n"
            '{\n'
            '  "UPSC preparation": [\n'
            '    "how to prepare for upsc 2026",\n'
            '    "upsc preparation strategy for beginners",\n'
            '    "upsc study plan for working professionals",\n'
            '    "best books for upsc preparation",\n'
            '    "upsc daily routine and timetable"\n'
            '  ]\n'
            '}'
        )

        user_prompt = f"Expand these keywords:\n{json.dumps(keyword_list)}"

        batch_expanded = []
        try:
            result = chat_completion_json(system_prompt, user_prompt)

            for seed_kw, variations in result.items():
                if isinstance(variations, list):
                    for variant in variations:
                        if isinstance(variant, str) and variant.strip():
                            batch_expanded.append({
                                "keyword": variant.strip().lower(),
                                "source": f"expanded:{seed_kw}",
                                "timestamp": _now(),
                            })

        except Exception as exc:
            logger.error("Keyword expansion failed for batch %d: %s", batch_index, exc)
            
        return batch_expanded

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_batch, batch, i) for i, batch in enumerate(batches)]
        for future in concurrent.futures.as_completed(futures):
            expanded.extend(future.result())

    logger.info(
        "Keyword expansion: %d seeds → %d long-tail keywords",
        len(keywords), len(expanded),
    )
    return expanded


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
