#!/usr/bin/env python3
"""
Comprehensive test suite for Cosmos sequence validation and conversion.

Tests all corner cases for the strict Cosmos workflow validation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import numpy as np
import cv2
import json
from unittest.mock import Mock, patch, MagicMock

from cosmos_workflow.local_ai.cosmos_sequence import (
    CosmosSequenceValidator,
    CosmosVideoConverter,
    CosmosSequenceInfo,
    CosmosMetadata
)


class TestCosmosSequenceValidator:
    """Test the CosmosSequenceValidator with all corner cases."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return CosmosSequenceValidator()
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    def create_dummy_png(self, path: Path, width: int = 100, height: int = 100):
        """Create a dummy PNG file."""
        img = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.imwrite(str(path), img)
    
    def test_minimal_valid_color_only(self, validator, temp_dir):
        """Test validation with only color modality (minimal valid case)."""
        # Create color.0001.png through color.0010.png
        for i in range(1, 11):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True
        assert result.frame_count == 10
        assert list(result.modalities.keys()) == ["color"]
        assert len(result.issues) == 0
        assert result.frame_numbers == list(range(1, 11))
    
    def test_full_five_modalities(self, validator, temp_dir):
        """Test validation with all five modalities."""
        modalities = ["color", "depth", "segmentation", "vis", "edge"]
        
        for modality in modalities:
            for i in range(1, 6):
                self.create_dummy_png(temp_dir / f"{modality}.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True
        assert result.frame_count == 5
        assert set(result.modalities.keys()) == set(modalities)
        assert len(result.issues) == 0
    
    def test_partial_modalities(self, validator, temp_dir):
        """Test validation with color plus some control modalities."""
        # Color and depth only
        for i in range(1, 11):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
            self.create_dummy_png(temp_dir / f"depth.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True
        assert set(result.modalities.keys()) == {"color", "depth"}
        assert result.frame_count == 10
    
    def test_missing_color_fails(self, validator, temp_dir):
        """Test that missing color modality causes validation to fail."""
        # Only depth and segmentation, no color
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"depth.{i:04d}.png")
            self.create_dummy_png(temp_dir / f"segmentation.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert "Required modality 'color' not found" in result.issues
    
    def test_wrong_naming_pattern_underscore(self, validator, temp_dir):
        """Test that color_0001.png pattern is rejected."""
        # Wrong pattern: underscore instead of dot
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"color_{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("Unexpected files found" in issue for issue in result.issues)
        assert "Required modality 'color' not found" in result.issues
    
    def test_wrong_naming_pattern_three_digits(self, validator, temp_dir):
        """Test that color.001.png pattern is rejected."""
        # Wrong pattern: 3 digits instead of 4
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"color.{i:03d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("Unexpected files found" in issue for issue in result.issues)
    
    def test_wrong_naming_pattern_five_digits(self, validator, temp_dir):
        """Test that color.00001.png pattern is rejected."""
        # Wrong pattern: 5 digits instead of 4
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"color.{i:05d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("Unexpected files found" in issue for issue in result.issues)
    
    def test_unexpected_files_fail(self, validator, temp_dir):
        """Test that unexpected files cause validation to fail."""
        # Valid color files
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        # Unexpected files
        self.create_dummy_png(temp_dir / "thumbnail.png")
        (temp_dir / ".DS_Store").touch()
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("Unexpected files found" in issue for issue in result.issues)
    
    def test_wrong_extension(self, validator, temp_dir):
        """Test that .jpg files are rejected."""
        # Create JPG instead of PNG
        for i in range(1, 6):
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.imwrite(str(temp_dir / f"color.{i:04d}.jpg"), img)
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("No PNG files found" in issue for issue in result.issues) or "Required modality 'color' not found" in result.issues
    
    def test_frame_number_mismatch_extra_frames(self, validator, temp_dir):
        """Test when control modality has extra frames."""
        # Color: frames 1-10
        for i in range(1, 11):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        # Depth: frames 1-12 (extra frames 11-12)
        for i in range(1, 13):
            self.create_dummy_png(temp_dir / f"depth.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True  # Valid but with warnings
        assert any("depth has extra frames" in warning for warning in result.warnings)
    
    def test_frame_number_mismatch_missing_frames(self, validator, temp_dir):
        """Test when control modality is missing some frames."""
        # Color: frames 1-10
        for i in range(1, 11):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        # Depth: frames 1-8 (missing 9-10)
        for i in range(1, 9):
            self.create_dummy_png(temp_dir / f"depth.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True  # Valid but with warnings
        assert any("depth missing frames" in warning for warning in result.warnings)
    
    def test_gaps_in_color_sequence(self, validator, temp_dir):
        """Test that gaps in color sequence are detected."""
        # Create frames 1-5 and 8-10 (missing 6-7)
        for i in [1, 2, 3, 4, 5, 8, 9, 10]:
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("Missing frames in color sequence" in issue for issue in result.issues)
        assert any("[6, 7]" in issue for issue in result.issues)
    
    def test_invalid_modality_name(self, validator, temp_dir):
        """Test that invalid modality names are rejected."""
        # Valid color
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        # Invalid modality name
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"normal.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("Unexpected files found" in issue for issue in result.issues)
    
    def test_case_sensitive_names(self, validator, temp_dir):
        """Test that capitalized names are rejected (Color vs color)."""
        # Wrong capitalization
        for i in range(1, 6):
            self.create_dummy_png(temp_dir / f"Color.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert "Required modality 'color' not found" in result.issues
    
    def test_mixed_digit_patterns(self, validator, temp_dir):
        """Test that mixed digit patterns are rejected."""
        # Some 3-digit, some 4-digit
        self.create_dummy_png(temp_dir / "color.001.png")
        self.create_dummy_png(temp_dir / "color.0002.png")
        self.create_dummy_png(temp_dir / "color.003.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is False
    
    def test_empty_directory(self, validator, temp_dir):
        """Test validation of empty directory."""
        result = validator.validate(temp_dir)
        
        assert result.valid is False
        assert any("No PNG files found" in issue for issue in result.issues)
    
    def test_nonexistent_directory(self, validator):
        """Test validation of non-existent directory."""
        result = validator.validate(Path("/nonexistent/directory"))
        
        assert result.valid is False
        assert any("Directory does not exist" in issue for issue in result.issues)
    
    def test_single_frame_valid(self, validator, temp_dir):
        """Test that a single frame is valid."""
        self.create_dummy_png(temp_dir / "color.0001.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True
        assert result.frame_count == 1
    
    def test_large_frame_numbers(self, validator, temp_dir):
        """Test validation with large frame numbers."""
        # Frames 1000-1010
        for i in range(1000, 1011):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True
        assert result.frame_count == 11
        assert result.frame_numbers[0] == 1000
        assert result.frame_numbers[-1] == 1010
    
    def test_non_sequential_start(self, validator, temp_dir):
        """Test that sequences don't have to start at frame 1."""
        # Frames 100-110
        for i in range(100, 111):
            self.create_dummy_png(temp_dir / f"color.{i:04d}.png")
        
        result = validator.validate(temp_dir)
        
        assert result.valid is True
        assert result.frame_count == 11
        assert result.frame_numbers[0] == 100


class TestCosmosVideoConverter:
    """Test the CosmosVideoConverter."""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return CosmosVideoConverter(fps=24)
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def valid_sequence_info(self, temp_dir):
        """Create a valid sequence info with mock data."""
        # Create dummy PNG files
        color_paths = []
        depth_paths = []
        for i in range(1, 6):
            color_path = temp_dir / f"color.{i:04d}.png"
            depth_path = temp_dir / f"depth.{i:04d}.png"
            
            # Create dummy images
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.imwrite(str(color_path), img)
            cv2.imwrite(str(depth_path), img)
            
            color_paths.append(color_path)
            depth_paths.append(depth_path)
        
        return CosmosSequenceInfo(
            valid=True,
            modalities={"color": color_paths, "depth": depth_paths},
            frame_count=5,
            frame_numbers=[1, 2, 3, 4, 5],
            issues=[],
            warnings=[]
        )
    
    def test_convert_valid_sequence(self, converter, valid_sequence_info, temp_dir):
        """Test converting a valid sequence to videos."""
        output_dir = temp_dir / "output"
        result = converter.convert_sequence(
            sequence_info=valid_sequence_info,
            output_dir=output_dir,
            name="test"
        )
        
        assert result["success"] is True
        assert "color" in result["videos"]
        assert "depth" in result["videos"]
        
        # Check that video files exist
        output_path = Path(result["output_dir"])
        assert (output_path / "color.mp4").exists()
        assert (output_path / "depth.mp4").exists()
    
    def test_convert_invalid_sequence(self, converter, temp_dir):
        """Test that invalid sequence returns error."""
        invalid_info = CosmosSequenceInfo(
            valid=False,
            modalities={},
            frame_count=0,
            frame_numbers=[],
            issues=["Test issue"]
        )
        
        result = converter.convert_sequence(
            sequence_info=invalid_info,
            output_dir=temp_dir,
            name="test"
        )
        
        assert result["success"] is False
        assert result["error"] == "Invalid sequence"
    
    def test_metadata_generation(self, converter, valid_sequence_info, temp_dir):
        """Test metadata generation with control inputs."""
        output_dir = temp_dir / "output" / "test_20250830_120000"
        output_dir.mkdir(parents=True)
        
        # Create dummy video files
        (output_dir / "color.mp4").touch()
        (output_dir / "depth.mp4").touch()
        
        metadata = converter.generate_metadata(
            sequence_info=valid_sequence_info,
            output_dir=output_dir,
            name="test",
            description="Test description",
            use_ai=False
        )
        
        assert metadata.name == "test"
        assert metadata.description == "Test description"
        assert metadata.frame_count == 5
        assert metadata.fps == 24.0
        assert "color" in metadata.modalities
        assert "depth" in metadata.modalities
        assert metadata.video_path == str(output_dir / "color.mp4")
        assert "depth" in metadata.control_inputs
        assert metadata.control_inputs["depth"] == str(output_dir / "depth.mp4")
        
        # Check that metadata JSON was saved
        metadata_file = output_dir / "metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file) as f:
            saved_metadata = json.load(f)
        
        assert saved_metadata["name"] == "test"
        assert saved_metadata["video_path"] == str(output_dir / "color.mp4")
        assert "depth" in saved_metadata["control_inputs"]
    
    def test_metadata_without_control_inputs(self, converter, temp_dir):
        """Test metadata generation with only color modality."""
        output_dir = temp_dir / "output" / "test_20250830_120000"
        output_dir.mkdir(parents=True)
        (output_dir / "color.mp4").touch()
        
        # Create sequence info with only color
        color_path = temp_dir / "color.0001.png"
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(color_path), img)
        
        sequence_info = CosmosSequenceInfo(
            valid=True,
            modalities={"color": [color_path]},
            frame_count=1,
            frame_numbers=[1],
            issues=[],
            warnings=[]
        )
        
        metadata = converter.generate_metadata(
            sequence_info=sequence_info,
            output_dir=output_dir,
            name="test",
            description=None,
            use_ai=False
        )
        
        assert metadata.control_inputs == {}
        assert metadata.video_path == str(output_dir / "color.mp4")
        assert len(metadata.modalities) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])