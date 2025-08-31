#!/usr/bin/env python3
"""
Comprehensive tests for SchemaUtils.
Tests all methods, edge cases, and error conditions.
"""

import pytest
from unittest.mock import Mock, patch

from cosmos_workflow.prompts.schemas import SchemaUtils, BlurStrength, CannyThreshold


class TestSchemaUtils:
    """Test the SchemaUtils class."""
    
    def test_generate_prompt_id_basic(self):
        """Test basic prompt ID generation."""
        prompt_text = "A beautiful sunset over the ocean"
        input_video_path = "inputs/videos/test.mp4"
        control_inputs = {
            "depth": "inputs/videos/test/depth.mp4",
            "seg": "inputs/videos/test/segmentation.mp4"
        }
        
        prompt_id = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs)
        
        assert isinstance(prompt_id, str)
        assert prompt_id.startswith("ps_")
        assert len(prompt_id) == 15  # ps_ + 12 hex chars
        assert prompt_id.count("_") == 1  # Only one underscore separator
    
    def test_generate_prompt_id_deterministic(self):
        """Test that prompt ID generation is deterministic."""
        prompt_text = "Test prompt"
        input_video_path = "inputs/videos/test.mp4"
        control_inputs = {"depth": "depth.mp4", "seg": "seg.mp4"}
        
        # Generate IDs multiple times
        id1 = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs)
        id2 = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs)
        id3 = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs)
        
        # Should all be identical
        assert id1 == id2 == id3
    
    def test_generate_prompt_id_different_inputs(self):
        """Test that different inputs generate different IDs."""
        base_prompt = "Test prompt"
        base_video = "inputs/videos/test.mp4"
        base_control = {"depth": "depth.mp4", "seg": "seg.mp4"}
        
        # Generate base ID
        base_id = SchemaUtils.generate_prompt_id(base_prompt, base_video, base_control)
        
        # Test different prompt text
        different_prompt_id = SchemaUtils.generate_prompt_id(
            "Different prompt", base_video, base_control
        )
        assert different_prompt_id != base_id
        
        # Test different video path
        different_video_id = SchemaUtils.generate_prompt_id(
            base_prompt, "inputs/videos/different.mp4", base_control
        )
        assert different_video_id != base_id
        
        # Test different control inputs
        different_control_id = SchemaUtils.generate_prompt_id(
            base_prompt, base_video, {"depth": "different_depth.mp4", "seg": "seg.mp4"}
        )
        assert different_control_id != base_id
    
    def test_generate_prompt_id_control_inputs_order(self):
        """Test that control inputs order doesn't affect ID generation."""
        prompt_text = "Test prompt"
        input_video_path = "inputs/videos/test.mp4"
        
        # Control inputs in different orders
        control_inputs1 = {"depth": "depth.mp4", "seg": "seg.mp4"}
        control_inputs2 = {"seg": "seg.mp4", "depth": "depth.mp4"}
        
        id1 = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs1)
        id2 = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs2)
        
        # Should be identical due to sorting
        assert id1 == id2
    
    def test_generate_prompt_id_edge_cases(self):
        """Test prompt ID generation with edge cases."""
        # Empty strings
        empty_id = SchemaUtils.generate_prompt_id("", "", {})
        assert empty_id.startswith("ps_")
        assert len(empty_id) == 15
        
        # Very long strings
        long_prompt = "A" * 1000
        long_video = "B" * 1000
        long_control = {"depth": "C" * 1000, "seg": "D" * 1000}
        
        long_id = SchemaUtils.generate_prompt_id(long_prompt, long_video, long_control)
        assert long_id.startswith("ps_")
        assert len(long_id) == 15
        
        # Special characters
        special_prompt = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        special_video = "path/with/special/chars/!@#$%^&*().mp4"
        special_control = {"depth": "depth!@#.mp4", "seg": "seg$%^.mp4"}
        
        special_id = SchemaUtils.generate_prompt_id(special_prompt, special_video, special_control)
        assert special_id.startswith("ps_")
        assert len(special_id) == 15
    
    def test_generate_run_id_basic(self):
        """Test basic run ID generation."""
        prompt_id = "ps_test123"
        control_weights = {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        parameters = {
            "num_steps": 50,
            "guidance": 10.0,
            "sigma_max": 75.0,
            "blur_strength": "high",
            "canny_threshold": "low",
            "fps": 30,
            "seed": 42
        }
        
        run_id = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)
        
        assert isinstance(run_id, str)
        assert run_id.startswith("rs_")
        assert len(run_id) == 15  # rs_ + 12 hex chars
        assert run_id.count("_") == 1  # Only one underscore separator
    
    def test_generate_run_id_deterministic(self):
        """Test that run ID generation is deterministic."""
        prompt_id = "ps_test123"
        control_weights = {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        parameters = {"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0}
        
        # Generate IDs multiple times
        id1 = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)
        id2 = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)
        id3 = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)
        
        # Should all be identical
        assert id1 == id2 == id3
    
    def test_generate_run_id_different_inputs(self):
        """Test that different inputs generate different IDs."""
        base_prompt_id = "ps_test123"
        base_weights = {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        base_params = {"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0}
        
        # Generate base ID
        base_id = SchemaUtils.generate_run_id(base_prompt_id, base_weights, base_params)
        
        # Test different prompt ID
        different_prompt_id = SchemaUtils.generate_run_id(
            "ps_different", base_weights, base_params
        )
        assert different_prompt_id != base_id
        
        # Test different control weights
        different_weights_id = SchemaUtils.generate_run_id(
            base_prompt_id, {"vis": 0.8, "edge": 0.2, "depth": 0.0, "seg": 0.0}, base_params
        )
        assert different_weights_id != base_id
        
        # Test different parameters
        different_params_id = SchemaUtils.generate_run_id(
            base_prompt_id, base_weights, {"num_steps": 100, "guidance": 20.0, "sigma_max": 80.0}
        )
        assert different_params_id != base_id
    
    def test_generate_run_id_weights_order(self):
        """Test that control weights order doesn't affect ID generation."""
        prompt_id = "ps_test123"
        parameters = {"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0}
        
        # Weights in different orders
        weights1 = {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        weights2 = {"seg": 0.1, "depth": 0.1, "edge": 0.3, "vis": 0.5}
        
        id1 = SchemaUtils.generate_run_id(prompt_id, weights1, parameters)
        id2 = SchemaUtils.generate_run_id(prompt_id, weights2, parameters)
        
        # Should be identical due to sorting
        assert id1 == id2
    
    def test_generate_run_id_parameters_order(self):
        """Test that parameters order doesn't affect ID generation."""
        prompt_id = "ps_test123"
        control_weights = {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        
        # Parameters in different orders
        params1 = {"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0}
        params2 = {"sigma_max": 75.0, "guidance": 10.0, "num_steps": 50}
        
        id1 = SchemaUtils.generate_run_id(prompt_id, control_weights, params1)
        id2 = SchemaUtils.generate_run_id(prompt_id, control_weights, params2)
        
        # Should be identical due to sorting
        assert id1 == id2
    
    def test_get_default_parameters(self):
        """Test getting default parameters."""
        default_params = SchemaUtils.get_default_parameters()
        
        assert isinstance(default_params, dict)
        assert "num_steps" in default_params
        assert "guidance" in default_params
        assert "sigma_max" in default_params
        assert "blur_strength" in default_params
        assert "canny_threshold" in default_params
        assert "fps" in default_params
        assert "seed" in default_params
        
        # Check specific values
        assert default_params["num_steps"] == 35
        assert default_params["guidance"] == 7.0
        assert default_params["sigma_max"] == 70.0
        assert default_params["blur_strength"] == BlurStrength.MEDIUM.value
        assert default_params["canny_threshold"] == CannyThreshold.MEDIUM.value
        assert default_params["fps"] == 24
        assert default_params["seed"] == 1
    
    def test_get_default_control_weights(self):
        """Test getting default control weights."""
        default_weights = SchemaUtils.get_default_control_weights()
        
        assert isinstance(default_weights, dict)
        assert "vis" in default_weights
        assert "edge" in default_weights
        assert "depth" in default_weights
        assert "seg" in default_weights
        
        # Check specific values
        assert default_weights["vis"] == 0.25
        assert default_weights["edge"] == 0.25
        assert default_weights["depth"] == 0.25
        assert default_weights["seg"] == 0.25
        
        # Check that weights sum to 1.0
        total_weight = sum(default_weights.values())
        assert total_weight == 1.0
    
    def test_validate_control_weights_valid(self):
        """Test validation of valid control weights."""
        valid_weights = [
            {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},
            {"vis": 1.0, "edge": 0.0, "depth": 0.0, "seg": 0.0},
            {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
            {"vis": 0.0, "edge": 0.0, "depth": 0.5, "seg": 0.5},
            # Partial weights are now valid
            {"vis": 0.5, "edge": 0.3, "depth": 0.1},  # Missing seg
            {"vis": 0.5},  # Single modality
            {"edge": 0.75, "seg": 0.25},  # Two modalities
        ]
        
        for weights in valid_weights:
            assert SchemaUtils.validate_control_weights(weights), f"Failed for {weights}"
    
    def test_validate_control_weights_invalid(self):
        """Test validation of invalid control weights."""
        invalid_weights = [
            {},  # Empty dict
            {"vis": -0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},  # Negative weight
            {"vis": "invalid", "edge": 0.3, "depth": 0.1, "seg": 0.1},  # Non-numeric
            {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1, "extra": 0.1},  # Extra key
            None  # None value
        ]
        
        for weights in invalid_weights:
            assert not SchemaUtils.validate_control_weights(weights), f"Failed for {weights}"
    
    def test_validate_control_weights_edge_cases(self):
        """Test validation of control weights with edge cases."""
        edge_cases = [
            {"vis": 0.0, "edge": 0.0, "depth": 0.0, "seg": 0.0},  # All zero
            {"vis": 0.999999, "edge": 0.000001, "depth": 0.0, "seg": 0.0},  # Very small
            {"vis": 1.0, "edge": 0.0, "depth": 0.0, "seg": 0.0},  # One weight = 1.0
            {"vis": 0.0},  # Single zero weight
            {"edge": 1.0},  # Single full weight
        ]
        
        for weights in edge_cases:
            assert SchemaUtils.validate_control_weights(weights), f"Failed for {weights}"
    
    def test_validate_parameters_valid(self):
        """Test validation of valid parameters."""
        valid_params = [
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 1,
                "guidance": 1.0,
                "sigma_max": 0.0,
                "blur_strength": "very_low",
                "canny_threshold": "very_low",
                "fps": 1,
                "seed": 1
            },
            {
                "num_steps": 100,
                "guidance": 20.0,
                "sigma_max": 80.0,
                "blur_strength": "very_high",
                "canny_threshold": "very_high",
                "fps": 60,
                "seed": 4294967295
            }
        ]
        
        for params in valid_params:
            assert SchemaUtils.validate_parameters(params), f"Failed for {params}"
    
    def test_validate_parameters_invalid(self):
        """Test validation of invalid parameters."""
        invalid_params = [
            {},  # Empty dict
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                # Missing blur_strength, canny_threshold, fps, seed
            },
            {
                "num_steps": 0,  # Below minimum
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 0.5,  # Below minimum
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 90.0,  # Above maximum
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "invalid",  # Invalid enum value
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "invalid",  # Invalid enum value
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 0,  # Below minimum
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 0  # Below minimum
            },
            None  # None value
        ]
        
        for params in invalid_params:
            assert not SchemaUtils.validate_parameters(params), f"Failed for {params}"
    
    def test_validate_parameters_edge_cases(self):
        """Test validation of parameters with edge cases."""
        edge_cases = [
            {
                "num_steps": 1,  # Minimum value
                "guidance": 1.0,  # Minimum value
                "sigma_max": 0.0,  # Minimum value
                "blur_strength": "very_low",  # Edge enum value
                "canny_threshold": "very_low",  # Edge enum value
                "fps": 1,  # Minimum value
                "seed": 1  # Minimum value
            },
            {
                "num_steps": 100,  # Maximum value
                "guidance": 20.0,  # Maximum value
                "sigma_max": 80.0,  # Maximum value
                "blur_strength": "very_high",  # Edge enum value
                "canny_threshold": "very_high",  # Edge enum value
                "fps": 60,  # Maximum value
                "seed": 4294967295  # Maximum value
            }
        ]
        
        for params in edge_cases:
            assert SchemaUtils.validate_parameters(params), f"Failed for {params}"
    
    def test_validate_parameters_enum_values(self):
        """Test validation of enum values for blur_strength and canny_threshold."""
        valid_blur_strengths = [e.value for e in BlurStrength]
        valid_canny_thresholds = [e.value for e in CannyThreshold]
        
        # Test each valid enum value
        for blur_strength in valid_blur_strengths:
            params = {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": blur_strength,
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            }
            assert SchemaUtils.validate_parameters(params), f"Failed for blur_strength: {blur_strength}"
        
        for canny_threshold in valid_canny_thresholds:
            params = {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": canny_threshold,
                "fps": 24,
                "seed": 1
            }
            assert SchemaUtils.validate_parameters(params), f"Failed for canny_threshold: {canny_threshold}"
    
    def test_validate_parameters_type_checking(self):
        """Test that parameter validation checks types correctly."""
        # Test with wrong types
        wrong_type_params = [
            {
                "num_steps": "35",  # String instead of int
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": "7.0",  # String instead of float
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": "24",  # String instead of int
                "seed": 1
            },
            {
                "num_steps": 35,
                "guidance": 7.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": "1"  # String instead of int
            }
        ]
        
        for params in wrong_type_params:
            assert not SchemaUtils.validate_parameters(params), f"Failed for {params}"
