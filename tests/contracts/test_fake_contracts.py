"""
Contract tests to ensure fake implementations match real ones.

These tests verify that our test doubles maintain the same interface
and contracts as the real implementations they replace.
"""

import inspect
from pathlib import Path

import pytest

from tests.fixtures.fakes import (
    FakeDockerExecutor,
    FakeFileTransferService,
    FakeSSHManager,
    FakeWorkflowOrchestrator,
)


class TestFakeContracts:
    """Verify fakes maintain same contracts as real implementations."""

    def test_fake_ssh_manager_interface(self):
        """FakeSSHManager should have all public methods of real SSHManager."""
        from cosmos_workflow.connection.ssh_manager import SSHManager

        # Get public methods (excluding special methods and properties)
        real_methods = self._get_public_methods(SSHManager)
        fake_methods = self._get_public_methods(FakeSSHManager)

        # Find missing methods
        missing = real_methods - fake_methods
        extra = fake_methods - real_methods

        # Report discrepancies
        if missing:
            pytest.fail(f"FakeSSHManager missing methods: {missing}")

        # Extra methods are OK (for testing), but let's track them
        if extra:
            print(f"FakeSSHManager has extra methods (OK for testing): {extra}")

    def test_fake_docker_executor_interface(self):
        """FakeDockerExecutor should match DockerExecutor interface."""
        from cosmos_workflow.execution.docker_executor import DockerExecutor

        real_methods = self._get_public_methods(DockerExecutor)
        fake_methods = self._get_public_methods(FakeDockerExecutor)

        missing = real_methods - fake_methods

        if missing:
            pytest.fail(f"FakeDockerExecutor missing methods: {missing}")

    def test_fake_file_transfer_interface(self):
        """FakeFileTransferService should match FileTransferService interface."""
        from cosmos_workflow.transfer.file_transfer import FileTransferService

        real_methods = self._get_public_methods(FileTransferService)
        fake_methods = self._get_public_methods(FakeFileTransferService)

        missing = real_methods - fake_methods

        if missing:
            pytest.fail(f"FakeFileTransferService missing methods: {missing}")

    def test_fake_workflow_orchestrator_interface(self):
        """FakeWorkflowOrchestrator should match WorkflowOrchestrator interface."""
        from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

        real_methods = self._get_public_methods(WorkflowOrchestrator)
        fake_methods = self._get_public_methods(FakeWorkflowOrchestrator)

        missing = real_methods - fake_methods

        if missing:
            pytest.fail(f"FakeWorkflowOrchestrator missing methods: {missing}")

    def test_method_signatures_match(self):
        """Critical method signatures should match between fake and real."""
        signature_tests = [
            (
                "cosmos_workflow.execution.docker_executor.DockerExecutor",
                FakeDockerExecutor,
                "run_inference",
            ),
            (
                "cosmos_workflow.connection.ssh_manager.SSHManager",
                FakeSSHManager,
                "execute_command",
            ),
            (
                "cosmos_workflow.transfer.file_transfer.FileTransferService",
                FakeFileTransferService,
                "upload_file",
            ),
        ]

        for real_class_path, fake_class, method_name in signature_tests:
            # Import real class
            module_path, class_name = real_class_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            real_class = getattr(module, class_name)

            # Get method signatures
            try:
                real_method = getattr(real_class, method_name)
                fake_method = getattr(fake_class, method_name)

                real_sig = inspect.signature(real_method)
                fake_sig = inspect.signature(fake_method)

                # Compare parameters (excluding self)
                real_params = list(real_sig.parameters.keys())[1:]
                fake_params = list(fake_sig.parameters.keys())[1:]

                # Check required parameters match
                real_required = [
                    p
                    for p, param in real_sig.parameters.items()
                    if p != "self" and param.default == inspect.Parameter.empty
                ]
                fake_required = [
                    p
                    for p, param in fake_sig.parameters.items()
                    if p != "self" and param.default == inspect.Parameter.empty
                ]

                if real_required != fake_required:
                    pytest.fail(
                        f"{fake_class.__name__}.{method_name} signature mismatch:\n"
                        f"  Real required params: {real_required}\n"
                        f"  Fake required params: {fake_required}"
                    )

            except AttributeError as e:
                pytest.fail(f"Method {method_name} not found: {e}")

    def test_fake_return_types_are_consistent(self):
        """Fakes should return appropriate types for their methods."""
        # Test that key methods return expected types
        fake_ssh = FakeSSHManager()
        fake_docker = FakeDockerExecutor()
        fake_transfer = FakeFileTransferService()

        # SSH Manager tests
        assert fake_ssh.is_connected() in [True, False], "is_connected should return bool"

        # Docker Executor tests
        status = fake_docker.get_docker_status()
        assert isinstance(status, dict), "get_docker_status should return dict"
        assert "docker_running" in status, "Status should have docker_running key"

        # File Transfer tests
        # Note: Methods return None on success (following real implementation)
        # This is tested in the behavior tests

    def test_fake_state_management(self):
        """Fakes should maintain state correctly."""
        # Test SSH Manager state
        ssh = FakeSSHManager()
        assert ssh.is_connected() is False
        ssh.connect()
        assert ssh.is_connected() is True
        ssh.disconnect()
        assert ssh.is_connected() is False

        # Test Docker Executor state
        docker = FakeDockerExecutor()
        assert len(docker.containers_run) == 0

        # Test File Transfer state
        transfer = FakeFileTransferService()
        assert len(transfer.uploaded_files) == 0
        assert len(transfer.downloaded_files) == 0

    def test_fake_error_handling_matches_contract(self):
        """Fakes should raise same exceptions as real implementations."""
        from pathlib import Path

        # Test FileNotFoundError for non-existent files
        transfer = FakeFileTransferService()
        non_existent = Path("/does/not/exist.txt")

        with pytest.raises(FileNotFoundError):
            transfer.upload_file(non_existent, "/remote")

        # Test Docker Executor validates input
        docker = FakeDockerExecutor()
        non_existent_prompt = Path("/fake/prompt.json")

        # Should not raise for inference (fake doesn't check file existence)
        # But should raise for upscaling without prior inference
        with pytest.raises(FileNotFoundError, match="Input video not found"):
            docker.run_upscaling(non_existent_prompt)

    def _get_public_methods(self, cls) -> set[str]:
        """Get all public methods of a class."""
        methods = set()
        for name in dir(cls):
            if not name.startswith("_"):  # Skip private/special methods
                attr = getattr(cls, name)
                if callable(attr) and not isinstance(attr, property):
                    methods.add(name)
        return methods


class TestFakeBehaviorContracts:
    """Test that fakes behave according to expected contracts."""

    def test_ssh_connection_lifecycle(self):
        """SSH connection should follow connect -> execute -> disconnect lifecycle."""
        ssh = FakeSSHManager()

        # Should start disconnected
        assert not ssh.is_connected()

        # Should be able to connect
        ssh.connect()
        assert ssh.is_connected()

        # Should be able to execute commands when connected
        exit_code, stdout, stderr = ssh.execute_command("echo test")
        assert exit_code == 0

        # Should track executed commands
        assert len(ssh.commands_executed) > 0

        # Should be able to disconnect
        ssh.disconnect()
        assert not ssh.is_connected()

    def test_docker_inference_workflow_contract(self):
        """Docker executor should follow expected inference workflow."""
        docker = FakeDockerExecutor()
        prompt_file = Path("test.json")
        prompt_file.write_text('{"name": "test"}')

        # Should be able to run inference
        docker.run_inference(prompt_file)

        # Should track the execution
        assert len(docker.containers_run) == 1
        assert docker.containers_run[0][0] == "inference"

        # Should store results
        assert prompt_file.stem in docker.inference_results
        result = docker.inference_results[prompt_file.stem]
        assert "status" in result
        assert "output_path" in result

        # Cleanup
        prompt_file.unlink()

    def test_file_transfer_upload_contract(self):
        """File transfer should follow upload contract."""
        transfer = FakeFileTransferService()
        test_file = Path("test.txt")
        test_file.write_text("test content")

        try:
            # Should be able to upload existing file
            result = transfer.upload_file(test_file, "/remote/dir")

            # Should return None on success (following real implementation)
            assert result is None

            # Should track the upload
            assert len(transfer.uploaded_files) == 1
            upload = transfer.uploaded_files[0]
            assert upload["local_path"] == test_file
            assert upload["remote_path"] == "/remote/dir"
            assert upload["filename"] == "test.txt"

        finally:
            test_file.unlink()

    def test_workflow_orchestrator_contract(self):
        """Workflow orchestrator should follow expected workflow."""
        orchestrator = FakeWorkflowOrchestrator()

        # Create a mock run spec file
        run_spec = Path("run.json")
        run_spec.write_text('{"prompt_spec_id": "test"}')

        try:
            # Should be able to run inference
            result = orchestrator.run_inference(str(run_spec))

            # Should return success/failure
            assert isinstance(result, bool)

            # Should track workflow execution
            assert len(orchestrator.workflows_run) > 0
            workflow = orchestrator.workflows_run[0]
            assert workflow["type"] == "inference"
            assert "timestamp" in workflow

        finally:
            run_spec.unlink()


class TestFakeDataIntegrity:
    """Test that fakes maintain data integrity."""

    def test_fake_ssh_command_history_integrity(self):
        """SSH fake should maintain accurate command history."""
        ssh = FakeSSHManager()
        ssh.connect()

        commands = ["echo test1", "echo test2", "ls -la"]
        for cmd in commands:
            ssh.execute_command(cmd)

        # Verify all commands are tracked
        executed = [cmd for cmd, _ in ssh.commands_executed]
        for original in commands:
            assert original in executed

    def test_fake_docker_result_consistency(self):
        """Docker fake results should be internally consistent."""
        docker = FakeDockerExecutor()
        prompt = Path("test.json")
        prompt.write_text('{"name": "test"}')

        try:
            # Run inference
            docker.run_inference(prompt)

            # Results should be consistent
            result = docker.inference_results[prompt.stem]
            assert result["status"] == "success"
            assert "outputs/" in result["output_path"]
            assert result["output_path"].endswith(".mp4")

            # Timestamp should be valid ISO format
            from datetime import datetime

            datetime.fromisoformat(result["timestamp"])

        finally:
            prompt.unlink()

    def test_fake_file_transfer_tracking_integrity(self):
        """File transfer fake should accurately track all operations."""
        transfer = FakeFileTransferService()

        # Track uploads
        files = []
        for i in range(3):
            f = Path(f"test_{i}.txt")
            f.write_text(f"content {i}")
            files.append(f)
            transfer.upload_file(f, "/remote")

        try:
            # Verify all uploads tracked
            assert len(transfer.uploaded_files) == 3

            # Verify each upload has complete information
            for upload in transfer.uploaded_files:
                assert "local_path" in upload
                assert "remote_path" in upload
                assert "filename" in upload
                assert upload["local_path"].exists()

        finally:
            for f in files:
                f.unlink()
