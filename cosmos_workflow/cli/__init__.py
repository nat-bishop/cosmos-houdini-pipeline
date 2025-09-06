"""Modern CLI interface for Cosmos-Transfer1 workflow orchestration."""

import click

from .base import CLIContext, ensure_utf8_encoding
from .create import create
from .delete import delete_group
from .enhance import prompt_enhance
from .inference import inference
from .list_commands import list_group
from .prepare import prepare
from .search import search_command
from .show import show_command
from .status import status
from .ui import ui
from .verify import verify


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "auto_envvar_prefix": "COSMOS",
    }
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output for debugging")
@click.version_option(version="0.1.0", prog_name="Cosmos Workflow Orchestrator")
@click.pass_context
def cli(ctx, verbose):
    r"""Cosmos-Transfer1 Workflow Orchestrator.

    A powerful CLI for orchestrating NVIDIA Cosmos video generation workflows.
    Manage prompts, run inference, and control remote GPU execution with ease.

    \b
    Quick Start:
      1. Create a prompt:  cosmos create prompt "A cyberpunk city"
      2. Run inference:    cosmos inference <prompt_file>
      3. Check status:     cosmos status

    Use 'cosmos <command> --help' for detailed command information.
    """
    ctx.obj = CLIContext(verbose=verbose)
    ctx.obj.setup_logging()


# Register all commands
cli.add_command(create)
cli.add_command(delete_group)
cli.add_command(inference)
cli.add_command(list_group)
cli.add_command(prompt_enhance)
cli.add_command(prepare)
cli.add_command(search_command)
cli.add_command(show_command)
cli.add_command(status)
cli.add_command(ui)
cli.add_command(verify)


def main():
    """Main entry point."""
    # Ensure UTF-8 encoding for Windows
    ensure_utf8_encoding()

    try:
        cli(obj=None)
    except KeyboardInterrupt:
        from .helpers import console

        console.print("\n[yellow]Interrupted by user[/yellow]")
        import sys

        sys.exit(1)
    except Exception as e:
        from .helpers import console

        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        import sys

        sys.exit(1)


__all__: list[str] = ["cli", "main"]
