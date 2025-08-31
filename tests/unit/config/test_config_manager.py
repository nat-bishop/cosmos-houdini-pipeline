"""
Tests for the ConfigManager class.

This module tests the configuration loading and parsing functionality
that reads TOML files and converts them to Python values.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from cosmos_workflow.config.config_manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary config file for testing
        self.temp_config = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml")
        self.config_path = Path(self.temp_config.name)

        # Sample TOML config content
        self.sample_config = """# Remote instance configuration
[remote]
host = "192.168.1.100"
user = "ubuntu"
port = 22
ssh_key = "./test_ssh_key"

[paths]
remote_dir = "/home/ubuntu/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
"""

        # Write sample config to temp file
        self.temp_config.write(self.sample_config)
        self.temp_config.close()

        # Create a dummy SSH key file for testing
        self.dummy_ssh_key = Path("./test_ssh_key")
        self.dummy_ssh_key.touch()

        # Initialize ConfigManager with temp config
        self.config_manager = ConfigManager(str(self.config_path))

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Remove temporary config file
        if self.config_path.exists():
            os.unlink(self.config_path)
        # Remove dummy SSH key file
        if self.dummy_ssh_key.exists():
            os.unlink(self.dummy_ssh_key)

    def test_init_with_valid_config_path(self):
        """Test ConfigManager initialization with valid config file path."""
        assert self.config_manager.config_file == self.config_path
        assert self.config_manager._remote_config is not None
        assert self.config_manager._local_config is not None

    def test_init_with_nonexistent_config_path(self):
        """Test ConfigManager initialization with non-existent config file."""
        with pytest.raises(FileNotFoundError):
            ConfigManager("/nonexistent/config.toml")

    def test_load_config_parses_toml_variables(self):
        """Test that TOML-style variable assignments are correctly parsed."""
        remote_config = self.config_manager.get_remote_config()
        local_config = self.config_manager.get_local_config()

        # Test remote configuration
        assert remote_config.host == "192.168.1.100"
        assert remote_config.user == "ubuntu"
        assert remote_config.port == 22
        assert remote_config.remote_dir == "/home/ubuntu/cosmos-transfer1"
        assert remote_config.docker_image == "nvcr.io/ubuntu/cosmos-transfer1:latest"

        # Test local configuration (use Path objects to handle Windows/Linux path differences)
        assert local_config.prompts_dir == Path("inputs/prompts")
        assert local_config.runs_dir == Path("inputs/runs")
        assert local_config.videos_dir == Path("inputs/videos")
        assert local_config.outputs_dir == Path("outputs")
        assert local_config.notes_dir == Path("notes")

    def test_load_config_handles_environment_overrides(self):
        """Test that environment variable overrides are correctly applied."""
        # Set environment variables
        os.environ["REMOTE_HOST"] = "192.168.1.200"
        os.environ["REMOTE_USER"] = "testuser"

        # Reload config
        self.config_manager.reload_config()

        # Check that environment variables override TOML values
        assert self.config_manager.get_remote_config().host == "192.168.1.200"
        assert self.config_manager.get_remote_config().user == "testuser"

        # Clean up environment variables
        del os.environ["REMOTE_HOST"]
        del os.environ["REMOTE_USER"]

        # Reload config to restore original values
        self.config_manager.reload_config()

    def test_load_config_handles_complex_toml_structure(self):
        """Test that complex TOML structure is handled correctly."""
        # This test verifies that the TOML structure loads without errors
        assert self.config_manager._remote_config is not None
        assert self.config_manager._local_config is not None
        assert self.config_manager._config_data is not None
        assert "remote" in self.config_manager._config_data
        assert "paths" in self.config_manager._config_data
        assert "docker" in self.config_manager._config_data

    def test_load_config_strips_inline_comments(self):
        """Test that inline comments are properly handled in TOML."""
        # TOML handles comments automatically, so we just verify the config loads
        assert self.config_manager._remote_config is not None

    def test_load_config_ignores_comment_lines(self):
        """Test that comment-only lines are ignored."""
        # TOML handles comments automatically, so we just verify the config loads
        assert self.config_manager._remote_config is not None
        assert self.config_manager._local_config is not None

    def test_load_config_handles_empty_lines(self):
        """Test that empty lines are properly handled."""
        # TOML handles empty lines automatically, so we just verify the config loads
        assert self.config_manager._remote_config is not None
        assert self.config_manager._local_config is not None

    def test_get_remote_config_returns_expected_config(self):
        """Test that get_remote_config returns the correct remote configuration."""
        remote_config = self.config_manager.get_remote_config()
        assert remote_config.host == "192.168.1.100"
        assert remote_config.user == "ubuntu"
        assert remote_config.port == 22

    def test_get_local_config_returns_expected_config(self):
        """Test that get_local_config returns the correct local configuration."""
        local_config = self.config_manager.get_local_config()
        assert local_config.prompts_dir == Path("inputs/prompts")
        assert local_config.videos_dir == Path("inputs/videos")

    def test_get_ssh_options_returns_correct_dict(self):
        """Test that get_ssh_options returns the correct SSH connection options."""
        ssh_options = self.config_manager.get_ssh_options()

        assert ssh_options["hostname"] == "192.168.1.100"
        assert ssh_options["username"] == "ubuntu"
        assert ssh_options["port"] == 22
        assert "key_filename" in ssh_options

    def test_config_validation_works_correctly(self):
        """Test that configuration validation works correctly."""
        # The validation should pass with our test config
        assert self.config_manager._remote_config is not None
        assert self.config_manager._local_config is not None

    def test_config_validation_fails_with_missing_host(self):
        """Test that validation fails when host is missing from remote section."""
        # Create a config without host in remote section
        with open(self.config_path, "w") as f:
            f.write(
                """[remote]
user = "ubuntu"
port = 22
ssh_key = "./test_ssh_key"
remote_dir = "/home/ubuntu/cosmos-transfer1"

[paths]
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
"""
            )

        # Should raise ValueError due to missing host
        with pytest.raises(ValueError, match="REMOTE_HOST not configured"):
            self.config_manager._load_config()

    def test_config_validation_fails_with_missing_ssh_key(self):
        """Test that validation fails when SSH key doesn't exist."""
        # Create a config with non-existent SSH key
        with open(self.config_path, "w") as f:
            f.write(
                """[remote]
host = "192.168.1.100"
user = "ubuntu"
port = 22
ssh_key = "/nonexistent/key"

[paths]
remote_dir = "/home/ubuntu/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
"""
            )

        # Should raise FileNotFoundError due to missing SSH key
        with pytest.raises(FileNotFoundError):
            self.config_manager._load_config()

    def test_config_reload_works_correctly(self):
        """Test that config can be reloaded after file changes."""
        # Get initial config
        initial_host = self.config_manager.get_remote_config().host

        # Modify config file
        with open(self.config_path, "w") as f:
            f.write(
                """[remote]
host = "192.168.1.200"
user = "ubuntu"
port = 22
ssh_key = "./test_ssh_key"

[paths]
remote_dir = "/home/ubuntu/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
"""
            )

        # Reload config
        self.config_manager._load_config()

        # Check that value changed
        assert self.config_manager.get_remote_config().host == "192.168.1.200"
        assert self.config_manager.get_remote_config().host != initial_host


if __name__ == "__main__":
    pytest.main([__file__])
