"""Policy configuration loader.

Loads rules from a YAML file and validates their structure.
Fails closed: invalid/missing policy file means the backend cannot serve requests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class PolicyCondition(BaseModel):
    """Conditions that must match for a rule to apply."""
    environment: str | None = None
    action_type: str | None = None
    is_read_only: bool | None = None
    is_destructive: bool | None = None
    tool: str | None = None


class PolicyRule(BaseModel):
    """A single policy rule: if conditions match, then decision applies."""
    id: str
    conditions: PolicyCondition = Field(alias="if")
    then: str  # ALLOW, BLOCK, REQUIRE_HUMAN_APPROVAL
    reason: str = ""

    model_config = {"populate_by_name": True}

    @field_validator("then")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        valid = {"ALLOW", "BLOCK", "REQUIRE_HUMAN_APPROVAL"}
        if v not in valid:
            raise ValueError(f"Invalid decision '{v}', must be one of {valid}")
        return v


class PolicyConfig(BaseModel):
    """Full policy configuration loaded from YAML."""
    rules: list[PolicyRule]
    default: str = "REQUIRE_HUMAN_APPROVAL"

    @field_validator("default")
    @classmethod
    def validate_default(cls, v: str) -> str:
        valid = {"ALLOW", "BLOCK", "REQUIRE_HUMAN_APPROVAL"}
        if v not in valid:
            raise ValueError(f"Invalid default decision '{v}', must be one of {valid}")
        return v


def load_policies(policy_path: Path) -> PolicyConfig:
    """Load and validate policy configuration from a YAML file.
    
    Fails closed: raises on any parse/validation error.
    The caller (FastAPI startup) should catch this and refuse to start.
    
    Args:
        policy_path: Path to the policies.yaml file.
        
    Returns:
        Validated PolicyConfig.
        
    Raises:
        FileNotFoundError: If the policy file doesn't exist.
        yaml.YAMLError: If the YAML is malformed.
        pydantic.ValidationError: If the structure doesn't match the schema.
    """
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    with open(policy_path, "r") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Policy file must contain a YAML mapping, got {type(raw).__name__}")

    return PolicyConfig(**raw)
