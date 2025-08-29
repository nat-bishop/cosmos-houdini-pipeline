#!/usr/bin/env python3
"""
Tests for the prompt management system.
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from cosmos_workflow.prompts import PromptManager, PromptSchema


class TestPromptManager:
    """Test the PromptManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create mock config
        self.mock_config = Mock()
        self.mock_config.prompts_dir = self.temp_path / "prompts"
        self.mock_config.outputs_dir = self.temp_path / "outputs"
        self.mock_config.videos_dir = self.temp_path / "videos"
        
        # Mock the ConfigManager
        with patch('cosmos_workflow.prompts.prompt_manager.ConfigManager') as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            self.prompt_manager = PromptManager("dummy_config.toml")
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()
    
    def test_create_prompt(self):
        """Test creating a new prompt."""
        prompt_file = self.prompt_manager.create_prompt(
            "test_shot", 
            "A beautiful sunset over the ocean"
        )
        
        assert prompt_file.exists()
        assert prompt_file.name.startswith("test_shot_")
        assert prompt_file.name.endswith(".json")
        
        # Check content
        with open(prompt_file, 'r') as f:
            data = json.load(f)
        
        assert data["prompt"] == "A beautiful sunset over the ocean"
        assert data["input_video_path"] == "inputs/videos/test_shot/color.mp4"
        assert data["vis"]["control_weight"] == 0.25
        assert data["depth"]["input_control"] == "inputs/videos/test_shot/depth.mp4"
    
    def test_create_prompt_with_custom_weights(self):
        """Test creating a prompt with custom control weights."""
        custom_weights = {
            "vis": 0.5,
            "edge": 0.3,
            "depth": 0.1,
            "seg": 0.1
        }
        
        prompt_file = self.prompt_manager.create_prompt(
            "test_shot", 
            "Test prompt",
            custom_weights
        )
        
        with open(prompt_file, 'r') as f:
            data = json.load(f)
        
        assert data["vis"]["control_weight"] == 0.5
        assert data["edge"]["control_weight"] == 0.3
        assert data["depth"]["control_weight"] == 0.1
        assert data["seg"]["control_weight"] == 0.1
    
    def test_create_prompt_with_custom_video_path(self):
        """Test creating a prompt with custom video path."""
        prompt_file = self.prompt_manager.create_prompt(
            "test_shot", 
            "Test prompt",
            custom_video_path="custom/path/video.mp4"
        )
        
        with open(prompt_file, 'r') as f:
            data = json.load(f)
        
        assert data["input_video_path"] == "custom/path/video.mp4"
    
    def test_duplicate_prompt(self):
        """Test duplicating an existing prompt."""
        # Create original prompt
        original_prompt = self.prompt_manager.create_prompt(
            "test_shot", 
            "Original prompt"
        )
        
        # Duplicate it
        duplicated_prompt = self.prompt_manager.duplicate_prompt(original_prompt)
        
        assert duplicated_prompt.exists()
        # The files should be different (even if timestamps are the same, they're different files)
        assert duplicated_prompt != original_prompt
        assert duplicated_prompt.name.startswith("test_shot_")
        
        # Check content is the same
        with open(original_prompt, 'r') as f1, open(duplicated_prompt, 'r') as f2:
            assert f1.read() == f2.read()
    
    def test_duplicate_prompt_file_not_found(self):
        """Test duplicating a non-existent prompt."""
        with pytest.raises(FileNotFoundError):
            self.prompt_manager.duplicate_prompt("nonexistent.json")
    
    def test_validate_prompt_valid(self):
        """Test validating a valid prompt."""
        prompt_file = self.prompt_manager.create_prompt(
            "test_shot", 
            "Test prompt"
        )
        
        assert self.prompt_manager.validate_prompt(prompt_file) is True
    
    def test_validate_prompt_invalid_json(self):
        """Test validating an invalid JSON file."""
        # Create an invalid JSON file
        invalid_file = self.temp_path / "prompts" / "invalid.json"
        invalid_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json")
        
        assert self.prompt_manager.validate_prompt(invalid_file) is False
    
    def test_validate_prompt_missing_fields(self):
        """Test validating a prompt with missing required fields."""
        # Create a prompt with missing fields
        incomplete_prompt = {
            "prompt": "Test prompt",
            "input_video_path": "test.mp4"
            # Missing vis, edge, depth, seg
        }
        
        incomplete_file = self.temp_path / "prompts" / "incomplete.json"
        incomplete_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(incomplete_file, 'w') as f:
            json.dump(incomplete_prompt, f)
        
        assert self.prompt_manager.validate_prompt(incomplete_file) is False
    
    def test_list_prompts(self):
        """Test listing available prompts."""
        # Create some prompts
        self.prompt_manager.create_prompt("shot1", "Prompt 1")
        self.prompt_manager.create_prompt("shot2", "Prompt 2")
        self.prompt_manager.create_prompt("shot3", "Prompt 3")
        
        # List all prompts
        all_prompts = self.prompt_manager.list_prompts()
        assert len(all_prompts) == 3
        
        # List with pattern
        shot1_prompts = self.prompt_manager.list_prompts("shot1")
        assert len(shot1_prompts) == 1
        assert "shot1" in shot1_prompts[0].name
    
    def test_get_prompt_info(self):
        """Test getting information about a prompt."""
        prompt_file = self.prompt_manager.create_prompt(
            "test_shot", 
            "A beautiful sunset over the ocean"
        )
        
        info = self.prompt_manager.get_prompt_info(prompt_file)
        
        assert info["base_name"] == "test_shot"
        assert info["prompt_text"] == "A beautiful sunset over the ocean"
        assert info["control_weights"]["vis"] == 0.25
        assert "timestamp" in info
        assert info["file_path"] == str(prompt_file)
    
    def test_get_prompt_info_file_not_found(self):
        """Test getting info for non-existent prompt."""
        with pytest.raises(FileNotFoundError):
            self.prompt_manager.get_prompt_info("nonexistent.json")


if __name__ == "__main__":
    pytest.main([__file__])
