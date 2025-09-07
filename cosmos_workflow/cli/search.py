"""Search command for finding prompts."""

import json
import logging
from datetime import datetime
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)
console = Console()


def get_operations() -> Any:
    """Get the workflow operations from context.

    Returns:
        CosmosAPI: The workflow operations instance.
    """
    ctx = click.get_current_context()
    return ctx.obj.get_operations()


@click.command(name="search")
@click.argument("query")
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Maximum number of results to show (default: 50)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def search_command(ctx: click.Context, query: str, limit: int, output_json: bool) -> None:
    """Search for prompts by text content.

    Searches prompt text for matching content (case-insensitive).

    Examples:
        cosmos search cyberpunk
        cosmos search "futuristic city"
        cosmos search robot --limit 10
        cosmos search transform --json
    """
    # Validate query
    if not query or not query.strip():
        console.print("[red]Error: Search query cannot be empty[/red]")
        ctx.exit(1)

    ops = get_operations()

    try:
        prompts = ops.search_prompts(query, limit=limit)

        if output_json:
            # Output as JSON
            click.echo(json.dumps(prompts, indent=2))
        else:
            # Output as rich table with highlighted matches
            if not prompts:
                console.print(f"[yellow]No prompts found matching '{query}'[/yellow]")
                return

            table = Table(title=f"Search Results for '{query}' ({len(prompts)} found)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Model", style="magenta")
            table.add_column("Prompt", style="white")
            table.add_column("Created", style="green")

            for prompt in prompts:
                # Highlight search term in prompt text
                prompt_text = prompt["prompt_text"]

                # Create a Text object for highlighting
                text = Text(prompt_text)

                # Find and highlight all occurrences (case-insensitive)
                query_lower = query.lower()
                text_lower = prompt_text.lower()
                start = 0
                while True:
                    pos = text_lower.find(query_lower, start)
                    if pos == -1:
                        break
                    text.stylize("bold yellow", pos, pos + len(query))
                    start = pos + 1

                # Truncate if too long but preserve highlighting
                if len(prompt_text) > 80:
                    # Try to show context around the match
                    match_pos = text_lower.find(query_lower)
                    if match_pos > 40:
                        # Match is far from start, show ellipsis
                        text = Text("...") + text[match_pos - 20 :]
                    if len(str(text)) > 80:
                        text = text[:77] + Text("...")

                # Format timestamp
                created_at = prompt["created_at"]
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        created_at = dt.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass  # Keep original string if parsing fails

                table.add_row(
                    prompt["id"],
                    prompt["model_type"],
                    text,
                    created_at,
                )

            console.print(table)

    except Exception as e:
        logger.error("Failed to search prompts: %s", e)
        console.print(f"[red]Error: Failed to search prompts - {e}[/red]")
        ctx.exit(1)
