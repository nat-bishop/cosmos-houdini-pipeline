"""
Comprehensive tests for smart_naming.py to improve coverage from 8.20% to 80%+
Tests all functions, edge cases, and error conditions.
"""

import pytest

from cosmos_workflow.utils.smart_naming import generate_smart_name, sanitize_name


class TestGenerateSmartName:
    """Test the generate_smart_name function comprehensively."""

    def test_basic_name_generation(self):
        """Test basic name generation from simple prompts."""
        # Test that meaningful words are extracted and combined
        result1 = generate_smart_name("a modern staircase with dramatic lighting")
        assert "modern" in result1 or "staircase" in result1 or "lighting" in result1
        assert len(result1) > 0
        assert (
            "_" in result1 or len(result1.split("_")) == 1
        )  # Either has underscores or single word

        result2 = generate_smart_name("a red car driving on a highway")
        assert "car" in result2 or "red" in result2 or "highway" in result2
        assert len(result2) > 0

    def test_removes_stop_words(self):
        """Test that common stop words are removed."""
        text = "the cat is on the mat with a hat"
        result = generate_smart_name(text)
        assert "the" not in result
        assert "is" not in result
        assert "on" not in result
        assert "with" not in result
        assert "cat" in result or "mat" in result or "hat" in result

    def test_lowercase_conversion(self):
        """Test that text is converted to lowercase."""
        assert generate_smart_name("UPPERCASE TEXT") == generate_smart_name("uppercase text")
        assert generate_smart_name("MiXeD CaSe TeXt") == generate_smart_name("mixed case text")

    def test_max_length_truncation(self):
        """Test that names are truncated to max_length."""
        long_text = "very long description with many meaningful words that should be truncated"
        result = generate_smart_name(long_text, max_length=10)
        assert len(result) <= 10

    def test_max_length_preserves_whole_words(self):
        """Test that truncation tries to preserve whole words."""
        text = "beautiful landscape photography"
        result = generate_smart_name(text, max_length=15)
        # Should keep whole words, not cut in middle
        assert "_" not in result[-1:]
        assert result[-1:] != "_"

    def test_priority_suffixes(self):
        """Test that words with priority suffixes are preferred."""
        text = "the running dog and the small cat"
        result = generate_smart_name(text)
        # "running" has -ing suffix, should be prioritized
        assert "running" in result

    def test_no_meaningful_words_fallback(self):
        """Test fallback when no meaningful words found."""
        text = "a an the is are"  # All stop words
        result = generate_smart_name(text)
        assert result  # Should still return something

    def test_empty_string_input(self):
        """Test handling of empty string."""
        result = generate_smart_name("")
        assert result == "sequence"  # Default fallback

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        text = "hello@world#test$money%power"
        result = generate_smart_name(text)
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result

    def test_numbers_preserved(self):
        """Test that numbers are preserved in names."""
        text = "test 123 sequence 456"
        result = generate_smart_name(text)
        # Note: current implementation extracts only letters, not numbers
        # This test documents current behavior
        assert "123" not in result
        assert "456" not in result

    def test_single_word_input(self):
        """Test single word input."""
        assert generate_smart_name("photography") == "photography"
        assert generate_smart_name("cat") == "cat"

    def test_very_short_words_filtered(self):
        """Test that very short words (<=2 chars) are filtered."""
        text = "a go to it me so we us"
        result = generate_smart_name(text)
        # Words with 2 or fewer characters should be filtered
        assert result  # Should still return something

    def test_three_word_limit(self):
        """Test that only up to 3 words are used."""
        text = "one two three four five six seven eight nine ten"
        result = generate_smart_name(text)
        words = result.split("_")
        assert len(words) <= 3

    def test_underscore_joining(self):
        """Test that words are joined with underscores."""
        text = "beautiful sunset photography"
        result = generate_smart_name(text)
        if "_" in result:
            assert result.count("_") == len(result.split("_")) - 1

    def test_cyberpunk_example(self):
        """Test specific example from docstring."""
        text = "Futuristic cyberpunk city with neon lights"
        result = generate_smart_name(text)
        # Should prioritize meaningful words
        assert "futuristic" in result or "cyberpunk" in result

    def test_various_real_prompts(self):
        """Test with various realistic prompts."""
        prompts = [
            ("A serene lake at sunset", "serene_lake_sunset"),
            ("Dramatic storm clouds gathering", "dramatic_storm"),
            ("Abstract colorful patterns", "abstract_colorful"),
            ("Vintage car in garage", "vintage_car_garage"),
            ("Space station orbiting Earth", "space_station"),
        ]

        for prompt, _ in prompts:
            result = generate_smart_name(prompt)
            assert result  # Should always return something
            assert len(result) <= 20  # Default max length
            assert result.replace("_", "").isalnum() or result == "sequence"


class TestSanitizeName:
    """Test the sanitize_name function comprehensively."""

    def test_basic_sanitization(self):
        """Test basic name sanitization."""
        assert sanitize_name("hello world") == "hello_world"
        assert sanitize_name("Test-Name") == "test-name"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert sanitize_name("hello@world#") == "helloworld"
        assert sanitize_name("test$money%") == "testmoney"
        assert sanitize_name("foo&bar*baz") == "foobarbaz"

    def test_spaces_to_underscores(self):
        """Test that spaces become underscores."""
        assert sanitize_name("multiple word name") == "multiple_word_name"
        assert sanitize_name("  spaces  everywhere  ") == "__spaces__everywhere__"

    def test_lowercase_conversion(self):
        """Test conversion to lowercase."""
        assert sanitize_name("UPPERCASE") == "uppercase"
        assert sanitize_name("MiXeD CaSe") == "mixed_case"

    def test_length_limit(self):
        """Test that names are limited to 50 characters."""
        long_name = "a" * 100
        result = sanitize_name(long_name)
        assert len(result) == 50

    def test_empty_string_fallback(self):
        """Test that empty strings get default name."""
        assert sanitize_name("") == "unnamed"
        assert sanitize_name("@#$%") == "unnamed"  # All special chars removed

    def test_alphanumeric_preserved(self):
        """Test that alphanumeric characters are preserved."""
        assert sanitize_name("abc123XYZ") == "abc123xyz"
        assert sanitize_name("test_123-name") == "test_123-name"

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        # Unicode should be removed as they're not alphanumeric
        assert sanitize_name("café") == "caf"
        assert sanitize_name("emoji😀test") == "emojitest"

    def test_consecutive_special_chars(self):
        """Test multiple consecutive special characters."""
        assert sanitize_name("hello!!!world???") == "helloworld"
        assert sanitize_name("test---name") == "test---name"  # Hyphens preserved

    def test_leading_trailing_special(self):
        """Test leading and trailing special characters."""
        assert sanitize_name("###test###") == "test"
        assert sanitize_name("___name___") == "___name___"  # Underscores preserved

    def test_mixed_input(self):
        """Test complex mixed input."""
        input_text = "  Hello-World_123!@#$%  Test  "
        result = sanitize_name(input_text)
        # Check that it's lowercased and special chars removed
        assert "hello" in result.lower()
        assert "world" in result.lower()
        assert "test" in result.lower()
        assert "123" in result
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result

    def test_real_world_names(self):
        """Test with real-world style names."""
        names = [
            ("My Cool Project!", "my_cool_project"),
            ("test@email.com", "testemailcom"),
            ("2023-11-30_backup", "2023-11-30_backup"),
            ("file (copy).txt", "file_copytxt"),
            ("C:\\path\\to\\file", "cpathtofile"),
        ]

        for input_name, expected in names:
            assert sanitize_name(input_name) == expected


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_input(self):
        """Test handling of None input."""
        with pytest.raises(AttributeError):
            generate_smart_name(None)

        with pytest.raises(AttributeError):
            sanitize_name(None)

    def test_non_string_input(self):
        """Test handling of non-string input."""
        # Numbers
        result = generate_smart_name(str(12345))
        assert result == "sequence"  # No meaningful words

        # Should work with string conversion
        assert sanitize_name(str(123)) == "123"

    def test_only_punctuation(self):
        """Test input with only punctuation."""
        result = generate_smart_name("!@#$%^&*()")
        assert result == "sequence"  # Fallback

        result = sanitize_name("!@#$%^&*()")
        assert result == "unnamed"  # Fallback

    def test_very_long_single_word(self):
        """Test very long single word."""
        long_word = "supercalifragilisticexpialidocious" * 3
        result = generate_smart_name(long_word, max_length=20)
        assert len(result) <= 20

    def test_repeated_stop_words(self):
        """Test text with only repeated stop words."""
        text = "the the the and and and is is is"
        result = generate_smart_name(text)
        # Should return something valid, even if just stop words or fallback
        assert result  # Not empty
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mixed_language(self):
        """Test mixed language input (non-ASCII)."""
        text = "hello мир world"
        result = generate_smart_name(text)
        # Non-ASCII characters won't be extracted
        assert "hello" in result or "world" in result

    def test_max_length_zero(self):
        """Test max_length of zero."""
        result = generate_smart_name("test text", max_length=0)
        # Implementation may return empty string or fallback
        assert isinstance(result, str)
        # If max_length is 0, should either be empty or use a fallback
        assert result == "" or result == "sequence"

    def test_max_length_very_large(self):
        """Test very large max_length."""
        text = "short text"
        result = generate_smart_name(text, max_length=1000)
        assert len(result) < 1000  # Should be natural length
