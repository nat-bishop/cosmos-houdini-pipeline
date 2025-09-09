# Enhancement Metadata Refactor Plan

## Status: IN PROGRESS
Last Updated: 2024-01-09

## Objective
Simplify enhancement metadata storage to reduce duplication and improve maintainability while preserving query performance.

## Key Decision: Minimal Prompt Metadata
After analysis, prompts should ONLY store:
```python
parameters = {
    "enhanced": True  # Just this boolean flag for performance
}
```

Everything else lives in the enhancement run outputs, avoiding duplication.

## Current State (Before Refactor)

### Prompts Currently Store (when enhanced):
```python
parameters = {
    "enhanced": True,
    "enhancement_model": "pixtral",  # DUPLICATE with run
    "enhanced_at": "2024-01-01T12:00:00Z",  # DUPLICATE with run
    "last_enhancement_run_id": "rs_xxx",  # Recently added
    "parent_prompt_id": "ps_yyy"  # Only when create_new=True
}
```

### Runs Currently Store:
```python
outputs = {
    "enhanced_text": "...",
    "original_prompt_id": "ps_xxx",
    "enhanced_prompt_id": "ps_yyy",
    "duration_seconds": 45.2,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Target State (After Refactor)

### Prompts Will Store:
```python
parameters = {
    "enhanced": True  # ONLY THIS - for fast filtering
}
```

### Runs Will Store (complete record):
```python
outputs = {
    "enhanced_text": "...",
    "original_prompt_id": "ps_xxx",
    "enhanced_prompt_id": "ps_yyy",  # Same as original if overwrite
    "enhancement_model": "pixtral",
    "enhanced_at": "2024-01-01T12:00:00Z",
    "duration_seconds": 45.2
}
```

## Why This Design?

1. **No parent_prompt_id needed**: The run already tracks `original_prompt_id` and `enhanced_prompt_id`, which tells us:
   - If they're the same: it was an overwrite
   - If they're different: it was create_new, and original is the parent

2. **Single source of truth**: All enhancement details in the run

3. **Performance preserved**: The `enhanced` boolean enables fast filtering without JOINs

## Implementation Steps

### Step 1: Add Helper Functions to DataRepository
**File**: `cosmos_workflow/services/data_repository.py`

Add these methods:
```python
def get_enhancement_details(self, prompt_id: str) -> dict[str, Any] | None:
    """Get the latest enhancement details for a prompt from its runs."""

def get_original_prompt(self, enhanced_prompt_id: str) -> dict[str, Any] | None:
    """Get the original prompt that was enhanced to create this prompt."""

def list_enhanced_prompts(self, limit: int = 100) -> list[dict[str, Any]]:
    """List all prompts where parameters->enhanced is true."""

def get_enhancement_history(self, prompt_id: str) -> list[dict[str, Any]]:
    """Get all enhancement runs for a prompt (as original or enhanced)."""
```

### Step 2: Update enhance_prompt() in CosmosAPI
**File**: `cosmos_workflow/api/cosmos_api.py`

Lines to modify:
- **278-285** (create_new=True): Remove `parent_prompt_id`, `enhancement_model`, `enhanced_at`
- **294-300** (create_new=False): Remove `enhancement_model`, `enhanced_at`, `last_enhancement_run_id`
- **306-312** (run outputs): Add `enhancement_model` and `enhanced_at` if not already there

### Step 3: Update Existing Tests
**Files to update**:

1. `tests/integration/test_prompt_enhancement_database.py`
   - `test_create_new_preserves_original_prompt`: Check metadata NOT in prompt
   - `test_overwrite_updates_enhancement_metadata`: Check run outputs instead
   - Remove assertions for `parent_prompt_id` in prompt

2. `tests/safety/test_deletion_safety_critical.py`
   - Update any checks for enhancement metadata

### Step 4: Add New Query Tests
**New file**: `tests/integration/test_enhancement_queries.py`

Test the new helper functions:
- `test_get_enhancement_details()`
- `test_get_original_prompt()`
- `test_list_enhanced_prompts()`
- `test_get_enhancement_history()`
- `test_queries_work_with_old_structure()` (backward compatibility)

### Step 5: Update Documentation
**Files to update**:

1. **API.md** - Add new helper methods documentation:
   - Document `get_enhancement_details()`
   - Document `get_original_prompt()`
   - Document `list_enhanced_prompts()`
   - Document `get_enhancement_history()`
   - Update `enhance_prompt()` documentation

2. **DEVELOPMENT.md** - Add section on enhancement metadata:
   - Explain the design decision
   - Show example queries
   - Document the data model

3. **Delete**: `docs/enhancement_metadata_design.md` (this working doc replaces it)

## Backward Compatibility

- Existing enhanced prompts with old metadata structure will continue to work
- Helper functions should handle both old and new structures gracefully
- No database migration required - just stop writing duplicate data

## Testing Checklist

- [ ] All existing tests pass
- [ ] New helper functions have tests
- [ ] Backward compatibility tested
- [ ] Performance of list_enhanced_prompts() verified
- [ ] Enhancement lineage queries work correctly

## Verification Queries

After implementation, verify with these queries:

```sql
-- Check prompts only have boolean
SELECT id, parameters FROM prompts
WHERE parameters->>'enhanced' = 'true' LIMIT 5;

-- Check runs have complete metadata
SELECT outputs FROM runs
WHERE model_type = 'enhance' LIMIT 5;

-- Verify lineage tracking works
SELECT
    outputs->>'original_prompt_id' as original,
    outputs->>'enhanced_prompt_id' as enhanced
FROM runs
WHERE model_type = 'enhance';
```

## Notes for Next Session

If handing this to a new session, emphasize:
1. The key insight: We don't need `parent_prompt_id` because runs already track the relationship
2. Keep ONLY `enhanced: true` in prompts for performance
3. Everything else goes in run outputs
4. Tests are critical - this touches core functionality
5. Update API.md with the new helper functions

## Questions Resolved

- **Q: Do we need parent_prompt_id?** No, runs already track this via original/enhanced IDs
- **Q: Should we remove enhanced boolean?** No, keep it for query performance
- **Q: Where should docs live?** Update existing API.md, don't create new database doc
- **Q: How to track lineage?** Query runs where enhanced_prompt_id = target

## Definition of Done

- [ ] Code changes complete
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No duplicate metadata in new enhancements
- [ ] Helper functions working
- [ ] Backward compatibility verified