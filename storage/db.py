# storage/db.py
"""
SQLite-backed job deduplication store.
Tracks which job IDs have already been included in a digest,
so jobs are never emailed twice.
"""
import sqlite3
from datetime import datetime, timedelta
from config import DEDUP_DAYS


class JobDatabase:
    def __init__(self, db_path: str = "jobs.db"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id   TEXT PRIMARY KEY,
                seen_at  TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def is_seen(self, job_id: str) -> bool:
        """Return True if this job_id was seen within DEDUP_DAYS."""
        cutoff = (datetime.utcnow() - timedelta(days=DEDUP_DAYS)).isoformat()
        row = self._conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ? AND seen_at >= ?",
            (job_id, cutoff),
        ).fetchone()
        return row is not None

    def mark_seen(self, job_id: str):
        """Record job_id as seen now. Safe to call multiple times."""
        self._conn.execute(
            "INSERT OR REPLACE INTO seen_jobs (job_id, seen_at) VALUES (?, ?)",
            (job_id, datetime.utcnow().isoformat()),
        )
        self._conn.commit()

    def filter_new(self, jobs: list[dict]) -> list[dict]:
        """Return only jobs whose 'id' field has not been seen before."""
        return [j for j in jobs if not self.is_seen(j["id"])]

    def mark_seen_batch(self, jobs: list[dict]):
        """Mark all jobs in list as seen in a single transaction."""
        now = datetime.utcnow().isoformat()
        self._conn.executemany(
            "INSERT OR REPLACE INTO seen_jobs (job_id, seen_at) VALUES (?, ?)",
            [(j["id"], now) for j in jobs],
        )
        self._conn.commit()

    def close(self):
        self._conn.close()
