"""Context resolver — gathers local execution context.

Collects: CWD, env vars (AG_ENVIRONMENT, AG_TASK), git branch, config values.
Builds the context portion of the ActionRequest.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from agentguard_cli.config import AgentGuardConfig
from agentguard_cli.models import RequestContext


def _get_git_branch() -> str | None:
    """Attempt to get the current git branch. Returns None on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def resolve_context(config: AgentGuardConfig) -> RequestContext:
    """Build execution context from config, env vars, and local state.
    
    Priority for environment:
        1. AG_ENVIRONMENT env var (explicit override)
        2. config.yaml environment.name
    
    Args:
        config: Loaded project configuration.
        
    Returns:
        RequestContext ready to include in ActionRequest.
    """
    # Environment: env var overrides config
    environment = os.environ.get("AG_ENVIRONMENT", config.environment.name)

    # Original task: from env var or absent (intent checking is skipped if absent)
    original_task = os.environ.get("AG_TASK")

    # Agent ID: from config
    agent_id = config.agent.id

    # Project ID: from config
    project_id = config.project.id or config.project.name

    # Git branch: best-effort
    git_branch = _get_git_branch()

    return RequestContext(
        agent_id=agent_id,
        user_id=None,  # No auth in Milestone 1
        project_id=project_id,
        environment=environment,
        original_task=original_task,
        working_directory=str(Path.cwd()),
        git_branch=git_branch,
    )
