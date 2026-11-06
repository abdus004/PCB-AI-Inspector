"""SQLite persistence for inspection history (standard library only)."""
import json
import sqlite3
from contextlib import contextmanager
from typing import Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS inspections (
    id                 TEXT PRIMARY KEY,
    original_filename  TEXT NOT NULL,
    original_path      TEXT NOT NULL,
    annotated_path     TEXT NOT NULL,
    thumbnail_path     TEXT,
    created_at         TEXT NOT NULL,          -- UTC, ISO 8601
    detections_json    TEXT NOT NULL,
    total_detections   INTEGER NOT NULL,
    unique_classes     INTEGER NOT NULL,
    status             TEXT NOT NULL,
    model_json         TEXT NOT NULL,
    image_json         TEXT NOT NULL,
    low_confidence     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_inspections_created ON inspections (created_at DESC);
"""


@contextmanager
def get_connection():
    """One short-lived connection per operation keeps threading simple."""
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def insert_inspection(record: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO inspections (
                id, original_filename, original_path, annotated_path, thumbnail_path,
                created_at, detections_json, total_detections, unique_classes,
                status, model_json, image_json, low_confidence
            ) VALUES (
                :id, :original_filename, :original_path, :annotated_path, :thumbnail_path,
                :created_at, :detections_json, :total_detections, :unique_classes,
                :status, :model_json, :image_json, :low_confidence
            )
            """,
            record,
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["detections"] = json.loads(data.pop("detections_json"))
    data["model"] = json.loads(data.pop("model_json"))
    data["image"] = json.loads(data.pop("image_json"))
    return data


def get_inspection(inspection_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM inspections WHERE id = ?", (inspection_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_inspections(limit: int = 10, offset: int = 0) -> tuple[list[dict], int]:
    """Return (rows, total). Detection JSON is not decoded for the list view."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, original_filename, created_at, total_detections,
                   unique_classes, status, detections_json
            FROM inspections ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows], total


def delete_inspection(inspection_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM inspections WHERE id = ?", (inspection_id,))
        return cur.rowcount > 0
