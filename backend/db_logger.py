"""
db_logger.py — Passive SQLite logger for seat state change events.

This is intentionally a "dumb logger": it only appends rows. There is no
complex querying or ORM. Python's built-in sqlite3 module is used so no
extra dependency is needed.

Table schema:
    seat_events(id INTEGER PK, timestamp TEXT, seat_id TEXT, status TEXT)
"""
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from logger_config import get_logger

logger = get_logger(__name__)

# Path is relative to project root: data/analytics.db
_DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"

# Module-level lock for thread-safe writes from the vision engine thread
_db_lock = threading.Lock()
_initialized = False


def _ensure_initialized():
    """Create the DB file and table if they don't exist (idempotent)."""
    global _initialized
    if _initialized:
        return
    try:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seat_events (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT    NOT NULL,
                    seat_id   TEXT    NOT NULL,
                    status    TEXT    NOT NULL
                )
            """)
            conn.commit()
        _initialized = True
        logger.info(f"SQLite analytics DB ready at {_DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize analytics DB: {e}")


def log_seat_change(seat_id: str, new_status: str) -> None:
    """Append a seat status change event to the DB (non-blocking best-effort).
    
    This function is called from the vision engine background thread. Any 
    failure is logged and silently swallowed — the DB is informational only 
    and must never crash the detection loop.
    """
    _ensure_initialized()
    timestamp = datetime.now().isoformat(timespec="seconds")
    try:
        with _db_lock:
            with sqlite3.connect(_DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO seat_events (timestamp, seat_id, status) VALUES (?, ?, ?)",
                    (timestamp, seat_id, new_status)
                )
                conn.commit()
    except Exception as e:
        logger.warning(f"db_logger: failed to log seat change ({seat_id} → {new_status}): {e}")


def get_recent_events(limit: int = 200) -> list[dict]:
    """Return the most recent N seat events, newest first (for debugging)."""
    _ensure_initialized()
    try:
        with _db_lock:
            with sqlite3.connect(_DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT timestamp, seat_id, status FROM seat_events ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"db_logger: failed to fetch recent events: {e}")
        return []
