"""Server-side action re-validation.

The CLI does a first-pass parse, but the backend MUST independently re-classify
the action. This is the actual security boundary — the CLI's classification
is untrusted input.

This module re-derives action_type, is_destructive, and is_read_only from the
raw command argv, ignoring whatever the client sent in parsed_action.
"""
from __future__ import annotations

import logging

from app.models import ActionRequest, ActionType, ParsedAction

logger = logging.getLogger(__name__)

# Terraform operation classification
_TERRAFORM_OPS: dict[str, tuple[ActionType, bool, bool]] = {
    # operation: (action_type, is_destructive, is_read_only)
    "plan": (ActionType.INFRASTRUCTURE_READ, False, True),
    "show": (ActionType.INFRASTRUCTURE_READ, False, True),
    "output": (ActionType.INFRASTRUCTURE_READ, False, True),
    "validate": (ActionType.INFRASTRUCTURE_READ, False, True),
    "fmt": (ActionType.INFRASTRUCTURE_READ, False, True),
    "init": (ActionType.INFRASTRUCTURE_READ, False, True),
    "apply": (ActionType.INFRASTRUCTURE_MODIFY, False, False),
    "import": (ActionType.INFRASTRUCTURE_MODIFY, False, False),
    "taint": (ActionType.INFRASTRUCTURE_MODIFY, False, False),
    "untaint": (ActionType.INFRASTRUCTURE_MODIFY, False, False),
    "destroy": (ActionType.INFRASTRUCTURE_DESTROY, True, False),
}

# Shell patterns considered high-risk
_HIGH_RISK_PATTERNS: list[list[str]] = [
    ["rm", "-rf"],
    ["rm", "-r"],
    ["chmod", "777"],
    ["mkfs"],
    ["dd"],
]


def _classify_terraform(operation: str) -> tuple[ActionType, bool, bool]:
    """Classify a Terraform operation."""
    return _TERRAFORM_OPS.get(
        operation,
        (ActionType.SHELL_UNKNOWN, False, False),  # Unknown TF op → conservative
    )


def _classify_shell(argv: list[str]) -> tuple[ActionType, bool, bool]:
    """Classify a generic shell command."""
    if not argv:
        return (ActionType.SHELL_UNKNOWN, False, False)

    # Check for high-risk patterns
    argv_lower = [a.lower() for a in argv]
    for pattern in _HIGH_RISK_PATTERNS:
        if all(p in argv_lower for p in pattern):
            return (ActionType.SHELL_HIGH_RISK, True, False)

    # Check for pipe-to-shell pattern (curl | sh)
    raw_joined = " ".join(argv)
    if "|" in raw_joined and any(
        sh in raw_joined for sh in ["sh", "bash", "zsh"]
    ):
        return (ActionType.SHELL_HIGH_RISK, True, False)

    return (ActionType.SHELL_UNKNOWN, False, False)


def validate_and_reclassify(request: ActionRequest) -> ActionRequest:
    """Re-validate and re-classify the parsed action server-side.
    
    Overrides the client-supplied action_type, is_destructive, and is_read_only
    with server-side classification derived from the raw command.
    
    Args:
        request: The original ActionRequest from the CLI.
        
    Returns:
        A new ActionRequest with server-validated classification.
    """
    tool = request.parsed_action.tool.lower()
    operation = request.parsed_action.operation.lower()
    argv = request.command.argv

    if tool == "terraform":
        action_type, is_destructive, is_read_only = _classify_terraform(operation)
    elif tool == "psql":
        # For psql, trust the SQL-level classification from the parser for now.
        # Full SQL re-parsing (sqlparse/sqlglot) is a Milestone 2 enhancement.
        action_type = request.parsed_action.action_type
        is_destructive = request.parsed_action.is_destructive
        is_read_only = request.parsed_action.is_read_only
    elif tool == "shell":
        action_type, is_destructive, is_read_only = _classify_shell(argv)
    else:
        # Unknown tool → conservative classification
        action_type = ActionType.SHELL_UNKNOWN
        is_destructive = False
        is_read_only = False

    # Log if server classification differs from client
    if action_type != request.parsed_action.action_type:
        logger.warning(
            "Server reclassified action: client=%s, server=%s (command: %s)",
            request.parsed_action.action_type,
            action_type,
            request.command.raw,
        )

    # Build new request with server-validated fields
    validated_action = request.parsed_action.model_copy(
        update={
            "action_type": action_type,
            "is_destructive": is_destructive,
            "is_read_only": is_read_only,
        }
    )

    return request.model_copy(update={"parsed_action": validated_action})
