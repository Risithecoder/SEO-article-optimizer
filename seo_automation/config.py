"""
config.py — Central configuration for the SEO/AEO automation pipeline.

Loads all settings from environment variables via a .env file.
Provides a single Config dataclass used across all modules.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Central configuration loaded from environment variables."""

    # ── OpenAI ──────────────────────────────────────────────
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))

    # ── Gemini (image generation only) ─────────────────────
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # ── WordPress ───────────────────────────────────────────
    wp_url: str = os.getenv("WP_URL", "")  # e.g. https://example.com
    wp_username: str = os.getenv("WP_USERNAME", "")
    wp_app_password: str = os.getenv("WP_APP_PASSWORD", "")
    wp_publish_status: str = os.getenv("WP_PUBLISH_STATUS", "draft")  # draft | publish

    # ── Database ────────────────────────────────────────────
    db_path: str = os.getenv("DB_PATH", "seo_automation.db")

    # ── Google Trends ───────────────────────────────────────
    trends_region: str = os.getenv("TRENDS_REGION", "india")
    trends_language: str = os.getenv("TRENDS_LANGUAGE", "en-IN")

    # ── Reddit ──────────────────────────────────────────────
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "SEOBot/1.0")

    # ── Article Settings ────────────────────────────────────
    min_word_count: int = int(os.getenv("MIN_WORD_COUNT", "1500"))
    max_word_count: int = int(os.getenv("MAX_WORD_COUNT", "2000"))
    articles_per_day: int = int(os.getenv("ARTICLES_PER_DAY", "10"))

    # ── Internal Linking ────────────────────────────────────
    related_links_count: int = int(os.getenv("RELATED_LINKS_COUNT", "3"))
    pillar_links_count: int = int(os.getenv("PILLAR_LINKS_COUNT", "1"))

    # ── Relevant Domains (for filtering broad trends) ──────
    relevant_domains: List[str] = field(default_factory=lambda: [
        "competitive exams",
        "government job preparation",
        "study techniques",
        "career guidance",
        "learning productivity",
        "exam notifications",
        "current affairs",
        "interview preparation",
        "mock tests",
        "skill building",
        "student productivity",
        "UPSC", "SSC", "banking exams", "IBPS", "SBI PO",
        "railways", "quantitative aptitude", "reasoning",
        "general knowledge", "exam preparation",
    ])

    # ── Seed Keywords (broad + exam-specific) ───────────────
    seed_keywords: List[str] = field(default_factory=lambda: [
        "exam preparation",
        "study tips",
        "government jobs",
        "career guidance",
        "competitive exams India",
        "current affairs today",
        "interview preparation",
        "UPSC preparation",
        "SSC exam tips",
        "banking exam preparation",
        "IBPS PO preparation",
        "SBI PO exam",
        "railway exam preparation",
        "mock test strategies",
        "student productivity tips",
        "skill building for jobs",
    ])

    # ── Reddit Subreddits ───────────────────────────────────
    reddit_subreddits: List[str] = field(default_factory=lambda: [
        "UPSC",
        "IndianExams",
        "India_Exams",
        "governmentjobs",
        "SSC",
        "bankexams",
        "Indian_Academia",
        "careerguidance",
    ])

    def validate(self) -> List[str]:
        """Return list of missing required configuration keys."""
        errors = []
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        if not self.wp_url:
            errors.append("WP_URL is required for publishing")
        if not self.wp_username:
            errors.append("WP_USERNAME is required for publishing")
        if not self.wp_app_password:
            errors.append("WP_APP_PASSWORD is required for publishing")
        return errors


# Singleton instance
config = Config()
