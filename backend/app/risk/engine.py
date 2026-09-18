"""Risk Engine — weighted, explainable risk scoring.

Computes: risk_score = action_weight + environment_weight + blast_radius_weight
                       + reversibility_weight + privilege_weight

Score ranges:
    0-3   = LOW
    4-7   = MEDIUM  
    8-12  = HIGH
    13+   = CRITICAL

All weights are deterministic lookups — no ML, no LLM.
"""
from __future__ import annotations

from app.models import (
    ActionRequest,
    ActionType,
    RiskAssessment,
    RiskFactors,
    RiskLevel,
)

# --- Weight tables (from design doc §13) ---

ACTION_WEIGHTS: dict[ActionType, int] = {
    ActionType.INFRASTRUCTURE_READ: 0,
    ActionType.INFRASTRUCTURE_MODIFY: 3,
    ActionType.INFRASTRUCTURE_DESTROY: 6,
    ActionType.DATABASE_READ: 0,
    ActionType.DATABASE_WRITE: 3,
    ActionType.DATABASE_DESTRUCTIVE: 6,
    ActionType.SHELL_HIGH_RISK: 6,
    ActionType.SHELL_UNKNOWN: 3,
}

ENVIRONMENT_WEIGHTS: dict[str, int] = {
    "local": 0,
    "development": 0,
    "staging": 1,
    "production": 4,
}

# Static blast-radius weights per operation type (MVP — no plan parsing)
BLAST_RADIUS_WEIGHTS: dict[ActionType, int] = {
    ActionType.INFRASTRUCTURE_READ: 0,
    ActionType.INFRASTRUCTURE_MODIFY: 3,
    ActionType.INFRASTRUCTURE_DESTROY: 5,
    ActionType.DATABASE_READ: 0,
    ActionType.DATABASE_WRITE: 1,
    ActionType.DATABASE_DESTRUCTIVE: 5,
    ActionType.SHELL_HIGH_RISK: 5,
    ActionType.SHELL_UNKNOWN: 3,
}

REVERSIBILITY_WEIGHTS: dict[ActionType, int] = {
    ActionType.INFRASTRUCTURE_READ: 0,
    ActionType.INFRASTRUCTURE_MODIFY: 1,
    ActionType.INFRASTRUCTURE_DESTROY: 5,
    ActionType.DATABASE_READ: 0,
    ActionType.DATABASE_WRITE: 1,
    ActionType.DATABASE_DESTRUCTIVE: 5,
    ActionType.SHELL_HIGH_RISK: 5,
    ActionType.SHELL_UNKNOWN: 3,
}

# Flags/patterns that indicate elevated privilege
ELEVATED_PRIVILEGE_FLAGS: set[str] = {
    "-auto-approve",
    "--auto-approve",
    "-force",
    "--force",
}


def _compute_privilege_weight(request: ActionRequest) -> int:
    """Check for elevated privilege indicators in flags and args."""
    flags = request.parsed_action.flags
    raw_args = request.parsed_action.raw_args

    # Check flags dict keys
    for flag_name in flags:
        if flag_name in ELEVATED_PRIVILEGE_FLAGS:
            return 3

    # Check raw args for privilege flags
    for arg in raw_args:
        if arg in ELEVATED_PRIVILEGE_FLAGS:
            return 3

    return 0


def _score_to_level(score: int) -> RiskLevel:
    """Map numeric risk score to risk level."""
    if score <= 3:
        return RiskLevel.LOW
    elif score <= 7:
        return RiskLevel.MEDIUM
    elif score <= 12:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def assess_risk(request: ActionRequest) -> RiskAssessment:
    """Compute a weighted, explainable risk assessment.
    
    Every factor is a deterministic lookup. The output includes all individual
    factor weights so the decision is fully explainable.
    
    Args:
        request: The action request to assess.
        
    Returns:
        RiskAssessment with level, score, and individual factors.
    """
    action_type = request.parsed_action.action_type
    environment = request.context.environment

    action_weight = ACTION_WEIGHTS.get(action_type, 3)
    environment_weight = ENVIRONMENT_WEIGHTS.get(environment, 2)  # unknown env = moderate
    blast_radius_weight = BLAST_RADIUS_WEIGHTS.get(action_type, 3)
    reversibility_weight = REVERSIBILITY_WEIGHTS.get(action_type, 3)
    privilege_weight = _compute_privilege_weight(request)

    factors = RiskFactors(
        action_weight=action_weight,
        environment_weight=environment_weight,
        blast_radius_weight=blast_radius_weight,
        reversibility_weight=reversibility_weight,
        privilege_weight=privilege_weight,
    )

    total_score = (
        factors.action_weight
        + factors.environment_weight
        + factors.blast_radius_weight
        + factors.reversibility_weight
        + factors.privilege_weight
    )

    return RiskAssessment(
        risk_level=_score_to_level(total_score),
        risk_score=total_score,
        factors=factors,
    )
