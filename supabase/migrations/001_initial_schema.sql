-- AgentGuard Initial Schema
-- Run this in the Supabase SQL editor (once).
-- All tables from design doc §19.

-- ============================================================
-- users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL DEFAULT 'developer',
    is_approver BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- projects
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id         TEXT PRIMARY KEY,   -- slug, e.g. "payment-service"
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- action_requests
-- One row per evaluation (the central fact table).
-- ============================================================
CREATE TABLE IF NOT EXISTS action_requests (
    request_id     TEXT PRIMARY KEY,          -- AG-xxxxxxxx
    user_id        UUID REFERENCES users(id),
    project_id     TEXT REFERENCES projects(id),
    agent_id       TEXT,
    environment    TEXT NOT NULL,
    original_task  TEXT,
    command        JSONB NOT NULL,            -- {raw, argv}
    parsed_action  JSONB NOT NULL,            -- full ParsedAction
    decision       TEXT NOT NULL,             -- ALLOW | BLOCK | REQUIRE_HUMAN_APPROVAL
    policy_id      TEXT,
    risk_level     TEXT NOT NULL,
    risk_score     INT NOT NULL,
    risk_factors   JSONB NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_requests_project_created
    ON action_requests (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_action_requests_decision
    ON action_requests (decision);

CREATE INDEX IF NOT EXISTS idx_action_requests_environment
    ON action_requests (environment);

-- ============================================================
-- risk_assessments
-- One-to-one with action_requests (denormalized for fast reads).
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_assessments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id  TEXT NOT NULL REFERENCES action_requests(request_id) ON DELETE CASCADE,
    risk_level  TEXT NOT NULL,
    risk_score  INT NOT NULL,
    factors     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (request_id)
);

-- ============================================================
-- approval_requests
-- Only created when decision = REQUIRE_HUMAN_APPROVAL.
-- One-to-one with action_requests (enforced by UNIQUE).
-- ============================================================
CREATE TABLE IF NOT EXISTS approval_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id   TEXT NOT NULL REFERENCES action_requests(request_id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | expired
    approver_id  UUID REFERENCES users(id),
    comment      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at  TIMESTAMPTZ,
    UNIQUE (request_id),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'approved', 'rejected', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_approval_requests_status
    ON approval_requests (status);

CREATE INDEX IF NOT EXISTS idx_approval_requests_created
    ON approval_requests (created_at DESC);

-- ============================================================
-- execution_records
-- Created by CLI after the command runs (on ALLOW or approved).
-- ============================================================
CREATE TABLE IF NOT EXISTS execution_records (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id   TEXT NOT NULL REFERENCES action_requests(request_id) ON DELETE CASCADE,
    exit_code    INT NOT NULL,
    stdout_meta  TEXT,           -- first 4KB of stdout
    stderr_meta  TEXT,           -- first 4KB of stderr
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (request_id)
);

-- ============================================================
-- audit_events
-- One row per lifecycle event — full timeline reconstructable.
-- event_type values: request_created | decision_made |
--   approval_requested | approval_resolved |
--   execution_started | execution_completed
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id  TEXT NOT NULL REFERENCES action_requests(request_id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_request_id
    ON audit_events (request_id, occurred_at ASC);
