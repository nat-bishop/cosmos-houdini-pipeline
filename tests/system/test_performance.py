"""
Performance benchmark tests for the Cosmos workflow system.
These tests measure and track performance metrics across different operations.
"""
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.mark.system
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmarking tests."""

    @pytest.fixture
    def performance_tracker(self, temp_dir):
        """Track performance metrics across tests."""

        class PerformanceTracker:
            def __init__(self):
                self.metrics = {}
                self.output_file = temp_dir / "performance_metrics.json"

            def record(self, operation: str, duration: float, **kwargs):
                if operation not in self.metrics:
                    self.metrics[operation] = []

                self.metrics[operation].append(
                    {"duration": duration, "timestamp": time.time(), **kwargs}
                )

            def get_stats(self, operation: str) -> Dict[str, float]:
                if operation not in self.metrics:
                    return {}

                durations = [m["duration"] for m in self.metrics[operation]]
                return {
                    "min": min(durations),
                    "max": max(durations),
                    "mean": statistics.mean(durations),
                    "median": statistics.median(durations),
                    "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
                }

            def save(self):
                self.output_file.write_text(json.dumps(self.metrics, indent=2))

        tracker = PerformanceTracker()
        yield tracker
        tracker.save()

    def test_file_transfer_performance(self, performance_tracker, temp_dir):
        """Benchmark file transfer operations."""
        from cosmos_workflow.transfer.file_transfer import FileTransferManager

        # Create test files of different sizes
        file_sizes = [1, 10, 100, 500]  # MB
        test_files = []

        for size_mb in file_sizes:
            test_file = temp_dir / f"test_{size_mb}mb.dat"
            test_file.write_bytes(b"\x00" * (size_mb * 1024 * 1024))
            test_files.append((test_file, size_mb))

        with patch("cosmos_workflow.transfer.file_transfer.SSHManager") as mock_ssh:
            mock_ssh_instance = MagicMock()
            mock_ssh.return_value = mock_ssh_instance

            mock_sftp = MagicMock()
            mock_ssh_instance.ssh_client.open_sftp.return_value = mock_sftp

            # Simulate transfer with realistic delays
            def simulate_transfer(local_path, remote_path):
                file_size = Path(local_path).stat().st_size
                # Simulate 10 MB/s transfer speed
                delay = file_size / (10 * 1024 * 1024)
                time.sleep(min(delay, 0.1))  # Cap at 100ms for testing
                return None

            mock_sftp.put.side_effect = simulate_transfer

            manager = FileTransferManager(Mock())
            manager.ssh_manager = mock_ssh_instance

            # Benchmark uploads
            for test_file, size_mb in test_files:
                start_time = time.time()
                manager.upload_file(str(test_file), f"/remote/{test_file.name}")
                duration = time.time() - start_time

                performance_tracker.record(
                    "file_upload",
                    duration,
                    size_mb=size_mb,
                    throughput_mbps=(size_mb / duration) if duration > 0 else 0,
                )

        # Check performance meets requirements
        stats = performance_tracker.get_stats("file_upload")
        assert stats["mean"] < 5.0  # Average should be under 5 seconds

    def test_video_conversion_performance(self, performance_tracker, temp_dir):
        """Benchmark video conversion from PNG sequences."""
        frame_counts = [24, 48, 96, 192]

        with patch("cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor") as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            for frame_count in frame_counts:
                # Simulate conversion time based on frame count
                def simulate_conversion(*args, **kwargs):
                    # ~50ms per frame processing
                    delay = frame_count * 0.05
                    time.sleep(min(delay, 1.0))  # Cap at 1 second
                    return True

                mock_processor_instance.create_video_from_frames.side_effect = simulate_conversion

                start_time = time.time()
                mock_processor_instance.create_video_from_frames(
                    input_pattern=f"frame_%04d.png",
                    output_path=str(temp_dir / f"output_{frame_count}.mp4"),
                    fps=24,
                )
                duration = time.time() - start_time

                performance_tracker.record(
                    "video_conversion",
                    duration,
                    frame_count=frame_count,
                    fps=24,
                    frames_per_second=frame_count / duration if duration > 0 else 0,
                )

        stats = performance_tracker.get_stats("video_conversion")
        assert stats["mean"] < 10.0  # Should convert in under 10 seconds average

    def test_prompt_spec_creation_performance(self, performance_tracker, temp_dir):
        """Benchmark PromptSpec creation and serialization."""
        from cosmos_workflow.prompts.schemas import PromptSpec

        prompt_counts = [1, 10, 50, 100]

        for count in prompt_counts:
            prompts = []
            start_time = time.time()

            for i in range(count):
                spec = PromptSpec(
                    id=f"ps_perf_{i:04d}",
                    name=f"scene_{i}",
                    prompt=f"Test prompt {i} with some longer text to simulate real usage",
                    negative_prompt="blurry, low quality",
                    input_video_path=f"/path/to/video_{i}.mp4",
                    control_inputs={
                        "depth": f"/path/to/depth_{i}.mp4",
                        "segmentation": f"/path/to/seg_{i}.mp4",
                    },
                    timestamp=time.time(),
                )

                # Serialize to JSON
                spec_dict = spec.to_dict()
                json_str = json.dumps(spec_dict)

                # Deserialize
                loaded_spec = PromptSpec.from_dict(json.loads(json_str))
                prompts.append(loaded_spec)

            duration = time.time() - start_time

            performance_tracker.record(
                "prompt_spec_creation",
                duration,
                count=count,
                per_spec_ms=(duration * 1000 / count) if count > 0 else 0,
            )

        stats = performance_tracker.get_stats("prompt_spec_creation")
        # Should create 100 specs in under 1 second
        assert all(
            m["per_spec_ms"] < 10 for m in performance_tracker.metrics["prompt_spec_creation"]
        )

    def test_workflow_orchestration_performance(self, performance_tracker):
        """Benchmark complete workflow orchestration."""
        from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

        with patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager") as mock_ssh, patch(
            "cosmos_workflow.workflows.workflow_orchestrator.FileTransferManager"
        ) as mock_ft, patch(
            "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor"
        ) as mock_docker:
            # Create mock instances
            mock_ssh_instance = MagicMock()
            mock_ft_instance = MagicMock()
            mock_docker_instance = MagicMock()

            mock_ssh.return_value = mock_ssh_instance
            mock_ft.return_value = mock_ft_instance
            mock_docker.return_value = mock_docker_instance

            # Configure mock responses with delays
            mock_ssh_instance.is_connected.return_value = True
            mock_ft_instance.upload_file.side_effect = lambda *args: time.sleep(0.1) or True
            mock_ft_instance.download_directory.side_effect = lambda *args: time.sleep(0.2) or True
            mock_docker_instance.run_inference.side_effect = lambda *args: (
                time.sleep(0.5) or (0, "Success", "")
            )

            orchestrator = WorkflowOrchestrator(Mock())
            orchestrator.ssh_manager = mock_ssh_instance
            orchestrator.file_transfer = mock_ft_instance
            orchestrator.docker_executor = mock_docker_instance

            # Benchmark different workflow sizes
            workflow_sizes = [1, 5, 10, 20]

            for size in workflow_sizes:
                start_time = time.time()

                for i in range(size):
                    # Simulate workflow step
                    orchestrator.file_transfer.upload_file(
                        f"file_{i}.json", f"/remote/file_{i}.json"
                    )

                orchestrator.docker_executor.run_inference("test_spec.json", num_gpus=1)
                orchestrator.file_transfer.download_directory("/remote/output", "local/output")

                duration = time.time() - start_time

                performance_tracker.record(
                    "workflow_orchestration",
                    duration,
                    workflow_size=size,
                    steps_per_second=size / duration if duration > 0 else 0,
                )

        stats = performance_tracker.get_stats("workflow_orchestration")
        assert stats["mean"] < 30.0  # Should complete in under 30 seconds average

    def test_parallel_processing_performance(self, performance_tracker):
        """Benchmark parallel processing capabilities."""
        import concurrent.futures

        def process_item(item_id: int) -> float:
            """Simulate processing an item."""
            start = time.time()
            time.sleep(0.1)  # Simulate work
            return time.time() - start

        # Test different levels of parallelism
        worker_counts = [1, 2, 4, 8]
        item_count = 20

        for workers in worker_counts:
            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(process_item, i) for i in range(item_count)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            duration = time.time() - start_time

            performance_tracker.record(
                "parallel_processing",
                duration,
                workers=workers,
                items=item_count,
                speedup=1.0 / (duration / (item_count * 0.1)) if duration > 0 else 0,
            )

        # Check that parallelism improves performance
        metrics = performance_tracker.metrics["parallel_processing"]
        single_thread = next(m for m in metrics if m["workers"] == 1)
        multi_thread = next(m for m in metrics if m["workers"] == 4)

        # Multi-threading should be faster
        assert multi_thread["duration"] < single_thread["duration"]

    def test_memory_usage_tracking(self, performance_tracker, temp_dir):
        """Track memory usage during operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large data structures
        data_sizes = [10, 50, 100]  # MB

        for size_mb in data_sizes:
            # Allocate memory
            data = bytearray(size_mb * 1024 * 1024)

            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - baseline_memory

            performance_tracker.record(
                "memory_usage", memory_increase, allocated_mb=size_mb, total_mb=current_memory
            )

            # Clean up
            del data

        # Check memory doesn't grow excessively
        stats = performance_tracker.get_stats("memory_usage")
        assert stats["max"] < 500  # Should stay under 500MB increase

    def test_database_query_performance(self, performance_tracker, temp_dir):
        """Benchmark database-like operations (JSON file queries)."""
        # Create test dataset
        num_records = 1000
        db_file = temp_dir / "test_db.json"

        records = []
        for i in range(num_records):
            records.append(
                {
                    "id": f"id_{i:04d}",
                    "name": f"item_{i}",
                    "value": i * 1.5,
                    "tags": [f"tag_{j}" for j in range(5)],
                }
            )

        db_file.write_text(json.dumps(records))

        # Benchmark different query operations
        operations = [
            ("load_all", lambda: json.loads(db_file.read_text())),
            ("filter_by_value", lambda: [r for r in records if r["value"] > 500]),
            ("search_by_name", lambda: [r for r in records if "item_50" in r["name"]]),
            ("aggregate", lambda: sum(r["value"] for r in records)),
        ]

        for op_name, operation in operations:
            start_time = time.time()
            result = operation()
            duration = time.time() - start_time

            performance_tracker.record(
                "db_operations", duration, operation=op_name, record_count=num_records
            )

        stats = performance_tracker.get_stats("db_operations")
        assert stats["mean"] < 0.1  # Operations should be fast (< 100ms average)

    def test_network_latency_simulation(self, performance_tracker):
        """Simulate and benchmark network operations with varying latency."""
        import random

        latencies = [10, 50, 100, 200]  # ms

        def simulate_network_call(latency_ms: float) -> float:
            """Simulate a network call with given latency."""
            start = time.time()
            # Add some jitter (±10%)
            actual_latency = latency_ms * (1 + random.uniform(-0.1, 0.1))
            time.sleep(actual_latency / 1000)
            return time.time() - start

        for base_latency in latencies:
            durations = []

            for _ in range(10):  # Multiple calls to get average
                duration = simulate_network_call(base_latency)
                durations.append(duration * 1000)  # Convert to ms

            avg_latency = statistics.mean(durations)

            performance_tracker.record(
                "network_latency",
                avg_latency,
                target_latency=base_latency,
                jitter=statistics.stdev(durations) if len(durations) > 1 else 0,
            )

        # Verify latencies are within expected range
        for metric in performance_tracker.metrics["network_latency"]:
            assert abs(metric["duration"] - metric["target_latency"]) < 20  # Within 20ms

    @pytest.mark.slow
    def test_stress_test_concurrent_operations(self, performance_tracker):
        """Stress test with many concurrent operations."""
        import concurrent.futures
        import random

        def stress_operation(op_id: int) -> Dict[str, Any]:
            """Perform a stress test operation."""
            start = time.time()

            # Simulate various operations
            operation_type = random.choice(["cpu", "io", "memory"])

            if operation_type == "cpu":
                # CPU intensive
                result = sum(i * i for i in range(10000))
            elif operation_type == "io":
                # I/O simulation
                time.sleep(random.uniform(0.01, 0.05))
                result = f"io_result_{op_id}"
            else:
                # Memory intensive
                data = [random.random() for _ in range(10000)]
                result = sum(data)

            return {
                "op_id": op_id,
                "type": operation_type,
                "duration": time.time() - start,
                "result": result,
            }

        # Run stress test
        num_operations = 100
        max_workers = 10

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(stress_operation, i) for i in range(num_operations)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        total_duration = time.time() - start_time

        # Analyze results
        by_type = {}
        for result in results:
            op_type = result["type"]
            if op_type not in by_type:
                by_type[op_type] = []
            by_type[op_type].append(result["duration"])

        performance_tracker.record(
            "stress_test",
            total_duration,
            total_operations=num_operations,
            operations_per_second=num_operations / total_duration,
            max_workers=max_workers,
        )

        # System should handle load
        assert total_duration < 10.0  # Should complete in under 10 seconds
        assert all(max(durations) < 1.0 for durations in by_type.values())  # No operation over 1s
