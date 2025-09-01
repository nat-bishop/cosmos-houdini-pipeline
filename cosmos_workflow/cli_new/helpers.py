"""Display helpers and utilities for CLI output."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def display_success(message: str, details: dict[str, Any] | None = None):
    """Display a success message with optional details."""
    console.print(f"\n[bold green]✅ {message}[/bold green]")

    if details:
        table = create_info_table(details)
        console.print(table)


def display_error(message: str, error: str | None = None, verbose: bool = False):
    """Display an error message with optional details."""
    console.print(f"[bold red]❌ {message}[/bold red]")

    if error:
        console.print(f"  {error}")

    if verbose:
        console.print_exception()


def display_warning(message: str):
    """Display a warning message."""
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def display_info(message: str):
    """Display an informational message."""
    console.print(f"[cyan]i  {message}[/cyan]")  # Using 'i' instead of emoji


def create_info_table(data: Dict[str, Any], show_header: bool = False) -> Table:
    """Create a formatted table for displaying information."""
    table = Table(show_header=show_header, box=None)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    for key, value in data.items():
        # Format value based on type
        formatted_value = value
        if isinstance(formatted_value, Path):
            formatted_value = str(formatted_value)
        elif isinstance(formatted_value, dict):
            formatted_value = json.dumps(formatted_value, indent=2)
        elif isinstance(formatted_value, list):
            formatted_value = ", ".join(str(v) for v in formatted_value)
        elif formatted_value is None:
            formatted_value = "[dim]N/A[/dim]"
        else:
            formatted_value = str(formatted_value)

        table.add_row(key, formatted_value)

    return table


def create_progress_context(description: str):  # noqa: ARG001
    """Create a progress context for long-running operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def format_file_path(path: Path, truncate: bool = True) -> str:
    """Format a file path for display, optionally truncating long paths."""
    path_str = str(path)

    if truncate and len(path_str) > 50:
        # Show first and last parts of the path
        parts = path_str.split("/")
        if len(parts) > 3:
            return f"{parts[0]}/.../{parts[-1]}"

    return path_str


def format_prompt_text(prompt: str, max_length: int = 50) -> str:
    """Format prompt text for display, truncating if necessary."""
    if len(prompt) > max_length:
        return f"{prompt[:max_length]}..."
    return prompt


def format_id(id_str: str, length: int = 16) -> str:
    """Format an ID string for display, truncating if necessary."""
    if len(id_str) > length:
        return f"{id_str[:length]}..."
    return id_str


def display_dry_run_header():
    """Display the dry run mode header."""
    console.print("\n[bold yellow]🔍 DRY RUN MODE[/bold yellow]")
    console.print("This is a preview of what would happen:\n")


def display_dry_run_footer():
    """Display the dry run mode footer."""
    console.print("\n[dim]To execute for real, run without --dry-run[/dim]")


def display_next_step(command: str):
    """Display the next suggested command."""
    console.print("\n[dim]Next step:[/dim]")
    console.print(f"  {command}")


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Ask for user confirmation (for future interactive features)."""
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"{prompt}{suffix}: ").strip().lower()

    if not response:
        return default

    return response in ["y", "yes"]


def format_weights(weights: dict[str, float]) -> str:
    """Format control weights for display."""
    parts = []
    for key, value in weights.items():
        parts.append(f"{key}={value:.2f}")
    return " ".join(parts)


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable string."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def display_command_result(success: bool, message: str, details: dict[str, Any] | None = None):
    """Display the result of a command execution."""
    if success:
        display_success(message, details)
    else:
        display_error(message)
