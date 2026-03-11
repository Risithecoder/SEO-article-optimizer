"""
keyword_cluster.py — Group keywords into topical clusters.

Uses OpenAI to semantically cluster related keywords, identifying
a primary keyword and supporting keywords for each cluster.
"""

import concurrent.futures
import json
import logging
from typing import Any, Dict, List

from .utils.openai_client import chat_completion_json

logger = logging.getLogger(__name__)


def cluster_keywords(keywords: List[Dict[str, Any]], cancel_check=None) -> List[Dict[str, Any]]:
    """
    Group keywords into topical clusters using OpenAI.

    Args:
        keywords: List of keyword dicts with at least a 'keyword' key.

    Returns:
        List of cluster dicts:
        [
            {
                "cluster_name": "UPSC Preparation Strategy",
                "primary_keyword": "upsc preparation strategy",
                "supporting_keywords": ["upsc daily routine", "upsc tips", ...]
            },
            ...
        ]
    """
    if not keywords:
        return []

    keyword_list = [kw["keyword"] for kw in keywords]

    # Process in chunks if too many keywords
    max_per_batch = 100
    all_clusters: List[Dict[str, Any]] = []

    batches = [keyword_list[i : i + max_per_batch] for i in range(0, len(keyword_list), max_per_batch)]

    def process_batch(batch, batch_index):
        system_prompt = (
            "You are an SEO content strategist specialising in the Indian education "
            "and competitive exam space.\n\n"
            "Given a list of keywords, group them into topical clusters. Each cluster "
            "should represent a single article topic.\n\n"
            "Rules:\n"
            "- Each cluster must have a descriptive cluster_name\n"
            "- Identify one primary_keyword (highest search intent)\n"
            "- List 3–8 supporting_keywords per cluster\n"
            "- A keyword should only appear in one cluster\n"
            "- Discard any irrelevant or low-value keywords\n"
            "- Create between 5–20 clusters depending on keyword diversity\n\n"
            "Return a JSON object with a key 'clusters' containing a list of cluster objects.\n\n"
            "Example:\n"
            '{\n'
            '  "clusters": [\n'
            '    {\n'
            '      "cluster_name": "UPSC Preparation Strategy",\n'
            '      "primary_keyword": "upsc preparation strategy",\n'
            '      "supporting_keywords": [\n'
            '        "upsc daily routine",\n'
            '        "upsc preparation tips for beginners",\n'
            '        "upsc study plan 2026"\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            '}'
        )

        user_prompt = f"Keywords to cluster:\n{json.dumps(batch, indent=2)}"
        
        batch_clusters = []
        try:
            result = chat_completion_json(system_prompt, user_prompt, max_tokens=4096)
            clusters = result.get("clusters", [])

            for cluster in clusters:
                if (
                    isinstance(cluster, dict)
                    and "cluster_name" in cluster
                    and "primary_keyword" in cluster
                ):
                    batch_clusters.append({
                        "cluster_name": cluster["cluster_name"],
                        "primary_keyword": cluster["primary_keyword"],
                        "supporting_keywords": cluster.get("supporting_keywords", []),
                    })

        except Exception as exc:
            logger.error("Keyword clustering failed for batch %d: %s", batch_index, exc)
            
        return batch_clusters
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_batch, batch, i) for i, batch in enumerate(batches)]
        for future in concurrent.futures.as_completed(futures):
            if cancel_check and cancel_check():
                for f in futures:
                    f.cancel()
                break
            all_clusters.extend(future.result())

    logger.info(
        "Clustering: %d keywords → %d clusters",
        len(keyword_list), len(all_clusters),
    )
    return all_clusters
