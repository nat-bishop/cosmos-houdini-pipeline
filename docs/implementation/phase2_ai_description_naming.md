# Phase 2 Implementation: AI-Powered Description and Smart Naming

## Overview

Phase 2 introduces AI-powered scene analysis and intelligent naming capabilities to the Cosmos workflow system. This feature automatically generates meaningful descriptions of video content and creates concise, descriptive names for output directories.

## Implementation Date
**Completed:** August 30, 2025

## Key Features

### 1. AI Scene Description Generation
- **Model:** BLIP (Bootstrapping Language-Image Pre-training) from Salesforce
- **Model Size:** ~400MB (downloaded and cached on first use)
- **Input:** Middle frame from video sequence
- **Output:** Natural language description of scene content

### 2. Smart Name Generation Algorithm
- Extracts meaningful words from AI descriptions
- Removes common stop words (a, the, with, etc.)
- Prioritizes nouns and action words (words ending in -ing, -tion, etc.)
- Limits names to 20 characters maximum
- Ensures valid filesystem naming (alphanumeric + underscores only)

### 3. Directory Naming Format
- Format: `{name}_{YYYYMMDD_HHMMSS}`
- Example: `modern_staircase_20250830_163604`
- Name is auto-generated from AI description if not provided
- Timestamp ensures uniqueness

## Files Modified

### Core Implementation Files

#### 1. `cosmos_workflow/local_ai/cosmos_sequence.py`
**Changes:**
- Added `_generate_smart_name()` method to `CosmosVideoConverter` class
- Enhanced `generate_metadata()` to support optional name parameter
- Updated `convert_sequence()` to auto-generate names when not provided
- Integrated AI description generation with smart naming

**Key Methods:**
```python
def _generate_smart_name(self, description: str, max_length: int = 20) -> str:
    """Generate a short, meaningful name from an AI description."""

def generate_metadata(self, sequence_info, output_dir, name=None, description=None, use_ai=True):
    """Generate metadata with optional AI-powered naming."""
```

#### 2. `cosmos_workflow/cli.py`
**Changes:**
- Made `--name` parameter optional in `prepare-inference` command
- Updated help text to reflect AI capabilities
- Modified `prepare_inference()` function signature

**Command Usage:**
```bash
# AI auto-generates name and description
python -m cosmos_workflow.cli prepare-inference ./renders/sequence/

# Provide custom name, AI generates description
python -m cosmos_workflow.cli prepare-inference ./renders/sequence/ --name my_scene

# Disable AI entirely
python -m cosmos_workflow.cli prepare-inference ./renders/sequence/ --no-ai
```

#### 3. `requirements.txt`
**Added Dependencies:**
```
transformers>=4.30.0  # For BLIP model
torch>=2.0.0         # PyTorch backend
torchvision>=0.15.0  # Image processing
pillow>=9.5.0        # PIL Image support
accelerate>=0.20.0   # Model optimization
```

## Test Files

### 1. `tests/test_ai_functionality.py` (Unit Tests)
**Coverage:** 14 tests
- Smart name generation with various inputs
- AI description mocking and fallback behavior
- Metadata generation workflow
- Directory naming format compliance

**Test Classes:**
- `TestSmartNameGeneration` - Algorithm behavior
- `TestAIDescriptionGeneration` - Model integration
- `TestIntegratedAIWorkflow` - End-to-end workflow
- `TestDirectoryNaming` - Format compliance

### 2. `tests/test_ai_integration.py` (Integration Tests)
**Coverage:** 13 tests
- Real AI model loading and inference
- Description generation with actual images
- Performance testing with multiple frames
- Various scene type testing (urban, nature, abstract)

**Test Classes:**
- `TestAIIntegration` - Real model tests
- `TestSmartNameAlgorithm` - Detailed algorithm tests
- `TestDirectoryNamingCompliance` - Format validation

### 3. Test Helper Scripts
- `test_ai_real.py` - Direct AI model testing
- `test_ai_with_image.py` - Generate test image and verify

## Algorithm Details

### Smart Name Generation Process

1. **Input Processing:**
   - Convert description to lowercase
   - Extract all words using regex

2. **Stop Word Removal:**
   - Remove common English stop words
   - List includes: a, an, the, in, on, at, with, for, of, etc.

3. **Word Prioritization:**
   - Words with meaningful suffixes get priority:
     - `-ing` (action words): walking, running, jumping
     - `-tion`: decoration, celebration
     - `-ment`: movement, arrangement
     - Other noun/adjective indicators

4. **Selection and Truncation:**
   - Select top 3 most meaningful words
   - Join with underscores
   - Truncate to max_length (default 20 chars)
   - Preserve whole words when possible

5. **Validation:**
   - Remove any non-alphanumeric characters (except underscores)
   - Default to "sequence" if no valid name generated

### Examples

| AI Description | Generated Name |
|---------------|----------------|
| "a modern staircase with dramatic lighting" | `modern_staircase` |
| "a red car driving on a highway" | `driving_red_car` |
| "a person walking in a park" | `walking_person_park` |
| "a futuristic city skyline at night" | `city_futuristic` |
| "a red house with a tree and a sun" | `red_house_tree` |

## Performance Characteristics

### Model Loading
- **First Run:** ~5-10 seconds (downloading model)
- **Subsequent Runs:** ~1-2 seconds (cached model)
- **Model Cache Location:** `~/.cache/huggingface/`

### Inference Speed
- **Single Frame:** ~0.5-1 second
- **Multiple Frames:** Uses middle frame only (same speed)
- **Batch Processing:** Not implemented (uses single inference)

### Memory Usage
- **Model Size:** ~400MB in memory
- **GPU:** Optional, falls back to CPU
- **Offloading:** Not currently implemented

## Error Handling

### Graceful Fallbacks
1. **No transformers installed:** Falls back to "Sequence with N frames"
2. **Model loading fails:** Uses default description
3. **Invalid image:** Returns default description
4. **AI error:** Catches and logs, returns default

### Default Behaviors
- **Default Description:** "Sequence with {frame_count} frames"
- **Default Name:** "sequence"
- **Always Maintains:** Directory format compliance

## Usage Examples

### Basic Usage
```python
from cosmos_workflow.local_ai.cosmos_sequence import CosmosVideoConverter

converter = CosmosVideoConverter()

# Auto-generate everything
metadata = converter.generate_metadata(
    sequence_info=sequence_info,
    output_dir=output_dir,
    name=None,  # AI generates
    description=None,  # AI generates
    use_ai=True
)
```

### CLI Usage
```bash
# Minimal command - AI does everything
python -m cosmos_workflow.cli prepare-inference ./renders/v3/

# Output:
# Generated AI description: 'a modern architectural interior with stairs'
# Generated smart name: 'modern_architectural'
# Output directory: ./outputs/modern_architectural_20250830_163604/
```

## Testing Results

### Unit Tests (test_ai_functionality.py)
- **Total:** 14 tests
- **Passed:** 13
- **Skipped:** 1 (complex mocking requirement)
- **Coverage:** Smart naming, fallback behavior, format compliance

### Integration Tests (test_ai_integration.py)
- **Total:** 13 tests
- **Passed:** 13
- **Failed:** 0
- **Coverage:** Real model loading, actual inference, performance

### Combined Test Suite
- **Total Tests:** 27
- **Passed:** 26
- **Skipped:** 1
- **Success Rate:** 96.3%

## Known Limitations

1. **Model Size:** Requires ~400MB download on first use
2. **Processing Speed:** ~1 second per description
3. **Name Length:** Limited to 20 characters
4. **Language:** English only (BLIP model limitation)
5. **Frame Selection:** Only analyzes middle frame

## Future Enhancements

1. **Batch Processing:** Process multiple sequences efficiently
2. **Custom Models:** Support for other captioning models
3. **Multi-frame Analysis:** Analyze multiple frames for better descriptions
4. **Language Support:** Multi-language descriptions and names
5. **GPU Optimization:** Better GPU utilization for faster inference
6. **Caching:** Cache descriptions for identical frames
7. **User Preferences:** Configurable naming preferences

## Configuration

Currently, AI features are controlled by CLI flags:
- `--no-ai` - Disable AI features
- `--name` - Override auto-generated name
- `--description` - Override auto-generated description

Future configuration file support planned for:
- Model selection
- Name generation preferences
- Max name length
- Stop word customization
- GPU/CPU selection

## Troubleshooting

### Common Issues

1. **"Could not load AI models"**
   - Solution: Install transformers and torch
   - Command: `pip install -r requirements.txt`

2. **"vocab out of range" error**
   - Issue: Known BLIP tokenizer issue with certain inputs
   - Solution: Falls back to default description automatically

3. **Slow first run**
   - Issue: Model downloading from Hugging Face
   - Solution: Wait for download, subsequent runs will be fast

4. **Unicode errors on Windows**
   - Issue: Console encoding
   - Solution: Use text labels instead of emoji in output

## API Reference

### CosmosVideoConverter Methods

```python
def _generate_ai_description(self, color_frames: List[Path]) -> str:
    """
    Generate AI description from color frames.

    Args:
        color_frames: List of paths to color frames

    Returns:
        Generated description or fallback
    """

def _generate_smart_name(self, description: str, max_length: int = 20) -> str:
    """
    Generate a short, meaningful name from an AI description.

    Args:
        description: AI-generated description
        max_length: Maximum length for the name

    Returns:
        Smart name derived from description
    """

def generate_metadata(
    self,
    sequence_info: CosmosSequenceInfo,
    output_dir: Path,
    name: Optional[str] = None,
    description: Optional[str] = None,
    use_ai: bool = True
) -> CosmosMetadata:
    """
    Generate metadata for the sequence with optional AI.

    Args:
        sequence_info: Validated sequence information
        output_dir: Directory containing videos
        name: Optional name (AI-generated if None)
        description: Optional description (AI-generated if None)
        use_ai: Whether to use AI features

    Returns:
        CosmosMetadata object with all information
    """
```

## Conclusion

Phase 2 successfully adds intelligent, context-aware naming to the Cosmos workflow system. The implementation is robust, well-tested, and provides meaningful value to users by automatically organizing their renders with descriptive names based on actual content analysis.
