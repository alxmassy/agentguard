"""Configuration loader for .agentguard/config.yaml.

Reads project configuration on every CLI invocation (cheap, no caching for MVP).
Fails closed: missing or invalid config means the CLI refuses to proceed.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class ProjectConfig(BaseModel):
    """Project identity configuration."""
    name: str
    id: str | None = None  # defaults to name if not set


class EnvironmentConfig(BaseModel):
    """Environment configuration."""
    name: str

    @field_validator("name")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Warn on non-standard environment names but don't reject."""
        standard = {"local", "development", "staging", "production"}
        if v not in standard:
            # Don't reject — might be a valid custom env — but it'll get
            # conservative risk scoring from the unknown-env weight.
            pass
        return v


class AgentConfig(BaseModel):
    """Agent identity configuration."""
    id: str = "unknown"


class ApiConfig(BaseModel):
    """Backend API connection configuration."""
    base_url: str = "http://localhost:8000/api/v1"


class AgentGuardConfig(BaseModel):
    """Full .agentguard/config.yaml configuration."""
    project: ProjectConfig
    environment: EnvironmentConfig
    agent: AgentConfig = AgentConfig()
    api: ApiConfig = ApiConfig()


def load_config(working_dir: Path | None = None) -> AgentGuardConfig:
    """Load and validate .agentguard/config.yaml from the working directory.
    
    Fails closed: missing or invalid config causes the CLI to exit non-zero.
    
    Args:
        working_dir: Directory to search for .agentguard/config.yaml.
                     Defaults to current working directory.
    
    Returns:
        Validated AgentGuardConfig.
    
    Raises:
        SystemExit: On missing or invalid configuration.
    """
    if working_dir is None:
        working_dir = Path.cwd()

    config_path = working_dir / ".agentguard" / "config.yaml"

    if not config_path.exists():
        print(
            f"ERROR: AgentGuard config not found at {config_path}\n"
            f"Create .agentguard/config.yaml in your project root.\n"
            f"See: https://github.com/agentguard/agentguard#configuration",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in {config_path}: {e}", file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(raw, dict):
        print(f"ERROR: {config_path} must contain a YAML mapping", file=sys.stderr)
        raise SystemExit(1)

    try:
        return AgentGuardConfig(**raw)
    except Exception as e:
        print(f"ERROR: Invalid configuration in {config_path}: {e}", file=sys.stderr)
        raise SystemExit(1)
