"""Supabase client singleton.

Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from environment.
The lifespan function in main.py calls init_db() on startup.
"""
from __future__ import annotations

import os

from supabase import Client, create_client

_client: Client | None = None


def init_db() -> Client:
    """Initialize and return the Supabase client.
    
    Called once at startup. Raises if env vars are missing.
    
    Returns:
        Initialized Supabase Client.
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_SERVICE_KEY is not set.
    """
    global _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url:
        raise ValueError("SUPABASE_URL environment variable is not set")
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY environment variable is not set")

    _client = create_client(url, key)
    return _client


def get_db() -> Client:
    """Return the initialized Supabase client.
    
    Raises:
        RuntimeError: If init_db() has not been called.
    """
    if _client is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _client
