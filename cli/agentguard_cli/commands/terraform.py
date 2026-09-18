"""Terraform subcommand for the AgentGuard CLI.

Usage:
    agentguard terraform plan
    agentguard terraform apply
    agentguard terraform destroy
    agentguard terraform destroy -auto-approve
"""
from __future__ import annotations

import time
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from agentguard_cli.client import evaluate_action, poll_approval, report_execution
from agentguard_cli.config import load_config
from agentguard_cli.context import resolve_context
from agentguard_cli.executor import execute_command
from agentguard_cli.models import ActionRequest, CommandInfo, Decision
from agentguard_cli.parser.terraform import parse_terraform

app = typer.Typer(name="terraform", help="Terraform command gateway")
console = Console()
err_console = Console(stderr=True)

# Approval polling settings
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 15 * 60  # 15 minutes


def _wait_for_approval(
    approval_id: str,
    request_id: str,
    base_url: str,
) -> str:
    """Poll for approval status with a live spinner.

    Args:
        approval_id: UUID of the approval_requests row.
        request_id: AG-xxxxxxxx request ID (for display).
        base_url: Backend API base URL.

    Returns:
        Final status: 'approved', 'rejected', or 'expired' (timeout).
    """
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    elapsed = 0

    spinner = Spinner("dots", text="")

    with Live(spinner, refresh_per_second=10, console=console) as live:
        while time.time() < deadline:
            elapsed = int(time.time() - (deadline - POLL_TIMEOUT_SECONDS))
            remaining = int(deadline - time.time())
            mins, secs = divmod(remaining, 60)

            spinner.text = Text(
                f" Waiting for approval [{request_id}] — "
                f"open the dashboard to approve/reject "
                f"({mins}m {secs:02d}s remaining)",
                style="yellow",
            )
            live.update(spinner)

            status = poll_approval(approval_id, base_url)

            if status == "approved":
                live.update(Text("✓ Approved!", style="bold green"))
                return "approved"
            elif status in ("rejected", "expired"):
                live.update(Text(f"✗ {status.capitalize()}", style="bold red"))
                return status
            # status == "pending" or None (connection error) → keep polling

            time.sleep(POLL_INTERVAL_SECONDS)

    return "expired"


@app.callback(invoke_without_command=True)
def terraform_command(ctx: typer.Context, args: Optional[list[str]] = typer.Argument(None)):
    """Route a terraform command through AgentGuard for safety evaluation."""
    if not args:
        console.print("[yellow]Usage: agentguard terraform <operation> [args...][/yellow]")
        raise typer.Exit(1)

    # 1. Load config (fail closed)
    config = load_config()

    # 2. Parse the terraform command
    parsed = parse_terraform(args)

    # 3. Resolve execution context
    context = resolve_context(config)

    # 4. Build the full request
    raw_command = "terraform " + " ".join(args)
    request = ActionRequest(
        command=CommandInfo(raw=raw_command, argv=["terraform"] + args),
        parsed_action=parsed,
        context=context,
    )

    # 5. Send to backend for evaluation
    console.print(f"[dim]Evaluating: {raw_command}[/dim]")
    response = evaluate_action(
        request=request,
        base_url=config.api.base_url,
    )

    # 6. Handle response (or lack thereof)
    if response is None:
        err_console.print(
            Panel(
                "[bold red]BLOCKED[/bold red] — Cannot reach AgentGuard backend.\n"
                "Refusing to execute command (fail safe).",
                title="AgentGuard",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    if response.decision == Decision.ALLOW:
        console.print(
            Panel(
                f"[bold green]ALLOWED[/bold green] — {response.reason}\n"
                f"Risk: {response.risk_level.value} (score: {response.risk_score})",
                title=f"AgentGuard [{response.request_id}]",
                border_style="green",
            )
        )
        result = execute_command(argv=["terraform"] + args)
        # Report execution result to backend for audit trail
        report_execution(
            request_id=response.request_id,
            exit_code=result.exit_code,
            stdout_meta=result.stdout,
            stderr_meta=result.stderr,
            base_url=config.api.base_url,
        )
        raise typer.Exit(result.exit_code)

    elif response.decision == Decision.BLOCK:
        err_console.print(
            Panel(
                f"[bold red]BLOCKED[/bold red] — {response.reason}\n"
                f"Risk: {response.risk_level.value} (score: {response.risk_score})\n"
                f"Policy: {response.policy_id}",
                title=f"AgentGuard [{response.request_id}]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    elif response.decision == Decision.REQUIRE_HUMAN_APPROVAL:
        approval_id = response.approval_id

        if not approval_id:
            # DB not available — backend couldn't create approval record
            console.print(
                Panel(
                    f"[bold yellow]REQUIRES APPROVAL[/bold yellow] — {response.reason}\n"
                    f"Risk: {response.risk_level.value} (score: {response.risk_score})\n"
                    f"Policy: {response.policy_id}\n\n"
                    f"[dim]No approval ID returned (DB unavailable).\n"
                    f"Command will not execute.[/dim]",
                    title=f"AgentGuard [{response.request_id}]",
                    border_style="yellow",
                )
            )
            raise typer.Exit(2)

        console.print(
            Panel(
                f"[bold yellow]REQUIRES APPROVAL[/bold yellow] — {response.reason}\n"
                f"Risk: {response.risk_level.value} (score: {response.risk_score})\n"
                f"Policy: {response.policy_id}\n"
                f"Approval ID: {approval_id}",
                title=f"AgentGuard [{response.request_id}]",
                border_style="yellow",
            )
        )

        # Poll for approval
        final_status = _wait_for_approval(
            approval_id=approval_id,
            request_id=response.request_id,
            base_url=config.api.base_url,
        )

        if final_status == "approved":
            console.print(
                Panel(
                    "[bold green]APPROVED[/bold green] — Executing command...",
                    title=f"AgentGuard [{response.request_id}]",
                    border_style="green",
                )
            )
            result = execute_command(argv=["terraform"] + args)
            report_execution(
                request_id=response.request_id,
                exit_code=result.exit_code,
                stdout_meta=result.stdout,
                stderr_meta=result.stderr,
                base_url=config.api.base_url,
            )
            raise typer.Exit(result.exit_code)

        elif final_status == "rejected":
            err_console.print(
                Panel(
                    "[bold red]REJECTED[/bold red] — Approval was rejected.\n"
                    "Command will not execute.",
                    title=f"AgentGuard [{response.request_id}]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

        else:  # expired / timeout
            err_console.print(
                Panel(
                    "[bold red]TIMED OUT[/bold red] — Approval wait exceeded 15 minutes.\n"
                    "Treated as rejected. Command will not execute.",
                    title=f"AgentGuard [{response.request_id}]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
