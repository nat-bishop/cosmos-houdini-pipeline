"""Test batch inference controlnet spec generation for NVIDIA Cosmos format.

This module tests the creation of base controlnet specs that are required
for batch inference, and the proper formatting of batch JSONL with control overrides.
"""

from cosmos_workflow.utils import nvidia_format


class TestCreateBatchBaseControlnetSpec:
    """Test the creation of base controlnet specs for batch inference."""

    def test_empty_batch_returns_minimal_spec(self):
        """Empty batch should return a minimal valid controlnet spec."""
        runs_and_prompts = []

        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        assert spec == {
            "prompt": "",
            "input_video_path": "",
        }

    def test_single_prompt_with_all_controls(self):
        """Single prompt with all control types should include all in base spec."""
        run_dict = {
            "id": "rs_test123",
            "execution_config": {
                "weights": {
                    "vis": 0.3,
                    "edge": 0.4,
                    "depth": 0.5,
                    "seg": 0.6,
                }
            },
        }
        prompt_dict = {
            "id": "ps_test456",
            "prompt_text": "Test prompt",
            "inputs": {
                "video": "test.mp4",
                "depth": "depth.mp4",
                "seg": "seg.mp4",
            },
        }
        runs_and_prompts = [(run_dict, prompt_dict)]

        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should have all controls with their weights from the prompt
        # and input_video_path from first video
        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_test123/inputs/videos/test.mp4",
            "vis": {"control_weight": 0.3},
            "edge": {"control_weight": 0.4},
            "depth": {"control_weight": 0.5},
            "seg": {"control_weight": 0.6},
        }

    def test_multiple_prompts_merge_unique_controls(self):
        """Multiple prompts with different controls should merge all unique controls."""
        run1 = {"id": "rs_001", "execution_config": {"weights": {"vis": 0.2, "depth": 0.3}}}
        prompt1 = {
            "id": "ps_001",
            "prompt_text": "Prompt 1",
            "inputs": {"video": "video1.mp4", "depth": "depth1.mp4"},
        }

        run2 = {"id": "rs_002", "execution_config": {"weights": {"edge": 0.4, "seg": 0.5}}}
        prompt2 = {
            "id": "ps_002",
            "prompt_text": "Prompt 2",
            "inputs": {"video": "video2.mp4", "seg": "seg2.mp4"},
        }

        run3 = {
            "id": "rs_003",
            "execution_config": {
                "weights": {"vis": 0.6, "edge": 0.7}  # Overlapping controls
            },
        }
        prompt3 = {"id": "ps_003", "prompt_text": "Prompt 3", "inputs": {"video": "video3.mp4"}}

        runs_and_prompts = [(run1, prompt1), (run2, prompt2), (run3, prompt3)]

        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should have union of all controls
        # When multiple prompts have same control, use first encountered weight
        # input_video_path from first prompt with video
        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_001/inputs/videos/video1.mp4",
            "vis": {"control_weight": 0.2},  # From run1 (first encountered)
            "depth": {"control_weight": 0.3},  # From run1
            "edge": {"control_weight": 0.4},  # From run2 (first encountered)
            "seg": {"control_weight": 0.5},  # From run2
        }

    def test_zero_weight_controls_excluded(self):
        """Controls with zero weight should be excluded from base spec."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "vis": 0.5,
                    "edge": 0.0,  # Zero weight
                    "depth": 0.3,
                    "seg": 0,  # Also zero
                }
            },
        }
        prompt = {"id": "ps_test", "prompt_text": "Test", "inputs": {"video": "test.mp4"}}

        runs_and_prompts = [(run, prompt)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should only include non-zero weight controls
        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_test/inputs/videos/test.mp4",
            "vis": {"control_weight": 0.5},
            "depth": {"control_weight": 0.3},
        }
        assert "edge" not in spec
        assert "seg" not in spec

    def test_no_controls_returns_minimal_spec(self):
        """Prompts with no control weights should return minimal spec with video path."""
        run = {
            "id": "rs_test",
            "execution_config": {},  # No weights key
        }
        prompt = {"id": "ps_test", "prompt_text": "Test prompt", "inputs": {"video": "test.mp4"}}

        runs_and_prompts = [(run, prompt)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_test/inputs/videos/test.mp4",
        }

    def test_missing_execution_config(self):
        """Handle runs missing execution_config gracefully."""
        run = {"id": "rs_test"}  # No execution_config
        prompt = {"id": "ps_test", "prompt_text": "Test", "inputs": {}}

        runs_and_prompts = [(run, prompt)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        assert spec == {
            "prompt": "",
            "input_video_path": "",
        }

    def test_none_values_handled_safely(self):
        """Handle None values in weights gracefully."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "vis": 0.3,
                    "edge": None,  # None should be treated as 0
                    "depth": 0.5,
                }
            },
        }
        prompt = {"id": "ps_test", "prompt_text": "Test", "inputs": {"video": "test.mp4"}}

        runs_and_prompts = [(run, prompt)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # None weight should be excluded
        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_test/inputs/videos/test.mp4",
            "vis": {"control_weight": 0.3},
            "depth": {"control_weight": 0.5},
        }
        assert "edge" not in spec

    def test_invalid_control_types_ignored(self):
        """Invalid/unknown control types should be ignored."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "vis": 0.3,
                    "invalid_control": 0.5,  # Not a valid control type
                    "depth": 0.4,
                    "unknown": 0.6,  # Another invalid one
                }
            },
        }
        prompt = {"id": "ps_test", "prompt_text": "Test", "inputs": {"video": "test.mp4"}}

        runs_and_prompts = [(run, prompt)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should only include valid control types
        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_test/inputs/videos/test.mp4",
            "vis": {"control_weight": 0.3},
            "depth": {"control_weight": 0.4},
        }
        assert "invalid_control" not in spec
        assert "unknown" not in spec

    def test_base_spec_never_includes_input_control_paths(self):
        """Base spec should never include input_control paths, even if prompts have them."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "depth": 0.5,
                    "seg": 0.6,
                }
            },
        }
        prompt = {
            "id": "ps_test",
            "prompt_text": "Test",
            "inputs": {
                "video": "video.mp4",
                "depth": "manual_depth.mp4",  # Manual depth input
                "seg": "manual_seg.mp4",  # Manual seg input
            },
        }

        runs_and_prompts = [(run, prompt)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should have controls but NO input_control paths
        assert spec == {
            "prompt": "",
            "input_video_path": "runs/rs_test/inputs/videos/video.mp4",
            "depth": {"control_weight": 0.5},  # No input_control
            "seg": {"control_weight": 0.6},  # No input_control
        }
        # Verify no input_control keys exist
        assert "input_control" not in spec.get("depth", {})
        assert "input_control" not in spec.get("seg", {})

    def test_large_batch_performance(self):
        """Test performance with a large batch of prompts."""
        runs_and_prompts = []
        for i in range(100):
            run = {
                "id": f"rs_{i:03d}",
                "execution_config": {
                    "weights": {
                        "vis": 0.1 + (i % 5) * 0.1,
                        "edge": 0.2 + (i % 3) * 0.1,
                        "depth": 0.3 if i % 2 == 0 else 0,
                        "seg": 0.4 if i % 4 == 0 else 0,
                    }
                },
            }
            prompt = {
                "id": f"ps_{i:03d}",
                "prompt_text": f"Prompt {i}",
                "inputs": {"video": f"video_{i}.mp4"},
            }
            runs_and_prompts.append((run, prompt))

        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should complete quickly and have all control types that appear
        assert "prompt" in spec
        assert "input_video_path" in spec
        assert "vis" in spec
        assert "edge" in spec
        assert "depth" in spec  # Appears in even-indexed runs
        assert "seg" in spec  # Appears in every 4th run

    def test_no_video_path_in_any_prompt(self):
        """If no prompts have video paths, input_video_path remains empty."""
        run1 = {"id": "rs_001", "execution_config": {"weights": {"vis": 0.2}}}
        prompt1 = {"id": "ps_001", "prompt_text": "P1", "inputs": {}}  # No video

        run2 = {"id": "rs_002", "execution_config": {"weights": {"edge": 0.4}}}
        prompt2 = {"id": "ps_002", "prompt_text": "P2", "inputs": {}}  # No video

        runs_and_prompts = [(run1, prompt1), (run2, prompt2)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Should have empty input_video_path if no videos found
        assert spec["input_video_path"] == ""
        assert "vis" in spec
        assert "edge" in spec

    def test_weight_averaging_strategy(self):
        """Test if we want to use averaging strategy for conflicting weights."""
        # Note: Current implementation uses first-encountered weight
        # This test documents that behavior and can be updated if we change strategy
        run1 = {"id": "rs_001", "execution_config": {"weights": {"vis": 0.2}}}
        prompt1 = {"id": "ps_001", "prompt_text": "P1", "inputs": {}}

        run2 = {"id": "rs_002", "execution_config": {"weights": {"vis": 0.8}}}
        prompt2 = {"id": "ps_002", "prompt_text": "P2", "inputs": {}}

        runs_and_prompts = [(run1, prompt1), (run2, prompt2)]
        spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Currently uses first-encountered (0.2), not average (0.5)
        assert spec["vis"]["control_weight"] == 0.2

        # If we wanted averaging, we'd test:
        # assert spec["vis"]["control_weight"] == 0.5


class TestBatchInferenceJsonlWithNull:
    """Test that batch JSONL properly uses null for automatic control generation."""

    def test_automatic_control_uses_null(self):
        """Controls without input paths should use null for automatic generation."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "depth": 0.5,  # Will be auto-generated
                    "seg": 0.6,  # Will be auto-generated
                }
            },
        }
        prompt = {
            "id": "ps_test",
            "prompt_text": "Test prompt",
            "inputs": {
                "video": "test_video.mp4",
                # No depth or seg inputs - should auto-generate
            },
        }

        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl([(run, prompt)])

        assert len(batch_lines) == 1
        line = batch_lines[0]

        # Check that auto-generated controls have null input_control
        assert line["control_overrides"]["depth"]["input_control"] is None
        assert line["control_overrides"]["seg"]["input_control"] is None
        assert line["control_overrides"]["depth"]["control_weight"] == 0.5
        assert line["control_overrides"]["seg"]["control_weight"] == 0.6

    def test_manual_control_preserves_path(self):
        """Controls with input paths should preserve the path."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "depth": 0.5,
                    "seg": 0.6,
                }
            },
        }
        prompt = {
            "id": "ps_test",
            "prompt_text": "Test prompt",
            "inputs": {
                "video": "test_video.mp4",
                "depth": "manual_depth.mp4",  # Manual input
                "seg": "manual_seg.mp4",  # Manual input
            },
        }

        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl([(run, prompt)])

        assert len(batch_lines) == 1
        line = batch_lines[0]

        # Check that manual controls have proper paths
        assert (
            line["control_overrides"]["depth"]["input_control"]
            == "runs/rs_test/inputs/videos/manual_depth.mp4"
        )
        assert (
            line["control_overrides"]["seg"]["input_control"]
            == "runs/rs_test/inputs/videos/manual_seg.mp4"
        )

    def test_mixed_manual_and_automatic_controls(self):
        """Test mix of manual and automatic controls in same prompt."""
        run = {
            "id": "rs_mixed",
            "execution_config": {
                "weights": {
                    "vis": 0.3,  # Always auto
                    "edge": 0.4,  # Auto (no input)
                    "depth": 0.5,  # Manual (has input)
                    "seg": 0.6,  # Auto (no input)
                }
            },
        }
        prompt = {
            "id": "ps_mixed",
            "prompt_text": "Mixed controls",
            "inputs": {
                "video": "base_video.mp4",
                "depth": "custom_depth.mp4",  # Only depth is manual
            },
        }

        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl([(run, prompt)])
        line = batch_lines[0]

        # vis and edge should not have input_control at all (different from null)
        assert "input_control" not in line["control_overrides"]["vis"]
        assert "input_control" not in line["control_overrides"]["edge"]

        # depth should have the manual path
        assert (
            line["control_overrides"]["depth"]["input_control"]
            == "runs/rs_mixed/inputs/videos/custom_depth.mp4"
        )

        # seg should be null for auto-generation
        assert line["control_overrides"]["seg"]["input_control"] is None

    def test_zero_weight_controls_excluded_from_jsonl(self):
        """Controls with zero weight should not appear in JSONL."""
        run = {
            "id": "rs_test",
            "execution_config": {
                "weights": {
                    "vis": 0.3,
                    "edge": 0,  # Zero weight
                    "depth": 0.5,
                    "seg": 0.0,  # Also zero
                }
            },
        }
        prompt = {"id": "ps_test", "prompt_text": "Test", "inputs": {"video": "test.mp4"}}

        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl([(run, prompt)])
        line = batch_lines[0]

        # Zero weight controls should not be in control_overrides
        assert "edge" not in line["control_overrides"]
        assert "seg" not in line["control_overrides"]
        assert "vis" in line["control_overrides"]
        assert "depth" in line["control_overrides"]


class TestBatchSpecIntegration:
    """Test integration between base spec and batch JSONL."""

    def test_base_spec_and_jsonl_consistency(self):
        """Base spec should contain all controls, JSONL should override specifics."""
        runs_and_prompts = [
            (
                {"id": "rs_001", "execution_config": {"weights": {"vis": 0.2, "depth": 0.3}}},
                {
                    "id": "ps_001",
                    "prompt_text": "Prompt 1",
                    "inputs": {"video": "v1.mp4", "depth": "d1.mp4"},
                },
            ),
            (
                {"id": "rs_002", "execution_config": {"weights": {"edge": 0.4, "seg": 0.5}}},
                {"id": "ps_002", "prompt_text": "Prompt 2", "inputs": {"video": "v2.mp4"}},
            ),
        ]

        # Generate base spec
        base_spec = nvidia_format.create_batch_base_controlnet_spec(runs_and_prompts)

        # Generate batch JSONL
        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Base spec should have all control types
        assert "vis" in base_spec
        assert "depth" in base_spec
        assert "edge" in base_spec
        assert "seg" in base_spec

        # First JSONL line should override only its controls
        line1 = batch_lines[0]
        assert "vis" in line1["control_overrides"]
        assert "depth" in line1["control_overrides"]
        assert "edge" not in line1["control_overrides"]
        assert "seg" not in line1["control_overrides"]

        # Second JSONL line should override only its controls
        line2 = batch_lines[1]
        assert "vis" not in line2["control_overrides"]
        assert "depth" not in line2["control_overrides"]
        assert "edge" in line2["control_overrides"]
        assert "seg" in line2["control_overrides"]

        # Check null vs path handling
        assert (
            line1["control_overrides"]["depth"]["input_control"]
            == "runs/rs_001/inputs/videos/d1.mp4"
        )
        assert line2["control_overrides"]["seg"]["input_control"] is None
