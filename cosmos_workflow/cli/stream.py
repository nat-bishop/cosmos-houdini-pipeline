"""Stream command for monitoring run logs in real-time."""

import click

from .base import CLIContext, handle_errors
from .helpers import console


@click.command()
@click.argument("run_id", required=False)
@click.option(
    "--tail-lines",
    "-t",
    default=100,
    help="Number of previous lines to show before streaming (default: 100)",
)
@click.option(
    "--follow/--no-follow",
    "-f",
    default=True,
    help="Follow log output (default: --follow)",
)
@click.pass_context
@handle_errors
def stream(ctx, run_id, tail_lines, follow):
    """Stream logs from a run in real-time.

    If RUN_ID is not provided, streams the most recent run.
    Shows previous log lines before starting the stream for context.

    \b
    Examples:
      cosmos stream                    # Stream most recent run with 100 lines history
      cosmos stream rn_abc123          # Stream specific run
      cosmos stream -t 50              # Show 50 lines before streaming
      cosmos stream --no-follow -t 200 # Just show last 200 lines, don't stream
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    try:
        if follow:
            console.print(f"[cyan]Streaming logs (showing last {tail_lines} lines)...[/cyan]")
            console.print("[dim]Press Ctrl+C to stop streaming[/dim]\n")
        else:
            console.print(f"[cyan]Showing last {tail_lines} lines of logs...[/cyan]\n")

        # Stream logs using the new API
        result = ops.stream_run_logs(
            run_id=run_id,
            tail_lines=tail_lines,
            follow=follow,
        )

        if not follow:
            console.print(f"\n[dim]Run ID: {result['run_id']}[/dim]")
            console.print(f"[dim]Log path: {result['log_path']}[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[yellow]Tip:[/yellow] Use 'cosmos list runs' to see available runs")
    except KeyboardInterrupt:
        console.print("\n[cyan]Stopped streaming logs[/cyan]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
