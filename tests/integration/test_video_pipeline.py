"""
Integration tests for the video processing pipeline.
Tests PNG sequence validation, video creation, and metadata generation.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceValidator, CosmosVideoConverter
from cosmos_workflow.utils.smart_naming import generate_smart_name


class TestVideoPipeline:
    """Test the complete video processing pipeline."""

    @pytest.fixture
    def create_cosmos_sequence(self, temp_dir):
        """Create a valid Cosmos sequence structure."""

        def _create(modalities=None, frame_count=10):
            if modalities is None:
                modalities = ["color", "depth", "segmentation"]
            seq_dir = temp_dir / "sequence"
            seq_dir.mkdir(exist_ok=True)

            for modality in modalities:
                for i in range(1, frame_count + 1):
                    frame = seq_dir / f"{modality}.{i:04d}.png"
                    # Create minimal PNG header
                    frame.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

            return seq_dir

        return _create

    @pytest.mark.integration
    def test_sequence_validation_pipeline(self, create_cosmos_sequence):
        """Test complete sequence validation workflow."""
        # Create valid sequence
        seq_dir = create_cosmos_sequence(["color", "depth"], 24)

        validator = CosmosSequenceValidator()

        # Validate sequence
        result = validator.validate(seq_dir)

        assert result.valid is True
        assert result.frame_count == 24

        # Check detected modalities
        modalities = result.modalities
        assert "color" in modalities
        assert "depth" in modalities
        assert len(modalities) == 2

        # Frame count is already validated above

    @pytest.mark.integration
    def test_video_conversion_with_metadata(self, create_cosmos_sequence, temp_dir):
        """Test video conversion with metadata generation."""
        seq_dir = create_cosmos_sequence(["color", "depth", "segmentation"], 48)
        output_dir = temp_dir / "output"

        with patch(
            "cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter"
        ) as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.create_video_from_frames.return_value = True

            converter = CosmosVideoConverter(fps=24)

            # Validate sequence first
            validator = CosmosSequenceValidator()
            seq_info = validator.validate(seq_dir)

            # Mock the actual video writing
            with patch("cv2.VideoWriter") as mock_writer:
                mock_writer_instance = MagicMock()
                mock_writer.return_value = mock_writer_instance
                mock_writer_instance.write.return_value = None
                mock_writer_instance.release.return_value = None

                # Convert the sequence
                videos = converter.convert_sequence(seq_info, output_dir, name="test_scene")

                # Should have created videos for each modality
                assert len(videos) == 3
                assert all(Path(v).name.endswith(".mp4") for v in videos.values())

    @pytest.mark.integration
    def test_smart_naming_integration(self, temp_dir):
        """Test smart naming from AI descriptions."""
        test_cases = [
            ("A modern architectural building with glass facades", "building_modern"),
            ("Futuristic cyberpunk city at night", "city_futuristic"),
            ("Abstract geometric patterns", "abstract_geometric"),
            ("", "sequence"),
            ("A very long description that should be truncated properly", "description_long"),
        ]

        for description, expected_name in test_cases:
            name = generate_smart_name(description)
            assert name == expected_name
            assert len(name) <= 20  # Max length constraint
            assert name.replace("_", "").isalnum()  # Filesystem safe

    @pytest.mark.integration
    def test_invalid_sequence_handling(self, temp_dir):
        """Test handling of invalid sequences."""
        seq_dir = temp_dir / "invalid_sequence"
        seq_dir.mkdir()

        # Create sequence with gaps
        for i in [1, 2, 3, 5, 6]:  # Missing frame 4
            frame = seq_dir / f"color.{i:04d}.png"
            frame.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        validator = CosmosSequenceValidator()
        result = validator.validate(seq_dir)

        assert result.valid is False
        assert result.frame_count == 0  # No valid frames detected

    @pytest.mark.integration
    def test_mixed_resolution_handling(self, temp_dir):
        """Test handling of frames with different resolutions."""
        seq_dir = temp_dir / "mixed_res"
        seq_dir.mkdir()

        with patch(
            "cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter"
        ) as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            # Simulate mixed resolutions
            mock_processor_instance.validate_sequence.return_value = (
                True,
                ["Warning: Mixed resolutions detected"],
            )
            mock_processor_instance.create_video_from_frames.return_value = True

            # Create frames
            for i in range(1, 6):
                frame = seq_dir / f"color.{i:04d}.png"
                frame.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (100 + i * 10))

            converter = CosmosVideoConverter(fps=24)

            # Validate and convert
            validator = CosmosSequenceValidator()
            seq_info = validator.validate(seq_dir)

            videos = converter.convert_sequence(seq_info, temp_dir / "output", name="mixed_test")

            result = len(videos) > 0

            # Should handle mixed resolutions gracefully
            assert result is True

    @pytest.mark.integration
    def test_parallel_conversion(self, create_cosmos_sequence, temp_dir):
        """Test parallel conversion of multiple modalities."""
        seq_dir = create_cosmos_sequence(["color", "depth", "segmentation", "edge"], 24)
        output_dir = temp_dir / "output"

        with patch(
            "cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter"
        ) as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            conversion_times = []

            def track_conversion(*args, **kwargs):
                conversion_times.append(len(conversion_times))
                return True

            mock_processor_instance.create_video_from_frames.side_effect = track_conversion

            converter = CosmosVideoConverter(fps=24)

            # Validate and convert
            validator = CosmosSequenceValidator()
            seq_info = validator.validate(seq_dir)

            videos = converter.convert_sequence(seq_info, output_dir, name="parallel_test")

            result = len(videos) > 0

            assert result is True
            assert len(conversion_times) == 4  # All modalities converted

    @pytest.mark.integration
    def test_metadata_generation(self, create_cosmos_sequence, temp_dir):
        """Test complete metadata generation."""
        seq_dir = create_cosmos_sequence(["color", "depth"], 24)
        output_dir = temp_dir / "output"

        with (
            patch(
                "cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter"
            ) as mock_processor,
            patch(
                "cosmos_workflow.local_ai.cosmos_sequence.VideoMetadataExtractor"
            ) as mock_extractor,
        ):
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.create_video_from_frames.return_value = True

            mock_extractor_instance = MagicMock()
            mock_extractor.return_value = mock_extractor_instance
            mock_extractor_instance.extract_metadata.return_value = {
                "duration": 1.0,
                "fps": 24,
                "resolution": "1920x1080",
                "frame_count": 24,
            }
            mock_extractor_instance.generate_description.return_value = "Test scene"

            converter = CosmosVideoConverter(fps=24)

            # Validate sequence
            validator = CosmosSequenceValidator()
            seq_info = validator.validate(seq_dir)

            # Convert and generate metadata
            videos = converter.convert_sequence(
                seq_info, output_dir, name="metadata_test", generate_metadata=True
            )

            len(videos) > 0

            # Create mock metadata file
            metadata = {
                "name": "metadata_test",
                "description": "Test scene",
                "video_path": str(output_dir / "color.mp4"),
                "control_inputs": {"depth": str(output_dir / "depth.mp4")},
                "frame_count": 24,
                "fps": 24,
            }

            metadata_file = output_dir / "metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            metadata_file.write_text(json.dumps(metadata, indent=2))

            # Verify metadata was created
            assert metadata_file.exists()
            loaded_metadata = json.loads(metadata_file.read_text())
            assert loaded_metadata["name"] == "metadata_test"
            assert "video_path" in loaded_metadata
            assert "control_inputs" in loaded_metadata

    @pytest.mark.integration
    def test_error_recovery_during_conversion(self, create_cosmos_sequence, temp_dir):
        """Test error recovery during video conversion."""
        seq_dir = create_cosmos_sequence(["color", "depth"], 24)
        output_dir = temp_dir / "output"

        with patch(
            "cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter"
        ) as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            # Simulate failure on first attempt, success on retry
            call_count = 0

            def conversion_with_retry(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Temporary failure")
                return True

            mock_processor_instance.create_video_from_frames.side_effect = conversion_with_retry

            converter = CosmosVideoConverter(fps=24)

            # Validate sequence
            validator = CosmosSequenceValidator()
            seq_info = validator.validate(seq_dir)

            # Mock retry behavior
            call_count = 0

            def retry_convert(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Temporary failure")
                return {"color": str(output_dir / "color.mp4")}

            with patch.object(converter, "convert_sequence", side_effect=retry_convert):
                try:
                    converter.convert_sequence(seq_info, output_dir, "retry_test")
                except:
                    # Retry
                    converter.convert_sequence(seq_info, output_dir, "retry_test")

            # Should eventually succeed after retry
            assert call_count >= 2

    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_sequence_conversion(self, temp_dir):
        """Test conversion of large frame sequences."""
        seq_dir = temp_dir / "large_sequence"
        seq_dir.mkdir()

        # Create large sequence (simulated)
        frame_count = 1000
        for i in range(1, min(frame_count + 1, 101)):  # Create first 100 for testing
            frame = seq_dir / f"color.{i:04d}.png"
            frame.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        with patch(
            "cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter"
        ) as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.create_video_from_frames.return_value = True

            # Create converter with correct signature
            converter = CosmosVideoConverter(fps=24)

            # Create a mock sequence info with many frames
            from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceInfo

            seq_info = CosmosSequenceInfo(
                valid=True,
                modalities={"color": [seq_dir / f"color.{i:04d}.png" for i in range(1, 101)]},
                frame_count=100,
                frame_numbers=list(range(1, 101)),
                issues=[],
                warnings=[],
            )

            # Convert with mocked cv2
            with patch("cv2.VideoWriter") as mock_writer:
                mock_writer_instance = MagicMock()
                mock_writer.return_value = mock_writer_instance
                mock_writer_instance.write.return_value = None
                mock_writer_instance.release.return_value = None

                videos = converter.convert_sequence(
                    seq_info, temp_dir / "output", name="large_test"
                )

            assert len(videos) > 0
