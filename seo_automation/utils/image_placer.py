"""
utils/image_placer.py — Parses an article, selects image-worthy sections,
generates prompts, creates images via Gemini, and embeds them contextually.
"""

import concurrent.futures
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .image_generator import generate_section_image
from .openai_client import chat_completion
from ..config import config

logger = logging.getLogger(__name__)

def parse_sections(markdown_content: str) -> List[Dict[str, str]]:
    """Parse Markdown content into sections based on H2 headings only.
    
    H3 sub-headings are kept within their parent H2 section so that
    sections retain enough content to be eligible for images.
    """
    lines = markdown_content.splitlines()
    sections: List[Dict[str, str]] = []
    
    current_heading = "PREAMBLE"
    current_content: List[str] = []
    
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            # Flush previous section
            if current_content or current_heading != "PREAMBLE":
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip()
                })
                current_content = []
            current_heading = line.strip()
        elif line.startswith("# ") and not line.startswith("## "):
            # H1 title — flush preamble and start title section
            if current_content:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip()
                })
                current_content = []
            current_heading = line.strip()
        else:
            current_content.append(line)
            
    # Add final section
    if current_content:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_content).strip()
        })
        
    return sections


def select_sections_for_images(sections: List[Dict[str, str]], title: str) -> List[Dict[str, Any]]:
    """Use LLM to select 2-4 appropriate sections and generate image prompts."""
    # Filter out sections that should not have images
    eligible_sections = []
    for i, sec in enumerate(sections):
        head = sec["heading"].upper()
        # Skip the H1 title, FAQ, Conclusion, and very short sections
        if head.startswith("# ") and not head.startswith("## "):
            continue
        if "FAQ" in head or "CONCLUSION" in head or head == "PREAMBLE":
            continue
        if len(sec["content"].split()) < 20:
            continue
        eligible_sections.append({"section_id": f"sec_{i}", "heading": sec["heading"], "content_preview": sec["content"][:300]})

    if not eligible_sections:
        return []

    system_prompt = (
        "You are an expert educational content designer. Given a list of article sections, "
        "choose 2 to 4 sections that would most benefit from an educational visual (infographic, "
        "roadmap, comparison chart, etc.). Avoid decorative images.\n\n"
        "Return a JSON array of objects. Each object must have:\n"
        "  - 'section_id': The exact string 'section_id' of the section provided.\n"
        "  - 'prompt': A detailed image generation prompt specifically tailored for an educational "
        "infographic or diagram representing that section's content. The prompt should specify "
        "a clean, modern style with no text overlays (or minimal text), suitable for a professional blog."
    )

    sections_json = json.dumps(eligible_sections, indent=2)
    user_prompt = f"ARTICLE TITLE: {title}\n\nELIGIBLE SECTIONS:\n{sections_json}\n\nReturn ONLY raw JSON array, no markdown wrappers."

    try:
        response = chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Strip markdown code blocks if the LLM adds them
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
            
        selected = json.loads(response.strip())
        
        # Ensure it's a list and cap at 4
        if isinstance(selected, list):
            return selected[:4]
            
    except Exception as e:
        logger.error(f"Failed to select image sections: {e}")
        
    return []


def map_images_to_sections(
    article_content: str, 
    slug: str, 
    title: str,
    output_dir: str = "generated_images"
) -> Tuple[str, Optional[str]]:
    """
    Parse the article, determine 2-4 sections needing images, generate prompts,
    create the images, and embed the markdown in the returned content.
    
    Returns:
        Tuple of (updated_markdown_content, first_image_url)
        first_image_url is used for card thumbnails.
    """
    if not config.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set - skipping contextual image placement.")
        return article_content, None

    sections = parse_sections(article_content)
    logger.info(f"[ImagePlacer] '{title[:40]}': parsed {len(sections)} sections")
    for i, s in enumerate(sections):
        logger.info(f"  [{i}] {s['heading'][:50]} ({len(s['content'].split())} words)")
    
    selected_prompts = select_sections_for_images(sections, title)
    logger.info(f"[ImagePlacer] '{title[:40]}': {len(selected_prompts)} sections selected for images")
    
    if not selected_prompts:
        logger.warning(f"[ImagePlacer] '{title[:40]}': No sections selected — skipping images")
        return article_content, None

    # Generate images concurrently
    results = {} # index -> image_data
    
    def worker(item, i):
        sec_id = item.get("section_id")
        prompt = item.get("prompt")
        
        # Parse the integer index back from section_id like "sec_5"
        idx = None
        if isinstance(sec_id, str) and sec_id.startswith("sec_"):
            try:
                idx = int(sec_id.split("_")[1])
            except ValueError:
                pass
                
        if idx is None or not prompt:
            return None
            
        # Add context from title to the prompt to keep style consistent
        full_prompt = (
            f"A clean, modern educational infographic or diagram for an article about '{title}'. "
            f"Specific section focus: {prompt}. "
            "Professional design with structured layout, blue and white color scheme. "
            "No text overlays."
        )
        
        # Generate the image 
        img_info = generate_section_image(full_prompt, slug, i + 1, output_dir)
        if img_info:
            return (idx, img_info)
        return None

    # Reduced max_workers to prevent hitting Gemini API 15 RPM rate limit
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker, item, i) for i, item in enumerate(selected_prompts)]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                idx, img_info = res
                results[idx] = img_info

    if not results:
        return article_content, None

    # Reconstruct the markdown with images inserted
    first_image_url = None
    final_lines = []
    
    for i, sec in enumerate(sections):
        final_lines.append(sec["heading"])
        
        # Insert image immediately after the heading
        if i in results:
            img_info = results[i]
            img_filename = img_info['filename']
            # We assume frontend serves /images/ static path
            img_url = f"/images/{img_filename}"
            if not first_image_url:
                first_image_url = img_url
                
            heading_text = sec["heading"].lstrip("#").strip()
            final_lines.append(f"\n![{heading_text}]({img_url})")
            final_lines.append(f"*{heading_text} infographic*\n")
            
        final_lines.append(sec["content"])
        
    updated_content = "\n".join(final_lines)
    return updated_content, first_image_url
