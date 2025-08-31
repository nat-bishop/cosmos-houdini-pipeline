"""
GPU and performance tests following guide recommendations.

Tests for:
- VRAM leak detection
- Performance regression guards
- Throughput benchmarks
- Resource cleanup
"""

import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import psutil
import pytest

# Only import torch if available
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None


@contextmanager
def deterministic_mode(seed: int = 42) -> Generator[None, None, None]:
    """Context manager for deterministic execution.

    Following guide's recommendation for deterministic seams.
    """
    if TORCH_AVAILABLE:
        # Save current state
        torch.initial_seed() if torch.cuda.is_available() else None
        old_deterministic = (
            torch.are_deterministic_algorithms_enabled()
            if hasattr(torch, "are_deterministic_algorithms_enabled")
            else None
        )
        old_cudnn_benchmark = torch.backends.cudnn.benchmark if torch.cuda.is_available() else None

        # Set deterministic mode
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
        if hasattr(torch, "use_deterministic_algorithms"):
            torch.use_deterministic_algorithms(True, warn_only=True)

        try:
            yield
        finally:
            # Restore state
            if old_deterministic is not None and hasattr(torch, "use_deterministic_algorithms"):
                torch.use_deterministic_algorithms(old_deterministic, warn_only=True)
            if old_cudnn_benchmark is not None and torch.cuda.is_available():
                torch.backends.cudnn.benchmark = old_cudnn_benchmark
    else:
        # No torch, just yield
        yield


class TestGPUResources:
    """Test GPU resource management and leak detection."""

    @pytest.mark.gpu
    @pytest.mark.skipif(
        not TORCH_AVAILABLE or not torch.cuda.is_available(), reason="CUDA not available"
    )
    def test_no_vram_leak(self):
        """Test that operations don't leak VRAM.

        Following guide section 5: VRAM leak detection.
        """
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

        # Measure baseline
        initial_memory = torch.cuda.memory_allocated()

        # Simulate some GPU operations
        with deterministic_mode():
            # Create tensors
            x = torch.randn(256, 256, device="cuda")
            y = torch.randn(256, 256, device="cuda")
            z = torch.matmul(x, y)

            # Clean up explicitly
            del x, y, z

        # Force cleanup
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

        # Check memory
        final_memory = torch.cuda.memory_allocated()

        # Allow small slack (8MB as per guide)
        memory_diff = final_memory - initial_memory
        assert memory_diff < 8 * 1024 * 1024, f"Memory leak detected: {memory_diff} bytes"

    @pytest.mark.gpu
    @pytest.mark.skipif(
        not TORCH_AVAILABLE or not torch.cuda.is_available(), reason="CUDA not available"
    )
    def test_gpu_memory_reporting(self):
        """Test GPU memory reporting functionality."""
        # Get memory info
        total_memory = torch.cuda.get_device_properties(0).total_memory
        allocated = torch.cuda.memory_allocated()
        reserved = torch.cuda.memory_reserved()

        # Verify reporting works
        assert total_memory > 0
        assert allocated >= 0
        assert reserved >= allocated

        # Verify we can track memory usage
        initial = torch.cuda.memory_allocated()
        tensor = torch.randn(1024, 1024, device="cuda")
        after_alloc = torch.cuda.memory_allocated()

        assert after_alloc > initial

        del tensor
        torch.cuda.empty_cache()
        final = torch.cuda.memory_allocated()

        assert final <= after_alloc

    @pytest.mark.gpu
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="Torch not available")
    def test_deterministic_gpu_execution(self):
        """Test that GPU operations can be deterministic.

        Following guide's deterministic seams requirement.
        """
        if not torch.cuda.is_available():
            # CPU determinism test
            with deterministic_mode(seed=123):
                x1 = torch.randn(100, 100)

            with deterministic_mode(seed=123):
                x2 = torch.randn(100, 100)

            torch.testing.assert_close(x1, x2)
        else:
            # GPU determinism test
            with deterministic_mode(seed=456):
                x1 = torch.randn(100, 100, device="cuda")
                y1 = torch.nn.functional.softmax(x1, dim=1)

            with deterministic_mode(seed=456):
                x2 = torch.randn(100, 100, device="cuda")
                y2 = torch.nn.functional.softmax(x2, dim=1)

            torch.testing.assert_close(y1, y2)


class TestPerformanceRegression:
    """Performance regression tests."""

    @pytest.mark.benchmark
    def test_file_processing_performance(self, tmp_path):
        """Test file processing performance doesn't regress.

        Following guide's throughput guard recommendation.
        """
        # Create test files
        test_files = []
        for i in range(100):
            file = tmp_path / f"test_{i}.txt"
            file.write_text(f"test content {i}" * 100)
            test_files.append(file)

        # Measure processing time
        start = time.perf_counter()

        # Process files (simulated)
        results = []
        for file in test_files:
            content = file.read_text()
            results.append(len(content))

        elapsed = time.perf_counter() - start

        # Performance assertion - should process 100 files in < 1 second
        assert elapsed < 1.0, f"File processing too slow: {elapsed:.2f}s"

        # Verify correctness
        assert len(results) == 100
        assert all(r > 0 for r in results)

    @pytest.mark.benchmark
    def test_json_serialization_performance(self):
        """Test JSON serialization performance."""
        import json

        # Create large test data
        test_data = {
            "prompts": [f"prompt_{i}" for i in range(1000)],
            "configs": {
                f"config_{i}": {"value": i, "nested": {"a": i, "b": i * 2}} for i in range(100)
            },
        }

        # Measure serialization
        start = time.perf_counter()
        for _ in range(10):
            json_str = json.dumps(test_data)
            loaded = json.loads(json_str)
        elapsed = time.perf_counter() - start

        # Should handle 10 iterations in < 0.5 seconds
        assert elapsed < 0.5, f"JSON processing too slow: {elapsed:.2f}s"

        # Verify correctness
        assert loaded["prompts"][0] == "prompt_0"
        assert len(loaded["configs"]) == 100

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_workflow_simulation_performance(self):
        """Test workflow simulation performance.

        Simulates a complete workflow to catch performance regressions.
        """
        from unittest.mock import Mock, patch
        from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

        # Use REAL orchestrator with mocked external dependencies
        with patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager'):
            orchestrator = WorkflowOrchestrator()
            # Mock only external services
            orchestrator.ssh_manager = Mock()
            orchestrator.file_transfer = Mock()
            orchestrator.file_transfer.upload_file.return_value = True
            orchestrator.docker_executor = Mock()
            orchestrator.docker_executor.run_inference.return_value = True

            # Create test specs
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)

                # Measure workflow execution
                start = time.perf_counter()

                for i in range(10):
                    spec_file = tmpdir / f"spec_{i}.json"
                    spec_file.write_text(f'{{"id": "test_{i}"}}')

                    # Run workflow
                    result = orchestrator.run_inference(str(spec_file))
                    assert result is True

                elapsed = time.perf_counter() - start

            # 10 workflows should complete in < 2 seconds with mocks
            assert elapsed < 2.0, f"Workflow simulation too slow: {elapsed:.2f}s"

            # Verify all workflows completed (check mock was called)
            assert orchestrator.docker_executor.run_inference.call_count >= 10


class TestResourceCleanup:
    """Test resource cleanup and management."""

    def test_memory_usage_baseline(self):
        """Test that memory usage stays within bounds."""
        process = psutil.Process()

        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Do some work
        data = []
        for _ in range(100):
            data.append([0] * 10000)

        # Clear data
        data.clear()
        del data

        # Check memory after cleanup (with some time for GC)
        import gc

        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Memory increase should be reasonable (< 100MB for this test)
        memory_increase = final_memory - initial_memory
        assert (
            memory_increase < 100
        ), f"Memory not properly released: {memory_increase:.1f}MB increase"

    def test_file_cleanup(self, tmp_path):
        """Test that temporary files are cleaned up."""
        # Track initial state
        initial_files = list(tmp_path.iterdir())

        # Create temporary files
        temp_files = []
        for i in range(10):
            file = tmp_path / f"temp_{i}.txt"
            file.write_text("temp data")
            temp_files.append(file)

        # Verify files exist
        assert all(f.exists() for f in temp_files)

        # Clean up
        for f in temp_files:
            f.unlink()

        # Verify cleanup
        final_files = list(tmp_path.iterdir())
        assert len(final_files) == len(initial_files)
        assert not any(f.name.startswith("temp_") for f in final_files)

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="Torch not available")
    def test_tensor_cleanup(self):
        """Test that tensors are properly cleaned up."""
        if torch.cuda.is_available():
            initial = torch.cuda.memory_allocated()

            # Create and delete tensors
            tensors = [torch.randn(100, 100, device="cuda") for _ in range(10)]
            del tensors

            torch.cuda.synchronize()
            torch.cuda.empty_cache()

            final = torch.cuda.memory_allocated()

            # Should return to near initial state
            assert final - initial < 1024 * 1024  # < 1MB difference


class TestDeterministicExecution:
    """Test deterministic execution capabilities."""

    def test_random_seed_control(self):
        """Test that random seeds can be controlled."""
        import random

        import numpy as np

        # Set seed and generate numbers
        random.seed(123)
        np.random.seed(123)

        random_vals1 = [random.random() for _ in range(5)]
        numpy_vals1 = np.random.random(5)

        # Reset seed and regenerate
        random.seed(123)
        np.random.seed(123)

        random_vals2 = [random.random() for _ in range(5)]
        numpy_vals2 = np.random.random(5)

        # Should be identical
        assert random_vals1 == random_vals2
        np.testing.assert_array_equal(numpy_vals1, numpy_vals2)

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="Torch not available")
    def test_torch_determinism(self):
        """Test PyTorch deterministic mode."""
        with deterministic_mode(seed=789):
            x1 = torch.randn(50, 50)
            if x1.is_cuda:
                x1 = x1.cpu()
            vals1 = x1.numpy()

        with deterministic_mode(seed=789):
            x2 = torch.randn(50, 50)
            if x2.is_cuda:
                x2 = x2.cpu()
            vals2 = x2.numpy()

        np.testing.assert_array_almost_equal(vals1, vals2)

    def test_deterministic_fixture_works(self):
        """Test that deterministic fixture properly controls randomness."""
        results = []

        for _ in range(2):
            with deterministic_mode(seed=999):
                import random

                import numpy as np

                # Generate some random values
                r = random.random()
                n = np.random.random()

                results.append((r, n))

        # Both iterations should produce same values
        assert results[0][0] == results[1][0]  # Random values match
        assert results[0][1] == results[1][1]  # Numpy values match
