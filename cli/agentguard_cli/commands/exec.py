"""Generic exec subcommand for the AgentGuard CLI.

Usage:
    agentguard exec -- rm -rf /tmp/data
    agentguard exec -- curl https://example.com/script.sh | sh
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
from agentguard_cli.parser.generic import parse_generic

app = typer.Typer(name="exec", help="Generic command gateway (fallback)")
console = Console()
err_console = Console(stderr=True)

POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 15 * 60  # 15 minutes


def _wait_for_approval(
    approval_id: str,
    request_id: str,
    base_url: str,
) -> str:
    """Poll for approval status with a live spinner."""
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    spinner = Spinner("dots", text="")

    with Live(spinner, refresh_per_second=10, console=console) as live:
        while time.time() < deadline:
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

            time.sleep(POLL_INTERVAL_SECONDS)

    return "expired"


@app.callback(invoke_without_command=True)
def exec_command(ctx: typer.Context, args: Optional[list[str]] = typer.Argument(None)):
    """Route an arbitrary command through AgentGuard for safety evaluation."""
    if not args:
        console.print("[yellow]Usage: agentguard exec -- <command> [args...][/yellow]")
        raise typer.Exit(1)

    config = load_config()
    parsed = parse_generic(args)
    context = resolve_context(config)

    raw_command = " ".join(args)
    request = ActionRequest(
        command=CommandInfo(raw=raw_command, argv=args),
        parsed_action=parsed,
        context=context,
    )

    console.print(f"[dim]Evaluating: {raw_command}[/dim]")
    response = evaluate_action(request=request, base_url=config.api.base_url)

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
        result = execute_command(argv=args)
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
            console.print(
                Panel(
                    f"[bold yellow]REQUIRES APPROVAL[/bold yellow] — {response.reason}\n"
                    f"Risk: {response.risk_level.value} (score: {response.risk_score})\n"
                    f"[dim]No approval ID returned (DB unavailable). Command will not execute.[/dim]",
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
            result = execute_command(argv=args)
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
                    "[bold red]REJECTED[/bold red] — Approval was rejected.\nCommand will not execute.",
                    title=f"AgentGuard [{response.request_id}]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
        else:
            err_console.print(
                Panel(
                    "[bold red]TIMED OUT[/bold red] — Approval wait exceeded 15 minutes.\n"
                    "Treated as rejected. Command will not execute.",
                    title=f"AgentGuard [{response.request_id}]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
