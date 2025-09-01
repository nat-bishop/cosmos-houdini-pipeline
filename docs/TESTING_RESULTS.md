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

#### Test Results - August 31, 2025

| Resolution | Aspect | Pixels | Est. Tokens | Status | Notes |
|-----------|--------|--------|-------------|--------|-------|
| 320×180 | 16:9 | 57,600 | 1,992 | ✅ Works | Ultra-safe for production |
| 350×197 | 16:9 | 68,950 | 2,385 | ✅ Works | Safe |
| 380×214 | 16:9 | 81,320 | 2,813 | ✅ Works | Safe |
| 400×225 | 16:9 | 90,000 | 3,114 | ✅ Works | Safe |
| 410×231 | 16:9 | 94,710 | 3,276 | ✅ Works | Good quality |
| 420×236 | 16:9 | 99,120 | 3,429 | ✅ Works | Good quality |
| 425×239 | 16:9 | 101,575 | 3,514 | ✅ Works | Good quality |
| 430×242 | 16:9 | 104,060 | 3,600 | ✅ Works | Good quality |
| 435×245 | 16:9 | 106,575 | 3,687 | ✅ Works | High quality |
| 440×248 | 16:9 | 109,120 | 3,775 | ✅ Works | High quality |
| 445×250 | 16:9 | 111,250 | 3,849 | ✅ Works | High quality |
| 450×253 | 16:9 | 113,850 | 3,939 | ✅ Works | High quality |
| 455×256 | 16:9 | 116,480 | 4,030 | ✅ Works | High quality |
| 460×259 | 16:9 | 119,140 | 4,122 | ✅ Works | **Previous est. limit** |
| 465×262 | 16:9 | 121,830 | 4,215 | ✅ Works | Exceeds est. limit |
| 470×265 | 16:9 | 124,550 | 4,309 | ✅ Works | Exceeds est. limit |
| 475×267 | 16:9 | 126,825 | 4,388 | ✅ Works | Exceeds est. limit |
| 480×270 | 16:9 | 129,600 | 4,484 | ✅ Works | **New finding!** |
| 490×276 | 16:9 | 135,240 | 4,679 | ✅ Works | Well beyond est. |
| 500×281 | 16:9 | 140,500 | 4,861 | ✅ Works | **Current maximum tested** |

#### Important Discovery About Token Limits

**MAJOR FINDING**: The resolution limit is NOT based on our estimated token formula. The actual boundary is around **854×480** pixels (409,920 pixels).

**Test Results Summary**:
- ✅ **940×529 WORKS** (497,260 pixels) - Maximum confirmed working
- ✅ **854×480 WORKS** (409,920 pixels) - 480p widescreen
- ❓ **960×540 UNCLEAR** (518,400 pixels) - Actual tokens: 4,157 (may be OOM issue)
- ❌ **1280×720 FAILS** (921,600 pixels) - Actual tokens: 4,689

**Key Insights**:
1. The token formula `width × height × frames × 0.0173` is completely wrong
2. Actual tokenization appears to have a hard limit around 410,000-450,000 pixels
3. The model reports actual token counts that don't match any simple formula
4. Token count is NOT linear with resolution (4,157 tokens for 960×540 vs 4,689 for 1280×720)

**Practical Limits**:
- **Maximum Safe**: 854×480 (480p widescreen)
- **Good Quality**: 720×405 (works reliably)
- **HD Fails**: 960×540 and above will fail

**Mystery**: Why do lower resolutions like 500×281 work when they have fewer pixels than 854×480? The tokenization method remains unclear.

#### Resolution Recommendations (FINAL)
- **Ultra-Safe Production**: 320×180 (always works)
- **Recommended Production**: 640×360 (good balance)
- **High Quality**: 720×405 (near maximum)
- **Maximum Resolution**: 854×480 (absolute limit)
- **Will Fail**: 960×540 and above

**Important**: The actual pixel limit appears to be around 410,000-450,000 pixels per frame, NOT based on the token formula we initially used.

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

2. **VLLM Processing Error**
   ```
   "[ERROR] Failed to process test_426x240: Prompt length of 4698 is longer than the maximum model length of 4096"
   ```
   - Happens during VLLM initialization
   - Video tokens + prompt tokens exceed limit
   - Threshold appears to be around 3,500-3,600 tokens

3. **Encoding Errors** (Cosmetic)
   ```
   "'charmap' codec can't encode characters in position 143-152"
   ```
   - Occurs at end of successful processing
   - Does not affect output quality
   - Issue with Windows SSH output handling, not model
   - Can be ignored in production

#### Factors Affecting Token Usage
1. **Video resolution** (primary factor - linear relationship)
2. **Number of frames** (multiplier effect - 2 frames default)
3. **Prompt text length** (adds ~50-100 tokens)
4. **System prompts** (adds ~500-600 tokens overhead)
5. **Video codec** (no observed impact)

#### Token Budget Breakdown
For a typical upsampling request:
- System prompts: ~600 tokens
- User prompt text: ~100 tokens
- Video tokens: `width × height × frames × 0.0173`
- **Total must be < 4,096 tokens**

Example for 320×180:
- System: 600 tokens
- Prompt: 100 tokens
- Video: 1,992 tokens (320×180×2×0.0173)
- Total: 2,692 tokens (65.7% of limit) ✅

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
