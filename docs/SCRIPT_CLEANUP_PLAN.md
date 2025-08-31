# Script Cleanup and Integration Plan

## Current State Analysis

We have **28 scripts** in the scripts/ directory, many of which are duplicates, tests, or experimental versions. This is unsustainable and needs consolidation.

## Script Categories

### 1. Working/Proven Scripts
- `working_prompt_upsampler.py` - The main working upsampler that runs in cosmos-transfer1 directory
- `deploy_and_test_upsampler.py` - Deployment script that works

### 2. Test Scripts (Various Attempts)
- `test_upsampling_resolution_limits.py` - Resolution testing
- `test_token_limits.py` - Token limit testing
- `test_actual_resolution_limits.py` - Actual resolution testing
- `test_token_limit_config.py` - Token config testing
- `persistent_upsampler_test.py` - Testing without model reload
- `remote_resolution_test.py` - Remote GPU testing
- Multiple others: `batch_token_test.py`, `simple_token_tests.py`, `quick_token_check.py`, etc.

### 3. Deployment Scripts
- `deploy_resolution_test.py` - Deploys tests to remote
- `deploy_and_test_upsampler.py` - Original deployment
- `check_remote_results.py` - Checks remote results

### 4. Different Approaches
- `nvidia_style_upsampler.py` - NVIDIA's approach
- `standalone_upsampler.py` - Standalone version
- `simple_prompt_upsampler.py` - Simplified version
- `force_spawn_upsampler.py` - With spawn workaround

## Problems to Solve

1. **Too many scripts** - Confusing and unmaintainable
2. **Scripts require cosmos-transfer1 directory** - Not integrated with our workflow
3. **Manual deployment** - No automatic copying to remote
4. **No unified testing framework** - Each script tests differently
5. **Results not integrated** - Test results aren't fed back into the workflow

## Proposed Clean Architecture

```
cosmos_workflow/
├── upsampling/
│   ├── __init__.py
│   ├── upsampler.py           # Core upsampling logic
│   ├── resolution.py          # Resolution validation & token estimation
│   ├── batch_processor.py     # Batch processing with checkpoints
│   └── tests/
│       ├── test_resolutions.py
│       └── test_token_limits.py
│
├── workflows/
│   └── upsampling_workflow.py # Integrated workflow
│
└── cli.py                      # CLI commands
```

## Integration Plan

### Phase 1: Core Module (cosmos_workflow/upsampling/)

```python
# cosmos_workflow/upsampling/upsampler.py
class PromptUpsampler:
    """Unified prompt upsampler with configurable token limits."""

    def __init__(self, max_model_len: int = 4096):
        self.max_model_len = max_model_len
        self.model = None

    def estimate_tokens(self, width: int, height: int, frames: int = 2) -> int:
        """Estimate token usage for given resolution."""
        return int(width * height * frames * 0.0173)

    def validate_resolution(self, video_path: Path) -> tuple[bool, int, str]:
        """Check if video resolution is within token limits."""
        # Extract resolution
        # Calculate tokens
        # Return (is_valid, token_count, message)

    def upsample_prompt(self, prompt: str, video_path: Path) -> str:
        """Upsample a single prompt with video context."""
        # Validate resolution
        # Generate hint video if needed
        # Run upsampling
        # Return enhanced prompt
```

### Phase 2: Resolution Management

```python
# cosmos_workflow/upsampling/resolution.py
class ResolutionManager:
    """Manages resolution validation and hint video generation."""

    NVIDIA_RESOLUTIONS = {
        "720p": {"16:9": (1280, 704), "4:3": (960, 704), ...},
        "512p": {...},
        "256p": {...}
    }

    MAX_SAFE_RESOLUTION = (320, 180)  # For 4096 token limit

    def create_hint_video(self, input_video: Path, output_dir: Path) -> Path:
        """Create low-res hint video for upsampling."""
        # Resize to MAX_SAFE_RESOLUTION
        # Return path to hint video

    def get_optimal_resolution(self, video_path: Path, max_tokens: int) -> tuple[int, int]:
        """Calculate optimal resolution within token budget."""
```

### Phase 3: Batch Processing

```python
# cosmos_workflow/upsampling/batch_processor.py
class BatchUpsampleProcessor:
    """Process multiple prompts with checkpoint recovery."""

    def __init__(self, checkpoint_file: Path = None):
        self.checkpoint = self.load_checkpoint(checkpoint_file)
        self.upsampler = PromptUpsampler()

    def process_batch(self, prompt_specs: list[PromptSpec]) -> list[PromptSpec]:
        """Process batch with automatic resolution handling."""
        results = []

        for spec in prompt_specs:
            # Check if already processed
            if spec.id in self.checkpoint['completed']:
                continue

            # Validate resolution
            # Create hint video if needed
            # Upsample prompt
            # Update checkpoint
            # Add to results

        return results
```

### Phase 4: Workflow Integration

```python
# cosmos_workflow/workflows/upsampling_workflow.py
class UpsamplingWorkflow:
    """Complete upsampling workflow with remote execution."""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.ssh_manager = SSHManager(config_manager.get_ssh_options())

    def run_upsampling_pipeline(
        self,
        prompt_specs: list[PromptSpec],
        max_model_len: int = 4096,
        auto_resize: bool = True
    ) -> list[PromptSpec]:
        """Run complete upsampling pipeline."""

        # Step 1: Validate all resolutions locally
        validation_results = self.validate_batch(prompt_specs)

        # Step 2: Generate hint videos for high-res inputs
        if auto_resize:
            self.generate_hint_videos(validation_results['needs_resize'])

        # Step 3: Deploy to remote
        self.deploy_to_remote(prompt_specs)

        # Step 4: Execute on GPU
        results = self.execute_remote_upsampling(max_model_len)

        # Step 5: Retrieve results
        upsampled_specs = self.retrieve_results(results)

        return upsampled_specs
```

### Phase 5: CLI Integration

```python
# Add to cosmos_workflow/cli.py

@cli.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.option("--max-tokens", default=4096, help="Maximum token limit")
@click.option("--auto-resize", is_flag=True, help="Auto-generate hint videos")
@click.option("--test-mode", is_flag=True, help="Test resolutions without upsampling")
def upsample_batch(input_dir, max_tokens, auto_resize, test_mode):
    """Batch upsample prompts with automatic resolution handling."""

    workflow = UpsamplingWorkflow(config_manager)

    # Load prompt specs
    specs = load_prompt_specs(input_dir)

    if test_mode:
        # Just test resolutions
        results = workflow.test_resolutions(specs, max_tokens)
        print_resolution_report(results)
    else:
        # Run full upsampling
        upsampled = workflow.run_upsampling_pipeline(
            specs,
            max_model_len=max_tokens,
            auto_resize=auto_resize
        )
        save_upsampled_specs(upsampled)
```

## Migration Steps

### Step 1: Create Core Modules
1. Create `cosmos_workflow/upsampling/` directory
2. Extract working logic from `working_prompt_upsampler.py`
3. Add resolution validation from test scripts
4. Implement batch processing

### Step 2: Test Locally
1. Test token estimation accuracy
2. Verify hint video generation
3. Test checkpoint/recovery

### Step 3: Remote Integration
1. Update deployment to use new modules
2. Test remote execution
3. Verify result retrieval

### Step 4: Clean Up
1. Move working scripts to `archive/` directory
2. Delete redundant/broken scripts
3. Update documentation

## Benefits of This Approach

1. **Single source of truth** - One upsampling module
2. **Integrated with workflow** - Part of main system
3. **Automatic deployment** - No manual copying
4. **Proper testing** - Unit tests for each component
5. **Configuration-driven** - Uses config.toml
6. **Recoverable** - Checkpoint support
7. **Observable** - Logging and progress tracking

## Testing Strategy

### Unit Tests
```python
def test_token_estimation():
    """Test token calculation accuracy."""
    assert estimate_tokens(320, 180, 2) == 1991
    assert estimate_tokens(1280, 720, 2) == 31918

def test_resolution_validation():
    """Test resolution validation."""
    assert validate_resolution((320, 180), 4096) == True
    assert validate_resolution((1280, 720), 4096) == False

def test_hint_video_generation():
    """Test hint video creation."""
    # Test video is resized correctly
    # Test aspect ratio preserved
```

### Integration Tests
- Test full pipeline with small batch
- Test checkpoint recovery
- Test remote execution
- Test error handling

## Next Actions

1. **Immediate**: Create `cosmos_workflow/upsampling/` module structure
2. **Today**: Port working logic from scripts
3. **Tomorrow**: Test integrated workflow
4. **This Week**: Clean up scripts directory
5. **Document**: Update README with new workflow
