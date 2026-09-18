"""AgentGuard CLI — entry point.

Usage:
    agentguard terraform plan
    agentguard terraform apply  
    agentguard terraform destroy
    agentguard exec -- <command>
    agentguard status
"""
from __future__ import annotations

import typer

from agentguard_cli.commands.exec import app as exec_app
from agentguard_cli.commands.terraform import app as terraform_app

app = typer.Typer(
    name="agentguard",
    help="AgentGuard — runtime safety gateway for AI agent commands",
    no_args_is_help=True,
)

# Register subcommands
app.add_typer(terraform_app, name="terraform")
app.add_typer(exec_app, name="exec")


@app.command()
def status():
    """Show AgentGuard CLI status and configuration."""
    from agentguard_cli.config import load_config
    from rich.console import Console
    from rich.table import Table

    console = Console()
    
    try:
        config = load_config()
    except SystemExit:
        return

    table = Table(title="AgentGuard Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Project", config.project.name)
    table.add_row("Environment", config.environment.name)
    table.add_row("Agent ID", config.agent.id)
    table.add_row("API Base URL", config.api.base_url)

    console.print(table)


if __name__ == "__main__":
    app()
