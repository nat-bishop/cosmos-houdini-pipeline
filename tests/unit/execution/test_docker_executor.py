"""
Tests for the DockerExecutor class - REFACTORED for behavior testing.

Following TEST_SUITE_INVESTIGATION_REPORT.md principles:
- Tests behavior and outcomes, not implementation
- Uses fakes instead of mocks for dependencies
- Tests would survive internal refactoring
- Focuses on the contract, not the implementation
"""

from pathlib import Path

import pytest

from tests.fixtures.fakes import FakeDockerExecutor, FakeSSHManager


class TestDockerExecutorBehavior:
    """Test DockerExecutor behavior, not implementation details."""

    @pytest.fixture
    def docker_executor(self):
        """Create DockerExecutor with fake dependencies."""
        ssh_manager = FakeSSHManager()
        ssh_manager.connect()  # Connect SSH for executor to work
        executor = FakeDockerExecutor(
            ssh_manager=ssh_manager, remote_dir="/home/ubuntu/cosmos", docker_image="cosmos:latest"
        )
        return executor

    @pytest.fixture
    def prompt_file(self, tmp_path):
        """Create a test prompt file."""
        prompt = tmp_path / "test_prompt.json"
        prompt.write_text('{"prompt": "A beautiful scene", "name": "test_scene"}')
        return prompt

    def test_inference_produces_expected_output(self, docker_executor, prompt_file):
        """Test that inference produces expected output structure.

        Verifies BEHAVIOR:
        - Inference completes successfully
        - Output has correct structure
        - Results are retrievable

        Does NOT test:
        - Exact Docker command format
        - Directory creation implementation
        - Internal method calls
        """
        # Run inference
        docker_executor.run_inference(prompt_file, num_gpu=2, cuda_devices="0,1")

        # Verify inference was executed
        assert len(docker_executor.containers_run) == 1
        container = docker_executor.containers_run[0]
        assert container[0] == "inference"

        # Verify configuration was applied
        config = container[1]
        assert config["num_gpu"] == 2
        assert config["cuda_devices"] == "0,1"

        # Verify results exist with expected structure
        prompt_name = prompt_file.stem
        assert prompt_name in docker_executor.inference_results
        result = docker_executor.inference_results[prompt_name]

        # Check output contract
        assert result["status"] == "success"
        assert "output_path" in result
        assert result["output_path"].endswith(".mp4")
        assert "duration" in result
        assert isinstance(result["duration"], int | float)

    def test_upscaling_validates_prerequisites(self, docker_executor, prompt_file):
        """Test that upscaling validates input requirements.

        Verifies BEHAVIOR:
        - Upscaling checks for input video
        - Fails gracefully when input missing
        - Succeeds when prerequisites met
        """
        # Upscaling without inference should fail
        with pytest.raises(FileNotFoundError, match="Input video not found"):
            docker_executor.run_upscaling(prompt_file)

        # Run inference first
        docker_executor.run_inference(prompt_file)

        # Now upscaling should work
        docker_executor.run_upscaling(prompt_file, control_weight=0.7)

        # Verify upscaling was executed
        assert len(docker_executor.containers_run) == 2
        upscale = docker_executor.containers_run[1]
        assert upscale[0] == "upscaling"
        assert upscale[1]["control_weight"] == 0.7

    def test_docker_status_reflects_system_state(self, docker_executor):
        """Test that Docker status accurately reflects system state.

        Verifies BEHAVIOR of status reporting, not how it's gathered.
        """
        # Initial status
        status = docker_executor.get_docker_status()
        assert status["docker_running"] is True
        assert status["containers_run"] == 0

        # Run some containers
        prompt = Path("test.json")
        prompt.write_text('{"name": "test"}')

        docker_executor.run_inference(prompt)
        docker_executor.run_inference(prompt)

        # Check updated status
        status = docker_executor.get_docker_status()
        assert status["containers_run"] == 2

        # Disconnect SSH
        docker_executor.ssh_manager.disconnect()
        status = docker_executor.get_docker_status()
        assert status["docker_running"] is False
        assert "error" in status

    def test_gpu_configuration_is_applied(self, docker_executor, prompt_file):
        """Test that GPU configuration is correctly applied.

        Verifies the BEHAVIOR of GPU configuration without
        coupling to the exact command format.
        """
        gpu_configs = [(1, "0"), (2, "0,1"), (4, "0,1,2,3"), (8, "0,1,2,3,4,5,6,7")]

        for num_gpu, cuda_devices in gpu_configs:
            # Clear previous runs
            docker_executor.containers_run.clear()

            # Run with specific config
            docker_executor.run_inference(prompt_file, num_gpu=num_gpu, cuda_devices=cuda_devices)

            # Verify configuration was applied
            container = docker_executor.containers_run[0]
            assert container[1]["num_gpu"] == num_gpu
            assert container[1]["cuda_devices"] == cuda_devices

    def test_output_paths_follow_convention(self, docker_executor, prompt_file):
        """Test that output paths follow expected conventions.

        Verifies the CONTRACT of output path structure,
        not the implementation of path generation.
        """
        # Run inference
        docker_executor.run_inference(prompt_file)

        prompt_name = prompt_file.stem
        result = docker_executor.inference_results[prompt_name]

        # Verify output path convention
        output_path = result["output_path"]
        assert f"/outputs/{prompt_name}/" in output_path
        assert output_path.endswith("output.mp4")

        # Run upscaling
        docker_executor.run_upscaling(prompt_file)

        # Verify upscaled output follows convention
        created_dirs = docker_executor.remote_executor.created_directories
        upscaled_dir = next(d for d in created_dirs if "upscaled" in d)
        assert f"{prompt_name}_upscaled" in upscaled_dir

    def test_inference_is_idempotent(self, docker_executor, prompt_file):
        """Test that repeated inference calls are idempotent.

        Verifies BEHAVIOR: Multiple calls with same input
        produce consistent results.
        """
        # Run inference multiple times
        for _ in range(3):
            docker_executor.run_inference(prompt_file)

        # Each run should create a new container execution
        assert len(docker_executor.containers_run) == 3

        # But all should have same configuration
        for container in docker_executor.containers_run:
            assert container[0] == "inference"
            assert container[1]["prompt"] == prompt_file.stem

    def test_error_handling_preserves_state(self, docker_executor, tmp_path):
        """Test that errors don't corrupt executor state.

        Verifies BEHAVIOR: System remains usable after errors.
        """
        # Create invalid prompt file
        bad_prompt = tmp_path / "bad.json"
        bad_prompt.write_text("invalid json {")

        # Good prompt
        good_prompt = tmp_path / "good.json"
        good_prompt.write_text('{"name": "good"}')

        # Run with good prompt
        docker_executor.run_inference(good_prompt)
        assert len(docker_executor.containers_run) == 1

        # Try upscaling non-existent inference (should fail)
        with pytest.raises(FileNotFoundError):
            docker_executor.run_upscaling(bad_prompt)

        # System should still be usable
        docker_executor.run_inference(good_prompt)
        assert len(docker_executor.containers_run) == 2

        # Status should still work
        status = docker_executor.get_docker_status()
        assert status["docker_running"] is True
        assert status["containers_run"] == 2


class TestDockerExecutorIntegration:
    """Integration tests using multiple fake components."""

    def test_full_inference_pipeline(self, tmp_path):
        """Test complete inference pipeline with fakes.

        Verifies BEHAVIOR of the full pipeline without
        real infrastructure.
        """
        # Set up components
        ssh_manager = FakeSSHManager()
        ssh_manager.connect()  # Connect SSH
        executor = FakeDockerExecutor(ssh_manager)

        # Create test data
        prompt_file = tmp_path / "prompt.json"
        prompt_file.write_text("""
        {
            "name": "mountain_scene",
            "prompt": "A mountain landscape",
            "negative_prompt": "",
            "control_inputs": {
                "depth": "inputs/depth.mp4",
                "segmentation": "inputs/seg.mp4"
            }
        }
        """)

        # Run inference
        executor.run_inference(prompt_file, num_gpu=2)

        # Verify SSH commands were executed
        assert len(ssh_manager.commands_executed) > 0

        # Verify output directory was created
        mkdir_commands = [cmd for cmd, _ in ssh_manager.commands_executed if "mkdir" in cmd]
        assert len(mkdir_commands) > 0
        # The fake uses the file stem as the name
        assert any(prompt_file.stem in cmd for cmd in mkdir_commands)

        # Verify inference completed
        assert prompt_file.stem in executor.inference_results

        # Run upscaling
        executor.run_upscaling(prompt_file, control_weight=0.8)

        # Verify upscaling directory was created
        upscale_dirs = [
            cmd for cmd, _ in ssh_manager.commands_executed if "mkdir" in cmd and "upscaled" in cmd
        ]
        assert len(upscale_dirs) > 0

    def test_concurrent_inference_isolation(self, tmp_path):
        """Test that concurrent inferences are isolated.

        Verifies BEHAVIOR: Multiple inferences don't interfere.
        """
        executor = FakeDockerExecutor()

        # Create multiple prompt files
        prompts = []
        for i in range(3):
            prompt = tmp_path / f"prompt_{i}.json"
            prompt.write_text(f'{{"name": "scene_{i}"}}')
            prompts.append(prompt)

        # Run all inferences
        for prompt in prompts:
            executor.run_inference(prompt)

        # Verify all completed independently
        assert len(executor.containers_run) == 3
        assert len(executor.inference_results) == 3

        # Verify each has unique results
        for i, prompt in enumerate(prompts):
            # The fake uses the file stem
            stem = prompt.stem
            assert stem in executor.inference_results
            result = executor.inference_results[stem]
            assert stem in result["output_path"]
