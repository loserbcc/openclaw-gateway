"""SQLite message storage for history and persistence."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from .config import settings

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(db_path))
        _db.row_factory = aiosqlite.Row
        await _init_tables(_db)
    return _db


async def _init_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'text',
            priority TEXT NOT NULL DEFAULT 'normal',
            text_content TEXT,
            audio_url TEXT,
            image_url TEXT,
            file_url TEXT,
            metadata TEXT
        )
    """)
    await db.commit()


async def store_message(
    source: str,
    type: str = "text",
    priority: str = "normal",
    text_content: str | None = None,
    audio_url: str | None = None,
    image_url: str | None = None,
    file_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db = await get_db()
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT INTO messages
           (id, created_at, source, type, priority, text_content, audio_url, image_url, file_url, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            msg_id,
            now,
            source,
            type,
            priority,
            text_content,
            audio_url,
            image_url,
            file_url,
            json.dumps(metadata) if metadata else None,
        ),
    )
    await db.commit()

    return {
        "id": msg_id,
        "created_at": now,
        "source": source,
        "type": type,
        "priority": priority,
        "text_content": text_content,
        "audio_url": audio_url,
        "image_url": image_url,
        "file_url": file_url,
    }


async def get_messages(limit: int = 50) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in reversed(rows)]


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
