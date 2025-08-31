# Batch Upsampling Integration Plan

## Executive Summary

This document outlines the complete integration plan for batch prompt upsampling in the Cosmos workflow system. Based on our investigation, we've identified critical resolution limits (320x180 max safe) and have multiple working scripts to consolidate into a unified system.

## Current State Analysis

### ✅ What We Have Working

1. **Schema Fix Completed**: Added `metadata` field to `PromptSpec`
2. **Multiple Test Scripts**:
   - `working_prompt_upsampler.py` - Batch processing with VLLM
   - `nvidia_style_upsampler.py` - NVIDIA's approach
   - `test_upsampling_resolution_limits.py` - Resolution testing
   - `deploy_and_test_upsampler.py` - Remote deployment
3. **Partial Integration**: `UpsampleWorkflowMixin` in `cosmos_workflow/workflows/upsample_integration.py`
4. **Known Limits**: 320x180 @ 2 frames = ~2000 tokens (safe under 4096 limit)

### ❌ What's Missing

1. Token estimation before processing
2. Automatic hint video generation
3. Batch checkpoint/recovery system
4. CLI command for batch upsampling
5. Resolution validation
6. Progress tracking

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Entry Point                        │
│         python -m cosmos_workflow.cli batch-upsample     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Batch Upsample Manager                      │
│  • Load PromptSpecs from directory                       │
│  • Validate resolutions & estimate tokens                │
│  • Generate hint videos if needed                        │
│  • Create batches within token limits                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            Resolution Preprocessor                       │
│  • Check video resolution                                │
│  • If > 320x180: create hint video                       │
│  • Token estimation: w × h × frames × 0.0173             │
│  • Validate under 4096 limit                             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           Remote Execution Pipeline                      │
│  • Transfer batch JSON + videos via SFTP                 │
│  • Execute Docker container on GPU                       │
│  • Monitor progress                                      │
│  • Retrieve upsampled results                            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│             Result Processing                            │
│  • Update PromptSpec metadata                            │
│  • Mark as upsampled                                     │
│  • Save enhanced prompts                                 │
│  • Generate summary report                               │
└─────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Core Components (Week 1)

#### 1.1 Token Estimation Module
```python
# cosmos_workflow/upsampling/token_estimator.py
class TokenEstimator:
    MAX_TOKENS = 4096
    TOKEN_FACTOR = 0.0173

    def estimate_tokens(self, width: int, height: int, frames: int) -> int:
        """Estimate token usage for given resolution."""
        return int(width * height * frames * self.TOKEN_FACTOR)

    def is_safe_resolution(self, width: int, height: int, frames: int = 2) -> bool:
        """Check if resolution is under token limit."""
        tokens = self.estimate_tokens(width, height, frames)
        return tokens < self.MAX_TOKENS * 0.9  # 10% safety margin
```

#### 1.2 Hint Video Generator
```python
# cosmos_workflow/upsampling/hint_video.py
class HintVideoGenerator:
    SAFE_RESOLUTION = (320, 180)

    def generate_hint_video(
        self,
        input_video: Path,
        output_dir: Path,
        frames: int = 2,
        fps: int = 2
    ) -> Path:
        """Generate low-res hint video for upsampling."""
        # Use ffmpeg to resize to 320x180
        # Extract specified frames
        # Return path to hint video
```

#### 1.3 Batch Processor
```python
# cosmos_workflow/upsampling/batch_processor.py
class BatchUpsampleProcessor:
    def __init__(self, checkpoint_file: Path = None):
        self.checkpoint = self.load_checkpoint(checkpoint_file)
        self.processed = set()
        self.failed = []

    def process_batch(
        self,
        prompt_specs: list[PromptSpec],
        max_batch_size: int = 10
    ) -> dict:
        """Process prompts in batches with checkpointing."""
        # Group by token usage
        # Process each batch
        # Save checkpoint after each batch
        # Handle failures gracefully
```

### Phase 2: CLI Integration (Week 1-2)

#### 2.1 New CLI Commands
```python
# Add to cosmos_workflow/cli.py

@cli.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.option("--output-dir", default="outputs/upsampled")
@click.option("--auto-resize", is_flag=True, help="Auto-generate hint videos")
@click.option("--max-resolution", default="320x180")
@click.option("--batch-size", default=10)
@click.option("--resume", type=click.Path(), help="Resume from checkpoint")
def batch_upsample(input_dir, output_dir, auto_resize, max_resolution, batch_size, resume):
    """Batch upsample prompts with automatic resolution handling."""
    processor = BatchUpsampleProcessor(checkpoint_file=resume)

    # Load all PromptSpecs
    specs = load_prompt_specs(input_dir)

    # Process with progress bar
    with click.progressbar(specs) as bar:
        for spec in bar:
            if auto_resize:
                ensure_safe_resolution(spec)
            processor.process(spec)
```

#### 2.2 Integration with Existing Commands
```python
# Modify create-spec command to add --upsample flag
@cli.command("create-spec")
@click.option("--upsample", is_flag=True, help="Upsample after creation")
def create_spec(..., upsample):
    spec = create_prompt_spec(...)
    if upsample:
        upsampler.process_single(spec)
```

### Phase 3: Workflow Integration (Week 2)

#### 3.1 Enhanced WorkflowOrchestrator
```python
# cosmos_workflow/workflows/workflow_orchestrator.py
class WorkflowOrchestrator:
    def run_complete_pipeline(
        self,
        prompt_specs: list[PromptSpec],
        upsample: bool = True,
        auto_resize: bool = True
    ):
        """Run complete pipeline with optional upsampling."""

        # Step 1: Prepare videos
        if auto_resize:
            self.prepare_hint_videos(prompt_specs)

        # Step 2: Upsample prompts
        if upsample:
            upsampled = self.batch_upsample(prompt_specs)
            prompt_specs = upsampled

        # Step 3: Run inference
        results = self.run_inference(prompt_specs)

        return results
```

#### 3.2 Progress Tracking
```python
# cosmos_workflow/upsampling/progress.py
class UpsampleProgress:
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = []
        self.start_time = time.time()

    def update(self, spec_id: str, success: bool):
        """Update progress for a spec."""
        if success:
            self.completed += 1
        else:
            self.failed.append(spec_id)

    @property
    def eta(self) -> float:
        """Estimate time remaining."""
        # Calculate based on average processing time
```

### Phase 4: Testing & Validation (Week 2-3)

#### 4.1 Resolution Testing
```bash
# Test on remote GPU
python scripts/test_upsampling_resolution_limits.py \
    --remote --gpu \
    --resolutions 256x144,320x180,400x225,480x270 \
    --output-dir test_results/
```

#### 4.2 Batch Processing Tests
```python
# tests/integration/test_batch_upsampling.py
def test_batch_processing():
    """Test batch upsampling with various resolutions."""
    specs = create_test_specs([
        (320, 180),  # Safe
        (480, 270),  # Borderline
        (640, 480),  # Should trigger hint video
    ])

    processor = BatchUpsampleProcessor()
    results = processor.process_batch(specs, auto_resize=True)

    assert all(r.is_upsampled for r in results)
```

#### 4.3 Recovery Testing
```python
def test_checkpoint_recovery():
    """Test resuming from checkpoint after failure."""
    # Simulate failure midway
    # Resume from checkpoint
    # Verify only remaining items processed
```

## Configuration Updates

### config.toml Additions
```toml
[upsampling]
max_tokens = 4096
safe_resolution = "320x180"
frames_to_extract = 2
fps_for_hints = 2
batch_size = 10
auto_resize = true
checkpoint_dir = "./checkpoints"

[upsampling.docker]
num_gpu = 1
cuda_devices = "0"
offload_models = true
```

## Error Handling Strategy

1. **Token Limit Errors**
   - Pre-validate before sending to GPU
   - Auto-generate hint videos
   - Log warnings with recommendations

2. **Video Processing Errors**
   - Fallback to lower resolution
   - Skip corrupted videos
   - Continue with remaining batch

3. **Remote Execution Errors**
   - Automatic retry with exponential backoff
   - Save checkpoint before retry
   - Report failed items for manual review

## Performance Optimization

1. **Batch Optimization**
   - Group prompts by total token usage
   - Process multiple prompts per GPU run
   - Minimize file transfers

2. **Caching**
   - Cache hint videos
   - Reuse upsampled prompts
   - Store token estimates

3. **Parallel Processing**
   - Generate hint videos in parallel
   - Transfer files concurrently
   - Process independent batches simultaneously

## Success Metrics

- [ ] Process 100+ prompts in single batch
- [ ] Automatic resolution handling (no manual intervention)
- [ ] <5% failure rate on standard videos
- [ ] Recovery from interruption without data loss
- [ ] Clear progress reporting with ETA
- [ ] Average processing time <30s per prompt

## Timeline

### Week 1 (Current)
- [x] Fix PromptSpec schema
- [ ] Implement token estimation
- [ ] Create hint video generator
- [ ] Build batch processor core

### Week 2
- [ ] CLI integration
- [ ] Workflow orchestrator updates
- [ ] Progress tracking
- [ ] Initial testing

### Week 3
- [ ] Remote GPU testing
- [ ] Performance optimization
- [ ] Documentation
- [ ] Final integration testing

## Next Immediate Steps

1. Choose best approach from existing scripts
2. Implement token estimation module
3. Create hint video generator
4. Build batch processor with checkpointing
5. Test on remote GPU with various resolutions

## References

- Investigation: `docs/UPSAMPLING_RESOLUTION_INVESTIGATION.md`
- Existing scripts: `scripts/working_prompt_upsampler.py`
- Integration code: `cosmos_workflow/workflows/upsample_integration.py`
- Token limits: 4096 (Pixtral-12B)
- Safe resolution: 320x180 @ 2 frames
