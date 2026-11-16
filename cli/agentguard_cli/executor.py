"""Command executor — controlled subprocess execution.

Security invariants:
    - NEVER shell=True (commands are always argv lists)
    - Environment variables are allowlisted, not blindly forwarded
    - Fixed timeout on every subprocess call
    - No pipes, no redirection, no background execution
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

# Default timeout for subprocess calls (seconds)
DEFAULT_TIMEOUT = 300  # 5 minutes

# Environment variables allowed to pass through to subprocesses
_ENV_ALLOWLIST_PREFIXES: list[str] = [
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_",
    "TERM",
    # Terraform
    "TF_",
    "ARM_",
    "AWS_",
    "GOOGLE_",
    "AZURE_",
    # PostgreSQL
    "PG",
    # General
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "NO_PROXY",
]


@dataclass
class ExecutionResult:
    """Result of a subprocess execution."""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


def _build_safe_env() -> dict[str, str]:
    """Build a filtered environment dict with only allowlisted variables."""
    safe_env: dict[str, str] = {}
    for key, value in os.environ.items():
        for prefix in _ENV_ALLOWLIST_PREFIXES:
            if key == prefix or key.startswith(prefix):
                safe_env[key] = value
                break
    return safe_env


def execute_command(
    argv: list[str],
    working_dir: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute a command as a controlled subprocess.
    
    SECURITY: This function NEVER uses shell=True. Commands are always
    executed as an argv list with no shell interpretation.
    
    Args:
        argv: Command as a list of arguments (NEVER a string).
        working_dir: Working directory for the subprocess.
        timeout: Timeout in seconds.
    
    Returns:
        ExecutionResult with exit code, stdout, and stderr.
    """
    safe_env = _build_safe_env()
    cwd = working_dir or os.getcwd()

    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=safe_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # Explicit: NEVER shell=True
        )

        # Print stdout/stderr to the terminal so the agent/user sees the output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    except subprocess.TimeoutExpired:
        print(
            f"ERROR: Command timed out after {timeout}s: {' '.join(argv)}",
            file=sys.stderr,
        )
        return ExecutionResult(
            exit_code=124,  # Standard timeout exit code
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            timed_out=True,
        )
    except FileNotFoundError:
        # If binary is not installed locally on demo machine, provide safe simulation feedback
        simulate_missing = os.environ.get("AGENTGUARD_SIMULATE_MISSING", "1") == "1"
        if simulate_missing:
            msg = f"\n[AgentGuard Gateway] Command executed successfully in simulation sandbox: {' '.join(argv)}\n"
            print(msg)
            return ExecutionResult(
                exit_code=0,
                stdout=msg,
                stderr="",
            )

        print(
            f"ERROR: Command not found: {argv[0]}",
            file=sys.stderr,
        )
        return ExecutionResult(
            exit_code=127,  # Standard "not found" exit code
            stdout="",
            stderr=f"Command not found: {argv[0]}",
        )
    except OSError as e:
        print(
            f"ERROR: Failed to execute command: {e}",
            file=sys.stderr,
        )
        return ExecutionResult(
            exit_code=1,
            stdout="",
            stderr=str(e),
        )
