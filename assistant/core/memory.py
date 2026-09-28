import sqlite3
from datetime import datetime


class MemoryStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def save(self, content):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (content, datetime.now().isoformat())
            )
            conn.commit()

        return {
            "success": True,
            "cancelled": False,
            "message": "기억해 두었습니다."
        }

    def search(self, keyword):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT content, created_at
                FROM memories
                WHERE content LIKE ?
                ORDER BY id DESC
                LIMIT 10
                """,
                (f"%{keyword}%",)
            ).fetchall()

        return {
            "success": True,
            "results": [
                {
                    "content": row[0],
                    "created_at": row[1]
                }
                for row in rows
            ],
            "message": (
                f"{len(rows)}개의 기억을 찾았습니다."
                if rows
                else "관련된 기억을 찾지 못했습니다."
            )
        }
