# Merge Strategy Plan: feature/parallel-development → main

## Branch Analysis Summary

### Current State
- **Main branch**: Has merged feature/new-developments (commit 8b39df4)
- **Parallel branch**: Diverged from commit 555dc68, has 15 unique commits
- **Common ancestor**: 555dc68 "Add comprehensive test suite investigation and TODO documentation"

### Work Done in parallel-development Branch
1. **Test Suite Overhaul** (Primary focus)
   - Comprehensive test refactoring and cleanup
   - Achieved 614 passing tests, 0 failures
   - Added 25 WorkflowOrchestrator tests (93.79% coverage)
   - Fixed SFTP integration tests
   - Removed outdated/broken tests

2. **Prompt Upsampling Features**
   - Added resolution testing framework
   - Created upsampling integration
   - Added working scripts for prompt upsampling

3. **Documentation**
   - Multiple test analysis documents
   - Green baseline achievement documentation
   - Infrastructure requirements
   - Test cleanup summaries

## Potential Conflict Areas

### Files Modified in Both Branches
Based on the diff analysis, these files will likely have conflicts:

1. **cosmos_workflow/cli.py**
   - Main: Has AI integration, smart naming features
   - Parallel: Has upsampling commands
   - **Resolution**: Keep both sets of features

2. **cosmos_workflow/transfer/file_transfer.py**
   - Main: Refactored for new structure
   - Parallel: Added upload_directory/download_directory methods
   - **Resolution**: Keep parallel's additions

3. **cosmos_workflow/workflows/workflow_orchestrator.py**
   - Main: Major refactoring
   - Parallel: Comment clarifications, test improvements
   - **Resolution**: Keep parallel's clarifications

4. **tests/** directory structure
   - Main: Reorganized into unit/integration/system
   - Parallel: Further test improvements and fixes
   - **Resolution**: Keep parallel's improvements

5. **Documentation files**
   - CHANGELOG.md, README.md, TODO.md
   - **Resolution**: Merge both sets of changes

## Safe Merge Strategy

### Pre-Merge Checklist
- [ ] Ensure all work in other session is saved/committed
- [ ] Create backup branch: `git branch backup/pre-merge-parallel`
- [ ] Push parallel branch to remote: `git push origin feature/parallel-development`

### Merge Procedure

#### Step 1: Prepare for Merge
```bash
# 1. Ensure you're on parallel-development
git checkout feature/parallel-development

# 2. Create a backup
git branch backup/parallel-development-$(date +%Y%m%d)

# 3. Fetch latest main
git fetch origin main
```

#### Step 2: Test Merge (Dry Run)
```bash
# Create a test branch
git checkout -b test-merge

# Try merging main into test branch
git merge origin/main --no-commit --no-ff

# Review conflicts
git status

# If conflicts are manageable, abort and do real merge
git merge --abort
git checkout feature/parallel-development
```

#### Step 3: Actual Merge Strategy - REBASE (Recommended)
```bash
# Rebase parallel-development on top of main
# This will apply your commits on top of the latest main
git checkout feature/parallel-development
git rebase origin/main

# Resolve conflicts as they appear
# For each conflict:
# 1. Fix the conflict
# 2. git add <fixed-files>
# 3. git rebase --continue
```

**Why Rebase?**
- Cleaner history
- Your test improvements will appear as a logical sequence after the AI features
- Easier to review what changed

#### Step 4: Alternative - MERGE (If Rebase is Too Complex)
```bash
# If rebase has too many conflicts, use merge instead
git checkout feature/parallel-development
git merge origin/main

# Resolve all conflicts
# Then commit the merge
```

## Conflict Resolution Guidelines

### For Each Conflict Type:

1. **Test Files**
   - Keep ALL test improvements from parallel-development
   - These are the latest, most comprehensive tests

2. **CLI Commands**
   - Keep BOTH sets of commands (AI features + upsampling)
   - May need to manually combine command definitions

3. **File Transfer Methods**
   - Keep parallel's upload_directory/download_directory
   - These are needed for tests

4. **Documentation**
   - Merge both sets of changes chronologically
   - Keep all test improvement documentation

5. **Workflow Orchestrator**
   - Keep parallel's comment clarifications
   - Ensure compatibility with both branches' features

## Post-Merge Verification

### Testing Checklist
```bash
# 1. Run all tests
pytest tests/ -v

# 2. Verify test count (should be 614+)
pytest tests/ --co -q | wc -l

# 3. Check coverage
pytest tests/unit/ --cov=cosmos_workflow --cov-report=term-missing

# 4. Verify CLI commands work
python -m cosmos_workflow.cli --help

# 5. Check pre-commit hooks
pre-commit run --all-files
```

### Final Steps
```bash
# 1. Push the merged branch
git push origin feature/parallel-development

# 2. Create PR to main
# Include comprehensive description of:
# - Test improvements
# - Coverage increases
# - Bug fixes
# - New features (upsampling)

# 3. After PR approval and merge to main
git checkout main
git pull origin main
```

## Risk Mitigation

### Backup Strategy
1. Keep backup branches at each stage
2. Push to remote before major operations
3. Document any manual conflict resolutions

### Rollback Plan
If merge goes wrong:
```bash
# Reset to backup
git reset --hard backup/parallel-development-[date]

# Or fetch from remote
git fetch origin
git reset --hard origin/feature/parallel-development
```

## Timeline Recommendation

1. **When other session is complete**: Save and commit all work there
2. **Create backups**: 5 minutes
3. **Test merge**: 15-30 minutes to review conflicts
4. **Actual merge/rebase**: 30-60 minutes depending on conflicts
5. **Testing**: 30 minutes
6. **Total**: ~2 hours for safe, thorough merge

## Notes

- The parallel-development branch has valuable test improvements that should be preserved
- Most conflicts will be in test files - always prefer parallel-development's versions
- The upsampling features are additive and shouldn't conflict with AI features
- Documentation conflicts can be resolved by keeping both sets of changes

Ready to proceed when you are!
