import json
import sqlite3
from typing import Optional, Tuple

from model import Session, DEFAULT_RATE, DEFAULT_CURRENCY, DEFAULT_ROUNDING

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    chat_id INTEGER PRIMARY KEY,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    chat_id INTEGER PRIMARY KEY,
    rate INTEGER NOT NULL DEFAULT 16,
    currency TEXT NOT NULL DEFAULT '₾',
    lang TEXT NOT NULL DEFAULT 'ru',
    rounding REAL NOT NULL DEFAULT 0.1,
    blocks INTEGER NOT NULL DEFAULT 0,
    min_transfer REAL
);

CREATE TABLE IF NOT EXISTS copies (
    code TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._migrate()
        self.db.commit()

    def _migrate(self) -> None:
        columns = {r["name"] for r in self.db.execute("PRAGMA table_info(settings)")}
        if "lang" not in columns:
            self.db.execute("ALTER TABLE settings ADD COLUMN lang TEXT NOT NULL DEFAULT 'ru'")
        if "rounding" not in columns:
            self.db.execute("ALTER TABLE settings ADD COLUMN rounding REAL NOT NULL DEFAULT 0.1")
        if "blocks" not in columns:
            self.db.execute("ALTER TABLE settings ADD COLUMN blocks INTEGER NOT NULL DEFAULT 0")
        if "min_transfer" not in columns:
            self.db.execute("ALTER TABLE settings ADD COLUMN min_transfer REAL")

    def load(self, chat_id: int) -> Optional[Session]:
        row = self.db.execute("SELECT payload FROM sessions WHERE chat_id = ?", (chat_id,)).fetchone()
        if not row:
            return None
        return Session.from_dict(json.loads(row["payload"]))

    def save(self, session: Session) -> None:
        self.db.execute(
            "INSERT INTO sessions (chat_id, payload) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET payload = excluded.payload",
            (session.chat_id, json.dumps(session.to_dict(), ensure_ascii=False)),
        )
        self.db.commit()

    def delete(self, chat_id: int) -> None:
        self.db.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))
        self.db.commit()

    def save_copy(self, code: str, session: Session) -> None:
        self.db.execute("INSERT OR IGNORE INTO copies (code, payload) VALUES (?, ?)",
                        (code, json.dumps(session.to_dict(), ensure_ascii=False)))
        self.db.commit()

    def load_copy(self, code: str) -> Optional[Session]:
        row = self.db.execute("SELECT payload FROM copies WHERE code = ?", (code,)).fetchone()
        return Session.from_dict(json.loads(row["payload"])) if row else None

    def settings(self, chat_id: int) -> Tuple[int, str, str, float, bool, Optional[float]]:
        row = self.db.execute(
            "SELECT rate, currency, lang, rounding, blocks, min_transfer FROM settings "
            "WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        if not row:
            return DEFAULT_RATE, DEFAULT_CURRENCY, "ru", DEFAULT_ROUNDING, False, None
        return (row["rate"], row["currency"], row["lang"],
                float(row["rounding"]) or DEFAULT_ROUNDING, bool(row["blocks"]), row["min_transfer"])

    def remember_settings(self, s: Session) -> None:
        self.db.execute(
            "INSERT INTO settings (chat_id, rate, currency, lang, rounding, blocks, min_transfer) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET "
            "rate = excluded.rate, currency = excluded.currency, lang = excluded.lang, "
            "rounding = excluded.rounding, blocks = excluded.blocks, "
            "min_transfer = excluded.min_transfer",
            (s.chat_id, s.rate, s.currency, s.lang, float(s.rounding), int(s.blocks),
             s.min_transfer),
        )
        self.db.commit()
