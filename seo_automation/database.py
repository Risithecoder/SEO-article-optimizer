"""
database.py — SQLite database layer for the SEO/AEO automation pipeline.

Manages all persistent storage: keywords, clusters, blueprints,
articles, and publish logs. Automatically creates tables on first run.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import config


class Database:
    """SQLite database manager for the SEO automation pipeline."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        self.conn: Optional[sqlite3.Connection] = None

    # ── Connection ──────────────────────────────────────────

    def connect(self) -> None:
        """Open the database connection and create tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ── Schema ──────────────────────────────────────────────

    def _create_tables(self) -> None:
        """Create all required tables if they do not exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword     TEXT NOT NULL,
                source      TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                cluster_id  INTEGER,
                expanded    INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(keyword)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_name        TEXT NOT NULL,
                primary_keyword     TEXT NOT NULL,
                supporting_keywords TEXT NOT NULL,
                created_at          TEXT DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blueprints (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id       INTEGER NOT NULL,
                title            TEXT NOT NULL,
                slug             TEXT NOT NULL,
                meta_description TEXT,
                outline          TEXT,
                word_count       INTEGER DEFAULT 1800,
                faq_questions    TEXT,
                semantic_keywords TEXT,
                snippet_answers  TEXT,
                created_at       TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (cluster_id) REFERENCES clusters(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                blueprint_id    INTEGER NOT NULL,
                title           TEXT NOT NULL,
                slug            TEXT NOT NULL,
                content         TEXT,
                html_content    TEXT,
                schema_markup   TEXT,
                meta_description TEXT,
                image_url       TEXT,
                status          TEXT DEFAULT 'draft',
                published_url   TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (blueprint_id) REFERENCES blueprints(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publish_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id  INTEGER NOT NULL,
                status      TEXT NOT NULL,
                response    TEXT,
                timestamp   TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)

        self.conn.commit()
        
        # Simple migration for existing databases
        try:
            cursor.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column likely already exists

    # ── Keywords ────────────────────────────────────────────

    def save_keywords(self, keywords: List[Dict[str, str]]) -> int:
        """
        Save a list of keyword dicts. Skips duplicates.
        Returns the number of newly inserted keywords.
        """
        cursor = self.conn.cursor()
        inserted = 0
        for kw in keywords:
            try:
                cursor.execute(
                    "INSERT INTO keywords (keyword, source, timestamp) VALUES (?, ?, ?)",
                    (kw["keyword"].lower().strip(), kw["source"], kw.get("timestamp", _now())),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # duplicate keyword
        self.conn.commit()
        return inserted

    def keyword_exists(self, keyword: str) -> bool:
        """Check whether a keyword already exists in the DB."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM keywords WHERE keyword = ?", (keyword.lower().strip(),))
        return cursor.fetchone() is not None

    def get_unexpanded_keywords(self) -> List[Dict[str, Any]]:
        """Return keywords not yet expanded into long-tail variants."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, keyword, source FROM keywords WHERE expanded = 0")
        return [dict(row) for row in cursor.fetchall()]

    def mark_keywords_expanded(self, keyword_ids: List[int]) -> None:
        """Mark keywords as expanded."""
        cursor = self.conn.cursor()
        cursor.executemany(
            "UPDATE keywords SET expanded = 1 WHERE id = ?",
            [(kid,) for kid in keyword_ids],
        )
        self.conn.commit()

    def get_all_keywords(self) -> List[Dict[str, Any]]:
        """Return all stored keywords."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, keyword, source, cluster_id FROM keywords")
        return [dict(row) for row in cursor.fetchall()]

    def update_keyword_cluster(self, keyword_id: int, cluster_id: int) -> None:
        """Assign a keyword to a cluster."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE keywords SET cluster_id = ? WHERE id = ?", (cluster_id, keyword_id))
        self.conn.commit()

    # ── Clusters ────────────────────────────────────────────

    def save_cluster(self, cluster: Dict[str, Any]) -> int:
        """Save a keyword cluster. Returns the cluster id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO clusters (cluster_name, primary_keyword, supporting_keywords)
               VALUES (?, ?, ?)""",
            (
                cluster["cluster_name"],
                cluster["primary_keyword"],
                json.dumps(cluster["supporting_keywords"]),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_clusters(self) -> List[Dict[str, Any]]:
        """Return all clusters."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM clusters")
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            row["supporting_keywords"] = json.loads(row["supporting_keywords"])
        return rows

    # ── Blueprints ──────────────────────────────────────────

    def save_blueprint(self, bp: Dict[str, Any]) -> int:
        """Save an article blueprint. Returns the blueprint id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO blueprints
               (cluster_id, title, slug, meta_description, outline,
                word_count, faq_questions, semantic_keywords, snippet_answers)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bp["cluster_id"],
                bp["title"],
                bp["slug"],
                bp.get("meta_description", ""),
                json.dumps(bp.get("outline", [])),
                bp.get("word_count", 1800),
                json.dumps(bp.get("faq_questions", [])),
                json.dumps(bp.get("semantic_keywords", [])),
                json.dumps(bp.get("snippet_answers", [])),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_blueprints_without_articles(self) -> List[Dict[str, Any]]:
        """Return blueprints that do not yet have generated articles."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT b.* FROM blueprints b
            LEFT JOIN articles a ON a.blueprint_id = b.id
            WHERE a.id IS NULL
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            for field in ("outline", "faq_questions", "semantic_keywords", "snippet_answers"):
                if row.get(field):
                    row[field] = json.loads(row[field])
        return rows

    def get_all_blueprints(self) -> List[Dict[str, Any]]:
        """Return all blueprints."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM blueprints")
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            for field in ("outline", "faq_questions", "semantic_keywords", "snippet_answers"):
                if row.get(field):
                    row[field] = json.loads(row[field])
        return rows

    # ── Articles ────────────────────────────────────────────

    def save_article(self, article: Dict[str, Any]) -> int:
        """Save a generated article. Returns the article id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO articles
               (blueprint_id, title, slug, content, html_content,
                schema_markup, meta_description, image_url, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                article["blueprint_id"],
                article["title"],
                article["slug"],
                article.get("content", ""),
                article.get("html_content", ""),
                json.dumps(article.get("schema_markup", {})),
                article.get("meta_description", ""),
                article.get("image_url", ""),
                article.get("status", "draft"),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_article(self, article_id: int, updates: Dict[str, Any]) -> None:
        """Update fields of an existing article."""
        cursor = self.conn.cursor()
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(json.dumps(value) if isinstance(value, (dict, list)) else value)
        values.append(article_id)
        cursor.execute(
            f"UPDATE articles SET {', '.join(set_clauses)} WHERE id = ?",
            values,
        )
        self.conn.commit()

    def get_unpublished_articles(self) -> List[Dict[str, Any]]:
        """Return articles that haven't been published yet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE status != 'published' AND status != 'failed'")
        return [dict(row) for row in cursor.fetchall()]

    def get_articles_needing_images(self) -> List[Dict[str, Any]]:
        """Return articles that don't have an image URL yet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE (image_url IS NULL OR image_url = '') AND status != 'published'")
        return [dict(row) for row in cursor.fetchall()]

    def get_published_articles(self) -> List[Dict[str, Any]]:
        """Return all published articles with their URLs."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE status = 'published'")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Return all articles."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_article_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Return a single article by its ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_article(self, article_id: int) -> None:
        """Delete an article by its ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM publish_log WHERE article_id = ?", (article_id,))
        cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        self.conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Return system-wide statistics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM keywords")
        keywords_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clusters")
        clusters_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM articles")
        articles_total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'awaiting_approval'")
        awaiting = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'published'")
        published = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'draft' OR status = 'optimized'")
        drafts = cursor.fetchone()[0]
        return {
            "keywords_fetched": keywords_count,
            "clusters_created": clusters_count,
            "articles_total": articles_total,
            "articles_awaiting_approval": awaiting,
            "articles_published": published,
            "articles_draft": drafts,
        }

    # ── Publish Log ─────────────────────────────────────────

    def log_publish(self, article_id: int, status: str, response: str = "") -> None:
        """Log a publish attempt."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO publish_log (article_id, status, response) VALUES (?, ?, ?)",
            (article_id, status, response),
        )
        self.conn.commit()


def _now() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()
