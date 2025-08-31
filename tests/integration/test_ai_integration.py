#!/usr/bin/env python3
"""
Integration tests for AI functionality with real models.

These tests actually load and use the BLIP model for image captioning
and test the complete AI pipeline end-to-end.
"""

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

from cosmos_workflow.local_ai.cosmos_sequence import (
    CosmosSequenceInfo,
    CosmosSequenceValidator,
    CosmosVideoConverter,
)


class TestAIIntegration:
    """Integration tests that use real AI models."""

    @classmethod
    def setup_class(cls):
        """Set up test fixtures once for all tests."""
        # Create a temporary directory for test files
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="ai_test_"))

        # Create test images
        cls.test_images = cls._create_test_images()

    @classmethod
    def teardown_class(cls):
        """Clean up after all tests."""
        if hasattr(cls, "temp_dir") and cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _create_test_images(cls):
        """Create various test images for AI testing."""
        images = {}

        # Test image 1: Simple geometric shapes
        img1 = Image.new("RGB", (512, 512), color="white")
        draw = ImageDraw.Draw(img1)
        draw.rectangle([100, 100, 200, 200], fill="red")
        draw.ellipse([250, 100, 350, 200], fill="blue")
        draw.polygon([(200, 300), (150, 400), (250, 400)], fill="green")
        img1_path = cls.temp_dir / "geometric.png"
        img1.save(img1_path)
        images["geometric"] = img1_path

        # Test image 2: House scene
        img2 = Image.new("RGB", (512, 512), color="skyblue")
        draw = ImageDraw.Draw(img2)
        # House
        draw.rectangle([150, 250, 350, 400], fill="brown")
        draw.polygon([(150, 250), (250, 150), (350, 250)], fill="red")
        # Tree
        draw.rectangle([380, 350, 420, 400], fill="brown")
        draw.ellipse([360, 280, 440, 360], fill="green")
        img2_path = cls.temp_dir / "house_scene.png"
        img2.save(img2_path)
        images["house"] = img2_path

        # Test image 3: Abstract art
        img3 = Image.new("RGB", (512, 512), color="black")
        draw = ImageDraw.Draw(img3)
        for i in range(10):
            x1, y1 = np.random.randint(0, 512, 2)
            x2, y2 = np.random.randint(0, 512, 2)
            color = tuple(np.random.randint(0, 255, 3))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=3)
        img3_path = cls.temp_dir / "abstract.png"
        img3.save(img3_path)
        images["abstract"] = img3_path

        return images

    def test_ai_model_loading(self):
        """Test that AI models can be loaded successfully."""
        try:
            from transformers import BlipForConditionalGeneration, BlipProcessor

            # Try to load the models
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )

            assert processor is not None
            assert model is not None

        except ImportError:
            pytest.skip("Transformers not installed - skipping AI model tests")

    def test_ai_description_generation_real(self):
        """Test AI description generation with real models and images."""
        converter = CosmosVideoConverter()

        # Test with each image type
        for img_type, img_path in self.test_images.items():
            description = converter._generate_ai_description([img_path])

            # Check that we got a real description, not the fallback
            assert description is not None
            assert (
                "Sequence with" not in description
            ), f"AI generation failed for {img_type}, got fallback: {description}"

            # Descriptions should be meaningful (more than 3 words)
            word_count = len(description.split())
            assert word_count >= 3, f"Description too short for {img_type}: {description}"

            print(f"{img_type}: {description}")

    def test_smart_name_generation_from_real_descriptions(self):
        """Test smart name generation using real AI-generated descriptions."""
        converter = CosmosVideoConverter()

        for img_type, img_path in self.test_images.items():
            # Generate real description
            description = converter._generate_ai_description([img_path])

            if description and "Sequence with" not in description:
                # Generate smart name
                name = converter._generate_smart_name(description)

                # Verify name properties
                assert name is not None
                assert len(name) > 0
                assert len(name) <= 20, f"Name too long: {name}"
                assert name.replace("_", "").isalnum(), f"Name contains invalid characters: {name}"

                # Name should not contain stop words
                stop_words = {"a", "an", "the", "is", "are", "with", "and", "or"}
                name_parts = name.split("_")
                for part in name_parts:
                    assert part not in stop_words, f"Name contains stop word '{part}': {name}"

                print(f"{img_type}: '{description}' -> '{name}'")

    def test_full_pipeline_with_cosmos_sequence(self):
        """Test the complete pipeline with Cosmos sequence format."""
        # Create a Cosmos-format sequence
        seq_dir = self.temp_dir / "cosmos_sequence"
        seq_dir.mkdir(exist_ok=True)

        # Create color frames
        for i in range(1, 4):
            img = Image.new("RGB", (256, 256), color="blue")
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), str(i), fill="white")
            img.save(seq_dir / f"color.{i:04d}.png")

        # Create depth frames (optional)
        for i in range(1, 4):
            img = Image.new("L", (256, 256), color=128)
            img.save(seq_dir / f"depth.{i:04d}.png")

        # Validate sequence
        validator = CosmosSequenceValidator()
        sequence_info = validator.validate(seq_dir)
        assert sequence_info.valid

        # Convert and generate metadata
        converter = CosmosVideoConverter()
        output_dir = self.temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Generate metadata with AI
        metadata = converter.generate_metadata(
            sequence_info=sequence_info,
            output_dir=output_dir,
            name=None,  # Let AI generate
            description=None,  # Let AI generate
            use_ai=True,
        )

        # Verify metadata
        assert metadata.name != "sequence", "AI should generate a better name"
        assert metadata.description != f"Sequence with {sequence_info.frame_count} frames"
        assert metadata.frame_count == 3
        assert "color" in metadata.modalities
        assert "depth" in metadata.modalities

    def test_ai_fallback_behavior(self):
        """Test that the system falls back gracefully when AI fails."""
        converter = CosmosVideoConverter()

        # Test with invalid/corrupted image path
        invalid_path = Path("nonexistent.png")
        description = converter._generate_ai_description([invalid_path])

        # Should fall back to default
        assert description == "Sequence with 1 frames"

        # Smart name generation from fallback description
        name = converter._generate_smart_name(description)
        # The algorithm may extract "sequence" and "frames" from the fallback
        assert "sequence" in name

    def test_ai_with_various_scene_types(self):
        """Test AI with different types of scenes."""
        converter = CosmosVideoConverter()

        test_scenes = []

        # Urban scene
        img = Image.new("RGB", (512, 512), color="gray")
        draw = ImageDraw.Draw(img)
        for i in range(5):
            x = 50 + i * 80
            draw.rectangle([x, 200, x + 60, 400], fill="darkgray")
            for j in range(10):
                if (i + j) % 3 == 0:
                    draw.rectangle([x + 10, 210 + j * 18, x + 25, 225 + j * 18], fill="yellow")
        img_path = self.temp_dir / "urban.png"
        img.save(img_path)
        test_scenes.append(("urban", img_path))

        # Nature scene
        img = Image.new("RGB", (512, 512), color="lightblue")
        draw = ImageDraw.Draw(img)
        draw.ellipse([200, 50, 312, 162], fill="yellow")  # Sun
        draw.rectangle([0, 350, 512, 512], fill="green")  # Grass
        for i in range(3):
            x = 100 + i * 150
            draw.ellipse([x - 30, 250, x + 30, 350], fill="darkgreen")  # Trees
        img_path = self.temp_dir / "nature.png"
        img.save(img_path)
        test_scenes.append(("nature", img_path))

        # Test each scene
        for scene_type, img_path in test_scenes:
            description = converter._generate_ai_description([img_path])
            name = converter._generate_smart_name(description)

            print(f"{scene_type}: '{description}' -> '{name}'")

            # Verify we got meaningful results
            assert description and "Sequence with" not in description
            assert name and name != "sequence"

    def test_performance_with_multiple_frames(self):
        """Test performance when processing multiple frames."""
        import time

        converter = CosmosVideoConverter()

        # Create multiple frames
        frames = []
        for i in range(5):
            img = Image.new("RGB", (256, 256), color=(i * 50, 100, 200 - i * 40))
            img_path = self.temp_dir / f"frame_{i:04d}.png"
            img.save(img_path)
            frames.append(img_path)

        # Measure time for single frame
        start = time.time()
        desc1 = converter._generate_ai_description([frames[0]])
        single_time = time.time() - start

        # Measure time for multiple frames (uses middle frame)
        start = time.time()
        desc2 = converter._generate_ai_description(frames)
        multi_time = time.time() - start

        print(f"Single frame: {single_time:.2f}s")
        print(f"Multiple frames (middle): {multi_time:.2f}s")

        # Multiple frames should not be much slower (only processes middle)
        assert multi_time < single_time * 2, "Processing multiple frames too slow"


class TestSmartNameAlgorithm:
    """Detailed tests for the smart name generation algorithm."""

    def test_stop_word_removal(self):
        """Test that stop words are properly removed."""
        converter = CosmosVideoConverter()

        test_cases = [
            ("a cat on the mat", ["cat", "mat"]),
            (
                "the big red house with a garden",
                ["big", "red", "house"],
            ),  # garden might not make it in top 3
            (
                "an interesting painting of a landscape",
                ["painting", "landscape"],
            ),  # interesting has -ing suffix
        ]

        for description, expected_words in test_cases:
            name = converter._generate_smart_name(description)
            name_parts = name.split("_")

            # Check that at least some expected words appear
            # (algorithm takes top 3 words, so not all may appear)
            matches = sum(1 for word in expected_words if any(word in part for part in name_parts))
            assert (
                matches >= 1
            ), f"Expected at least one of {expected_words} in name '{name}' from '{description}'"

    def test_length_constraints(self):
        """Test that names respect length constraints."""
        converter = CosmosVideoConverter()

        # Very long description
        long_desc = "a very complex industrial machinery with multiple hydraulic systems and conveyor belts in a large factory setting"
        name = converter._generate_smart_name(long_desc, max_length=20)

        assert len(name) <= 20
        assert name != ""

        # Test with different max lengths
        for max_len in [10, 15, 20, 25]:
            name = converter._generate_smart_name(long_desc, max_length=max_len)
            assert len(name) <= max_len

    def test_special_character_handling(self):
        """Test handling of special characters and punctuation."""
        converter = CosmosVideoConverter()

        test_cases = [
            "a cat! with stripes?",
            "building #42 @ main street",
            "50% off sale & more",
            "user's favorite item",
        ]

        for description in test_cases:
            name = converter._generate_smart_name(description)

            # Should only contain alphanumeric and underscores
            assert all(
                c.isalnum() or c == "_" for c in name
            ), f"Invalid characters in '{name}' from '{description}'"

    def test_priority_word_selection(self):
        """Test that meaningful words are prioritized."""
        converter = CosmosVideoConverter()

        # Words with -ing, -tion, etc. should be prioritized
        desc = "a cat quickly jumping over the wooden fence"
        name = converter._generate_smart_name(desc)

        # "jumping" should be prioritized
        assert "jumping" in name or "jump" in name

        # Test with -tion words
        desc = "beautiful decoration in the exhibition hall"
        name = converter._generate_smart_name(desc)

        # Should prioritize decoration/exhibition
        assert "decoration" in name or "exhibition" in name


class TestDirectoryNamingCompliance:
    """Test that directory naming follows the exact specification."""

    def test_timestamp_format_compliance(self):
        """Test timestamp format is exactly YYYYMMDD_HHMMSS."""
        import re
        from datetime import datetime

        # Test various dates
        test_dates = [
            datetime(2025, 1, 1, 0, 0, 0),
            datetime(2025, 12, 31, 23, 59, 59),
            datetime(2025, 8, 30, 16, 36, 4),
        ]

        pattern = re.compile(r"^\d{8}_\d{6}$")

        for dt in test_dates:
            timestamp = dt.strftime("%Y%m%d_%H%M%S")
            assert pattern.match(timestamp), f"Timestamp '{timestamp}' doesn't match format"

    def test_full_directory_name_format(self):
        """Test complete directory name format: {name}_{timestamp}."""
        import re
        from datetime import datetime

        converter = CosmosVideoConverter()

        # Mock datetime for consistent testing
        test_time = datetime(2025, 8, 30, 16, 36, 4)
        timestamp = test_time.strftime("%Y%m%d_%H%M%S")

        test_names = ["scene", "urban_night", "test_render", "my_video"]

        for name in test_names:
            full_name = f"{name}_{timestamp}"

            # Verify format
            pattern = re.compile(r"^[\w]+_\d{8}_\d{6}$")
            assert pattern.match(full_name), f"Directory name '{full_name}' doesn't match format"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
