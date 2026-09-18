"""Generic command parser for the `exec` fallback.

Conservatively classifies arbitrary shell commands. Checks against a small
blocklist of known-dangerous patterns. Defaults to shell_unknown which
triggers the default REQUIRE_HUMAN_APPROVAL policy.
"""
from __future__ import annotations

from agentguard_cli.models import ActionType, ParsedAction

# Known high-risk command patterns
_HIGH_RISK_COMMANDS: list[dict] = [
    {"pattern": ["rm", "-rf"], "action_type": ActionType.SHELL_HIGH_RISK, "destructive": True},
    {"pattern": ["rm", "-r"], "action_type": ActionType.SHELL_HIGH_RISK, "destructive": True},
    {"pattern": ["chmod", "777"], "action_type": ActionType.SHELL_HIGH_RISK, "destructive": True},
    {"pattern": ["mkfs"], "action_type": ActionType.SHELL_HIGH_RISK, "destructive": True},
    {"pattern": ["dd"], "action_type": ActionType.SHELL_HIGH_RISK, "destructive": True},
]


def parse_generic(args: list[str]) -> ParsedAction:
    """Parse a generic shell command conservatively.
    
    Checks against a blocklist of known-dangerous patterns.
    Unknown commands default to shell_unknown (→ REQUIRE_HUMAN_APPROVAL).
    
    Args:
        args: The full command argv, e.g. ['rm', '-rf', '/tmp/data']
    
    Returns:
        ParsedAction with conservative classification.
    """
    if not args:
        return ParsedAction(
            tool="shell",
            operation="unknown",
            action_type=ActionType.SHELL_UNKNOWN,
            is_destructive=False,
            is_read_only=False,
        )

    command_name = args[0].lower()
    args_lower = [a.lower() for a in args]

    # Check for pipe-to-shell pattern (curl | sh)
    raw_joined = " ".join(args)
    if "|" in raw_joined and any(sh in raw_joined for sh in ["sh", "bash", "zsh"]):
        return ParsedAction(
            tool="shell",
            operation=command_name,
            raw_args=args[1:],
            action_type=ActionType.SHELL_HIGH_RISK,
            is_destructive=True,
            is_read_only=False,
        )

    # Check against known high-risk patterns
    for entry in _HIGH_RISK_COMMANDS:
        pattern = entry["pattern"]
        if all(p in args_lower for p in pattern):
            return ParsedAction(
                tool="shell",
                operation=command_name,
                raw_args=args[1:],
                action_type=entry["action_type"],
                is_destructive=entry["destructive"],
                is_read_only=False,
            )

    # Default: unknown shell command (conservative)
    return ParsedAction(
        tool="shell",
        operation=command_name,
        raw_args=args[1:],
        action_type=ActionType.SHELL_UNKNOWN,
        is_destructive=False,
        is_read_only=False,
    )
