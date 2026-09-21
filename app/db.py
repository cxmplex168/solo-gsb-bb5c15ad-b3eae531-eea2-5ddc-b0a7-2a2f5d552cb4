"""SQLite persistence for experiments and their allocations."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

DB_PATH = os.environ.get("DATABASE_PATH", "/data/experiments.db")


def _connect() -> sqlite3.Connection:
    directory = os.path.dirname(DB_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    """Create tables if they do not exist. Safe to call on every startup."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id           TEXT PRIMARY KEY,
                conditions   TEXT NOT NULL,
                subject_ids  TEXT NOT NULL,
                seed         INTEGER NOT NULL,
                n_conditions INTEGER NOT NULL,
                n_subjects   INTEGER NOT NULL,
                block_size   INTEGER NOT NULL,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS allocations (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id  TEXT NOT NULL,
                subject_id     TEXT NOT NULL,
                sequence       TEXT NOT NULL,
                sequence_index INTEGER NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id),
                UNIQUE (experiment_id, subject_id)
            );

            CREATE INDEX IF NOT EXISTS idx_allocations_experiment
                ON allocations (experiment_id);
            """
        )


def save_experiment(
    experiment_id: str,
    conditions: list[str],
    subject_ids: list[str],
    seed: int,
    block_size: int,
    assignments: list[tuple[str, list[str], int]],
) -> None:
    """Persist one experiment and its subject assignments atomically.

    ``assignments`` is a list of ``(subject_id, sequence, sequence_index)``.
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO experiments
                (id, conditions, subject_ids, seed, n_conditions, n_subjects,
                 block_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                json.dumps(conditions, ensure_ascii=False),
                json.dumps(subject_ids, ensure_ascii=False),
                seed,
                len(conditions),
                len(subject_ids),
                block_size,
                now,
            ),
        )
        conn.executemany(
            """
            INSERT INTO allocations
                (experiment_id, subject_id, sequence, sequence_index)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    experiment_id,
                    subject_id,
                    json.dumps(sequence, ensure_ascii=False),
                    seq_idx,
                )
                for subject_id, sequence, seq_idx in assignments
            ],
        )


def get_experiment(experiment_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()


def list_experiments() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(
            conn.execute("SELECT * FROM experiments ORDER BY created_at, id")
        )


def get_allocations(experiment_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(
            conn.execute(
                "SELECT * FROM allocations WHERE experiment_id = ? ORDER BY id",
                (experiment_id,),
            )
        )
