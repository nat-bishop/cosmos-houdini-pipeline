#!/usr/bin/env python3
"""Configuration manager for Cosmos-Transfer1 workflow system.

Loads configuration from TOML files with environment variable overrides.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import toml


@dataclass
class RemoteConfig:
    """Remote instance configuration."""

    host: str
    user: str
    port: int
    ssh_key: str
    remote_dir: str
    docker_image: str


@dataclass
class LocalConfig:
    """Local paths configuration."""

    prompts_dir: Path
    runs_dir: Path
    videos_dir: Path
    outputs_dir: Path
    notes_dir: Path


class ConfigManager:
    """Manages configuration loading from TOML files with environment variable overrides."""

    def __init__(self, config_file: str | None = None):
        """Initialize the ConfigManager.

        Args:
            config_file: Path to the TOML configuration file. If None, uses default location.

        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
        """
        if config_file is None:
            # Find config.toml relative to this module's location
            # config_manager.py is in cosmos_workflow/config/
            # So we need to go to the same directory for config.toml
            config_dir = Path(__file__).parent
            self.config_file = config_dir / "config.toml"
        else:
            self.config_file = Path(config_file)
        self._config_data: dict[str, Any] | None = None
        self._remote_config: RemoteConfig | None = None
        self._local_config: LocalConfig | None = None

        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from TOML file with environment variable overrides.

        Raises:
            toml.TomlDecodeError: If the TOML file is malformed.
            ValueError: If required configuration values are missing.
            FileNotFoundError: If the SSH key file doesn't exist.
        """
        # Load base TOML configuration
        with open(self.config_file) as f:
            self._config_data = toml.load(f)

        # Apply environment variable overrides
        self._apply_environment_overrides()

        # Validate configuration
        self._validate_config()

        # Create configuration objects
        self._create_config_objects()

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration.

        Environment variables checked:
            REMOTE_USER, REMOTE_HOST, REMOTE_PORT, SSH_KEY, REMOTE_DIR,
            DOCKER_IMAGE, LOCAL_PROMPTS_DIR, LOCAL_RUNS_DIR, LOCAL_VIDEOS_DIR,
            LOCAL_OUTPUTS_DIR, LOCAL_NOTES_DIR.
        """
        # Remote instance overrides
        if "REMOTE_USER" in os.environ:
            self._config_data["remote"]["user"] = os.environ["REMOTE_USER"]
        if "REMOTE_HOST" in os.environ:
            self._config_data["remote"]["host"] = os.environ["REMOTE_HOST"]
        if "REMOTE_PORT" in os.environ:
            self._config_data["remote"]["port"] = int(os.environ["REMOTE_PORT"])
        if "SSH_KEY" in os.environ:
            self._config_data["remote"]["ssh_key"] = os.environ["SSH_KEY"]
        if "REMOTE_DIR" in os.environ:
            self._config_data["paths"]["remote_dir"] = os.environ["REMOTE_DIR"]
        if "DOCKER_IMAGE" in os.environ:
            self._config_data["docker"]["image"] = os.environ["DOCKER_IMAGE"]

        # Local paths overrides
        if "LOCAL_PROMPTS_DIR" in os.environ:
            self._config_data["paths"]["local_prompts_dir"] = os.environ["LOCAL_PROMPTS_DIR"]
        if "LOCAL_RUNS_DIR" in os.environ:
            self._config_data["paths"]["local_runs_dir"] = os.environ["LOCAL_RUNS_DIR"]
        if "LOCAL_VIDEOS_DIR" in os.environ:
            self._config_data["paths"]["local_videos_dir"] = os.environ["LOCAL_VIDEOS_DIR"]
        if "LOCAL_OUTPUTS_DIR" in os.environ:
            self._config_data["paths"]["local_outputs_dir"] = os.environ["LOCAL_OUTPUTS_DIR"]
        if "LOCAL_NOTES_DIR" in os.environ:
            self._config_data["paths"]["local_notes_dir"] = os.environ["LOCAL_NOTES_DIR"]

    def _validate_config(self) -> None:
        """Validate that required configuration values are present.

        Raises:
            ValueError: If required configuration values are missing.
            FileNotFoundError: If the SSH key file doesn't exist.
        """
        remote = self._config_data.get("remote", {})
        paths = self._config_data.get("paths", {})
        docker = self._config_data.get("docker", {})

        # Check required remote configuration
        if not remote.get("host"):
            raise ValueError("REMOTE_HOST not configured")
        if not remote.get("user"):
            raise ValueError("REMOTE_USER not configured")
        if not remote.get("ssh_key"):
            raise ValueError("SSH_KEY not configured")
        if not paths.get("remote_dir"):
            raise ValueError("REMOTE_DIR not configured")
        if not docker.get("image"):
            raise ValueError("DOCKER_IMAGE not configured")

        # Check SSH key file exists (expand user path)
        ssh_key_path = Path(remote["ssh_key"]).expanduser()
        if not ssh_key_path.exists():
            raise FileNotFoundError(f"SSH key file not found: {ssh_key_path}")

    def _create_config_objects(self) -> None:
        """Create configuration objects from loaded data.

        Creates RemoteConfig and LocalConfig dataclass instances from
        the loaded configuration data.
        """
        remote = self._config_data["remote"]
        paths = self._config_data["paths"]
        docker = self._config_data["docker"]

        # Create remote config
        self._remote_config = RemoteConfig(
            host=remote["host"],
            user=remote["user"],
            port=remote["port"],
            ssh_key=remote["ssh_key"],
            remote_dir=paths["remote_dir"],
            docker_image=docker["image"],
        )

        # Create local config
        self._local_config = LocalConfig(
            prompts_dir=Path(paths["local_prompts_dir"]),
            runs_dir=Path(paths["local_runs_dir"]),
            videos_dir=Path(paths["local_videos_dir"]),
            outputs_dir=Path(paths["local_outputs_dir"]),
            notes_dir=Path(paths["local_notes_dir"]),
        )

    def get_remote_config(self) -> RemoteConfig:
        """Get remote configuration.

        Returns:
            RemoteConfig object containing remote instance settings.

        Raises:
            RuntimeError: If configuration hasn't been loaded.
        """
        if not self._remote_config:
            raise RuntimeError("Configuration not loaded")
        return self._remote_config

    def get_local_config(self) -> LocalConfig:
        """Get local configuration.

        Returns:
            LocalConfig object containing local path settings.

        Raises:
            RuntimeError: If configuration hasn't been loaded.
        """
        if not self._local_config:
            raise RuntimeError("Configuration not loaded")
        return self._local_config

    def get_ssh_options(self) -> dict[str, Any]:
        """Get SSH connection options in the format expected by paramiko.

        Returns:
            Dictionary with hostname, username, port, and key_filename.

        Raises:
            RuntimeError: If configuration hasn't been loaded.
        """
        remote_config = self.get_remote_config()

        return {
            "hostname": remote_config.host,
            "username": remote_config.user,
            "port": remote_config.port,
            "key_filename": str(Path(remote_config.ssh_key).expanduser()),
        }

    def get_config_section(self, section: str) -> dict[str, Any]:
        """Get a specific configuration section.

        Args:
            section: The configuration section name (e.g., 'ui', 'remote', 'docker')

        Returns:
            Dictionary containing the configuration section, or empty dict if not found.
        """
        return self._config_data.get(section, {})

    def reload_config(self) -> None:
        """Reload configuration from file.

        Reloads the configuration from the TOML file and reapplies
        environment variable overrides.

        Raises:
            toml.TomlDecodeError: If the TOML file is malformed.
            ValueError: If required configuration values are missing.
            FileNotFoundError: If the SSH key file doesn't exist.
        """
        self._load_config()
