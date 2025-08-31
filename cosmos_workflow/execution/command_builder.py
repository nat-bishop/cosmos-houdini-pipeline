#!/usr/bin/env python3
"""Command builder for Docker and shell commands.
Provides abstractions for building complex commands with proper escaping.
"""

from shlex import quote


class DockerCommandBuilder:
    """Builds Docker run commands with proper configuration."""

    def __init__(self, image: str, workspace: str = "/workspace"):
        self.image = image
        self.workspace = workspace
        self.volumes: list[str] = []
        self.environment: dict[str, str] = {}
        self.gpu_enabled = False
        self.options: list[str] = []
        self.command: str | None = None

    def with_gpu(self, enabled: bool = True) -> "DockerCommandBuilder":
        """Enable GPU support."""
        self.gpu_enabled = enabled
        return self

    def add_volume(self, host_path: str, container_path: str) -> "DockerCommandBuilder":
        """Add a volume mount."""
        self.volumes.append(f"{host_path}:{container_path}")
        return self

    def add_environment(self, key: str, value: str) -> "DockerCommandBuilder":
        """Add an environment variable."""
        self.environment[key] = value
        return self

    def add_option(self, option: str) -> "DockerCommandBuilder":
        """Add a Docker run option."""
        self.options.append(option)
        return self

    def set_command(self, command: str) -> "DockerCommandBuilder":
        """Set the command to run in the container."""
        self.command = command
        return self

    def build(self) -> str:
        """Build the complete Docker command."""
        parts = ["sudo docker run"]

        # Add standard options
        parts.append("--rm")

        # Add GPU support
        if self.gpu_enabled:
            parts.append("--gpus all")

        # Add custom options
        parts.extend(self.options)

        # Add environment variables
        for key, value in self.environment.items():
            parts.append(f"-e {key}={quote(value)}")

        # Add volumes
        for volume in self.volumes:
            parts.append(f"-v {volume}")

        # Add working directory
        if self.workspace:
            parts.append(f"-w {self.workspace}")

        # Add image
        parts.append(self.image)

        # Add command
        if self.command:
            parts.append(self.command)

        return " \\\n  ".join(parts)


class BashScriptBuilder:
    """Builds bash script commands with proper error handling."""

    def __init__(self):
        self.lines: list[str] = []
        self.variables: dict[str, str] = {}

    def add_shebang(self, shell: str = "/bin/bash") -> "BashScriptBuilder":
        """Add shebang line."""
        self.lines.append(f"#!{shell}")
        return self

    def add_options(self, options: list[str]) -> "BashScriptBuilder":
        """Add shell options (e.g., set -e)."""
        self.lines.append(f"set {' '.join(options)}")
        return self

    def add_variable(self, name: str, value: str) -> "BashScriptBuilder":
        """Add a variable assignment."""
        self.variables[name] = value
        # Only quote if value contains spaces or special characters
        if " " in value or '"' in value or "'" in value or "$" in value:
            self.lines.append(f"{name}={quote(value)}")
        else:
            self.lines.append(f"{name}={value}")
        return self

    def add_comment(self, comment: str) -> "BashScriptBuilder":
        """Add a comment."""
        self.lines.append(f"# {comment}")
        return self

    def add_command(self, command: str) -> "BashScriptBuilder":
        """Add a command."""
        self.lines.append(command)
        return self

    def add_echo(self, message: str) -> "BashScriptBuilder":
        """Add an echo statement."""
        self.lines.append(f"echo {quote(message)}")
        return self

    def add_conditional(
        self, condition: str, then_commands: list[str], else_commands: list[str] | None = None
    ) -> "BashScriptBuilder":
        """Add a conditional block."""
        self.lines.append(f"if {condition}; then")
        for cmd in then_commands:
            self.lines.append(f"  {cmd}")

        if else_commands:
            self.lines.append("else")
            for cmd in else_commands:
                self.lines.append(f"  {cmd}")

        self.lines.append("fi")
        return self

    def build(self) -> str:
        """Build the complete bash script."""
        return "\n".join(self.lines)


class RemoteCommandExecutor:
    """Abstraction for executing commands on remote systems."""

    def __init__(self, ssh_manager):
        self.ssh_manager = ssh_manager

    def execute_docker(self, builder: DockerCommandBuilder, timeout: int = 3600) -> str:
        """Execute a Docker command built with DockerCommandBuilder."""
        command = builder.build()
        return self.ssh_manager.execute_command_success(command, timeout=timeout)

    def execute_script(self, builder: BashScriptBuilder, timeout: int = 300) -> str:
        """Execute a bash script built with BashScriptBuilder."""
        script = builder.build()
        return self.ssh_manager.execute_command_success(script, timeout=timeout)

    def file_exists(self, path: str) -> bool:
        """Check if a file exists on the remote system."""
        try:
            self.ssh_manager.execute_command_success(f"test -f {path}")
            return True
        except RuntimeError:
            return False

    def directory_exists(self, path: str) -> bool:
        """Check if a directory exists on the remote system."""
        try:
            self.ssh_manager.execute_command_success(f"test -d {path}")
            return True
        except RuntimeError:
            return False

    def create_directory(self, path: str) -> None:
        """Create a directory on the remote system."""
        self.ssh_manager.execute_command_success(f"mkdir -p {path}")

    def write_file(self, path: str, content: str) -> None:
        """Write content to a file on the remote system."""
        command = f"cat > {path} << 'EOF'\n{content}\nEOF"
        self.ssh_manager.execute_command_success(command)

    def read_file(self, path: str) -> str:
        """Read content from a file on the remote system."""
        return self.ssh_manager.execute_command_success(f"cat {path}")

    def list_directory(self, path: str) -> list[str]:
        """List files in a directory on the remote system."""
        output = self.ssh_manager.execute_command_success(f"ls -1 {path}")
        return output.strip().split("\n") if output.strip() else []
