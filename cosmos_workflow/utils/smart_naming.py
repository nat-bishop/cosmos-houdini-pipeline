#!/usr/bin/env python3
"""Smart naming utility for generating meaningful names from descriptions.

This module provides the core algorithm for converting AI-generated descriptions
or user prompts into concise, filesystem-friendly names.
"""

import logging
import re

logger = logging.getLogger(__name__)


def generate_smart_name(text: str, max_length: int = 20) -> str:
    """Generate a short, meaningful name from a text description or prompt.

    This is the centralized smart naming algorithm used throughout the system
    for converting descriptions, prompts, or other text into concise names.

    Args:
        text: Input text (description, prompt, etc.)
        max_length: Maximum length for the name (default 20)

    Returns:
        Smart name derived from text

    Examples:
        "a modern staircase with dramatic lighting" -> "modern_staircase"
        "a red car driving on a highway" -> "red_car_highway"
        "Futuristic cyberpunk city with neon lights" -> "futuristic_cyberpunk"
    """
    # Convert to lowercase
    text = text.lower()

    # Remove common filler words
    stop_words = {
        "a",
        "an",
        "the",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "very",
        "and",
        "or",
        "but",
        "there",
        "here",
        "that",
        "this",
    }

    # Extract meaningful words
    words = re.findall(r"\b[a-z]+\b", text)
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]

    if not meaningful_words:
        # Fallback to first few words if no meaningful words found
        meaningful_words = words[:3]

    # Prioritize nouns and adjectives (heuristic approach)
    # Words ending in common noun/adjective suffixes get priority
    priority_suffixes = ["ing", "tion", "ment", "ness", "ity", "er", "or", "ist"]
    priority_words = []
    other_words = []

    for word in meaningful_words:
        if any(word.endswith(suffix) for suffix in priority_suffixes):
            priority_words.append(word)
        else:
            other_words.append(word)

    # Combine priority words first, then others
    final_words = (priority_words + other_words)[:3]  # Take up to 3 words

    # Join words with underscores
    name = "_".join(final_words)

    # Truncate if too long
    if len(name) > max_length:
        # Try to keep whole words
        parts = name.split("_")
        truncated = []
        current_length = 0

        for part in parts:
            if current_length + len(part) + (1 if truncated else 0) <= max_length:
                truncated.append(part)
                current_length += len(part) + (1 if len(truncated) > 1 else 0)
            else:
                break

        name = "_".join(truncated) if truncated else name[:max_length]

    # Ensure name is valid (alphanumeric and underscores only)
    name = re.sub(r"[^a-z0-9_]", "", name)

    # Default fallback
    if not name:
        name = "sequence"

    logger.debug("Generated smart name: '%s' from text: '{text}'", name)
    return name


def sanitize_name(name: str) -> str:
    """Sanitize a name to be filesystem-friendly.

    Args:
        name: Input name to sanitize

    Returns:
        Sanitized name safe for filesystem use
    """
    # Replace spaces with underscores
    name = name.replace(" ", "_")

    # Remove or replace special characters
    name = re.sub(r"[^a-zA-Z0-9_-]", "", name)

    # Convert to lowercase
    name = name.lower()

    # Limit length
    if len(name) > 50:
        name = name[:50]

    # Ensure non-empty
    if not name:
        name = "unnamed"

    return name
