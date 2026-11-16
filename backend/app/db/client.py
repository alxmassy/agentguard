"""Database client singleton for AgentGuard.

Supports Supabase if SUPABASE_URL and SUPABASE_SERVICE_KEY are provided.
Gracefully and automatically falls back to local SQLite database (agentguard.db)
for zero-friction local development and guaranteed demo reliability.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_client_type: str = "sqlite"  # "supabase" or "sqlite"
_supabase_client: Any = None
_sqlite_path: Path = Path(__file__).parent.parent.parent / "agentguard.db"


def init_sqlite_tables(conn: sqlite3.Connection) -> None:
    """Initialize schema in SQLite if not exists."""
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL DEFAULT 'developer',
        is_approver INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS action_requests (
        request_id TEXT PRIMARY KEY,
        user_id TEXT,
        project_id TEXT,
        agent_id TEXT,
        environment TEXT NOT NULL,
        original_task TEXT,
        command TEXT NOT NULL,
        parsed_action TEXT NOT NULL,
        decision TEXT NOT NULL,
        policy_id TEXT,
        risk_level TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        risk_factors TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS risk_assessments (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL UNIQUE,
        risk_level TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        factors TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS approval_requests (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        approver_id TEXT,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS execution_records (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL UNIQUE,
        exit_code INTEGER NOT NULL,
        stdout_meta TEXT,
        stderr_meta TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_events (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}',
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()


def init_db():
    """Initialize database connection.
    
    Attempts Supabase if credentials are provided; falls back to SQLite.
    """
    global _client_type, _supabase_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if url and key and len(key.strip()) > 0:
        try:
            from supabase import create_client
            _supabase_client = create_client(url, key)
            _client_type = "supabase"
            logger.info("Connected to Supabase at %s", url)
            return _supabase_client
        except Exception as e:
            logger.warning("Supabase connection failed: %s. Falling back to local SQLite.", e)

    # Fallback to SQLite
    _client_type = "sqlite"
    conn = get_sqlite_conn()
    init_sqlite_tables(conn)
    conn.close()
    logger.info("Using local SQLite storage at %s", _sqlite_path)
    return None


def get_client_type() -> str:
    """Return 'supabase' or 'sqlite'."""
    return _client_type


def get_db():
    """Return Supabase client if configured, else raises RuntimeError if not in Supabase mode."""
    if _client_type == "supabase" and _supabase_client is not None:
        return _supabase_client
    raise RuntimeError("Supabase client is not active.")


def get_sqlite_conn() -> sqlite3.Connection:
    """Return a new SQLite connection with row factory configured."""
    conn = sqlite3.connect(str(_sqlite_path))
    conn.row_factory = sqlite3.Row
    return conn
