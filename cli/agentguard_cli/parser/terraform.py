"""Terraform command parser.

Parses terraform operations and flags into a structured ParsedAction.
Rule-based, deterministic, testable.
"""
from __future__ import annotations

from agentguard_cli.models import ActionType, ParsedAction

# Classification table from design doc §9
_TERRAFORM_CLASSIFICATION: dict[str, tuple[ActionType, bool, bool]] = {
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

# Flags that are security-relevant
_KNOWN_FLAGS: set[str] = {
    "-auto-approve",
    "--auto-approve",
    "-target",
    "--target",
    "-var",
    "--var",
    "-var-file",
    "--var-file",
    "-lock",
    "--lock",
    "-force",
    "--force",
}


def parse_terraform(args: list[str]) -> ParsedAction:
    """Parse terraform command arguments into a structured ParsedAction.
    
    Args:
        args: Arguments after 'terraform', e.g. ['destroy', '-auto-approve']
        
    Returns:
        ParsedAction with terraform-specific classification.
    """
    if not args:
        # No operation specified — classify conservatively
        return ParsedAction(
            tool="terraform",
            operation="unknown",
            action_type=ActionType.SHELL_UNKNOWN,
            is_destructive=False,
            is_read_only=False,
        )

    operation = args[0].lower()
    remaining_args = args[1:]

    # Classify the operation
    if operation in _TERRAFORM_CLASSIFICATION:
        action_type, is_destructive, is_read_only = _TERRAFORM_CLASSIFICATION[operation]
    else:
        # Unknown terraform subcommand — conservative
        action_type = ActionType.SHELL_UNKNOWN
        is_destructive = False
        is_read_only = False

    # Extract flags and remaining args
    flags: dict[str, str | bool] = {}
    raw_args: list[str] = []
    target_resource: str | None = None

    i = 0
    while i < len(remaining_args):
        arg = remaining_args[i]
        if arg.startswith("-"):
            # Check if this is a flag that takes a value
            if arg in ("-target", "--target") and i + 1 < len(remaining_args):
                target_resource = remaining_args[i + 1]
                flags[arg] = remaining_args[i + 1]
                i += 2
                continue
            elif arg in ("-var", "--var", "-var-file", "--var-file") and i + 1 < len(remaining_args):
                flags[arg] = remaining_args[i + 1]
                i += 2
                continue
            elif arg in ("-auto-approve", "--auto-approve", "-force", "--force"):
                flags[arg] = True
                i += 1
                continue
            else:
                flags[arg] = True
                i += 1
                continue
        else:
            raw_args.append(arg)
            i += 1

    return ParsedAction(
        tool="terraform",
        operation=operation,
        raw_args=raw_args,
        flags=flags,
        action_type=action_type,
        target_resource=target_resource,
        is_destructive=is_destructive,
        is_read_only=is_read_only,
    )
