import sqlite3
from pathlib import Path
from typing import Literal


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "feedback.sqlite3"


class FeedbackStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dislikes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL UNIQUE,
                    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('like', 'dislike')),
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._migrate_legacy_feedback(conn)

    def save_like(self, message_id: str, question: str, answer: str, created_at: str):
        self._save("like", message_id, question, answer, created_at)

    def save_dislike(
        self, message_id: str, question: str, answer: str, created_at: str
    ):
        self._save("dislike", message_id, question, answer, created_at)

    def _save(
        self,
        feedback_type: Literal["like", "dislike"],
        message_id: str,
        question: str,
        answer: str,
        created_at: str,
    ):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback (
                    message_id,
                    feedback_type,
                    question,
                    answer,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    feedback_type = excluded.feedback_type,
                    question = excluded.question,
                    answer = excluded.answer,
                    created_at = excluded.created_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (message_id, feedback_type, question, answer, created_at),
            )

    def _migrate_legacy_feedback(self, conn: sqlite3.Connection):
        legacy_rows = []

        if self._table_exists(conn, "likes"):
            legacy_rows.extend(
                conn.execute(
                    """
                    SELECT message_id, 'like' AS feedback_type, question, answer, created_at, stored_at, id
                    FROM likes
                    """
                ).fetchall()
            )

        if self._table_exists(conn, "dislikes"):
            legacy_rows.extend(
                conn.execute(
                    """
                    SELECT message_id, 'dislike' AS feedback_type, question, answer, created_at, stored_at, id
                    FROM dislikes
                    """
                ).fetchall()
            )

        legacy_rows.sort(key=lambda row: (row[5], row[6]))

        for message_id, feedback_type, question, answer, created_at, stored_at, _ in legacy_rows:
            conn.execute(
                """
                INSERT INTO feedback (
                    message_id,
                    feedback_type,
                    question,
                    answer,
                    created_at,
                    stored_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    feedback_type = excluded.feedback_type,
                    question = excluded.question,
                    answer = excluded.answer,
                    created_at = excluded.created_at,
                    stored_at = excluded.stored_at,
                    updated_at = excluded.updated_at
                """,
                (
                    message_id,
                    feedback_type,
                    question,
                    answer,
                    created_at,
                    stored_at,
                    stored_at,
                ),
            )

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        ).fetchone()
        return row is not None
