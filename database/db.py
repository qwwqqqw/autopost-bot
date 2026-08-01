import aiosqlite
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from config import DB_PATH

async def init_db():
    """Инициализация БД и создание таблиц."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_text TEXT,
                photo_path TEXT,
                buttons_json TEXT,
                publish_time TIMESTAMP,
                status TEXT DEFAULT 'pending',
                target_channel TEXT,
                telegram_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                user_id INTEGER,
                reaction_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_links (
                link TEXT PRIMARY KEY,
                summary TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Try to add summary column if table already existed without it
        try:
            await db.execute("ALTER TABLE published_links ADD COLUMN summary TEXT")
        except Exception:
            pass
        await db.commit()
        await db.commit()

async def get_setting(key: str, default: str = None) -> str:
    """Получение настройки по ключу."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default

async def set_setting(key: str, value: str):
    """Сохранение или обновление настройки."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO settings (key, value) 
            VALUES (?, ?) 
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        await db.commit()

async def add_scheduled_post(content_text: str, photo_path: Optional[str], buttons: list, publish_time: str, target_channel: str) -> int:
    """Добавление отложенного поста в очередь."""
    buttons_json = json.dumps(buttons, ensure_ascii=False)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO scheduled_posts (content_text, photo_path, buttons_json, publish_time, target_channel)
            VALUES (?, ?, ?, ?, ?)
        """, (content_text, photo_path, buttons_json, publish_time, target_channel))
        await db.commit()
        return cursor.lastrowid

async def get_post_by_id(post_id: int) -> Optional[Dict]:
    """Получение поста по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_due_posts(current_time_iso: str) -> List[Dict]:
    """Получение постов, время публикации которых наступило."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM scheduled_posts
            WHERE status = 'pending' AND publish_time <= ?
            ORDER BY publish_time ASC
        """, (current_time_iso,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def mark_post_published(post_id: int, telegram_message_id: int):
    """Отметка поста как опубликованного."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE scheduled_posts
            SET status = 'published', telegram_message_id = ?
            WHERE id = ?
        """, (telegram_message_id, post_id))
        await db.commit()

async def get_pending_posts() -> List[Dict]:
    """Получение всех запланированных постов."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM scheduled_posts
            WHERE status = 'pending'
            ORDER BY publish_time ASC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def cancel_scheduled_post(post_id: int):
    """Отмена запланированного поста."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE scheduled_posts SET status = 'cancelled' WHERE id = ?", (post_id,))
        await db.commit()

async def toggle_reaction(post_id: int, user_id: int, reaction_type: str) -> Dict[str, int]:
    """Добавление/изменение реакции пользователя на пост."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reaction_type FROM reactions WHERE post_id = ? AND user_id = ?",
            (post_id, user_id)
        )
        row = await cursor.fetchone()
        
        if row:
            if row[0] == reaction_type:
                await db.execute("DELETE FROM reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            else:
                await db.execute(
                    "UPDATE reactions SET reaction_type = ? WHERE post_id = ? AND user_id = ?",
                    (reaction_type, post_id, user_id)
                )
        else:
            await db.execute(
                "INSERT INTO reactions (post_id, user_id, reaction_type) VALUES (?, ?, ?)",
                (post_id, user_id, reaction_type)
            )
        await db.commit()

        cursor = await db.execute("""
            SELECT reaction_type, COUNT(*) FROM reactions
            WHERE post_id = ?
            GROUP BY reaction_type
        """, (post_id,))
        rows = await cursor.fetchall()
        counts = {r[0]: r[1] for r in rows}
        return counts

async def check_link_published(link: str) -> bool:
    """Проверяет, публиковалась ли уже эта новость."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM published_links WHERE link = ?", (link,))
        row = await cursor.fetchone()
        return bool(row)

async def mark_link_published(link: str, summary: str = ""):
    """Отмечает ссылку как опубликованную (вместе с ее саммари для ИИ проверки дубликатов)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO published_links (link, summary) VALUES (?, ?)", (link, summary))
        await db.commit()

async def get_recent_summaries(limit: int = 15) -> List[str]:
    """Возвращает список саммари последних опубликованных постов."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT summary FROM published_links WHERE summary IS NOT NULL AND summary != '' ORDER BY published_at DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def get_published_count_last_hour() -> int:
    """Возвращает количество успешно опубликованных постов за последний час."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM published_links WHERE summary IS NOT NULL AND summary != '' AND published_at >= datetime('now', '-1 hour')"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
