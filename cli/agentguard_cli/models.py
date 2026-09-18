"""Pydantic models for the AgentGuard CLI API contract.

These models define the CLI's view of the API contract.
The backend defines matching models independently — they share the same JSON schema
but are separate Python code (no cross-package imports).
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Classified action types from command parsing."""
    INFRASTRUCTURE_READ = "infrastructure_read"
    INFRASTRUCTURE_MODIFY = "infrastructure_modify"
    INFRASTRUCTURE_DESTROY = "infrastructure_destroy"
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"
    DATABASE_DESTRUCTIVE = "database_destructive"
    SHELL_HIGH_RISK = "shell_high_risk"
    SHELL_UNKNOWN = "shell_unknown"


class Decision(str, Enum):
    """Possible decisions from the backend."""
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"


class RiskLevel(str, Enum):
    """Risk classification levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# --- Outbound models (to backend) ---

class CommandInfo(BaseModel):
    """Raw command information sent to the backend."""
    raw: str
    argv: list[str]


class ParsedAction(BaseModel):
    """Structured representation of a parsed command."""
    tool: str
    operation: str
    raw_args: list[str] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)
    action_type: ActionType
    target_resource: str | None = None
    is_destructive: bool = False
    is_read_only: bool = False


class RequestContext(BaseModel):
    """Execution context gathered locally."""
    agent_id: str | None = None
    user_id: str | None = None
    project_id: str
    environment: str
    original_task: str | None = None
    working_directory: str | None = None
    git_branch: str | None = None


class ActionRequest(BaseModel):
    """Full request sent to the backend for evaluation."""
    command: CommandInfo
    parsed_action: ParsedAction
    context: RequestContext


# --- Inbound models (from backend) ---

class RiskFactors(BaseModel):
    """Individual risk factor weights."""
    action_weight: int = 0
    environment_weight: int = 0
    blast_radius_weight: int = 0
    reversibility_weight: int = 0
    privilege_weight: int = 0


class DecisionResponse(BaseModel):
    """Response received from the backend after evaluation."""
    request_id: str
    decision: Decision
    reason: str
    policy_id: str | None = None
    risk_level: RiskLevel
    risk_score: int
    risk_factors: RiskFactors
    approval_id: str | None = None
