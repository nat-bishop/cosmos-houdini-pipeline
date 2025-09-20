# Rollback and Backup Information - September 20, 2025

## Current Situation
- **Problem**: Batch inference jobs failing immediately after queue processing changes
- **Last Known Good**: Commit 490f358 (Sep 19, 15:11) - system was working
- **Current HEAD**: Commit 2d9deb0 (Sep 19, 18:30) - has issues

## Backup Branches Created
1. **backup/2025-09-20-all-work** - All committed work up to 2d9deb0
2. **backup/2025-09-20-with-fixes** - Includes uncommitted logging fixes

## Changes Being Preserved

### Commits We're Keeping (in 490f358)
- `9c8d508` - feat: add base controlnet spec support for batch inference
- `8688559` - fix: batch inference output handling and enhance prompt update flow
- `a4bbea6` - docs: add architecture refactor plan and update roadmap
- `490f358` - fix: replace memory controller utilization with actual memory capacity

### Commits We're Removing (problematic)
- `b207ebb` - Queue race condition "fix" with complex locking (likely causing issues)
- `2d9deb0` - Module initialization changes (may prevent UI startup)

### Uncommitted Fixes Being Saved
- **queue_service.py** - Logging format fixes (%s -> {} for loguru compatibility)
- **CLAUDE.md** - Documentation updates

## Recovery Commands

### If Rollback Goes Wrong
```bash
# Return to exact state before rollback
git checkout backup/2025-09-20-with-fixes
```

### To View What's in Backups
```bash
# See commits in backup
git log --oneline backup/2025-09-20-all-work

# Compare backup to current
git diff HEAD..backup/2025-09-20-with-fixes

# Cherry-pick specific fixes if needed
git cherry-pick backup/2025-09-20-with-fixes~1  # logging fixes
```

## Post-Rollback TODOs
1. ✅ Logging format fixes (will be cherry-picked)
2. ⚠️ Auto-advance logic fix (check BEFORE processing any job)
3. ⚠️ Simple duplicate prevention (without complex locking)

## Testing Checklist After Rollback
- [ ] UI starts without errors
- [ ] Background processor thread starts (check logs)
- [ ] Single inference works
- [ ] Batch inference creates correct number of runs
- [ ] Auto-advance checkbox controls job processing
- [ ] No duplicate runs created

## Key Lessons Learned
1. Complex database locking can cause more problems than it solves
2. Module-level initialization in Gradio apps is problematic
3. Loguru requires {} format, not %s printf-style
4. Always test batch operations thoroughly after queue changes

## Files Most Affected
- `cosmos_workflow/services/queue_service.py` - Core queue processing
- `cosmos_workflow/ui/app.py` - Module initialization
- `cosmos_workflow/config/config.toml` - Auto-reload setting

## Contact for Issues
If you need to understand these changes later, key areas to review:
- Queue processor thread in queue_service.py `_process_queue_loop()`
- Auto-advance logic at line ~670 in queue_service.py
- Module initialization at bottom of ui/app.py