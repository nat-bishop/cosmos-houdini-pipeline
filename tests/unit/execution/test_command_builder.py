#!/usr/bin/env python3
"""
Test command builder module.
"""

import pytest
from unittest.mock import MagicMock, patch
from cosmos_workflow.execution.command_builder import (
    DockerCommandBuilder,
    BashScriptBuilder,
    RemoteCommandExecutor
)


class TestDockerCommandBuilder:
    """Test DockerCommandBuilder class."""
    
    def test_init(self):
        """Test DockerCommandBuilder initialization."""
        builder = DockerCommandBuilder("test-image", "/workspace")
        
        assert builder.image == "test-image"
        assert builder.workspace == "/workspace"
        assert builder.volumes == []
        assert builder.environment == {}
        assert builder.gpu_enabled is False
        assert builder.options == []
        assert builder.command is None
    
    def test_with_gpu(self):
        """Test enabling GPU support."""
        builder = DockerCommandBuilder("test-image")
        builder.with_gpu()
        
        assert builder.gpu_enabled is True
        
        command = builder.build()
        assert "--gpus all" in command
    
    def test_add_volume(self):
        """Test adding volume mounts."""
        builder = DockerCommandBuilder("test-image")
        builder.add_volume("/host/path", "/container/path")
        builder.add_volume("/another/host", "/another/container")
        
        command = builder.build()
        assert "-v /host/path:/container/path" in command
        assert "-v /another/host:/another/container" in command
    
    def test_add_environment(self):
        """Test adding environment variables."""
        builder = DockerCommandBuilder("test-image")
        builder.add_environment("VAR1", "value1")
        builder.add_environment("VAR2", "value2")
        
        command = builder.build()
        assert "-e VAR1=value1" in command
        assert "-e VAR2=value2" in command
    
    def test_add_option(self):
        """Test adding Docker options."""
        builder = DockerCommandBuilder("test-image")
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        
        command = builder.build()
        assert "--ipc=host" in command
        assert "--shm-size=8g" in command
    
    def test_set_command(self):
        """Test setting the container command."""
        builder = DockerCommandBuilder("test-image")
        builder.set_command("bash -c 'echo hello'")
        
        command = builder.build()
        assert "bash -c 'echo hello'" in command
    
    def test_build_complete_command(self):
        """Test building a complete Docker command."""
        builder = DockerCommandBuilder("nvidia/cuda:12.0", "/workspace")
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume("/data", "/data")
        builder.add_volume("/models", "/models")
        builder.add_environment("CUDA_VISIBLE_DEVICES", "0,1")
        builder.set_command("python train.py")
        
        command = builder.build()
        
        assert command.startswith("sudo docker run")
        assert "--rm" in command
        assert "--gpus all" in command
        assert "--ipc=host" in command
        assert "--shm-size=8g" in command
        assert "-v /data:/data" in command
        assert "-v /models:/models" in command
        assert "-e CUDA_VISIBLE_DEVICES=0,1" in command
        assert "-w /workspace" in command
        assert "nvidia/cuda:12.0" in command
        assert "python train.py" in command


class TestBashScriptBuilder:
    """Test BashScriptBuilder class."""
    
    def test_init(self):
        """Test BashScriptBuilder initialization."""
        builder = BashScriptBuilder()
        
        assert builder.lines == []
        assert builder.variables == {}
    
    def test_add_shebang(self):
        """Test adding shebang line."""
        builder = BashScriptBuilder()
        builder.add_shebang()
        
        script = builder.build()
        assert script.startswith("#!/bin/bash")
        
        builder = BashScriptBuilder()
        builder.add_shebang("/bin/sh")
        
        script = builder.build()
        assert script.startswith("#!/bin/sh")
    
    def test_add_options(self):
        """Test adding shell options."""
        builder = BashScriptBuilder()
        builder.add_options(["-e", "-u", "-o", "pipefail"])
        
        script = builder.build()
        assert "set -e -u -o pipefail" in script
    
    def test_add_variable(self):
        """Test adding variables."""
        builder = BashScriptBuilder()
        builder.add_variable("VAR1", "value1")
        builder.add_variable("VAR2", "value with spaces")
        
        script = builder.build()
        assert "VAR1=value1" in script
        assert "VAR2='value with spaces'" in script
        assert builder.variables["VAR1"] == "value1"
        assert builder.variables["VAR2"] == "value with spaces"
    
    def test_add_comment(self):
        """Test adding comments."""
        builder = BashScriptBuilder()
        builder.add_comment("This is a comment")
        builder.add_comment("Another comment")
        
        script = builder.build()
        assert "# This is a comment" in script
        assert "# Another comment" in script
    
    def test_add_command(self):
        """Test adding commands."""
        builder = BashScriptBuilder()
        builder.add_command("echo 'Hello'")
        builder.add_command("ls -la")
        
        script = builder.build()
        assert "echo 'Hello'" in script
        assert "ls -la" in script
    
    def test_add_echo(self):
        """Test adding echo statements."""
        builder = BashScriptBuilder()
        builder.add_echo("Hello World")
        builder.add_echo("Message with 'quotes'")
        
        script = builder.build()
        assert "echo 'Hello World'" in script
        assert "echo 'Message with '\"'\"'quotes'\"'\"''" in script
    
    def test_add_conditional(self):
        """Test adding conditional blocks."""
        builder = BashScriptBuilder()
        builder.add_conditional(
            "[ -f /tmp/test.txt ]",
            ["echo 'File exists'", "cat /tmp/test.txt"],
            ["echo 'File not found'", "exit 1"]
        )
        
        script = builder.build()
        assert "if [ -f /tmp/test.txt ]; then" in script
        assert "  echo 'File exists'" in script
        assert "  cat /tmp/test.txt" in script
        assert "else" in script
        assert "  echo 'File not found'" in script
        assert "  exit 1" in script
        assert "fi" in script
    
    def test_build_complete_script(self):
        """Test building a complete bash script."""
        builder = BashScriptBuilder()
        builder.add_shebang()
        builder.add_options(["-e", "-u"])
        builder.add_comment("Script to process data")
        builder.add_variable("INPUT_DIR", "/data/input")
        builder.add_variable("OUTPUT_DIR", "/data/output")
        builder.add_echo("Starting processing...")
        builder.add_conditional(
            "[ -d $INPUT_DIR ]",
            ["echo 'Processing files...'", "process_data.sh"],
            ["echo 'Input directory not found'", "exit 1"]
        )
        builder.add_echo("Processing complete!")
        
        script = builder.build()
        
        lines = script.split('\n')
        assert lines[0] == "#!/bin/bash"
        assert lines[1] == "set -e -u"
        assert "# Script to process data" in script
        assert "INPUT_DIR=/data/input" in script
        assert "OUTPUT_DIR=/data/output" in script
        assert "echo 'Starting processing...'" in script
        assert "if [ -d $INPUT_DIR ]; then" in script
        assert "echo 'Processing complete!'" in script


class TestRemoteCommandExecutor:
    """Test RemoteCommandExecutor class."""
    
    def test_init(self):
        """Test RemoteCommandExecutor initialization."""
        ssh_manager = MagicMock()
        executor = RemoteCommandExecutor(ssh_manager)
        
        assert executor.ssh_manager == ssh_manager
    
    def test_execute_docker(self):
        """Test executing Docker command."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(return_value="output")
        
        executor = RemoteCommandExecutor(ssh_manager)
        
        builder = DockerCommandBuilder("test-image")
        builder.set_command("echo hello")
        
        result = executor.execute_docker(builder, timeout=600)
        
        assert result == "output"
        ssh_manager.execute_command_success.assert_called_once()
        call_args = ssh_manager.execute_command_success.call_args
        assert "sudo docker run" in call_args[0][0]
        assert call_args[1]["timeout"] == 600
    
    def test_execute_script(self):
        """Test executing bash script."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(return_value="output")
        
        executor = RemoteCommandExecutor(ssh_manager)
        
        builder = BashScriptBuilder()
        builder.add_command("echo hello")
        
        result = executor.execute_script(builder, timeout=300)
        
        assert result == "output"
        ssh_manager.execute_command_success.assert_called_once()
        call_args = ssh_manager.execute_command_success.call_args
        assert "echo hello" in call_args[0][0]
        assert call_args[1]["timeout"] == 300
    
    def test_file_exists_true(self):
        """Test file_exists when file exists."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock()
        
        executor = RemoteCommandExecutor(ssh_manager)
        
        result = executor.file_exists("/tmp/test.txt")
        
        assert result is True
        ssh_manager.execute_command_success.assert_called_with("test -f /tmp/test.txt")
    
    def test_file_exists_false(self):
        """Test file_exists when file doesn't exist."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(side_effect=RuntimeError)
        
        executor = RemoteCommandExecutor(ssh_manager)
        
        result = executor.file_exists("/tmp/test.txt")
        
        assert result is False
    
    def test_directory_exists_true(self):
        """Test directory_exists when directory exists."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock()
        
        executor = RemoteCommandExecutor(ssh_manager)
        
        result = executor.directory_exists("/tmp/dir")
        
        assert result is True
        ssh_manager.execute_command_success.assert_called_with("test -d /tmp/dir")
    
    def test_directory_exists_false(self):
        """Test directory_exists when directory doesn't exist."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(side_effect=RuntimeError)
        
        executor = RemoteCommandExecutor(ssh_manager)
        
        result = executor.directory_exists("/tmp/dir")
        
        assert result is False
    
    def test_create_directory(self):
        """Test create_directory."""
        ssh_manager = MagicMock()
        
        executor = RemoteCommandExecutor(ssh_manager)
        executor.create_directory("/tmp/new/dir")
        
        ssh_manager.execute_command_success.assert_called_with("mkdir -p /tmp/new/dir")
    
    def test_write_file(self):
        """Test write_file."""
        ssh_manager = MagicMock()
        
        executor = RemoteCommandExecutor(ssh_manager)
        executor.write_file("/tmp/test.txt", "file content\nline 2")
        
        ssh_manager.execute_command_success.assert_called_once()
        call_args = ssh_manager.execute_command_success.call_args[0][0]
        assert "cat > /tmp/test.txt << 'EOF'" in call_args
        assert "file content\nline 2" in call_args
        assert "EOF" in call_args
    
    def test_read_file(self):
        """Test read_file."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(return_value="file content")
        
        executor = RemoteCommandExecutor(ssh_manager)
        result = executor.read_file("/tmp/test.txt")
        
        assert result == "file content"
        ssh_manager.execute_command_success.assert_called_with("cat /tmp/test.txt")
    
    def test_list_directory(self):
        """Test list_directory."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(return_value="file1.txt\nfile2.txt\ndir1")
        
        executor = RemoteCommandExecutor(ssh_manager)
        result = executor.list_directory("/tmp")
        
        assert result == ["file1.txt", "file2.txt", "dir1"]
        ssh_manager.execute_command_success.assert_called_with("ls -1 /tmp")
    
    def test_list_directory_empty(self):
        """Test list_directory with empty directory."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command_success = MagicMock(return_value="")
        
        executor = RemoteCommandExecutor(ssh_manager)
        result = executor.list_directory("/tmp/empty")
        
        assert result == []