#!/usr/bin/env python3
"""
Tests for the CosmosConverter module.
"""

import pytest
import json
from pathlib import Path
import tempfile
from datetime import datetime

from cosmos_workflow.prompts import (
    PromptSpec, RunSpec, CosmosConverter
)
from cosmos_workflow.prompts.schemas import ExecutionStatus


class TestCosmosConverter:
    """Test suite for CosmosConverter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create sample PromptSpec
        self.prompt_spec = PromptSpec(
            id="ps_test123",
            name="test_prompt",
            prompt="A futuristic city with flying cars",
            negative_prompt="bad quality, blurry",
            input_video_path="inputs/videos/test/color.mp4",
            control_inputs={
                "depth": "inputs/videos/test/depth.mp4",
                "seg": "inputs/videos/test/segmentation.mp4"
            },
            timestamp="2025-08-30T12:00:00Z",
            is_upsampled=False
        )
        
        # Create sample RunSpec
        self.run_spec = RunSpec(
            id="rs_test456",
            prompt_id="ps_test123",
            name="test_run",
            control_weights={
                "vis": 0.3,
                "edge": 0.4,
                "depth": 0.2,
                "seg": 0.1
            },
            parameters={
                "num_steps": 35,
                "guidance": 8.0,
                "sigma_max": 70.0,
                "seed": 42,
                "fps": 24
            },
            timestamp="2025-08-30T12:00:00Z",
            execution_status=ExecutionStatus.PENDING,
            output_path="outputs/test_run"
        )
    
    def test_prompt_spec_to_cosmos_basic(self):
        """Test basic conversion from PromptSpec to Cosmos format."""
        converter = CosmosConverter()
        cosmos_spec = converter.prompt_spec_to_cosmos(self.prompt_spec)
        
        # Check required fields
        assert cosmos_spec["prompt"] == "A futuristic city with flying cars"
        assert cosmos_spec["input_video_path"] == "inputs/videos/test/color.mp4"
        
        # Check control inputs are present with default weights
        assert "depth" in cosmos_spec
        assert cosmos_spec["depth"]["input_control"] == "inputs/videos/test/depth.mp4"
        assert cosmos_spec["depth"]["control_weight"] == 0.25  # Default weight
        
        assert "seg" in cosmos_spec
        assert cosmos_spec["seg"]["input_control"] == "inputs/videos/test/segmentation.mp4"
        assert cosmos_spec["seg"]["control_weight"] == 0.25  # Default weight
    
    def test_prompt_spec_to_cosmos_with_run_spec(self):
        """Test conversion with RunSpec providing weights."""
        converter = CosmosConverter()
        cosmos_spec = converter.prompt_spec_to_cosmos(self.prompt_spec, self.run_spec)
        
        # Check required fields
        assert cosmos_spec["prompt"] == "A futuristic city with flying cars"
        assert cosmos_spec["input_video_path"] == "inputs/videos/test/color.mp4"
        
        # Check seed from RunSpec parameters
        assert cosmos_spec["seed"] == 42
        
        # Check control inputs with RunSpec weights
        assert cosmos_spec["depth"]["control_weight"] == 0.2
        assert cosmos_spec["seg"]["control_weight"] == 0.1
        
        # Check modalities without explicit inputs (vis, edge)
        assert cosmos_spec["vis"]["control_weight"] == 0.3
        assert "input_control" not in cosmos_spec["vis"]  # vis doesn't need input
        
        assert cosmos_spec["edge"]["control_weight"] == 0.4
        assert "input_control" not in cosmos_spec["edge"]  # edge doesn't need input
    
    def test_zero_weight_exclusion(self):
        """Test that controls with zero weight are excluded."""
        # Create RunSpec with some zero weights
        run_spec = RunSpec(
            id="rs_test",
            prompt_id="ps_test",
            name="test",
            control_weights={
                "vis": 0.0,  # Zero weight
                "edge": 0.5,
                "depth": 0.5,
                "seg": 0.0  # Zero weight
            },
            parameters={},
            timestamp="2025-08-30T12:00:00Z",
            execution_status=ExecutionStatus.PENDING
        )
        
        converter = CosmosConverter()
        cosmos_spec = converter.prompt_spec_to_cosmos(self.prompt_spec, run_spec)
        
        # Check that zero-weight controls are excluded
        assert "vis" not in cosmos_spec
        assert "seg" not in cosmos_spec
        
        # Check that non-zero controls are included
        assert cosmos_spec["edge"]["control_weight"] == 0.5
        assert cosmos_spec["depth"]["control_weight"] == 0.5
    
    def test_run_spec_to_cosmos_params(self):
        """Test extracting Cosmos parameters from RunSpec."""
        converter = CosmosConverter()
        params = converter.run_spec_to_cosmos_params(self.run_spec)
        
        # Check parameter mapping
        assert params["num_steps"] == 35
        assert params["guidance_scale"] == 8.0  # Note: mapped from "guidance"
        assert params["sigma_max"] == 70.0
        assert params["fps"] == 24
        assert params["seed"] == 42
        
        # Check execution-specific parameters
        assert params["output_dir"] == "outputs/test_run"
        assert params["video_save_name"] == "test_run_rs_test456"
    
    def test_save_cosmos_spec(self):
        """Test saving Cosmos spec to JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            converter = CosmosConverter()
            cosmos_spec = converter.prompt_spec_to_cosmos(self.prompt_spec, self.run_spec)
            
            # Save the spec
            output_path = temp_path / "cosmos_spec.json"
            saved_path = converter.save_cosmos_spec(cosmos_spec, output_path)
            
            assert saved_path.exists()
            assert saved_path == output_path
            
            # Load and verify content
            with open(saved_path, 'r') as f:
                loaded_spec = json.load(f)
            
            assert loaded_spec["prompt"] == cosmos_spec["prompt"]
            assert loaded_spec["input_video_path"] == cosmos_spec["input_video_path"]
            assert loaded_spec["seed"] == cosmos_spec["seed"]
    
    def test_validate_cosmos_spec_valid(self):
        """Test validation of valid Cosmos specs."""
        converter = CosmosConverter()
        
        # Valid spec with all required fields
        valid_spec = {
            "prompt": "Test prompt",
            "input_video_path": "test.mp4",
            "depth": {
                "control_weight": 0.5
            }
        }
        
        assert converter.validate_cosmos_spec(valid_spec) is True
    
    def test_validate_cosmos_spec_invalid(self):
        """Test validation of invalid Cosmos specs."""
        converter = CosmosConverter()
        
        # Missing prompt
        invalid_spec1 = {
            "input_video_path": "test.mp4",
            "depth": {"control_weight": 0.5}
        }
        assert converter.validate_cosmos_spec(invalid_spec1) is False
        
        # Missing input_video_path
        invalid_spec2 = {
            "prompt": "Test prompt",
            "depth": {"control_weight": 0.5}
        }
        assert converter.validate_cosmos_spec(invalid_spec2) is False
        
        # Invalid control structure
        invalid_spec3 = {
            "prompt": "Test prompt",
            "input_video_path": "test.mp4",
            "depth": 0.5  # Should be dict
        }
        assert converter.validate_cosmos_spec(invalid_spec3) is False
        
        # Missing control_weight
        invalid_spec4 = {
            "prompt": "Test prompt",
            "input_video_path": "test.mp4",
            "depth": {
                "input_control": "depth.mp4"  # Missing control_weight
            }
        }
        assert converter.validate_cosmos_spec(invalid_spec4) is False
    
    def test_create_upscaler_spec(self):
        """Test creating upscaler specification."""
        converter = CosmosConverter()
        upscaler_spec = converter.create_upscaler_spec(
            "input_video.mp4",
            upscale_weight=0.7
        )
        
        assert upscaler_spec["input_video_path"] == "input_video.mp4"
        assert upscaler_spec["upscale"]["control_weight"] == 0.7
    
    def test_merge_specs(self):
        """Test merging two Cosmos specifications."""
        converter = CosmosConverter()
        
        base_spec = {
            "prompt": "Base prompt",
            "input_video_path": "base.mp4",
            "depth": {
                "control_weight": 0.5,
                "input_control": "depth.mp4"
            }
        }
        
        override_spec = {
            "prompt": "Override prompt",  # Override
            "depth": {
                "control_weight": 0.8  # Partial override
            },
            "edge": {  # New modality
                "control_weight": 0.3
            }
        }
        
        merged = converter.merge_specs(base_spec, override_spec)
        
        # Check overrides
        assert merged["prompt"] == "Override prompt"
        assert merged["input_video_path"] == "base.mp4"  # Not overridden
        assert merged["depth"]["control_weight"] == 0.8  # Overridden
        assert merged["depth"]["input_control"] == "depth.mp4"  # Preserved
        assert merged["edge"]["control_weight"] == 0.3  # Added
    
    def test_partial_control_weights(self):
        """Test handling of partial control weights."""
        # Create RunSpec with only some modalities
        run_spec = RunSpec(
            id="rs_test",
            prompt_id="ps_test",
            name="test",
            control_weights={
                "depth": 0.6,
                "edge": 0.4
                # No vis or seg
            },
            parameters={},
            timestamp="2025-08-30T12:00:00Z",
            execution_status=ExecutionStatus.PENDING
        )
        
        converter = CosmosConverter()
        cosmos_spec = converter.prompt_spec_to_cosmos(self.prompt_spec, run_spec)
        
        # Check that only specified modalities are included
        assert cosmos_spec["depth"]["control_weight"] == 0.6
        assert cosmos_spec["edge"]["control_weight"] == 0.4
        assert "vis" not in cosmos_spec  # Not specified
        # seg has input but no weight, so excluded
        assert "seg" not in cosmos_spec
    
    def test_spatiotemporal_weights_string(self):
        """Test that string weights (for .pt files) are handled correctly."""
        run_spec = RunSpec(
            id="rs_test",
            prompt_id="ps_test",
            name="test",
            control_weights={
                "depth": "weights/depth_weights.pt",  # String path
                "edge": 0.5  # Numeric
            },
            parameters={},
            timestamp="2025-08-30T12:00:00Z",
            execution_status=ExecutionStatus.PENDING
        )
        
        # Note: This would require modifying the RunSpec to accept string weights
        # For now, this test documents the expected behavior
        # The actual implementation would need to handle this in the schema
        pass  # TODO: Implement when spatiotemporal weights support is added


if __name__ == "__main__":
    pytest.main([__file__])