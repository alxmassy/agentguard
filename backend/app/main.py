"""AgentGuard Backend — FastAPI application entry point.

Usage:
    cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actions import router as actions_router
from app.api.approvals import router as approvals_router
from app.api.evaluate import router as evaluate_router
from app.policy.loader import load_policies

# Load .env before anything reads os.environ
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_POLICY_PATH = Path(__file__).parent.parent.parent / "policies" / "default.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: load policies and DB on startup."""
    # 1. Load policies — fail closed
    # Resolve relative paths relative to backend root (where .env lives), not CWD
    _backend_root = Path(__file__).parent.parent
    raw_policy_path = os.environ.get("AGENTGUARD_POLICY_PATH", str(DEFAULT_POLICY_PATH))
    policy_path = Path(raw_policy_path)
    if not policy_path.is_absolute():
        policy_path = (_backend_root / policy_path).resolve()
    try:
        policy_config = load_policies(policy_path)
        app.state.policy_config = policy_config
        logger.info(
            "Loaded %d policy rules from %s (default: %s)",
            len(policy_config.rules),
            policy_path,
            policy_config.default,
        )
    except Exception as e:
        logger.critical("Failed to load policy file %s: %s", policy_path, e)
        logger.critical("Backend cannot start without valid policies. Exiting.")
        sys.exit(1)

    # 2. Initialize Supabase client — warn but don't exit if missing
    #    (allows tests to run without DB credentials)
    try:
        from app.db.client import init_db
        init_db()
        app.state.db_available = True
        logger.info("Supabase connection initialized.")
    except Exception as e:
        logger.warning("DB unavailable: %s — evaluations will not be persisted.", e)
        app.state.db_available = False

    yield

    logger.info("AgentGuard backend shutting down.")


app = FastAPI(
    title="AgentGuard Backend",
    description="Runtime safety and governance layer for AI agents",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in Milestone 3 (auth)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(evaluate_router)
app.include_router(approvals_router)
app.include_router(actions_router)


@app.get("/health")
async def health_check():
    """Health check — includes DB status."""
    db_available = getattr(app.state, "db_available", False)
    return {"status": "healthy", "version": "0.2.0", "db_available": db_available}
