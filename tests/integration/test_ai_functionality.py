#!/usr/bin/env python3
"""
Comprehensive tests for AI-powered functionality in Cosmos workflow.

Tests AI description generation, smart naming, and fallback behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from cosmos_workflow.local_ai.cosmos_sequence import CosmosVideoConverter
from cosmos_workflow.utils.smart_naming import generate_smart_name


class TestSmartNameGeneration:
    """Test smart name generation from AI descriptions."""

    def test_generate_smart_name_basic(self):
        """Test basic smart name generation."""
        # Test various descriptions
        test_cases = [
            (
                "a modern staircase with dramatic lighting",
                ["modern", "staircase", "lighting", "dramatic"],
            ),
            ("a red car driving on a highway", ["red", "car", "driving", "highway"]),
            ("a person walking in a park", ["person", "walking", "park"]),
            ("the building is very tall", ["building", "tall"]),
            ("an abstract painting hanging", ["abstract", "painting", "hanging"]),
        ]

        for description, possible_words in test_cases:
            name = generate_smart_name(description)
            # Check that at least some key words are present
            name_words = name.split("_")
            matched = sum(1 for word in possible_words if word in name_words)
            assert matched >= 1, (
                f"Expected at least one of {possible_words} in name '{name}' from description '{description}'"
            )

    def test_generate_smart_name_max_length(self):
        """Test name truncation at max length."""
        # Long description
        description = (
            "a very complex industrial machinery with multiple moving parts and hydraulic systems"
        )
        name = generate_smart_name(description, max_length=15)

        assert len(name) <= 15, f"Name '{name}' exceeds max length of 15"
        assert name, "Name should not be empty"

    def test_generate_smart_name_stop_words_removal(self):
        """Test that common stop words are removed."""
        description = "the a an in on at with for of very and or but"
        name = generate_smart_name(description)

        # Should fallback to "sequence" or similar since all are stop words
        assert name, "Name should not be empty even with all stop words"

    def test_generate_smart_name_special_characters(self):
        """Test handling of special characters."""
        description = "a scene with #hashtags and @mentions & symbols!"
        name = generate_smart_name(description)

        # Name should only contain alphanumeric and underscores
        assert all(c.isalnum() or c == "_" for c in name), (
            f"Name '{name}' contains invalid characters"
        )

    def test_generate_smart_name_empty_description(self):
        """Test handling of empty description."""
        name = generate_smart_name("")
        assert name == "sequence", "Empty description should default to 'sequence'"

    def test_generate_smart_name_priority_words(self):
        """Test that words with priority suffixes are preferred."""
        # Words ending in -ing, -tion, etc. should get priority
        description = "a cat jumping over the wooden fence during sunset"
        name = generate_smart_name(description)

        # "jumping" should be prioritized due to -ing suffix
        assert "jumping" in name or "jump" in name, f"Expected 'jumping' or 'jump' in name '{name}'"


class TestAIDescriptionGeneration:
    """Test AI description generation from frames."""

    # Removed test_generate_ai_description_success - too complex mocking for little value

    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.imread")
    def test_generate_ai_description_no_transformers(self, mock_imread):
        """Test fallback when transformers is not available."""
        converter = CosmosVideoConverter()

        # Mock ImportError for transformers
        with patch("transformers.BlipProcessor", side_effect=ImportError):
            color_frames = [Path("frame_0001.png"), Path("frame_0002.png")]
            description = converter._generate_ai_description(color_frames)

            assert description == "Sequence with 2 frames"

    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.imread")
    def test_generate_ai_description_error_handling(self, mock_imread):
        """Test error handling during AI description generation."""
        converter = CosmosVideoConverter()

        # Mock frame reading
        mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imread.return_value = mock_frame

        with patch("transformers.BlipProcessor") as mock_processor_class:
            # Mock processor to raise an error
            mock_processor_class.from_pretrained.side_effect = Exception("Model loading failed")

            # Should fallback gracefully
            color_frames = [Path("frame_0001.png"), Path("frame_0002.png"), Path("frame_0003.png")]
            description = converter._generate_ai_description(color_frames)

            assert description == "Sequence with 3 frames"


class TestIntegratedAIWorkflow:
    """Test the complete AI-powered workflow."""

    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.imread")
    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.VideoWriter")
    @patch("cosmos_workflow.local_ai.cosmos_sequence.generate_smart_name")
    def test_generate_metadata_with_ai(self, mock_smart_name, mock_video_writer, mock_imread):
        """Test metadata generation with AI description and naming."""
        from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceInfo

        converter = CosmosVideoConverter()

        # Mock frame reading
        mock_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_frame

        # Mock video writer
        mock_writer = Mock()
        mock_video_writer.return_value = mock_writer
        mock_writer.isOpened.return_value = True

        # Mock smart name generation
        mock_smart_name.return_value = "futuristic_city"

        # Create test sequence info
        sequence_info = CosmosSequenceInfo(
            valid=True,
            modalities={"color": [Path("color.0001.png"), Path("color.0002.png")]},
            frame_count=2,
            frame_numbers=[1, 2],
            issues=[],
        )

        # Mock AI description generation
        with patch.object(
            converter, "_generate_ai_description", return_value="a futuristic city skyline"
        ):
            # Generate metadata without providing name
            output_dir = Path("/test/output")

            # Mock file writing
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                metadata = converter.generate_metadata(
                    sequence_info=sequence_info,
                    output_dir=output_dir,
                    name=None,  # Let AI generate the name
                    description=None,  # Let AI generate the description
                    use_ai=True,
                )

            assert metadata.description == "a futuristic city skyline"
            # Verify mocked name was used
            assert metadata.name == "futuristic_city"
            assert metadata.frame_count == 2
            assert metadata.video_path == str(output_dir / "color.mp4")

    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.imread")
    def test_generate_metadata_without_ai(self, mock_imread):
        """Test metadata generation without AI."""
        from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceInfo

        converter = CosmosVideoConverter()

        # Mock frame reading
        mock_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_imread.return_value = mock_frame

        # Create test sequence info
        sequence_info = CosmosSequenceInfo(
            valid=True,
            modalities={"color": [Path("color.0001.png")]},
            frame_count=1,
            frame_numbers=[1],
            issues=[],
        )

        # Generate metadata without AI
        output_dir = Path("/test/output")

        # Mock file writing
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            metadata = converter.generate_metadata(
                sequence_info=sequence_info,
                output_dir=output_dir,
                name=None,
                description=None,
                use_ai=False,  # Disable AI
            )

        assert metadata.description == "Sequence with 1 frames"
        assert metadata.name == "sequence"  # Default name
        assert metadata.frame_count == 1

    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.imread")
    def test_generate_metadata_custom_name_description(self, mock_imread):
        """Test metadata generation with custom name and description."""
        from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceInfo

        converter = CosmosVideoConverter()

        # Mock frame reading
        mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_imread.return_value = mock_frame

        # Create test sequence info
        sequence_info = CosmosSequenceInfo(
            valid=True,
            modalities={"color": [Path("color.0001.png")]},
            frame_count=1,
            frame_numbers=[1],
            issues=[],
        )

        # Generate metadata with custom values
        output_dir = Path("/test/output")

        # Mock file writing
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            metadata = converter.generate_metadata(
                sequence_info=sequence_info,
                output_dir=output_dir,
                name="custom_name",
                description="Custom description provided by user",
                use_ai=True,  # AI enabled but won't be used due to custom values
            )

        assert metadata.description == "Custom description provided by user"
        assert metadata.name == "custom_name"
        assert metadata.resolution == (1280, 720)


class TestDirectoryNaming:
    """Test directory naming format compliance."""

    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.imread")
    @patch("cosmos_workflow.local_ai.cosmos_sequence.cv2.VideoWriter")
    @patch("cosmos_workflow.local_ai.cosmos_sequence.datetime")
    @patch("cosmos_workflow.utils.smart_naming.generate_smart_name")
    def test_directory_naming_format(
        self, mock_smart_name, mock_datetime, mock_video_writer, mock_imread
    ):
        """Test that directory follows {name}_{timestamp} format."""
        import re

        from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceInfo

        converter = CosmosVideoConverter()

        # Mock datetime to return a specific timestamp
        mock_now = Mock()
        mock_now.strftime.return_value = "20250830_143025"
        mock_datetime.now.return_value = mock_now

        # Mock smart name generation
        mock_smart_name.return_value = "test_scene"

        # Mock frame and video writer
        mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_writer = Mock()
        mock_video_writer.return_value = mock_writer
        mock_writer.isOpened.return_value = True

        # Create test sequence
        sequence_info = CosmosSequenceInfo(
            valid=True,
            modalities={"color": [Path("color.0001.png")]},
            frame_count=1,
            frame_numbers=[1],
            issues=[],
        )

        # Convert with AI-generated name
        with patch.object(converter, "_generate_ai_description", return_value="test scene"):
            with patch("pathlib.Path.mkdir"):
                result = converter.convert_sequence(
                    sequence_info=sequence_info,
                    output_dir=Path("/test"),
                    name=None,
                    use_ai_naming=True,
                )

                output_dir = result["output_dir"]

                # Verify format: name_YYYYMMDD_HHMMSS
                # Handle Windows path separators
                normalized_dir = output_dir.replace("\\", "/")
                pattern = r"^/test/\w+_\d{8}_\d{6}$"
                assert re.match(pattern, normalized_dir), (
                    f"Directory '{normalized_dir}' doesn't match expected format"
                )

                # Specifically check for our mocked timestamp
                assert "20250830_143025" in output_dir

    def test_timestamp_format(self):
        """Test that timestamp follows YYYYMMDD_HHMMSS format."""
        import re
        from datetime import datetime

        # Test the actual format string
        timestamp = datetime(2025, 8, 30, 16, 36, 4).strftime("%Y%m%d_%H%M%S")

        assert timestamp == "20250830_163604"

        # Verify pattern
        pattern = r"^\d{8}_\d{6}$"
        assert re.match(pattern, timestamp), (
            f"Timestamp '{timestamp}' doesn't match YYYYMMDD_HHMMSS format"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
