"""
pipeline_controller.py — Runs the SEO pipeline in a background thread.

Provides an event-bus that broadcasts step status changes and log
messages to all connected WebSocket clients, so the React frontend
can show real-time progress.
"""

import asyncio
import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..config import config
from ..database import Database
from ..trend_fetcher import fetch_trending_keywords
from ..keyword_expander import expand_keywords
from ..keyword_cluster import cluster_keywords
from ..blueprint_generator import generate_blueprints
from ..article_generator import generate_articles
from ..seo_optimizer import optimize_articles
from ..internal_linker import add_internal_links_batch
from ..publisher import publish_article
from ..utils.deduplicator import deduplicate_keywords
from ..utils.image_generator import generate_images_for_articles

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Step definitions
# ────────────────────────────────────────────────────────────

PIPELINE_STEPS = [
    {"id": "trend_fetch",  "label": "Trend Fetcher",              "description": "Fetching trending keywords..."},
    {"id": "expand",       "label": "Keyword Expansion",          "description": "Expanding keywords..."},
    {"id": "cluster",      "label": "Keyword Clustering",         "description": "Clustering keywords into topics..."},
    {"id": "blueprint",    "label": "Article Blueprint Generation","description": "Generating article blueprints..."},
    {"id": "generate",     "label": "Article Generation",         "description": "Writing articles..."},
    {"id": "image_gen",    "label": "Image Generation",           "description": "Generating article images..."},
    {"id": "optimize",     "label": "SEO/AEO Optimization",       "description": "Optimizing for SEO and AI Overviews..."},
    {"id": "link",         "label": "Internal Linking",           "description": "Adding internal links..."},
    {"id": "publish_queue","label": "Publishing Queue",           "description": "Articles queued for review"},
]


class StepStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ────────────────────────────────────────────────────────────
# Singleton controller
# ────────────────────────────────────────────────────────────

class PipelineController:
    """
    Controls a single pipeline execution in a background thread.
    Broadcasts events to WebSocket subscribers.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._cancel_requested = False
        self._thread: Optional[threading.Thread] = None

        # Step statuses
        self.steps: Dict[str, Dict[str, Any]] = {}
        self._reset_steps()

        # Log buffer (last 500 messages)
        self.logs: deque = deque(maxlen=500)

        # WebSocket subscribers (asyncio queues)
        self._subscribers: Set[asyncio.Queue] = set()

        # Install custom log handler to capture logs
        self._install_log_handler()

    def _reset_steps(self):
        """Reset all step statuses to idle."""
        self.steps = {}
        for step_def in PIPELINE_STEPS:
            self.steps[step_def["id"]] = {
                "id": step_def["id"],
                "label": step_def["label"],
                "description": step_def["description"],
                "status": StepStatus.IDLE,
                "detail": "",
            }

    def _install_log_handler(self):
        """Add a handler that captures log messages for the frontend."""
        handler = _WebSocketLogHandler(self)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
            datefmt="%H:%M:%S",
        ))
        logging.getLogger("seo_automation").addHandler(handler)
        logging.getLogger("seo_automation").setLevel(logging.INFO)

    # ── Subscriber management ──────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        """Add a WebSocket subscriber. Returns an asyncio Queue."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a WebSocket subscriber."""
        self._subscribers.discard(q)

    def _broadcast(self, event: Dict[str, Any]):
        """Push an event to all WebSocket subscribers."""
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    # ── Step status updates ────────────────────────────────

    def _set_step(self, step_id: str, status: StepStatus, detail: str = ""):
        """Update a step's status and broadcast."""
        if step_id in self.steps:
            self.steps[step_id]["status"] = status
            self.steps[step_id]["detail"] = detail
            self._broadcast({
                "type": "step_update",
                "step_id": step_id,
                "status": status,
                "detail": detail,
                "label": self.steps[step_id]["label"],
            })

    def _add_log(self, message: str, level: str = "INFO"):
        """Add a log entry and broadcast."""
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        self._broadcast({"type": "log", **entry})

    # ── Pipeline state ─────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Return current pipeline status for REST API."""
        return {
            "running": self._running,
            "steps": list(self.steps.values()),
        }

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent log entries."""
        return list(self.logs)[-limit:]

    # ── Start / Stop ───────────────────────────────────────

    def start(self, dry_run: bool = False, limit: int = 0) -> bool:
        """
        Start the pipeline in a background thread.
        Returns False if already running.
        """
        with self._lock:
            if self._running:
                return False
            self._running = True

        self._reset_steps()
        self.logs.clear()
        self._cancel_requested = False
        self._add_log("Pipeline starting...")

        self._thread = threading.Thread(
            target=self._run_pipeline,
            args=(dry_run, limit),
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> bool:
        """
        Request the pipeline to stop gracefully.
        Returns True if a stop was requested, False if it wasn't running.
        """
        with self._lock:
            if not self._running:
                return False
            self._cancel_requested = True
        self._add_log("Stop requested. Pipeline will halt after compiling current step.", "WARNING")
        return True

    def _run_pipeline(self, dry_run: bool, limit: int):
        """Execute all pipeline steps in sequence."""
        try:
            max_articles = limit if limit > 0 else config.articles_per_day

            with Database() as db:
                # ── Step 1: Trend Fetch ─────────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("trend_fetch", StepStatus.RUNNING, "Fetching trending keywords...")
                try:
                    if dry_run:
                        raw_keywords = _mock_keywords()
                        self._add_log(f"[DRY RUN] Using {len(raw_keywords)} mock keywords")
                    else:
                        raw_keywords = fetch_trending_keywords(skip_scraping=False)

                    existing = {kw["keyword"] for kw in db.get_all_keywords()}
                    unique_keywords = deduplicate_keywords(raw_keywords, existing)
                    inserted = db.save_keywords(unique_keywords)
                    self._set_step("trend_fetch", StepStatus.COMPLETED, f"Saved {inserted} keywords")
                    self._add_log(f"Trend fetch complete: {inserted} new keywords")
                except Exception as e:
                    self._set_step("trend_fetch", StepStatus.FAILED, str(e))
                    self._add_log(f"Trend fetch failed: {e}", "ERROR")

                # ── Step 2: Expand ──────────────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Keywork Expansion.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("expand", StepStatus.RUNNING, "Expanding keywords into long-tail queries...")
                try:
                    unexpanded = db.get_unexpanded_keywords()
                    if unexpanded:
                        if dry_run:
                            expanded = [
                                {"keyword": f"how to {kw['keyword']} for beginners", "source": "mock_expanded", "timestamp": ""}
                                for kw in unexpanded[:5]
                            ]
                        else:
                            expanded = expand_keywords(unexpanded)
                        inserted = db.save_keywords(expanded)
                        db.mark_keywords_expanded([kw["id"] for kw in unexpanded])
                        self._add_log(f"Expanded {len(unexpanded)} keywords → {inserted} new long-tail")
                    self._set_step("expand", StepStatus.COMPLETED, f"{len(unexpanded)} keywords expanded")
                except Exception as e:
                    self._set_step("expand", StepStatus.FAILED, str(e))
                    self._add_log(f"Keyword expansion failed: {e}", "ERROR")

                # ── Step 3: Cluster ─────────────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Clustering.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("cluster", StepStatus.RUNNING, "Clustering keywords into topics...")
                try:
                    all_keywords = db.get_all_keywords()
                    unclustered = [kw for kw in all_keywords if not kw.get("cluster_id")]
                    if unclustered:
                        if dry_run:
                            clusters_data = [{
                                "cluster_name": "Exam Preparation Strategy",
                                "primary_keyword": unclustered[0]["keyword"],
                                "supporting_keywords": [kw["keyword"] for kw in unclustered[1:4]],
                            }]
                        else:
                            clusters_data = cluster_keywords(unclustered)
                        for cluster in clusters_data:
                            cid = db.save_cluster(cluster)
                            cluster["id"] = cid
                        self._add_log(f"Created {len(clusters_data)} keyword clusters")
                    self._set_step("cluster", StepStatus.COMPLETED, f"{len(unclustered)} keywords clustered")
                except Exception as e:
                    self._set_step("cluster", StepStatus.FAILED, str(e))
                    self._add_log(f"Clustering failed: {e}", "ERROR")

                # ── Step 4: Blueprint ───────────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Blueprint generation.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("blueprint", StepStatus.RUNNING, "Generating article blueprints...")
                try:
                    all_clusters = db.get_all_clusters()
                    existing_bp_ids = {bp["cluster_id"] for bp in db.get_all_blueprints()}
                    new_clusters = [c for c in all_clusters if c["id"] not in existing_bp_ids][:max_articles]

                    if new_clusters:
                        if dry_run:
                            bps = [{
                                "cluster_id": c.get("id", 0),
                                "title": f"Complete Guide to {c['cluster_name']}",
                                "slug": c["primary_keyword"].replace(" ", "-"),
                                "meta_description": f"Learn everything about {c['primary_keyword']}.",
                                "outline": [{"level": "h2", "text": f"What is {c['primary_keyword']}?"}],
                                "word_count": 1800,
                                "faq_questions": [f"What is {c['primary_keyword']}?"],
                                "semantic_keywords": c.get("supporting_keywords", []),
                                "snippet_answers": [],
                            } for c in new_clusters]
                        else:
                            bps = generate_blueprints(new_clusters)
                        for bp in bps:
                            bp["id"] = db.save_blueprint(bp)
                        self._add_log(f"Created {len(bps)} article blueprints")
                    self._set_step("blueprint", StepStatus.COMPLETED, f"{len(new_clusters)} blueprints created")
                except Exception as e:
                    self._set_step("blueprint", StepStatus.FAILED, str(e))
                    self._add_log(f"Blueprint generation failed: {e}", "ERROR")

                # ── Step 5: Generate Articles ───────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Article generation.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("generate", StepStatus.RUNNING, "Writing articles...")
                try:
                    pending_bps = db.get_blueprints_without_articles()[:max_articles]
                    if pending_bps:
                        if dry_run:
                            arts = [{
                                "blueprint_id": bp.get("id", 0),
                                "title": bp["title"],
                                "slug": bp["slug"],
                                "content": f"# {bp['title']}\n\nThis is a comprehensive guide about {bp['title']}.\n\n## Introduction\n\nIn this article, we cover everything you need to know.\n\n## Key Strategies\n\n- Tip 1: Start early\n- Tip 2: Be consistent\n- Tip 3: Use mock tests\n\n## FAQ\n\n### What is the best approach?\n\nThe best approach is consistent daily practice with focused study sessions.\n\n## Conclusion\n\nFollow these strategies to succeed.",
                                "meta_description": bp.get("meta_description", ""),
                                "status": "draft",
                            } for bp in pending_bps]
                        else:
                            arts = generate_articles(pending_bps)
                        for art in arts:
                            art["id"] = db.save_article(art)
                        self._add_log(f"Generated {len(arts)} articles")
                    self._set_step("generate", StepStatus.COMPLETED, f"{len(pending_bps)} articles written")
                except Exception as e:
                    self._set_step("generate", StepStatus.FAILED, str(e))
                    self._add_log(f"Article generation failed: {e}", "ERROR")

                # ── Step 6: Image Generation ────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Image generation.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("image_gen", StepStatus.RUNNING, "Generating article images...")
                try:
                    draft_arts = db.get_articles_needing_images()
                    if draft_arts and not dry_run:
                        # images is a Dict: {article_id: {"filename": "...", ...}}
                        images = generate_images_for_articles(draft_arts)
                        
                        # Save the generated image paths to the database so the frontend can load them
                        for art_id, img_info in images.items():
                            file_name = img_info.get("filename")
                            if file_name:
                                db.update_article(art_id, {"image_url": f"/images/{file_name}"})
                                
                        self._add_log(f"Generated {len(images)} images")
                    elif dry_run:
                        self._add_log("[DRY RUN] Skipping image generation")
                    self._set_step("image_gen", StepStatus.COMPLETED, f"{len(draft_arts)} images processed")
                except Exception as e:
                    self._set_step("image_gen", StepStatus.FAILED, str(e))
                    self._add_log(f"Image generation failed: {e}", "ERROR")

                # ── Step 7: SEO/AEO Optimize ────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before SEO Optimization.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("optimize", StepStatus.RUNNING, "Optimizing for SEO and AI Overviews...")
                try:
                    drafts = db.get_unpublished_articles()
                    if drafts:
                        all_bps = db.get_all_blueprints()
                        optimised = optimize_articles(drafts, all_bps)
                        for art in optimised:
                            if art.get("id"):
                                db.update_article(art["id"], {
                                    "html_content": art.get("html_content", ""),
                                    "schema_markup": art.get("schema_markup", {}),
                                    "status": "optimized",
                                })
                        self._add_log(f"Optimised {len(optimised)} articles")
                    self._set_step("optimize", StepStatus.COMPLETED, f"{len(drafts)} articles optimized")
                except Exception as e:
                    self._set_step("optimize", StepStatus.FAILED, str(e))
                    self._add_log(f"SEO optimization failed: {e}", "ERROR")

                # ── Step 7: Internal Linking ────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Internal Linking.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("link", StepStatus.RUNNING, "Adding internal links...")
                try:
                    opt_arts = [a for a in db.get_all_articles() if a.get("status") == "optimized"]
                    pub_arts = db.get_published_articles()
                    all_clusters = db.get_all_clusters()
                    if opt_arts:
                        linked = add_internal_links_batch(opt_arts, pub_arts, all_clusters, site_url=config.wp_url)
                        for art in linked:
                            if art.get("id"):
                                db.update_article(art["id"], {"html_content": art.get("html_content", "")})
                        self._add_log(f"Added internal links to {len(linked)} articles")
                    self._set_step("link", StepStatus.COMPLETED, f"{len(opt_arts)} articles linked")
                except Exception as e:
                    self._set_step("link", StepStatus.FAILED, str(e))
                    self._add_log(f"Internal linking failed: {e}", "ERROR")

                # ── Step 8: Queue for review ────────────────
                if self._cancel_requested:
                    self._add_log("Pipeline cancelled by user before Review queuing.", "WARNING")
                    self._broadcast({"type": "pipeline_complete"})
                    return
                self._set_step("publish_queue", StepStatus.RUNNING, "Queueing articles for review...")
                try:
                    ready = db.get_unpublished_articles()
                    # Mark them as awaiting approval instead of auto-publishing
                    for art in ready:
                        if art.get("id") and art.get("status") == "optimized":
                            db.update_article(art["id"], {"status": "awaiting_approval"})
                    self._set_step("publish_queue", StepStatus.COMPLETED, f"{len(ready)} articles queued")
                    self._add_log(f"{len(ready)} articles queued for manual approval")
                except Exception as e:
                    self._set_step("publish_queue", StepStatus.FAILED, str(e))

            self._add_log("Pipeline complete! Articles are ready for review.")
            self._broadcast({"type": "pipeline_complete"})

        except Exception as exc:
            self._add_log(f"Pipeline error: {exc}", "ERROR")
            logger.exception("Pipeline failed")
        finally:
            with self._lock:
                self._running = False


# ────────────────────────────────────────────────────────────
# Log handler that feeds into the controller
# ────────────────────────────────────────────────────────────

class _WebSocketLogHandler(logging.Handler):
    """Captures log records and pushes them to the controller."""

    def __init__(self, controller: PipelineController):
        super().__init__()
        self.controller = controller

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.controller._add_log(msg, record.levelname)
        except Exception:
            pass


# ── Mock data ──────────────────────────────────────────────

def _mock_keywords():
    return [
        {"keyword": "upsc preparation strategy 2026", "source": "mock", "timestamp": ""},
        {"keyword": "ssc cgl exam pattern", "source": "mock", "timestamp": ""},
        {"keyword": "banking exam current affairs", "source": "mock", "timestamp": ""},
        {"keyword": "study tips for competitive exams", "source": "mock", "timestamp": ""},
        {"keyword": "how to improve reasoning ability", "source": "mock", "timestamp": ""},
        {"keyword": "government job interview tips", "source": "mock", "timestamp": ""},
        {"keyword": "best mock test platforms india", "source": "mock", "timestamp": ""},
        {"keyword": "student productivity techniques", "source": "mock", "timestamp": ""},
    ]


# Singleton
controller = PipelineController()
