#!/usr/bin/env python3
"""
Text-to-name generation module.

Converts descriptive text into short, filesystem-safe names (3-4 words).
Uses lightweight NLP techniques for fast local processing.
"""

import re
import string
from typing import List, Optional
from collections import Counter


class TextToNameGenerator:
    """
    Generates short, descriptive names from text descriptions.
    
    This class uses simple NLP techniques to extract key words from
    descriptions and create filesystem-safe names suitable for prompts
    and video metadata.
    """
    
    # Common stop words to filter out
    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'the', 'this', 'these', 'those',
        'very', 'really', 'quite', 'just', 'even', 'also', 'such', 'own',
        'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will'
    }
    
    # Words that are often important in video generation contexts
    PRIORITY_WORDS = {
        'city', 'urban', 'rural', 'forest', 'ocean', 'mountain', 'desert',
        'night', 'day', 'dawn', 'dusk', 'sunset', 'sunrise', 'morning',
        'futuristic', 'ancient', 'modern', 'vintage', 'cyberpunk', 'steampunk',
        'robot', 'human', 'animal', 'creature', 'vehicle', 'building',
        'flying', 'walking', 'running', 'standing', 'sitting', 'moving',
        'neon', 'dark', 'bright', 'colorful', 'monochrome', 'vivid',
        'rain', 'snow', 'fog', 'clear', 'cloudy', 'storm', 'wind'
    }
    
    def __init__(self, max_words: int = 4, min_words: int = 2):
        """
        Initialize the text-to-name generator.
        
        Args:
            max_words: Maximum number of words in the generated name
            min_words: Minimum number of words in the generated name
        """
        self.max_words = max_words
        self.min_words = min_words
    
    def generate_name(self, text: str, context: Optional[str] = None) -> str:
        """
        Generate a short name from descriptive text.
        
        Args:
            text: The descriptive text to convert
            context: Optional context to help with name generation
            
        Returns:
            A filesystem-safe name of 2-4 words
        """
        # Handle empty input
        if not text.strip():
            return "untitled"
        
        # Clean and tokenize the text
        words = self._tokenize(text.lower())
        
        # Filter out stop words
        meaningful_words = [w for w in words if w not in self.STOP_WORDS]
        
        # If we have context, add it to consideration
        if context:
            context_words = self._tokenize(context.lower())
            context_words = [w for w in context_words if w not in self.STOP_WORDS]
        else:
            context_words = []
        
        # Score words based on importance
        word_scores = self._score_words(meaningful_words, context_words)
        
        # Select top words
        selected_words = self._select_top_words(word_scores)
        
        # Create the name
        name = self._create_name(selected_words)
        
        return name
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of word tokens
        """
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Filter out numbers and very short words
        words = [w for w in words if len(w) > 1 and not w.isdigit()]
        
        return words
    
    def _score_words(self, words: List[str], context_words: List[str]) -> dict:
        """
        Score words based on importance.
        
        Args:
            words: Main text words
            context_words: Context words
            
        Returns:
            Dictionary of word scores
        """
        scores = {}
        
        # Count word frequency
        word_freq = Counter(words)
        
        for word in set(words):
            score = 0
            
            # Base score from frequency (but not too high)
            score += min(word_freq[word], 3)
            
            # Bonus for priority words
            if word in self.PRIORITY_WORDS:
                score += 3
            
            # Bonus for being in context
            if word in context_words:
                score += 2
            
            # Bonus for longer words (more descriptive)
            if len(word) > 5:
                score += 1
            
            # Penalty for very common programming terms
            if word in {'test', 'example', 'demo', 'sample'}:
                score -= 2
            
            scores[word] = score
        
        return scores
    
    def _select_top_words(self, word_scores: dict) -> List[str]:
        """
        Select the top scoring words.
        
        Args:
            word_scores: Dictionary of word scores
            
        Returns:
            List of selected words
        """
        if not word_scores:
            return ["generated", "content"]
        
        # Sort by score
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Take top words up to max_words
        selected = []
        for word, score in sorted_words:
            if len(selected) >= self.max_words:
                break
            if score > 0:  # Only include positive scoring words
                selected.append(word)
        
        # Ensure minimum words
        while len(selected) < self.min_words and sorted_words:
            added = False
            for word, _ in sorted_words:
                if word not in selected:
                    selected.append(word)
                    added = True
                    break
            # If no words were added, we can't add more
            if not added:
                break
        
        return selected
    
    def _create_name(self, words: List[str]) -> str:
        """
        Create a filesystem-safe name from words.
        
        Args:
            words: List of words to use
            
        Returns:
            Filesystem-safe name
        """
        if not words:
            return "untitled"
        
        # Join with underscores
        name = "_".join(words[:self.max_words])
        
        # Ensure filesystem safety
        name = self._make_filesystem_safe(name)
        
        return name
    
    def _make_filesystem_safe(self, name: str) -> str:
        """
        Make a name filesystem-safe.
        
        Args:
            name: Name to make safe
            
        Returns:
            Filesystem-safe name
        """
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        
        # Remove or replace problematic characters
        safe_chars = string.ascii_letters + string.digits + "_-"
        name = "".join(c if c in safe_chars else "_" for c in name)
        
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip("_")
        
        # Ensure it's not empty
        if not name:
            name = "untitled"
        
        # Limit length
        if len(name) > 50:
            name = name[:50]
        
        return name.lower()
    
    def batch_generate(self, texts: List[str]) -> List[str]:
        """
        Generate names for multiple texts.
        
        Args:
            texts: List of descriptive texts
            
        Returns:
            List of generated names
        """
        names = []
        seen_names = set()
        
        for text in texts:
            base_name = self.generate_name(text)
            
            # Handle duplicates
            name = base_name
            counter = 1
            while name in seen_names:
                name = f"{base_name}_{counter}"
                counter += 1
            
            names.append(name)
            seen_names.add(name)
        
        return names


def main():
    """Example usage of TextToNameGenerator."""
    generator = TextToNameGenerator()
    
    # Test examples
    examples = [
        "A futuristic cyberpunk city at night with neon lights and flying cars",
        "Peaceful mountain landscape at sunrise with fog in the valleys",
        "Robot arm picking up a coffee cup in a modern office",
        "Ancient temple ruins in a dense jungle during a thunderstorm",
        "Underwater coral reef scene with colorful fish swimming"
    ]
    
    print("Text-to-Name Generation Examples:")
    print("-" * 50)
    
    for text in examples:
        name = generator.generate_name(text)
        print(f"Input: {text[:60]}...")
        print(f"Name:  {name}")
        print()


if __name__ == "__main__":
    main()