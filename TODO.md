# TODO - Cosmos Workflow Orchestrator
*Last Updated: 2025-08-31*

This document tracks planned features and improvements for the Cosmos Workflow Orchestrator project. Items are organized by category and priority.

---

## 🔴 Priority 1: Critical Issues

### Remote Environment Setup
- [ ] **Build Docker image on remote instance**
  - Run: `sudo docker build -f Dockerfile . -t nvcr.io/ubuntu/cosmos-transfer1:v1.0.0`
  - Verify image exists with `sudo docker images`
  - Update config.toml to use versioned image
  - *Effort: 1 day*

- [ ] **Setup model checkpoints**
  - Download all required checkpoints to `/home/ubuntu/NatsFS/cosmos-transfer1/checkpoints/`
  - Verify directory structure
  - Create manifest of checkpoint versions
  - *Effort: 1-2 days*

- [ ] **Configure Hugging Face authentication**
  - Set up read-only HF token
  - Configure as environment variable or Docker secret
  - Test model access
  - *Effort: 1 day*

### Security & Version Control
- [ ] **Pin Docker image versions**
  - Stop using `:latest` tags everywhere
  - Create versioned tags (e.g., `cosmos-transfer1:v1.0.0`)
  - Update all references in code and config
  - Document version in deployment notes
  - *Effort: 1 day*

- [ ] **Version control model checkpoints**
  - Document specific checkpoint versions/hashes
  - Create manifest file listing all checkpoints
  - Implement checkpoint validation
  - *Effort: 1-2 days*

### Code Quality
- [ ] **Fix hardcoded negative prompt**
  - Currently hardcoded as "bad quality, blurry, low resolution, cartoonish"
  - Make configurable via config.toml or command line
  - Add smart negative prompt generation based on input
  - *Effort: 1 day*

### Performance Issues
- [ ] **Investigate control weight zero optimization**
  - Check if control_weight=0 still passes params to controlnet
  - Could cause unnecessary inference slowdown
  - Implement conditional parameter passing
  - *Effort: 1-2 days*

---

## 🟡 Priority 2: Feature Enhancements

### Upsampling Integration
- [ ] **Complete upsampling integration testing**
  - Test with various resolutions on remote GPU
  - Verify model stays loaded between runs
  - Test batch processing with checkpoints
  - Document maximum working resolutions
  - *Effort: 2-3 days*

- [ ] **Implement automatic video preprocessing**
  - Auto-resize videos exceeding token limits
  - Create hint videos at 320×180 for upsampling
  - Add resolution validation before processing
  - *Effort: 2 days*

### Batch Processing
- [ ] **Implement batch inference support**
  - Allow multiple prompts in single run
  - Optimize GPU utilization for batches
  - Add progress tracking for batch jobs
  - *Effort: 3-5 days*

- [ ] **Add overnight batch processing with randomization**
  - Schedule batch runs for off-hours
  - Add parameter randomization for variations
  - Implement queue management
  - Add failure recovery and retry logic
  - *Effort: 4-5 days*

### AI & Smart Features
- [ ] **Improve AI naming and description generation**
  - Enhance prompt analysis for better names
  - Add context-aware description generation
  - Implement fallback strategies for edge cases
  - *Effort: 3-4 days*

---

## 🟢 Priority 3: Nice to Have

### CLI Enhancement
- [ ] **Add interactive prompt creation interface**
  - CLI wizard for creating prompts
  - Template system for common scenarios
  - Prompt preview and validation
  - *Effort: 2-3 days*

### Documentation
- [ ] **Create comprehensive user guide**
  - Step-by-step setup instructions
  - Common workflow examples
  - Troubleshooting guide
  - *Effort: 2 days*

### Infrastructure
- [ ] **Fix GitHub Actions workflows**
  - Update CI/CD pipelines
  - Add automated testing on PR
  - Configure release automation
  - *Effort: 2 days*

---

## 📊 Effort Summary

| Priority | Total Days | Items |
|----------|------------|-------|
| Priority 1 | 8-11 days | 7 items |
| Priority 2 | 11-14 days | 4 items |
| Priority 3 | 4-5 days | 3 items |
| **Total** | **23-30 days** | **14 items** |

---

## 🎯 Next Steps (In Order)

1. **Setup remote environment** - Build Docker image, download checkpoints
2. **Configure authentication** - Set up HF token
3. **Pin versions** - Move away from `:latest` tags
4. **Test upsampling** - Complete integration testing
5. **Fix performance issues** - Control weight optimization

---

## ✅ Completed Items

- [x] **Prompt upsampling integration** - Completed 2025-08-31
  - Integrated upsampling into WorkflowOrchestrator
  - Added CLI `upsample` command
  - Created resolution testing utilities
  - Documented token limits (320×180 safe resolution)

- [x] **Script cleanup** - Completed 2025-08-31
  - Removed 24 redundant upsampling scripts
  - Kept 4 essential scripts
  - Removed 15+ outdated documentation files
  - Cleaned Python cache files

- [x] **Test suite improvements** - Completed 2025-08-31
  - Reverted to real implementations (no fakes)
  - Fixed schema mismatches
  - Tests now verify actual code behavior

- [x] **Documentation cleanup** - Completed 2025-08-31
  - Removed all outdated test planning docs
  - Updated CHANGELOG with recent changes
  - Consolidated upsampling documentation

---

*This document should be updated regularly as priorities change and new requirements emerge.*
