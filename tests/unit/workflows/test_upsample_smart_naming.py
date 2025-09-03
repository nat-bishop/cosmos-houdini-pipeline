#!/usr/bin/env python3
"""Unit tests for smart naming functionality.

Tests the pure logic of name generation WITHOUT any mocking,
following the testing philosophy of using real code wherever possible.
"""

import pytest

from cosmos_workflow.utils.smart_naming import generate_smart_name, sanitize_name


class TestGenerateSmartName:
    """Test the generate_smart_name function with various inputs."""

    def test_descriptive_prompt_with_keywords(self):
        """Test smart name generation with descriptive prompts."""
        # Test various descriptive prompts
        assert "foggy" in generate_smart_name("A foggy morning in mountains")
        # Note: Algorithm prioritizes certain words differently
        name = generate_smart_name("Beautiful sunset over ocean")
        assert "beautiful" in name or "sunset" in name or "ocean" in name
        # Algorithm may prioritize different words
        name = generate_smart_name("Futuristic cyberpunk city with neon lights")
        assert "cyberpunk" in name or "city" in name or "futuristic" in name or "neon" in name
        assert "forest" in generate_smart_name("Dense forest with tall trees")

    def test_removes_stop_words(self):
        """Test that common stop words are removed."""
        # Should not include stop words like 'a', 'the', 'with', 'in', etc.
        name = generate_smart_name("A car in the city with lights")
        assert "a" not in name.split("_")
        assert "the" not in name.split("_")
        assert "in" not in name.split("_")
        assert "with" not in name.split("_")
        assert "car" in name or "city" in name or "lights" in name

    def test_prioritizes_meaningful_words(self):
        """Test that nouns and adjectives are prioritized."""
        # Words with priority suffixes should come first
        name = generate_smart_name("The running person is jumping quickly")
        words = name.split("_")
        # 'running' and 'jumping' (with -ing) should be prioritized
        assert "running" in words or "jumping" in words

    def test_max_length_constraint(self):
        """Test that names respect max_length parameter."""
        long_prompt = "A beautiful serene peaceful tranquil calm relaxing soothing atmosphere"

        # Test different max lengths
        name_10 = generate_smart_name(long_prompt, max_length=10)
        assert len(name_10) <= 10

        name_20 = generate_smart_name(long_prompt, max_length=20)
        assert len(name_20) <= 20

        name_30 = generate_smart_name(long_prompt, max_length=30)
        assert len(name_30) <= 30

    def test_handles_empty_input(self):
        """Test fallback for empty or minimal input."""
        assert generate_smart_name("") == "sequence"
        assert generate_smart_name("   ") == "sequence"
        # Single stop words are still kept if nothing else available
        assert generate_smart_name("a") in ["a", "sequence"]

    def test_handles_special_characters(self):
        """Test that special characters are handled correctly."""
        name = generate_smart_name("Hello! World@ #2024")
        assert "!" not in name
        assert "@" not in name
        assert "#" not in name
        assert "hello" in name or "world" in name

    def test_case_insensitive(self):
        """Test that input case doesn't affect output (always lowercase)."""
        name1 = generate_smart_name("BEAUTIFUL SUNSET")
        name2 = generate_smart_name("Beautiful Sunset")
        name3 = generate_smart_name("beautiful sunset")

        # All should produce the same result
        assert name1 == name2 == name3
        assert name1.islower()

    def test_preserves_numbers(self):
        """Test that numbers are preserved in names."""
        name = generate_smart_name("Scene 2024 with version 3")
        # Should keep meaningful words and numbers
        assert "scene" in name or "2024" in name or "version" in name

    def test_word_limit(self):
        """Test that only up to 3 meaningful words are used."""
        prompt = "beautiful sunny warm bright colorful vibrant exciting amazing day"
        name = generate_smart_name(prompt)
        words = name.split("_")
        assert len(words) <= 3

    def test_realistic_prompts(self):
        """Test with realistic AI enhancement prompts."""
        test_cases = [
            (
                "A misty morning with fog rolling through ancient forest paths",
                ["misty", "morning", "fog", "forest", "rolling"],
            ),
            (
                "Transform to anime style with vibrant colors",
                ["transform", "anime", "style", "vibrant", "colors"],
            ),
            (
                "Cyberpunk street scene with neon lights reflecting on wet pavement",
                ["cyberpunk", "street", "neon", "reflecting", "pavement", "lights", "wet"],
            ),
            (
                "Serene lake surrounded by mountains at golden hour",
                ["serene", "lake", "mountains", "golden", "surrounded", "hour"],
            ),
            (
                "Abandoned industrial facility overtaken by nature",
                ["abandoned", "industrial", "facility", "nature", "overtaken"],
            ),
        ]

        for prompt, expected_keywords in test_cases:
            name = generate_smart_name(prompt)
            # Should contain at least one of the expected keywords (algorithm may prioritize different words)
            assert any(keyword in name for keyword in expected_keywords), (
                f"Name '{name}' should contain one of {expected_keywords}"
            )
            # Should be valid filename
            assert name.replace("_", "").isalnum() or name == "sequence"


class TestSanitizeName:
    """Test the sanitize_name function."""

    def test_replaces_spaces(self):
        """Test that spaces are replaced with underscores."""
        assert sanitize_name("hello world") == "hello_world"
        assert sanitize_name("one two three") == "one_two_three"

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        assert sanitize_name("hello@world!") == "helloworld"
        assert sanitize_name("test#$%name") == "testname"
        assert sanitize_name("file.name.txt") == "filenametxt"

    def test_converts_to_lowercase(self):
        """Test that names are converted to lowercase."""
        assert sanitize_name("HelloWorld") == "helloworld"
        assert sanitize_name("TEST_NAME") == "test_name"

    def test_preserves_valid_characters(self):
        """Test that valid characters are preserved."""
        assert sanitize_name("valid_name_123") == "valid_name_123"
        assert sanitize_name("test-name") == "test-name"

    def test_length_limit(self):
        """Test that names are truncated at 50 characters."""
        long_name = "a" * 60
        result = sanitize_name(long_name)
        assert len(result) == 50
        assert result == "a" * 50

    def test_handles_empty_input(self):
        """Test fallback for empty input."""
        assert sanitize_name("") == "unnamed"
        assert sanitize_name("   ") == "___"  # Spaces become underscores
        assert sanitize_name("!!!") == "unnamed"  # Only special chars

    def test_unicode_handling(self):
        """Test that unicode characters are handled."""
        assert sanitize_name("café") == "caf"  # é is removed
        assert sanitize_name("naïve") == "nave"  # ï is removed
        assert sanitize_name("日本語") == "unnamed"  # Non-ASCII removed completely


class TestSmartNamingIntegration:
    """Integration tests for smart naming with PromptSpecManager."""

    def test_prompt_spec_uses_smart_naming(self):
        """Test that PromptSpecManager uses smart naming correctly."""
        import tempfile
        from pathlib import Path

        from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
        from cosmos_workflow.prompts.schemas import DirectoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup directories
            input_dir = Path(tmpdir) / "inputs"
            output_dir = Path(tmpdir) / "outputs"
            input_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            dir_manager = DirectoryManager(str(input_dir), str(output_dir))
            spec_manager = PromptSpecManager(dir_manager)

            # Test cases with expected smart names
            test_cases = [
                ("A foggy morning in the mountains", ["foggy", "morning", "mountains"]),
                ("Cyberpunk city with neon lights", ["cyberpunk", "city", "neon"]),
                ("Beautiful sunset over the ocean", ["beautiful", "sunset", "ocean"]),
                ("", ["sequence"]),  # Fallback case
            ]

            for prompt_text, expected_keywords in test_cases:
                spec = spec_manager.create_prompt_spec(prompt_text=prompt_text, is_upsampled=True)

                # Check that the name contains expected keywords
                name_lower = spec.name.lower()
                matches = any(keyword in name_lower for keyword in expected_keywords)
                assert matches, f"Name '{spec.name}' should contain one of {expected_keywords}"

                # Ensure it doesn't use the old '_enhanced' pattern
                assert "_enhanced" not in spec.name

    def test_upsampling_preserves_smart_names(self):
        """Test that upsampling workflow preserves smart names."""
        import tempfile
        from pathlib import Path

        from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
        from cosmos_workflow.prompts.schemas import DirectoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "inputs"
            output_dir = Path(tmpdir) / "outputs"
            input_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            dir_manager = DirectoryManager(str(input_dir), str(output_dir))
            spec_manager = PromptSpecManager(dir_manager)

            # Create an enhanced prompt with a very descriptive text
            enhanced_text = "A mystical enchanted forest with glowing mushrooms and ethereal fog"
            spec = spec_manager.create_prompt_spec(
                prompt_text=enhanced_text, is_upsampled=True, parent_prompt_text="forest scene"
            )

            # The name should be smart and descriptive
            assert spec.name != "forest scene_enhanced"
            assert any(
                word in spec.name.lower()
                for word in ["mystical", "enchanted", "forest", "glowing", "mushrooms"]
            )

            # The parent prompt text should be preserved
            assert spec.parent_prompt_text == "forest scene"

    def test_name_uniqueness_handling(self):
        """Test that the system handles duplicate names gracefully."""
        import tempfile
        from pathlib import Path

        from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
        from cosmos_workflow.prompts.schemas import DirectoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "inputs"
            output_dir = Path(tmpdir) / "outputs"
            input_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            dir_manager = DirectoryManager(str(input_dir), str(output_dir))
            spec_manager = PromptSpecManager(dir_manager)

            # Create prompts with different texts to ensure unique IDs
            spec1 = spec_manager.create_prompt_spec("Beautiful sunset over ocean")
            spec2 = spec_manager.create_prompt_spec("Gorgeous sunset above the sea")

            # Different prompt texts should create different IDs
            assert spec1.id != spec2.id

            # Different specs should be saved as separate files
            files = list(input_dir.rglob("*.json"))
            assert len(files) == 2  # Both should be saved

            # Test that same prompt creates same ID (deterministic behavior)
            spec3 = spec_manager.create_prompt_spec("Beautiful sunset over ocean")
            assert spec1.id == spec3.id  # Same prompt text creates same ID (by design)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])
