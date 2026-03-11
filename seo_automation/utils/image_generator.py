"""
utils/image_generator.py — Generate article images using Google Gemini API.

Uses the Gemini Imagen model to generate infographic-style images
for articles. Only uses the Gemini API (not OpenAI) for image generation.
"""

import base64
import concurrent.futures
import logging
import os
import time
from typing import Any, Dict, Optional

import requests

from ..config import config

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict"


def generate_article_image(
    title: str,
    keyword: str,
    output_dir: str = "generated_images",
    style: str = "infographic",
) -> Optional[Dict[str, Any]]:
    """
    Generate an image for an article using Google Gemini Imagen API.

    Args:
        title:      Article title to base the image on.
        keyword:    Primary keyword for context.
        output_dir: Directory to save generated images.
        style:      Image style (infographic, illustration, etc.).

    Returns:
        Dict with 'path', 'filename', 'alt_text', 'caption' or None on failure.
    """
    api_key = config.gemini_api_key
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping image generation")
        return None

    os.makedirs(output_dir, exist_ok=True)

    prompt = _build_image_prompt(title, keyword, style)
    slug = _slugify(title)
    filename = f"{slug}.png"
    filepath = os.path.join(output_dir, filename)

    try:
        url = f"{GEMINI_API_URL}?key={api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "personGeneration": "DONT_ALLOW",
            },
        }

        response = requests.post(url, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            predictions = data.get("predictions", [])
            if predictions:
                image_b64 = predictions[0].get("bytesBase64Encoded", "")
                if image_b64:
                    image_bytes = base64.b64decode(image_b64)
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)

                    result = {
                        "path": filepath,
                        "filename": filename,
                        "alt_text": f"{title} - {keyword}",
                        "caption": f"Infographic: {title}",
                    }
                    logger.info("Image generated: %s", filename)
                    return result

        logger.error("Gemini Imagen API error %d: %s", response.status_code, response.text[:300])
        return None

    except Exception as exc:
        logger.error("Image generation failed for '%s': %s", title, exc)
        return None


def generate_section_image(
    prompt: str,
    slug: str,
    section_index: int,
    output_dir: str = "generated_images",
    max_retries: int = 5,
) -> Optional[Dict[str, Any]]:
    """
    Generate an image for a specific article section using a custom prompt.
    Includes retry logic for rate-limited requests.
    """
    api_key = config.gemini_api_key
    if not api_key:
        logger.warning("No Gemini API key configured")
        return None

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{slug}-sec{section_index}.png"
    filepath = os.path.join(output_dir, filename)

    url = f"{GEMINI_API_URL}?key={api_key}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "16:9",
            "personGeneration": "DONT_ALLOW",
        },
    }

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Gemini API call for %s (attempt %d/%d)", filename, attempt, max_retries)
            response = requests.post(url, json=payload, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                predictions = data.get("predictions", [])
                if predictions:
                    image_b64 = predictions[0].get("bytesBase64Encoded", "")
                    if image_b64:
                        image_bytes = base64.b64decode(image_b64)
                        with open(filepath, "wb") as f:
                            f.write(image_bytes)
                        logger.info("Section image generated: %s", filename)
                        return {"path": filepath, "filename": filename}
                    else:
                        logger.warning("Gemini returned empty base64 for %s", filename)
                else:
                    logger.warning("Gemini returned no predictions for %s: %s", filename, str(data)[:200])
                return None  # Don't retry on empty predictions
                
            elif response.status_code == 429:
                # 429 is usually the 15 Requests Per Minute limit. Wait longer to let the bucket reset.
                wait = 15 * attempt
                logger.warning("Gemini rate limited for %s — waiting %ds (attempt %d/%d)", filename, wait, attempt, max_retries)
                time.sleep(wait)
                continue
            else:
                logger.error("Gemini API error %d for %s: %s", response.status_code, filename, response.text[:300])
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None

        except requests.exceptions.Timeout:
            logger.error("Gemini API timeout for %s (attempt %d/%d)", filename, attempt, max_retries)
            if attempt < max_retries:
                time.sleep(2)
                continue
        except Exception as exc:
            logger.error("Section image generation failed for %s: %s", filename, exc)
            return None
        
    return None


def generate_images_for_articles(
    articles: list,
    output_dir: str = "generated_images",
) -> Dict[int, Dict[str, Any]]:
    """
    Generate images for a batch of articles.

    Args:
        articles:   List of article dicts with 'id', 'title', 'slug'.
        output_dir: Directory to save images.

    Returns:
        Dict mapping article_id → image info dict.
    """
    results: Dict[int, Dict[str, Any]] = {}

    def process_article(article):
        article_id = article.get("id", 0)
        title = article.get("title", "")
        keyword = article.get("slug", "").replace("-", " ")

        image = generate_article_image(title, keyword, output_dir)
        return article_id, image

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_article, article): article for article in articles}
        for future in concurrent.futures.as_completed(futures):
            article_id, image = future.result()
            if image:
                results[article_id] = image

    logger.info("Generated images for %d/%d articles", len(results), len(articles))
    return results


def _build_image_prompt(title: str, keyword: str, style: str) -> str:
    """Build a descriptive prompt for the image generator."""
    prompts = {
        "infographic": (
            f"A clean, modern infographic about '{title}'. "
            f"Educational content related to {keyword}. "
            "Professional design with icons, charts, and structured layout. "
            "Use a blue and white color scheme. "
            "No text overlays. Suitable for a blog article header."
        ),
        "illustration": (
            f"A professional illustration for an article about '{title}'. "
            f"Related to {keyword} and exam preparation. "
            "Flat design style, modern colors, educational theme."
        ),
    }
    return prompts.get(style, prompts["infographic"])


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]
