#!/usr/bin/env python3
"""Smart naming utility using KeyBERT for semantic keyword extraction.

This module provides intelligent name generation from text descriptions using
semantic keyword extraction. It uses KeyBERT with SBERT embeddings to identify
the most relevant keywords, creating concise filesystem-friendly names.

Requirements:
- keybert>=0.8.0
- sentence-transformers>=2.2.0

Key features:
- Semantic keyword extraction using all-MiniLM-L6-v2 SBERT model
- N-gram support (1-2) for single words and phrases
- MMR diversity (0.7) to avoid duplicate keywords
- Comprehensive stopword filtering (common English + VFX domain terms)
- Maximum 3 words per name for better conciseness
"""

import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

# Load KeyBERT and SBERT (required)
try:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer

    # Use a small, fast model as recommended
    MODEL_NAME = "all-MiniLM-L6-v2"
    sentence_model = SentenceTransformer(MODEL_NAME)
    kw_model = KeyBERT(model=sentence_model)
    logger.info("KeyBERT with %s loaded for smart naming", MODEL_NAME)
except ImportError as e:
    error_msg = (
        "KeyBERT is required for smart naming functionality. "
        "Please install it with: pip install keybert sentence-transformers"
    )
    logger.error(error_msg)
    raise ImportError(error_msg) from e

# Common English stop words
COMMON_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "with",
    "for",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "has",
    "have",
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
    "can",
    "this",
    "that",
    "these",
    "those",
    "from",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "up",
    "down",
    "out",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
}

# Domain-specific stop words for VFX/rendering jargon we want to filter out
DOMAIN_STOPWORDS = {
    # Technical jargon
    "gradient",
    "falloff",
    "texture",
    "palette",
    "luminance",
    "speculars",
    "facades",
    "accumulation",
    "diffusion",
    "contrast",
    "saturation",
    "desaturate",
    "materials",
    "surfaces",
    "planes",
    "existing",
    "natural",
    "overall",
    "subtle",
    "uniform",
    "minimal",
    "plausible",
    "realistic",
    "produces",
    "creates",
    "increases",
    "decreases",
    "maintains",
    # Common filler words
    "video",
    "scene",
    "captures",
    "shows",
    "displays",
    "features",
    "includes",
    "contains",
    "various",
    "multiple",
    "several",
    # Directional/positional
    "upward",
    "downward",
    "horizontal",
    "vertical",
    "diagonal",
    "near",
    "far",
    "distance",
    "perspective",
    "aerial",
}

# Combine all stopwords
ALL_STOPWORDS = COMMON_STOPWORDS | DOMAIN_STOPWORDS


@lru_cache(maxsize=128)
def generate_smart_name(text: str, max_length: int = 20) -> str:
    """Generate smart name using KeyBERT semantic keyword extraction.

    Uses KeyBERT with SBERT embeddings to extract semantically important
    keywords/phrases from text. Configured with:
    - N-grams (1-2) to capture single words and phrases
    - MMR (Maximal Marginal Relevance) for diversity
    - Diversity 0.7 to avoid near-duplicate keywords
    - Maximum 3 words in final name for conciseness

    Args:
        text: Input text (description, prompt, etc.)
        max_length: Maximum character length for the name (default 50)

    Returns:
        Smart name derived from extracted keywords (underscore-separated).
        Returns "sequence" for empty input.

    Raises:
        AttributeError: If text is None.
        ValueError: If max_length is not a positive integer.
        RuntimeError: If KeyBERT extraction fails.
        ImportError: If KeyBERT is not installed.

    Examples:
        >>> generate_smart_name("Low-lying mist with gradual falloff")
        "low_lying_mist"
        >>> generate_smart_name("Golden hour light creating long shadows")
        "golden_hour_shadows"
        >>> generate_smart_name("Heavy rain with water puddles")
        "heavy_rain_puddles"
    """
    # Handle None input
    if text is None:
        raise AttributeError("Cannot generate name from None")

    # Validate max_length
    if not isinstance(max_length, int) or max_length < 0:
        raise ValueError("max_length must be a positive integer")

    # Handle empty input
    if not text or not text.strip():
        return "sequence"  # Tests expect "sequence" as fallback

    # Handle special cases
    if max_length == 0:
        return ""

    # Convert to lowercase for consistency
    text_lower = text.lower()

    # Special case for single word
    single_word_check = re.findall(r"\b[a-z]+\b", text_lower)
    if len(single_word_check) == 1:
        word = single_word_check[0]
        # Check length constraint
        if len(word) > max_length:
            word = word[:max_length]
        return word

    # Extract keywords using KeyBERT
    try:
        # Extract keywords using KeyBERT
        # Use n-grams (1-2) for shorter phrases and MMR for diversity
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),  # 1-2 word phrases (shorter)
            stop_words=list(ALL_STOPWORDS),  # Filter ALL stopwords
            use_mmr=True,  # Use MMR for diversity
            diversity=0.7,  # High diversity to avoid duplicates
            top_n=5,  # Get top 5 candidates
        )

        if keywords:
            # Extract just the keyword strings (not scores)
            keyword_strings = [kw[0] for kw in keywords]

            # Process keywords for naming
            name_parts = []
            seen_words = set()  # Track unique words to avoid duplicates

            for keyword in keyword_strings:
                # Clean and convert to name format - exclude numbers
                cleaned = re.sub(r"[^a-z\s]", "", keyword.lower())
                # Split multi-word phrases
                words = cleaned.split()

                for word in words:
                    # Check constraints before adding
                    if word and word not in seen_words and len(name_parts) < 3:
                        # Check if adding would exceed max_length
                        potential_name = "_".join([*name_parts, word])
                        if len(potential_name) <= max_length:
                            name_parts.append(word)
                            seen_words.add(word)
                        else:
                            break  # Stop if would exceed length

                if len(name_parts) >= 3:
                    break  # Stop once we have 3 words

            if name_parts:
                name = "_".join(name_parts)

                # Ensure it fits max_length
                if len(name) > max_length:
                    # Try with fewer parts
                    for num_parts in [2, 1]:
                        name = "_".join(name_parts[:num_parts])
                        if len(name) <= max_length:
                            break
                    # If still too long, truncate
                    if len(name) > max_length:
                        name = name[:max_length]

                return name if name else "sequence"

    except Exception as e:
        logger.error("KeyBERT extraction failed: %s", e)
        raise RuntimeError(f"Failed to generate smart name: {e}") from e

    # If we get here, no keywords were extracted
    logger.warning("No keywords extracted from text: %s", text[:100])
    return "sequence"


def sanitize_name(name: str) -> str:
    """Sanitize a name to be filesystem-friendly.

    Args:
        name: Input name to sanitize

    Returns:
        Sanitized name safe for filesystem use
    """
    # Handle None input
    if name is None:
        raise AttributeError("Cannot sanitize None")

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
