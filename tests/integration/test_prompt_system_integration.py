#!/usr/bin/env python3
"""
Comprehensive integration tests for the prompt system.
Tests how all components work together in real scenarios.
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from cosmos_workflow.prompts import (
    PromptManager, PromptSpecManager, RunSpecManager, SchemaValidator
)
from cosmos_workflow.prompts.schemas import (
    PromptSpec, RunSpec, DirectoryManager, SchemaUtils, ExecutionStatus
)


class TestPromptSystemIntegration:
    """Test the complete prompt system integration."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test directories
        self.prompts_dir = self.temp_path / "prompts"
        self.runs_dir = self.temp_path / "runs"
        self.outputs_dir = self.temp_path / "outputs"
        self.videos_dir = self.temp_path / "videos"
        
        self.prompts_dir.mkdir(parents=True)
        self.runs_dir.mkdir(parents=True)
        self.outputs_dir.mkdir(parents=True)
        self.videos_dir.mkdir(parents=True)
        
        # Create mock config
        self.mock_config = Mock()
        self.mock_config.prompts_dir = self.prompts_dir
        self.mock_config.runs_dir = self.runs_dir
        self.mock_config.outputs_dir = self.outputs_dir
        self.mock_config.videos_dir = self.videos_dir
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()
    
    def test_complete_workflow_integration(self):
        """Test complete workflow from PromptSpec creation to RunSpec execution."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            # Initialize the complete system
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Step 1: Create a PromptSpec
            prompt_spec = prompt_manager.create_prompt_spec(
                "cyberpunk_city",
                "A futuristic cyberpunk city with neon lights and flying cars",
                negative_prompt="Low quality, blurry, cartoonish",
                input_video_path="inputs/videos/cyberpunk_city/color.mp4",
                control_inputs={
                    "depth": "inputs/videos/cyberpunk_city/depth.mp4",
                    "seg": "inputs/videos/cyberpunk_city/segmentation.mp4"
                }
            )
            
            # Verify PromptSpec was created correctly
            assert isinstance(prompt_spec, PromptSpec)
            assert prompt_spec.name == "cyberpunk_city"
            assert prompt_spec.prompt == "A futuristic cyberpunk city with neon lights and flying cars"
            assert prompt_spec.id.startswith("ps_")
            assert prompt_spec.control_inputs["depth"] == "inputs/videos/cyberpunk_city/depth.mp4"
            
            # Step 2: Create a RunSpec for the PromptSpec
            run_spec = prompt_manager.create_run_spec(
                prompt_spec=prompt_spec,
                control_weights={"vis": 0.4, "edge": 0.3, "depth": 0.2, "seg": 0.1},
                parameters={
                    "num_steps": 50,
                    "guidance": 10.0,
                    "sigma_max": 75.0,
                    "blur_strength": "high",
                    "canny_threshold": "medium",
                    "fps": 30,
                    "seed": 42
                }
            )
            
            # Verify RunSpec was created correctly
            assert isinstance(run_spec, RunSpec)
            assert run_spec.prompt_id == prompt_spec.id
            assert run_spec.control_weights["vis"] == 0.4
            assert run_spec.parameters["num_steps"] == 50
            assert run_spec.id.startswith("rs_")
            
            # Step 3: Validate both specifications
            # Find the actual files created and validate them
            prompts_for_validation = prompt_manager.list_prompts()
            runs_for_validation = prompt_manager.list_runs()
            
            # Find our specific files
            prompt_file = None
            run_file = None
            for p in prompts_for_validation:
                info = prompt_manager.get_prompt_info(p)
                if info["id"] == prompt_spec.id:
                    prompt_file = p
                    break
            
            for r in runs_for_validation:
                info = prompt_manager.get_run_info(r)
                if info["id"] == run_spec.id:
                    run_file = r
                    break
            
            assert prompt_file is not None
            assert run_file is not None
            assert prompt_manager.validate_prompt_spec(prompt_file)
            assert prompt_manager.validate_run_spec(run_file)
            
            # Step 4: List and retrieve information
            prompts = prompt_manager.list_prompts()
            runs = prompt_manager.list_runs()
            
            assert len(prompts) >= 1
            assert len(runs) >= 1
            
            prompt_info = prompt_manager.get_prompt_info(prompts[0])
            run_info = prompt_manager.get_run_info(runs[0])
            
            assert prompt_info["id"] == prompt_spec.id
            assert run_info["id"] == run_spec.id
    
    def test_multiple_prompts_and_runs_integration(self):
        """Test creating multiple prompts and runs and managing them together."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create multiple PromptSpecs
            prompt_specs = []
            for i in range(3):
                prompt_spec = prompt_manager.create_prompt_spec(
                    f"test_prompt_{i}",
                    f"Test prompt text {i}",
                    input_video_path=f"inputs/videos/test_{i}/color.mp4"
                )
                prompt_specs.append(prompt_spec)
            
            # Create multiple RunSpecs for each PromptSpec
            run_specs = []
            for prompt_spec in prompt_specs:
                for j in range(2):
                    run_spec = prompt_manager.create_run_spec(
                        prompt_spec=prompt_spec,
                        control_weights={"vis": 0.3 + j*0.1, "edge": 0.3, "depth": 0.2, "seg": 0.2},
                        parameters={
                            "num_steps": 35 + j*10, 
                            "guidance": 7.0, 
                            "sigma_max": 70.0,
                            "blur_strength": "medium",
                            "canny_threshold": "medium",
                            "fps": 24,
                            "seed": 1
                        }
                    )
                    run_specs.append(run_spec)
            
            # Verify all were created
            assert len(prompt_specs) == 3
            assert len(run_specs) == 6
            
            # List all prompts and runs
            all_prompts = prompt_manager.list_prompts()
            all_runs = prompt_manager.list_runs()
            
            assert len(all_prompts) >= 3
            assert len(all_runs) >= 6
            
            # Test pattern filtering
            test_prompts = prompt_manager.list_prompts(pattern="test_prompt")
            assert len(test_prompts) >= 3
            
            # Test pattern filtering for runs
            test_runs = prompt_manager.list_runs(pattern="test_prompt")
            assert len(test_runs) >= 6
    
    def test_upsampled_prompt_integration(self):
        """Test creating upsampled prompts and their relationships."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create original prompt
            original_prompt = prompt_manager.create_prompt_spec(
                "building_shot",
                "A tall building in the city",
                input_video_path="inputs/videos/building/color.mp4"
            )
            
            # Create upsampled prompt
            upsampled_prompt = prompt_manager.create_prompt_spec(
                "building_shot_upsampled",
                "A tall building in the city with enhanced details and higher resolution",
                input_video_path="inputs/videos/building_upsampled/color.mp4",
                is_upsampled=True,
                parent_prompt_text="A tall building in the city"
            )
            
            # Create runs for both
            original_run = prompt_manager.create_run_spec(original_prompt)
            upsampled_run = prompt_manager.create_run_spec(upsampled_prompt)
            
            # Verify relationships
            assert original_prompt.is_upsampled is False
            assert upsampled_prompt.is_upsampled is True
            assert upsampled_prompt.parent_prompt_text == "A tall building in the city"
            
            # Verify both can be executed
            assert original_run.prompt_id == original_prompt.id
            assert upsampled_run.prompt_id == upsampled_prompt.id
    
    def test_custom_parameters_integration(self):
        """Test creating prompts and runs with custom parameters."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create prompt with custom control inputs
            prompt_spec = prompt_manager.create_prompt_spec(
                "custom_shot",
                "Custom shot with special requirements",
                input_video_path="custom/video.mp4",
                control_inputs={
                    "depth": "custom/depth.mp4",
                    "seg": "custom/seg.mp4",
                    "edge": "custom/edge.mp4"  # Additional control input
                }
            )
            
            # Create run with custom weights and parameters
            run_spec = prompt_manager.create_run_spec(
                prompt_spec=prompt_spec,
                control_weights={"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},
                parameters={
                    "num_steps": 100,
                    "guidance": 20.0,
                    "sigma_max": 80.0,
                    "blur_strength": "very_high",
                    "canny_threshold": "very_low",
                    "fps": 60,
                    "seed": 12345
                },
                custom_output_path="custom/output/directory"
            )
            
            # Verify custom parameters were applied
            assert prompt_spec.control_inputs["edge"] == "custom/edge.mp4"
            assert run_spec.control_weights["vis"] == 0.5
            assert run_spec.parameters["num_steps"] == 100
            assert run_spec.parameters["guidance"] == 20.0
            assert run_spec.parameters["blur_strength"] == "very_high"
            assert run_spec.parameters["canny_threshold"] == "very_low"
            assert run_spec.parameters["fps"] == 60
            assert run_spec.parameters["seed"] == 12345
            assert run_spec.output_path == "custom/output/directory"
    
    def test_validation_integration(self):
        """Test validation across the entire system."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create valid specifications
            prompt_spec = prompt_manager.create_prompt_spec(
                "validation_test",
                "Test prompt for validation"
            )
            
            run_spec = prompt_manager.create_run_spec(prompt_spec)
            
            # Test validation
            # Find the actual files created and validate them
            prompts_for_validation = prompt_manager.list_prompts()
            runs_for_validation = prompt_manager.list_runs()
            
            # Find our specific files
            prompt_file = None
            run_file = None
            for p in prompts_for_validation:
                info = prompt_manager.get_prompt_info(p)
                if info["id"] == prompt_spec.id:
                    prompt_file = p
                    break
            
            for r in runs_for_validation:
                info = prompt_manager.get_run_info(r)
                if info["id"] == run_spec.id:
                    run_file = r
                    break
            
            assert prompt_file is not None
            assert run_file is not None
            assert prompt_manager.validate_prompt_spec(prompt_file)
            assert prompt_manager.validate_run_spec(run_file)
            
            # Test validation of non-existent files
            assert not prompt_manager.validate_prompt_spec("nonexistent.json")
            assert not prompt_manager.validate_run_spec("nonexistent.json")
    
    def test_directory_structure_integration(self):
        """Test that the directory structure is properly maintained."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create specifications
            prompt_spec = prompt_manager.create_prompt_spec(
                "directory_test",
                "Test prompt for directory structure"
            )
            
            run_spec = prompt_manager.create_run_spec(prompt_spec)
            
            # Check that date-based directories were created
            date_dirs = list(self.prompts_dir.iterdir())
            assert len(date_dirs) > 0
            
            # Check that files exist in date directories
            prompt_files = list(date_dirs[0].glob("*.json"))
            assert len(prompt_files) > 0
            
            # Check that run files exist
            run_date_dirs = list(self.runs_dir.iterdir())
            assert len(run_date_dirs) > 0
            
            run_files = list(run_date_dirs[0].glob("*.json"))
            assert len(run_files) > 0
    
    def test_error_handling_integration(self):
        """Test error handling across the entire system."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Test that empty prompts are allowed (current implementation behavior)
            empty_prompt = prompt_manager.create_prompt_spec("", "")
            assert empty_prompt is not None
            assert empty_prompt.name == ""  # Empty name is allowed
            assert empty_prompt.prompt == ""  # Empty prompt is allowed
            
            # Test invalid run creation
            prompt_spec = prompt_manager.create_prompt_spec(
                "error_test",
                "Test prompt for error handling"
            )
            
            with pytest.raises(ValueError):
                # This should fail due to invalid parameters
                prompt_manager.create_run_spec(
                    prompt_spec=prompt_spec,
                    parameters={"invalid": "parameter"}
                )
    
    def test_id_uniqueness_integration(self):
        """Test that IDs are unique across the entire system."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create multiple prompts with same text but different names
            prompt_specs = []
            for i in range(5):
                prompt_spec = prompt_manager.create_prompt_spec(
                    f"unique_test_{i}",
                    "Same prompt text for all",
                    input_video_path=f"inputs/videos/test_{i}/color.mp4"
                )
                prompt_specs.append(prompt_spec)
            
            # Verify all IDs are unique
            prompt_ids = [ps.id for ps in prompt_specs]
            assert len(prompt_ids) == len(set(prompt_ids))
            
            # Create multiple runs for the same prompt
            run_specs = []
            for i in range(5):
                run_spec = prompt_manager.create_run_spec(
                    prompt_spec=prompt_specs[0],
                    control_weights={"vis": 0.2 + i*0.1, "edge": 0.2, "depth": 0.3, "seg": 0.3}
                )
                run_specs.append(run_spec)
            
            # Verify all run IDs are unique
            run_ids = [rs.id for rs in run_specs]
            assert len(run_ids) == len(set(run_ids))
            
            # Verify prompt IDs are different from run IDs
            all_ids = prompt_ids + run_ids
            assert len(all_ids) == len(set(all_ids))
    
    def test_serialization_integration(self):
        """Test that all objects can be properly serialized and deserialized."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Create specifications
            prompt_spec = prompt_manager.create_prompt_spec(
                "serialization_test",
                "Test prompt for serialization"
            )
            
            run_spec = prompt_manager.create_run_spec(prompt_spec)
            
            # Test PromptSpec serialization
            prompt_dict = prompt_spec.to_dict()
            assert isinstance(prompt_dict, dict)
            assert prompt_dict["id"] == prompt_spec.id
            assert prompt_dict["name"] == prompt_spec.name
            
            # Test RunSpec serialization
            run_dict = run_spec.to_dict()
            assert isinstance(run_dict, dict)
            assert run_dict["id"] == run_spec.id
            assert run_dict["prompt_id"] == run_spec.prompt_id
            assert run_dict["execution_status"] == "pending"
            
            # Test loading from files
            prompt_files = prompt_manager.list_prompts()
            run_files = prompt_manager.list_runs()
            
            if prompt_files:
                loaded_prompt = PromptSpec.load(prompt_files[0])
                assert loaded_prompt.id == prompt_spec.id
            
            if run_files:
                loaded_run = RunSpec.load(run_files[0])
                assert loaded_run.id == run_spec.id
    
    def test_manager_coordination_integration(self):
        """Test that all managers coordinate properly."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Verify all managers are properly initialized
            assert hasattr(prompt_manager, 'prompt_spec_manager')
            assert hasattr(prompt_manager, 'run_spec_manager')
            assert hasattr(prompt_manager, 'validator')
            assert hasattr(prompt_manager, 'dir_manager')
            
            # Verify managers share the same directory manager
            assert prompt_manager.prompt_spec_manager.dir_manager == prompt_manager.dir_manager
            assert prompt_manager.run_spec_manager.dir_manager == prompt_manager.dir_manager
            
            # Test that managers can work independently
            prompt_spec = prompt_manager.prompt_spec_manager.create_prompt_spec(
                "independent_test",
                "Test independent manager usage"
            )
            
            run_spec = prompt_manager.run_spec_manager.create_run_spec(
                prompt_id=prompt_spec.id,
                name=prompt_spec.name
            )
            
            # Verify both were created successfully
            assert prompt_spec.id.startswith("ps_")
            assert run_spec.id.startswith("rs_")
            assert run_spec.prompt_id == prompt_spec.id
    
    def test_edge_cases_integration(self):
        """Test edge cases across the entire system."""
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            
            prompt_manager = PromptManager("dummy_config.toml")
            
            # Test with very long text
            long_prompt = "A" * 1000
            prompt_spec = prompt_manager.create_prompt_spec(
                "long_text_test",
                long_prompt
            )
            
            # Test with special characters
            special_prompt = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            prompt_spec2 = prompt_manager.create_prompt_spec(
                "special_chars_test",
                special_prompt
            )
            
            # Test with unicode
            unicode_prompt = "Test with émojis🚀 and 字符"
            prompt_spec3 = prompt_manager.create_prompt_spec(
                "unicode_test",
                unicode_prompt
            )
            
            # Verify all were created successfully
            assert prompt_spec.id.startswith("ps_")
            assert prompt_spec2.id.startswith("ps_")
            assert prompt_spec3.id.startswith("ps_")
            
            # Test with edge case parameters
            run_spec = prompt_manager.create_run_spec(
                prompt_spec=prompt_spec,
                control_weights={"vis": 0.0, "edge": 1.0, "depth": 0.0, "seg": 0.0},
                parameters={
                    "num_steps": 1,
                    "guidance": 1.0,
                    "sigma_max": 0.0,
                    "blur_strength": "very_low",
                    "canny_threshold": "very_high",
                    "fps": 1,
                    "seed": 1
                }
            )
            
            assert run_spec.id.startswith("rs_")
            assert run_spec.control_weights["edge"] == 1.0
            assert run_spec.parameters["num_steps"] == 1
