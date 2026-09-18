"""HTTP client for communicating with the AgentGuard backend.

Fails safe: any connection error, timeout, or unexpected response
results in a local BLOCK. The CLI never falls through to executing
the raw command when the backend is unreachable.
"""
from __future__ import annotations

import sys
from typing import Optional

import httpx

from agentguard_cli.models import ActionRequest, DecisionResponse

# Request timeout (seconds)
DEFAULT_TIMEOUT = 30.0


def evaluate_action(
    request: ActionRequest,
    base_url: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> DecisionResponse | None:
    """Send an ActionRequest to the backend and return the DecisionResponse.

    Returns None on any failure (connection error, timeout, bad response).
    The caller should treat None as BLOCK (fail safe).

    Args:
        request: The ActionRequest to evaluate.
        base_url: Backend API base URL (e.g. http://localhost:8000/api/v1).
        timeout: Request timeout in seconds.

    Returns:
        DecisionResponse on success, None on any failure.
    """
    url = f"{base_url.rstrip('/')}/actions/evaluate"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                json=request.model_dump(mode="json"),
            )

        if response.status_code == 422:
            detail = response.json().get("detail", "Unknown validation error")
            print(f"ERROR: Backend rejected request: {detail}", file=sys.stderr)
            return None

        if response.status_code != 200:
            print(
                f"ERROR: Backend returned HTTP {response.status_code}: {response.text}",
                file=sys.stderr,
            )
            return None

        return DecisionResponse(**response.json())

    except httpx.ConnectError:
        print(
            "ERROR: Cannot reach AgentGuard backend. "
            "Refusing to execute command (fail safe).",
            file=sys.stderr,
        )
        return None
    except httpx.TimeoutException:
        print(
            "ERROR: AgentGuard backend timed out. "
            "Refusing to execute command (fail safe).",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(
            f"ERROR: Unexpected error communicating with backend: {e}. "
            f"Refusing to execute command (fail safe).",
            file=sys.stderr,
        )
        return None


def poll_approval(
    approval_id: str,
    base_url: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """Poll the backend for the current status of an approval request.

    Called in a loop by the CLI while waiting for a human to approve/reject.

    Args:
        approval_id: UUID of the approval_requests row.
        base_url: Backend API base URL.
        timeout: Request timeout in seconds.

    Returns:
        Status string ('pending', 'approved', 'rejected', 'expired')
        or None on connection error (caller should treat as 'pending' and retry).
    """
    url = f"{base_url.rstrip('/')}/approvals/{approval_id}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)

        if response.status_code == 404:
            print(
                f"ERROR: Approval {approval_id} not found on server.",
                file=sys.stderr,
            )
            return "rejected"

        if response.status_code != 200:
            # Connection issue — return None so caller retries
            return None

        data = response.json()
        return data.get("status", "pending")

    except (httpx.ConnectError, httpx.TimeoutException, Exception):
        # Network error — return None so the polling loop retries
        return None


def report_execution(
    request_id: str,
    exit_code: int,
    stdout_meta: Optional[str],
    stderr_meta: Optional[str],
    base_url: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """Report the result of executing an approved command back to the backend.

    This completes the audit trail. Failure here is non-fatal — the command
    already ran; we just lose the audit record for the execution result.

    Args:
        request_id: The AG-xxxxxxxx request ID from the DecisionResponse.
        exit_code: The subprocess exit code.
        stdout_meta: First 4KB of stdout.
        stderr_meta: First 4KB of stderr.
        base_url: Backend API base URL.
        timeout: Request timeout in seconds.

    Returns:
        True on success, False on any error.
    """
    url = f"{base_url.rstrip('/')}/actions/{request_id}/execute"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                json={
                    "exit_code": exit_code,
                    "stdout_meta": (stdout_meta or "")[:4096],
                    "stderr_meta": (stderr_meta or "")[:4096],
                },
            )
        return response.status_code == 200

    except Exception:
        # Non-fatal — command already ran, we just can't record the result
        return False
