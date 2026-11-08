"""Riwayat percakapan dan statistik di SQLite.

Semua nilai dari pengguna dikirim lewat parameter `?`, tidak pernah
digabung ke teks SQL (mencegah SQL injection).
"""
from __future__ import annotations

import sqlite3

SKEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    theme      TEXT NOT NULL,
    sender     TEXT NOT NULL CHECK (sender IN ('user', 'bot')),
    text       TEXT NOT NULL,
    intent     TEXT,
    score      REAL,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_messages_sesi ON messages (session_id, theme, id);
"""


class ChatHistory:
    def __init__(self, path: str):
        self.path = path
        with self._conn() as conn:
            conn.executescript(SKEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, session_id: str, theme: str, sender: str, text: str,
            intent: str | None = None, score: float | None = None) -> None:
        conn = self._conn()
        try:
            with conn:  # commit bila berhasil, rollback bila galat
                conn.execute(
                    "INSERT INTO messages (session_id, theme, sender, text, intent, score) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, theme, sender, text, intent, score))
        finally:
            conn.close()

    def get(self, session_id: str, theme: str, limit: int = 200) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT sender, text, intent, score, created_at FROM ("
                "  SELECT * FROM messages WHERE session_id = ? AND theme = ? "
                "  ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (session_id, theme, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def last_bot_reply(self, session_id: str, theme: str) -> str | None:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT text FROM messages WHERE session_id = ? AND theme = ? "
                "AND sender = 'bot' ORDER BY id DESC LIMIT 1",
                (session_id, theme)).fetchone()
            return row["text"] if row else None
        finally:
            conn.close()

    def clear(self, session_id: str, theme: str) -> int:
        conn = self._conn()
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM messages WHERE session_id = ? AND theme = ?",
                    (session_id, theme))
                return cur.rowcount
        finally:
            conn.close()

    def stats(self, theme: str) -> dict:
        """Ringkasan untuk halaman admin."""
        conn = self._conn()
        try:
            per_intent = conn.execute(
                "SELECT COALESCE(intent, '(tidak dikenali)') AS intent, COUNT(*) AS jumlah "
                "FROM messages WHERE theme = ? AND sender = 'user' "
                "GROUP BY intent ORDER BY jumlah DESC, intent ASC", (theme,)).fetchall()
            total = sum(r["jumlah"] for r in per_intent)
            tak_dikenali = sum(r["jumlah"] for r in per_intent if r["intent"] == "(tidak dikenali)")
            sesi = conn.execute(
                "SELECT COUNT(DISTINCT session_id) AS n FROM messages WHERE theme = ?",
                (theme,)).fetchone()["n"]
            unknown = conn.execute(
                "SELECT text, score, created_at FROM messages "
                "WHERE theme = ? AND sender = 'user' AND intent IS NULL "
                "ORDER BY id DESC LIMIT 50", (theme,)).fetchall()
            return {
                "total": total,
                "dikenali": total - tak_dikenali,
                "tidak_dikenali": tak_dikenali,
                "persen_dikenali": round(100 * (total - tak_dikenali) / total, 1) if total else 0.0,
                "sesi": sesi,
                "per_intent": [dict(r) for r in per_intent],
                "unknown": [dict(r) for r in unknown],
            }
        finally:
            conn.close()
