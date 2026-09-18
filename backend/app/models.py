"""Pydantic models for the AgentGuard backend API contract.

These models define the backend's view of the API contract.
The CLI defines matching models independently — they share the same JSON schema
but are separate Python code (no cross-package imports).
"""
from __future__ import annotations

import uuid
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
    """Possible decisions from the decision engine."""
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"


class RiskLevel(str, Enum):
    """Risk classification levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# --- Inbound models (from CLI) ---

class CommandInfo(BaseModel):
    """Raw command information as received from the CLI."""
    raw: str = Field(description="Original command string")
    argv: list[str] = Field(description="Command split into argv list")


class ParsedAction(BaseModel):
    """Structured representation of a parsed command."""
    tool: str = Field(description="Tool name: terraform, psql, shell")
    operation: str = Field(description="Operation: plan, apply, destroy, query, exec")
    raw_args: list[str] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)
    action_type: ActionType
    target_resource: str | None = Field(default=None)
    is_destructive: bool = Field(default=False)
    is_read_only: bool = Field(default=False)


class RequestContext(BaseModel):
    """Execution context gathered by the CLI."""
    agent_id: str | None = None
    user_id: str | None = None
    project_id: str
    environment: str
    original_task: str | None = None
    working_directory: str | None = None
    git_branch: str | None = None


class ActionRequest(BaseModel):
    """Full request from CLI to backend for evaluation."""
    command: CommandInfo
    parsed_action: ParsedAction
    context: RequestContext


# --- Internal models (engine outputs) ---

class PolicyVerdict(BaseModel):
    """Output of the policy engine."""
    decision: Decision
    reason: str
    policy_id: str | None = None


class RiskFactors(BaseModel):
    """Individual risk factor weights."""
    action_weight: int = 0
    environment_weight: int = 0
    blast_radius_weight: int = 0
    reversibility_weight: int = 0
    privilege_weight: int = 0


class RiskAssessment(BaseModel):
    """Output of the risk engine."""
    risk_level: RiskLevel
    risk_score: int
    factors: RiskFactors


class IntentResult(BaseModel):
    """Output of the LLM intent layer (advisory only).
    
    Not used in Milestone 1 — included for type completeness.
    The Decision Engine accepts this as Optional and works without it.
    """
    intent: str
    expected_environment: str | None = None
    observed_environment: str | None = None
    mismatch: bool = False
    confidence: float = 0.0


# --- Outbound models (to CLI) ---

class DecisionResponse(BaseModel):
    """Response from backend to CLI after evaluation."""
    request_id: str = Field(default_factory=lambda: f"AG-{uuid.uuid4().hex[:8]}")
    decision: Decision
    reason: str
    policy_id: str | None = None
    risk_level: RiskLevel
    risk_score: int
    risk_factors: RiskFactors
    approval_id: str | None = None
