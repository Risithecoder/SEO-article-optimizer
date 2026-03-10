"""
api_routes.py — FastAPI REST + WebSocket endpoints for the GUI dashboard.

Provides endpoints for pipeline control, article management,
and real-time status updates via WebSocket.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query

from ..database import Database
from ..publisher import publish_article as wp_publish_article
from .pipeline_controller import controller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ── Helper ─────────────────────────────────────────────────

def _get_db() -> Database:
    """Create and connect a Database instance."""
    db = Database()
    db.connect()
    return db


# ────────────────────────────────────────────────────────────
# Pipeline control
# ────────────────────────────────────────────────────────────

@router.post("/start_pipeline")
async def start_pipeline(
    dry_run: bool = Query(False),
    limit: int = Query(0),
):
    """Start the content pipeline in the background."""
    if controller.is_running:
        raise HTTPException(400, "Pipeline is already running")
    started = controller.start(dry_run=dry_run, limit=limit)
    if not started:
        raise HTTPException(400, "Failed to start pipeline")
    return {"status": "started", "dry_run": dry_run, "limit": limit}

@router.post("/stop_pipeline")
async def stop_pipeline():
    """Request the running pipeline to stop gracefuly."""
    stopped = controller.stop()
    if not stopped:
        raise HTTPException(400, "Pipeline is not currently running")
    return {"status": "stop_requested"}


@router.get("/pipeline_status")
async def pipeline_status():
    """Return current status of all pipeline steps."""
    return controller.get_status()


@router.get("/logs")
async def get_logs(limit: int = Query(100)):
    """Return recent log entries."""
    return {"logs": controller.get_logs(limit)}


@router.get("/stats")
async def get_stats():
    """Return system-wide statistics."""
    db = _get_db()
    try:
        stats = db.get_stats()
        stats["pipeline_running"] = controller.is_running
        return stats
    finally:
        db.close()


# ────────────────────────────────────────────────────────────
# Articles
# ────────────────────────────────────────────────────────────

@router.get("/articles")
async def list_articles():
    """Return all articles."""
    db = _get_db()
    try:
        articles = db.get_all_articles()
        # Parse JSON fields
        for art in articles:
            if art.get("schema_markup") and isinstance(art["schema_markup"], str):
                try:
                    art["schema_markup"] = json.loads(art["schema_markup"])
                except (json.JSONDecodeError, TypeError):
                    pass
        return {"articles": articles}
    finally:
        db.close()


@router.get("/articles/{article_id}")
async def get_article(article_id: int):
    """Return a single article by ID."""
    db = _get_db()
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        if article.get("schema_markup") and isinstance(article["schema_markup"], str):
            try:
                article["schema_markup"] = json.loads(article["schema_markup"])
            except (json.JSONDecodeError, TypeError):
                pass
        return article
    finally:
        db.close()


@router.post("/articles/{article_id}/approve")
async def approve_article(article_id: int):
    """Approve an article for publishing."""
    db = _get_db()
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        db.update_article(article_id, {"status": "approved"})
        return {"status": "approved", "article_id": article_id}
    finally:
        db.close()


@router.post("/articles/{article_id}/reject")
async def reject_article(article_id: int):
    """Reject an article."""
    db = _get_db()
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        db.update_article(article_id, {"status": "rejected"})
        return {"status": "rejected", "article_id": article_id}
    finally:
        db.close()


@router.post("/articles/{article_id}/regenerate")
async def regenerate_article(article_id: int):
    """Queue an article for regeneration."""
    db = _get_db()
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        db.update_article(article_id, {"status": "regenerate_queued"})
        return {"status": "regenerate_queued", "article_id": article_id}
    finally:
        db.close()


@router.post("/articles/{article_id}/publish")
async def publish_article(article_id: int):
    """Publish a single article to WordPress."""
    db = _get_db()
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(404, "Article not found")

        result = wp_publish_article(article, status="publish")
        if result["success"]:
            db.update_article(article_id, {
                "status": "published",
                "published_url": result["url"],
            })
            db.log_publish(article_id, "success", json.dumps(result))
            return {"status": "published", "url": result["url"]}
        else:
            db.log_publish(article_id, "failed", result["error"])
            raise HTTPException(500, f"Publish failed: {result['error']}")
    finally:
        db.close()


@router.delete("/articles/{article_id}")
async def delete_article(article_id: int):
    """Delete an article."""
    db = _get_db()
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        db.delete_article(article_id)
        return {"status": "deleted", "article_id": article_id}
    finally:
        db.close()


# ────────────────────────────────────────────────────────────
# WebSocket — real-time updates
# ────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time pipeline updates.
    Sends JSON events:
      - {type: "step_update", step_id, status, detail, label}
      - {type: "log", timestamp, level, message}
      - {type: "pipeline_complete"}
    """
    await websocket.accept()

    queue = controller.subscribe()
    try:
        # Send current state on connect
        await websocket.send_json({
            "type": "initial_state",
            "status": controller.get_status(),
            "logs": controller.get_logs(50),
        })

        # Stream events
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        controller.unsubscribe(queue)
