# Final Resolution Limits for Cosmos Transfer1 Prompt Upsampling

## Executive Summary
After extensive testing on September 1, 2025, we've determined the actual resolution limits for the NVIDIA Cosmos Transfer1 prompt upsampling model are **significantly higher** than initially believed.

## Key Findings

### Maximum Working Resolution
- **940×529** (497,260 pixels) - CONFIRMED WORKING
- This is **3x higher** than the initially believed limit of 320×180

### Resolution Boundaries
| Resolution | Pixels | Status | Notes |
|-----------|--------|--------|-------|
| 320×180 | 57,600 | ✅ Works | Ultra-safe baseline |
| 640×360 | 230,400 | ✅ Works | Good balance |
| 854×480 | 409,920 | ✅ Works | 480p widescreen |
| 940×529 | 497,260 | ✅ Works | **Maximum confirmed** |
| 960×540 | 518,400 | ❓ Unclear | Boundary case |
| 1280×720 | 921,600 | ❌ Fails | Exceeds limits |

### Token Formula is Wrong
The documented formula `width × height × frames × 0.0173` is **completely incorrect**:
- 960×540 reports **4,157 actual tokens** (not 17,936 estimated)
- 1280×720 reports **4,689 actual tokens** (not 31,887 estimated)
- The actual limit appears to be based on pixel count, not our formula
- Threshold is around 497,000-518,000 pixels

## Production Recommendations

### Resolution Guidelines
1. **Ultra-Safe**: 320×180 (always works, fastest)
2. **Recommended**: 640×360 (good quality/speed balance)
3. **High Quality**: 854×480 (480p widescreen)
4. **Maximum**: 940×529 (use with caution)
5. **Avoid**: 960×540 and above

### Memory Management
- **With offloading** (default): Safer for high resolutions
- **Without offloading** (`--no-offload`): 45% faster for batches but can cause OOM
- Use offloading for resolutions above 854×480

### Batch Processing Performance
| Configuration | Speed | Memory | Use Case |
|--------------|-------|--------|----------|
| With Offloading | Baseline | ~1GB idle | High resolutions, safety |
| No Offloading | 45% faster | 23.6GB constant | Batch processing, lower res |

## Technical Details

### Why the Token Formula Fails
1. Video tokenization is **non-linear** with resolution
2. Likely uses adaptive compression or sampling
3. May process fewer frames than input
4. Could have internal optimizations we're unaware of

### Error Patterns
- **Token Limit Error**: "Prompt length of X is longer than the maximum model length of 4096"
- **OOM Error**: Occurs with `--no-offload` at high resolutions
- **Encoding Error**: Windows SSH output issue (fixed in ssh_manager.py)

## Implementation Notes

### Video Preprocessing
```bash
# Resize video to safe resolution
ffmpeg -i input.mp4 -vf scale=854:480 output.mp4

# Or maximum quality
ffmpeg -i input.mp4 -vf scale=940:529 output.mp4
```

### Checking Resolution Safety
```python
def is_resolution_safe(width, height):
    pixels = width * height
    # Conservative limit
    if pixels <= 409920:  # 854×480
        return True, "Safe"
    # Experimental limit
    elif pixels <= 497260:  # 940×529
        return True, "Experimental - use with caution"
    else:
        return False, "Exceeds limits"
```

## Historical Context
- **August 31**: Initial testing suggested 320×180 limit based on token formula
- **September 1**: Discovered actual limit is 940×529 (3x higher)
- **Key Learning**: Don't trust documentation formulas - test empirically

## Remaining Questions
1. Why exactly does 960×540 fail while 940×529 works?
2. What is the actual tokenization algorithm?
3. Can we predict failure without testing?
4. Is the limit GPU-dependent or model-dependent?

## Conclusion
The Cosmos Transfer1 upsampling model is **much more capable** than initially documented. Production systems can safely use resolutions up to 854×480, with experimental support up to 940×529.

---
*Document Version: 1.0*
*Last Updated: September 1, 2025*
*Author: AI Assistant with empirical testing*
