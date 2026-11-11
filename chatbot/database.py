"""Penyimpanan riwayat percakapan menggunakan SQLite (modul bawaan Python)."""
import sqlite3
from pathlib import Path

SKEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL,
    theme       TEXT    NOT NULL,
    sender      TEXT    NOT NULL CHECK (sender IN ('user', 'bot')),
    text        TEXT    NOT NULL,
    intent      TEXT,
    score       REAL,
    created_at  TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_session_theme ON messages (session_id, theme);
"""


class ChatHistory:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.executescript(SKEMA)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row          # baris bisa diakses seperti dict
        return conn

    def add(self, session_id, theme, sender, text, intent=None, score=None):
        sql = ("INSERT INTO messages (session_id, theme, sender, text, intent, score) "
               "VALUES (?, ?, ?, ?, ?, ?)")    # parameter ? mencegah SQL injection
        conn = self._connect()
        try:
            with conn:                          # commit bila berhasil, rollback bila galat
                conn.execute(sql, (session_id, theme, sender, text, intent, score))
        finally:
            conn.close()

    def get(self, session_id, theme, limit=50):
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT sender, text, intent, score, created_at FROM messages "
                "WHERE session_id = ? AND theme = ? ORDER BY id DESC LIMIT ?",
                (session_id, theme, limit),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in reversed(rows)]

    def last_bot_reply(self, session_id, theme):
        """Balasan bot terakhir pada sesi ini (untuk 'ulangi jawaban tadi')."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT text FROM messages WHERE session_id = ? AND theme = ? "
                "AND sender = 'bot' ORDER BY id DESC LIMIT 1",
                (session_id, theme),
            ).fetchone()
        finally:
            conn.close()
        return row["text"] if row else None

    def clear(self, session_id, theme):
        conn = self._connect()
        try:
            with conn:
                conn.execute("DELETE FROM messages WHERE session_id = ? AND theme = ?",
                             (session_id, theme))
        finally:
            conn.close()

    def stats(self, theme):
        """Jumlah pertanyaan pengguna per intent (bahan evaluasi)."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT COALESCE(intent, '(tidak dikenali)') AS intent, COUNT(*) AS jumlah "
                "FROM messages WHERE theme = ? AND sender = 'user' "
                "GROUP BY intent ORDER BY jumlah DESC, intent ASC",
                (theme,),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def unknown_questions(self, theme, limit=20):
        """Pertanyaan terbaru yang tidak dikenali bot (kandidat pola baru)."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT text, score, created_at FROM messages "
                "WHERE theme = ? AND sender = 'user' AND intent IS NULL "
                "ORDER BY id DESC LIMIT ?",
                (theme, limit),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def summary(self, theme):
        """Ringkasan angka untuk halaman admin."""
        conn = self._connect()
        try:
            r = conn.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN intent IS NULL THEN 1 ELSE 0 END) AS gagal, "
                "COUNT(DISTINCT session_id) AS sesi "
                "FROM messages WHERE theme = ? AND sender = 'user'",
                (theme,),
            ).fetchone()
        finally:
            conn.close()
        total, gagal = r["total"] or 0, r["gagal"] or 0
        return {"total": total, "tidak_dikenali": gagal, "sesi": r["sesi"] or 0,
                "persen_dikenali": round(100 * (total - gagal) / total, 1) if total else 0.0}
