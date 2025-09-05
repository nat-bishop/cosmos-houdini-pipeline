"""Base utilities and context for the CLI."""

import logging
import sys
from functools import wraps

from rich.console import Console

console = Console()


class CLIContext:
    """Context object to pass around CLI state."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.orchestrator = None
        self.config_manager = None
        self.workflow_service = None
        self.db_connection = None

    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    def get_orchestrator(self):
        """Get or create workflow orchestrator (lazy-loaded)."""
        if self.orchestrator is None:
            from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

            self.orchestrator = WorkflowOrchestrator()
        return self.orchestrator

    def get_config_manager(self):
        """Get or create config manager (lazy-loaded)."""
        if self.config_manager is None:
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()
        return self.config_manager

    def get_workflow_service(self):
        """Get or create workflow service with database connection (lazy-loaded)."""
        if self.workflow_service is None:
            from cosmos_workflow.database import init_database
            from cosmos_workflow.services.workflow_service import WorkflowService

            # Initialize database connection if not already done
            if self.db_connection is None:
                config_manager = self.get_config_manager()
                local_config = config_manager.get_local_config()
                db_path = local_config.outputs_dir / "cosmos.db"
                self.db_connection = init_database(str(db_path))

            # Create service
            self.workflow_service = WorkflowService(self.db_connection, self.get_config_manager())
        return self.workflow_service


def handle_errors(func):
    """Decorator to handle common CLI errors consistently."""

    @wraps(func)
    def wrapper(ctx, *args, **kwargs):
        ctx_obj = ctx.obj
        try:
            return func(ctx, *args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[bold red][ERROR] File not found:[/bold red] {e}")
            if ctx_obj.verbose:
                console.print_exception()
            sys.exit(1)
        except PermissionError as e:
            console.print(f"[bold red][ERROR] Permission denied:[/bold red] {e}")
            if ctx_obj.verbose:
                console.print_exception()
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red][ERROR] Operation failed:[/bold red] {e}")
            if ctx_obj.verbose:
                console.print_exception()
            sys.exit(1)

    return wrapper


def ensure_utf8_encoding():
    """Ensure UTF-8 encoding for Windows."""
    if sys.platform == "win32":
        if sys.stdout.encoding != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        if sys.stderr.encoding != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
