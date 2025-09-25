#!/usr/bin/env python3
"""Integration test to verify UI handlers work correctly with CosmosAPI responses."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone


class TestUICosmosAPIIntegration:
    """Test that UI handlers correctly process real API response shapes."""

    def test_prompts_handler_with_real_api_response(self):
        """Test that prompt handlers work with actual API response format."""
        from cosmos_workflow.ui.tabs.prompts_handlers import load_ops_prompts

        with patch('cosmos_workflow.ui.tabs.prompts_handlers.CosmosAPI') as mock_api:
            # Use REAL response shape from CosmosAPI.list_prompts()
            mock_api.return_value.list_prompts.return_value = [
                {
                    "id": "ps_8b4e5f2a3d1c6789",
                    "prompt_text": "A beautiful sunset over mountains with golden light",
                    "parameters": {
                        "name": "sunset_mountain",
                        "enhanced": False,
                        "negative_prompt": "blurry, dark, low quality",
                        "fps": 24,
                        "resolution": "1024x576"
                    },
                    "inputs": {
                        "video": "/inputs/sunset/color.mp4",
                        "depth": "/inputs/sunset/depth.mp4",
                        "seg": "/inputs/sunset/segmentation.mp4"
                    },
                    "created_at": "2025-01-15T10:30:45.123456",
                    "updated_at": "2025-01-15T10:30:45.123456",
                    "metadata": {
                        "source": "user_upload",
                        "tags": ["nature", "sunset"]
                    }
                },
                {
                    "id": "ps_7f3a2b1c4d5e6890",
                    "prompt_text": "Cyberpunk city with neon lights",
                    "parameters": {
                        "name": "cyberpunk_city",
                        "enhanced": True,
                        "enhancement_model": "pixtral",
                        "negative_prompt": ""
                    },
                    "inputs": {
                        "video": "/inputs/city/color.mp4"
                    },
                    "created_at": "2025-01-14T08:15:30Z",
                    "updated_at": "2025-01-14T09:20:15Z"
                }
            ]

            result = load_ops_prompts(limit=10, search_text="", enhanced_filter="all")

            # Verify handler transforms API data correctly
            assert len(result) == 2

            # Check first row structure [checkbox, id, name, text, created]
            first_row = result[0]
            assert first_row[0] is False  # Checkbox unchecked
            assert first_row[1] == "ps_8b4e5f2a3d1c6789"
            assert first_row[2] == "sunset_mountain"
            assert "sunset" in first_row[3].lower()
            assert len(first_row[3]) <= 63  # Text truncated
            assert "2025-01-15" in first_row[4]

            # Check second row
            second_row = result[1]
            assert second_row[1] == "ps_7f3a2b1c4d5e6890"
            assert second_row[2] == "cyberpunk_city"

    def test_runs_handler_with_real_api_response(self):
        """Test that run handlers work with actual API response format."""
        from cosmos_workflow.ui.tabs.runs.run_actions import preview_delete_run

        with patch('cosmos_workflow.ui.tabs.runs.run_actions.CosmosAPI') as mock_api:
            # Use REAL response shape from CosmosAPI.get_run()
            mock_api.return_value.get_run.return_value = {
                "id": "rs_9c8d7e6f5a4b3210",
                "prompt_id": "ps_8b4e5f2a3d1c6789",
                "status": "completed",
                "model_type": "transfer",
                "execution_config": {
                    "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.3, "seg": 0.2},
                    "num_steps": 35,
                    "guidance_scale": 8.0,
                    "seed": 42,
                    "fps": 24,
                    "sigma_max": 1.0,
                    "blur_strength": 0.5
                },
                "outputs": {
                    "output_path": "/outputs/runs/rs_9c8d7e6f5a4b3210/output.mp4",
                    "files": ["output.mp4", "metadata.json", "preview.jpg"],
                    "size_bytes": 15728640,
                    "duration_seconds": 3.5
                },
                "created_at": "2025-01-15T10:35:00Z",
                "updated_at": "2025-01-15T10:37:45Z",
                "started_at": "2025-01-15T10:35:05Z",
                "completed_at": "2025-01-15T10:37:45Z",
                "rating": 4,
                "metadata": {
                    "container_id": "abc123def456",
                    "gpu_used": "NVIDIA RTX 4090"
                }
            }

            # Mock Path for output file checking
            with patch('cosmos_workflow.ui.tabs.runs.run_actions.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.name = "output.mp4"

                dialog, preview_text, checkbox, run_id = preview_delete_run("rs_9c8d7e6f5a4b3210")

                # Verify the preview was generated correctly (gr.update returns dict)
                assert dialog.get("visible") is True
                # preview_text is a gr.update dict, get the actual value
                preview_value = preview_text.get("value", "") if isinstance(preview_text, dict) else preview_text
                assert "rs_9c8d7e6f5a4b" in preview_value  # Only first part of ID shown
                assert "completed" in preview_value.lower()
                assert "transfer" in preview_value.lower()
                # File name might or might not appear
                assert run_id == "rs_9c8d7e6f5a4b3210"

    def test_queue_handler_with_real_service_response(self):
        """Test queue handlers with actual SimplifiedQueueService response format."""
        from cosmos_workflow.ui.queue_handlers import QueueHandlers

        mock_service = Mock()
        # Use REAL response shape from SimplifiedQueueService
        mock_service.get_queue_status.return_value = {
            "total_queued": 3,
            "paused": False,
            "running": {
                "id": "job_abc123",
                "type": "inference",
                "prompt_ids": ["ps_001"],
                "status": "running",
                "elapsed_time": 45,
                "started_at": "2025-01-15T10:35:00Z"
            },
            "queued": [
                {
                    "id": "job_def456",
                    "type": "batch_inference",
                    "position": 1,
                    "prompt_count": 3,
                    "prompt_ids": ["ps_002", "ps_003", "ps_004"],
                    "priority": 50
                },
                {
                    "id": "job_ghi789",
                    "type": "enhancement",
                    "position": 2,
                    "prompt_count": 1,
                    "prompt_ids": ["ps_005"],
                    "priority": 50
                }
            ]
        }

        handler = QueueHandlers(mock_service)
        status_text, table_data = handler.get_queue_display()

        # Verify status text
        assert "3 pending" in status_text
        assert "1 running" in status_text

        # Verify table structure
        assert len(table_data) == 3  # 1 running + 2 queued

        # Check running job row
        running_row = table_data[0]
        assert running_row[0] == "🏃"  # Status icon
        assert running_row[1] == "job_abc123"
        assert running_row[2] == "inference"
        assert running_row[3] == "running"
        assert "45s ago" in running_row[4]

        # Check queued job rows
        queued_row1 = table_data[1]
        assert queued_row1[0] == "1"  # Position
        assert queued_row1[1] == "job_def456"
        assert queued_row1[2] == "batch_inference"
        assert queued_row1[3] == "queued"
        assert "3 prompt(s)" in queued_row1[4]

    def test_status_check_with_real_api_response(self):
        """Test job status display with actual API status response."""
        from cosmos_workflow.ui.tabs.jobs_handlers import check_running_jobs

        with patch('cosmos_workflow.ui.tabs.jobs_handlers.CosmosAPI') as mock_api:
            # Use REAL response shape from CosmosAPI.check_status()
            mock_api.return_value.check_status.return_value = {
                "ssh_status": "connected",
                "ssh_host": "gpu-workstation.local",
                "docker_status": {
                    "docker_running": True,
                    "version": "24.0.7",
                    "containers_running": 1,
                    "containers_total": 5
                },
                "gpu_info": {
                    "name": "NVIDIA GeForce RTX 4090",
                    "memory_total": "24564 MiB",
                    "memory_used": "8192 MiB",
                    "memory_free": "16372 MiB",
                    "memory_percentage": "33%",
                    "gpu_utilization": "87%",
                    "temperature": "72°C",
                    "power_draw": "350W",
                    "power_limit": "450W",
                    "cuda_version": "12.1",
                    "driver_version": "535.129.03",
                    "clock_current": "2520 MHz",
                    "clock_max": "2520 MHz"
                },
                "active_run": {
                    "id": "rs_active123",
                    "prompt_id": "ps_source456",
                    "model_type": "transfer",
                    "status": "running",
                    "started_at": "2025-01-15T10:30:00Z",
                    "progress": 0.65
                },
                "container": {
                    "id": "c8f7e6d5c4b3a2190f8e7d6c5b4a3928",
                    "id_short": "c8f7e6d5c4b3",
                    "name": "cosmos_transfer_rs_active123",
                    "status": "running",
                    "created": "2025-01-15T10:30:00Z",
                    "image": "cosmos-inference:latest"
                },
                "disk_usage": {
                    "outputs_dir": "45.6 GB",
                    "inputs_dir": "12.3 GB",
                    "total": "57.9 GB"
                }
            }

            details, status, display = check_running_jobs()

            # Verify all status information is displayed correctly
            assert "SSH Connection     ✓ Connected" in details
            assert "Docker Daemon      ✓ Running" in details
            assert "NVIDIA GeForce RTX 4090" in details
            assert "24564 MiB" in details
            assert "8192 MiB / 24564 MiB (33%)" in details
            assert "87%" in details  # GPU utilization
            assert "72°C" in details  # Temperature
            assert "350W / 450W" in details  # Power
            assert "2520 MHz" in details  # Clock speed
            assert "CUDA Version       12.1" in details

            # Verify active run information
            assert "Active Operation   TRANSFER" in details
            assert "rs_active123" in details
            assert "ps_source456" in details

            # Verify container information
            assert "cosmos_transfer_rs_active123" in details
            assert "c8f7e6d5c4b3" in details

            # Verify status messages
            assert "Ready to stream" in status
            assert "🟢 Active Job Running" in display
            assert "TRANSFER" in display

    def test_enhancement_workflow_with_real_api(self):
        """Test enhancement workflow with actual API interactions."""
        from cosmos_workflow.ui.tabs.prompts_handlers import run_enhance_on_selected

        table_data = [
            [True, "ps_001", "Test Prompt", "Original text", "2025-01-15"],
        ]

        mock_queue = Mock()
        # Real response from SimplifiedQueueService.add_job()
        mock_queue.add_job.return_value = "job_enh_123abc"
        mock_queue.get_position.return_value = None  # Immediate execution

        with patch('gradio.Info') as mock_info:
            result = run_enhance_on_selected(
                table_data,
                create_new=False,  # Update existing
                force_overwrite=True,
                queue_service=mock_queue
            )

            # Verify job was added correctly
            assert mock_queue.add_job.called
            call_args = mock_queue.add_job.call_args
            assert call_args.kwargs["prompt_ids"] == ["ps_001"]
            assert call_args.kwargs["job_type"] == "enhancement"
            assert call_args.kwargs["config"]["create_new"] is False
            assert call_args.kwargs["config"]["enhancement_model"] == "pixtral"
            assert call_args.kwargs["config"]["force_overwrite"] is True

            # Verify response
            queue_table, enhance_status, status_display = result
            assert "Started 1 enhancement job" in enhance_status
            assert "updating 1 prompt" in enhance_status.lower()

    def test_filtering_with_real_data_shapes(self):
        """Test prompt filtering with realistic data shapes."""
        from cosmos_workflow.ui.tabs.prompts_handlers import filter_prompts

        # Real prompt data structure
        prompts = [
            {
                "id": "ps_today_001",
                "prompt_text": "Morning scene",
                "parameters": {"name": "morning", "enhanced": True},
                "inputs": {"video": "/inputs/morning/color.mp4"},
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "ps_week_002",
                "prompt_text": "Evening scene",
                "parameters": {"name": "evening", "enhanced": False},
                "inputs": {"video": "/inputs/evening/color.mp4"},
                "created_at": "2025-01-10T15:00:00Z"  # 5 days ago
            },
            {
                "id": "ps_old_003",
                "prompt_text": "Night scene",
                "parameters": {"name": "night", "enhanced": True},
                "inputs": {"video": "/inputs/night/color.mp4"},
                "created_at": "2024-12-01T10:00:00Z"  # Over 30 days ago
            }
        ]

        # Test search filter
        filtered = filter_prompts(prompts, search_text="evening")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "ps_week_002"

        # Test enhanced filter
        filtered = filter_prompts(prompts, enhanced_filter="enhanced")
        assert len(filtered) == 2
        assert all(p["parameters"]["enhanced"] for p in filtered)

        # Test date filter with mock datetime
        with patch('cosmos_workflow.ui.tabs.prompts_handlers.datetime') as mock_dt:
            mock_now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.fromisoformat = datetime.fromisoformat

            filtered = filter_prompts(prompts, date_filter="last_7_days")
            assert len(filtered) == 2  # Today and week ago

            filtered = filter_prompts(prompts, date_filter="older_than_30_days")
            assert len(filtered) == 1
            assert filtered[0]["id"] == "ps_old_003"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])