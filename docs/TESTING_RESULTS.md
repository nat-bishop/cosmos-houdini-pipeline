# Testing Documentation - Cosmos Transfer1 Workflow

## Overview
This document contains comprehensive testing results for the Cosmos Transfer1 workflow orchestrator, including performance benchmarks, resource usage analysis, and error boundary testing.

## Table of Contents
- [Prompt Upsampling Tests](#prompt-upsampling-tests)
  - [Batch Processing Performance](#batch-processing-performance)
  - [Resolution Limits](#resolution-limits)
  - [GPU Memory Usage](#gpu-memory-usage)
- [Inference Model Tests](#inference-model-tests) *(Coming Soon)*
- [Upscaling Tests](#upscaling-tests) *(Coming Soon)*

---

## Prompt Upsampling Tests

### Test Environment
- **Date**: August 31, 2025
- **GPU**: NVIDIA A10 (24GB VRAM)
- **Model**: Cosmos-UpsamplePrompt1-12B-Transfer (Pixtral)
- **Model Size**: 23.6GB
- **Docker Image**: `nvcr.io/ubuntu/cosmos-transfer1:latest`
- **VLLM Version**: 0.8.1+5f4af9e0.nv25.04

### Batch Processing Performance

#### Test Setup
- **Video Resolution**: 320×180 (safe resolution)
- **Batch Size**: 3 prompts
- **Test Scenarios**: With and without model offloading

#### Results Summary

| Configuration | Total Time | Per Prompt | Model Load Time | Inference Time | Memory Usage |
|--------------|------------|------------|-----------------|----------------|--------------|
| **With Offloading** | 250.71s | 83.57s | 13.2s × 3 | ~34s each | ~1GB idle |
| **Without Offloading** | 138.28s | 46.09s | 13.3s × 1 | ~14s each | 23.6GB constant |
| **Performance Gain** | **45% faster** | **45% faster** | **66% reduction** | **59% faster** | - |

#### Detailed Timing Breakdown

**With Offloading (Default)**
```
Prompt 1: 112s total (98.32s init + ~14s inference)
Prompt 2: 47s total (32.99s init + ~14s inference)
Prompt 3: 47s total (33.19s init + ~14s inference)
Total: 250.71s
```

**Without Offloading (`--no-offload`)**
```
Initial Load: 97.24s (one-time)
Prompt 1: ~14s inference
Prompt 2: ~14s inference
Prompt 3: ~14s inference
Total: 138.28s
```

#### Key Findings
1. **First prompt initialization** always takes ~97-98s due to:
   - Model loading: ~13s
   - torch.compile optimization: ~38s
   - Graph capturing: ~22s
   - KV cache initialization: remaining time

2. **Subsequent prompts with offloading** are faster (~33s init) because:
   - torch.compile cache is reused
   - Only model loading and graph capturing needed

3. **Without offloading** provides significant speedup for batches:
   - 45% faster overall execution
   - Model stays in VRAM between prompts
   - No repeated initialization overhead

### Resolution Limits

#### Test Methodology
Using the token estimation formula: `tokens = width × height × frames × 0.0173`

#### Working Resolutions

| Resolution | Aspect | Pixels | Tokens (2 frames) | Status | Notes |
|-----------|--------|--------|-------------------|--------|-------|
| 160×90 | 16:9 | 14,400 | 498 | ✅ Safe | Minimal quality |
| 240×135 | 16:9 | 32,400 | 1,121 | ✅ Safe | Low quality |
| 320×180 | 16:9 | 57,600 | 1,992 | ✅ Safe | **Recommended** |
| 426×240 | 16:9 | 102,240 | 3,537 | ✅ Works | Near limit |
| 480×270 | 16:9 | 129,600 | 4,484 | ❌ Fails | Exceeds 4096 |

#### Failed Resolutions

| Resolution | Tokens | Error Message |
|-----------|--------|---------------|
| 1280×704 | 31,191 | "Prompt length of 4699 is longer than the maximum model length of 4096" |
| 720×405 | 10,092 | Vocab size error (exceeds token limit) |
| 640×360 | 7,966 | Vocab size error (exceeds token limit) |

#### Maximum Safe Resolution
- **320×180 @ 2 frames** = 1,992 tokens (48.6% of limit)
- **426×240 @ 2 frames** = 3,537 tokens (86.3% of limit) - works but risky
- Safety margin recommended: Stay under 2,000 tokens

### GPU Memory Usage

#### Test Configuration
- **GPU**: NVIDIA A10 (24GB VRAM)
- **Base System Usage**: ~2GB
- **Available for Models**: ~22GB

#### Memory Profiles

| Scenario | VRAM Usage | Details |
|----------|------------|---------|
| **Idle State** | 2GB | System + Docker overhead |
| **Model Loaded** | 25.6GB | Full model in memory |
| **With Offloading** | 2GB → 25.6GB → 2GB | Cycles per prompt |
| **Without Offloading** | 25.6GB constant | Model stays loaded |
| **During Inference** | +0.5-1GB | Additional working memory |

#### Batch Size Limits *(To Be Tested)*

Estimated safe batch sizes based on memory:
- **With Offloading**: Unlimited (processes sequentially)
- **Without Offloading**:
  - 1 model instance: Unlimited prompts
  - Memory limit: ~22GB available
  - Practical limit: To be determined

### Error Analysis

#### Vocabulary Size Errors

**Error Types Observed:**

1. **Token Length Error** (Most Common)
   ```
   "Prompt length of 4699 is longer than the maximum model length of 4096"
   ```
   - Occurs when video resolution too high
   - Token count exceeds model's context window
   - Solution: Reduce video resolution to ≤320×180

2. **Encoding Errors** (Cosmetic)
   ```
   "'charmap' codec can't encode characters in position 143-152"
   ```
   - Occurs at end of successful processing
   - Does not affect output quality
   - Issue with SSH output handling, not model

#### Factors Affecting Token Usage
1. **Video resolution** (primary factor)
2. **Number of frames** (multiplier effect)
3. **Prompt text length** (minimal impact)
4. **Video codec** (no observed impact)

---

## Test Scripts

### Batch Performance Test
```bash
# With offloading (default)
python /workspace/scripts/working_prompt_upsampler.py \
    --batch /workspace/test_batch.json \
    --output-dir /workspace/outputs/batch_offload

# Without offloading
python /workspace/scripts/working_prompt_upsampler.py \
    --batch /workspace/test_batch.json \
    --output-dir /workspace/outputs/batch_no_offload \
    --no-offload
```

### Resolution Testing
```python
# See cosmos_workflow/workflows/resolution_tester.py
from cosmos_workflow.workflows.resolution_tester import ResolutionTest

test = ResolutionTest(width=320, height=180, frames=2)
print(f"Tokens: {test.estimated_tokens()}")  # 1,992
print(f"Safe: {test.is_safe()}")  # True
```

---

## Recommendations

### For Production Use

1. **Video Preprocessing**
   - Always resize videos to 320×180 before upsampling
   - Use ffmpeg: `ffmpeg -i input.mp4 -vf scale=320:180 output.mp4`

2. **Batch Processing Strategy**
   - For single prompts: Use default (with offloading)
   - For 2+ prompts: Use `--no-offload` for 45% speedup
   - Monitor GPU memory if processing large batches

3. **Error Handling**
   - Implement automatic video resizing for high-res inputs
   - Add token estimation before processing
   - Handle encoding errors gracefully

### Performance Optimization

1. **First-Run Optimization**
   - Keep model loaded for subsequent runs
   - Cache torch.compile artifacts
   - Warm up with dummy prompt if needed

2. **Memory Management**
   - Use offloading for memory-constrained environments
   - Monitor VRAM usage during batch processing
   - Implement batch size limits based on available memory

---

## Future Testing Plans

### Upcoming Tests
- [ ] Maximum batch size without OOM errors
- [ ] Impact of prompt text length on tokens
- [ ] Multi-frame video token scaling
- [ ] Different video codecs impact
- [ ] Concurrent processing capabilities
- [ ] Model warmup strategies

### Inference Model Tests *(Section Reserved)*
- Performance benchmarks
- Control modality impact
- Multi-GPU scaling
- Distilled vs full model comparison

### Upscaling Tests *(Section Reserved)*
- Resolution scaling performance
- Quality metrics
- Processing time analysis

---

## Test Log

### August 31, 2025
- Initial batch processing tests completed
- Resolution limits identified
- Memory profiling conducted
- Documentation created

---

*Last Updated: August 31, 2025*
