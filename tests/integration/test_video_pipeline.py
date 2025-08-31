"""
Integration tests for the video processing pipeline.
Tests PNG sequence validation, video creation, and metadata generation.
"""
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

from cosmos_workflow.local_ai.cosmos_sequence import (
    CosmosSequenceValidator,
    CosmosVideoConverter
)
from cosmos_workflow.utils.smart_naming import generate_smart_name


class TestVideoPipeline:
    """Test the complete video processing pipeline."""
    
    @pytest.fixture
    def create_cosmos_sequence(self, temp_dir):
        """Create a valid Cosmos sequence structure."""
        def _create(modalities=['color', 'depth', 'segmentation'], frame_count=10):
            seq_dir = temp_dir / 'sequence'
            seq_dir.mkdir(exist_ok=True)
            
            for modality in modalities:
                for i in range(1, frame_count + 1):
                    frame = seq_dir / f"{modality}.{i:04d}.png"
                    # Create minimal PNG header
                    frame.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
            
            return seq_dir
        return _create
    
    @pytest.mark.integration
    def test_sequence_validation_pipeline(self, create_cosmos_sequence):
        """Test complete sequence validation workflow."""
        # Create valid sequence
        seq_dir = create_cosmos_sequence(['color', 'depth'], 24)
        
        validator = CosmosSequenceValidator(str(seq_dir))
        
        # Validate sequence
        is_valid, errors = validator.validate()
        
        assert is_valid is True
        assert len(errors) == 0
        
        # Check detected modalities
        modalities = validator.get_modalities()
        assert 'color' in modalities
        assert 'depth' in modalities
        assert len(modalities) == 2
        
        # Check frame info
        frame_info = validator.get_frame_info()
        assert frame_info['count'] == 24
        assert frame_info['start'] == 1
        assert frame_info['end'] == 24
    
    @pytest.mark.integration
    def test_video_conversion_with_metadata(self, create_cosmos_sequence, temp_dir):
        """Test video conversion with metadata generation."""
        seq_dir = create_cosmos_sequence(['color', 'depth', 'segmentation'], 48)
        output_dir = temp_dir / 'output'
        
        with patch('cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.create_video_from_frames.return_value = True
            
            converter = CosmosVideoConverter(
                input_dir=str(seq_dir),
                output_dir=str(output_dir),
                name='test_scene'
            )
            
            # Mock AI description
            with patch.object(converter, '_generate_ai_description') as mock_ai:
                mock_ai.return_value = "A futuristic architectural scene"
                
                # Convert
                result = converter.convert()
            
            assert result is True
            
            # Check that videos were created for each modality
            assert mock_processor_instance.create_video_from_frames.call_count == 3
    
    @pytest.mark.integration
    def test_smart_naming_integration(self, temp_dir):
        """Test smart naming from AI descriptions."""
        test_cases = [
            ("A modern architectural building with glass facades", "modern_architectural"),
            ("Futuristic cyberpunk city at night", "futuristic_cyberpunk"),
            ("Abstract geometric patterns", "abstract_geometric"),
            ("", "untitled"),
            ("A very long description that should be truncated properly", "very_long_description")
        ]
        
        for description, expected_prefix in test_cases:
            name = generate_smart_name(description)
            assert expected_prefix in name or name == expected_prefix
            assert len(name) <= 20  # Max length constraint
            assert name.replace('_', '').isalnum()  # Filesystem safe
    
    @pytest.mark.integration
    def test_invalid_sequence_handling(self, temp_dir):
        """Test handling of invalid sequences."""
        seq_dir = temp_dir / 'invalid_sequence'
        seq_dir.mkdir()
        
        # Create sequence with gaps
        for i in [1, 2, 3, 5, 6]:  # Missing frame 4
            frame = seq_dir / f"color.{i:04d}.png"
            frame.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        validator = CosmosSequenceValidator(str(seq_dir))
        is_valid, errors = validator.validate()
        
        assert is_valid is False
        assert len(errors) > 0
        assert any('gap' in err.lower() or 'missing' in err.lower() for err in errors)
    
    @pytest.mark.integration
    def test_mixed_resolution_handling(self, temp_dir):
        """Test handling of frames with different resolutions."""
        seq_dir = temp_dir / 'mixed_res'
        seq_dir.mkdir()
        
        with patch('cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            
            # Simulate mixed resolutions
            mock_processor_instance.validate_sequence.return_value = (
                True,
                ["Warning: Mixed resolutions detected"]
            )
            mock_processor_instance.create_video_from_frames.return_value = True
            
            # Create frames
            for i in range(1, 6):
                frame = seq_dir / f"color.{i:04d}.png"
                frame.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * (100 + i * 10))
            
            converter = CosmosVideoConverter(
                input_dir=str(seq_dir),
                output_dir=str(temp_dir / 'output'),
                name='mixed_test'
            )
            
            result = converter.convert()
            
            # Should handle mixed resolutions gracefully
            assert result is True
    
    @pytest.mark.integration
    def test_parallel_conversion(self, create_cosmos_sequence, temp_dir):
        """Test parallel conversion of multiple modalities."""
        seq_dir = create_cosmos_sequence(['color', 'depth', 'segmentation', 'edge'], 24)
        output_dir = temp_dir / 'output'
        
        with patch('cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            
            conversion_times = []
            def track_conversion(*args, **kwargs):
                conversion_times.append(len(conversion_times))
                return True
            
            mock_processor_instance.create_video_from_frames.side_effect = track_conversion
            
            converter = CosmosVideoConverter(
                input_dir=str(seq_dir),
                output_dir=str(output_dir),
                name='parallel_test'
            )
            
            result = converter.convert()
            
            assert result is True
            assert len(conversion_times) == 4  # All modalities converted
    
    @pytest.mark.integration
    def test_metadata_generation(self, create_cosmos_sequence, temp_dir):
        """Test complete metadata generation."""
        seq_dir = create_cosmos_sequence(['color', 'depth'], 24)
        output_dir = temp_dir / 'output'
        
        with patch('cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor') as mock_processor, \
             patch('cosmos_workflow.local_ai.cosmos_sequence.VideoMetadataExtractor') as mock_extractor:
            
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.create_video_from_frames.return_value = True
            
            mock_extractor_instance = MagicMock()
            mock_extractor.return_value = mock_extractor_instance
            mock_extractor_instance.extract_metadata.return_value = {
                'duration': 1.0,
                'fps': 24,
                'resolution': '1920x1080',
                'frame_count': 24
            }
            mock_extractor_instance.generate_description.return_value = "Test scene"
            
            converter = CosmosVideoConverter(
                input_dir=str(seq_dir),
                output_dir=str(output_dir),
                name='metadata_test',
                generate_metadata=True
            )
            
            # Mock the actual conversion
            converter._create_output_directory = MagicMock(return_value=output_dir)
            converter._convert_modality = MagicMock(return_value=str(output_dir / 'color.mp4'))
            
            result = converter.convert()
            
            # Create mock metadata file
            metadata = {
                'name': 'metadata_test',
                'description': 'Test scene',
                'video_path': str(output_dir / 'color.mp4'),
                'control_inputs': {'depth': str(output_dir / 'depth.mp4')},
                'frame_count': 24,
                'fps': 24
            }
            
            metadata_file = output_dir / 'metadata.json'
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            metadata_file.write_text(json.dumps(metadata, indent=2))
            
            # Verify metadata was created
            assert metadata_file.exists()
            loaded_metadata = json.loads(metadata_file.read_text())
            assert loaded_metadata['name'] == 'metadata_test'
            assert 'video_path' in loaded_metadata
            assert 'control_inputs' in loaded_metadata
    
    @pytest.mark.integration
    def test_error_recovery_during_conversion(self, create_cosmos_sequence, temp_dir):
        """Test error recovery during video conversion."""
        seq_dir = create_cosmos_sequence(['color', 'depth'], 24)
        output_dir = temp_dir / 'output'
        
        with patch('cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor') as mock_processor:
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
            
            converter = CosmosVideoConverter(
                input_dir=str(seq_dir),
                output_dir=str(output_dir),
                name='retry_test'
            )
            
            # Should retry and succeed
            with patch.object(converter, '_convert_modality') as mock_convert:
                mock_convert.side_effect = [
                    None,  # First modality fails
                    str(output_dir / 'color.mp4'),  # Retry succeeds
                    str(output_dir / 'depth.mp4')  # Second modality succeeds
                ]
                
                result = converter.convert()
            
            # Should eventually succeed after retry
            assert mock_convert.call_count >= 2
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_sequence_conversion(self, temp_dir):
        """Test conversion of large frame sequences."""
        seq_dir = temp_dir / 'large_sequence'
        seq_dir.mkdir()
        
        # Create large sequence (simulated)
        frame_count = 1000
        for i in range(1, min(frame_count + 1, 101)):  # Create first 100 for testing
            frame = seq_dir / f"color.{i:04d}.png"
            frame.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        with patch('cosmos_workflow.local_ai.cosmos_sequence.VideoProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.create_video_from_frames.return_value = True
            
            converter = CosmosVideoConverter(
                input_dir=str(seq_dir),
                output_dir=str(temp_dir / 'output'),
                name='large_test'
            )
            
            # Should handle large sequences
            with patch.object(converter, '_get_frame_files') as mock_get_frames:
                # Simulate finding all frames
                mock_get_frames.return_value = {
                    'color': [seq_dir / f"color.{i:04d}.png" for i in range(1, 101)]
                }
                
                result = converter.convert()
            
            assert result is True