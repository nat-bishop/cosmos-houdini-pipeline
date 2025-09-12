# Migration Notes

## Breaking Change: Model Type Refactoring (2025-01-11)

### Overview
The `model_type` field has been removed from the Prompt model to make prompts model-agnostic. This is a **breaking change** that requires database migration and code updates.

### What Changed
- **Prompts no longer have a model_type field** - they are now model-agnostic (just text + inputs)
- **model_type is now specified only when creating a Run** (execution)
- This allows the same prompt to be executed with different models

### Database Migration Required
For existing databases, run this SQL command:
```sql
ALTER TABLE prompts DROP COLUMN model_type;
```

### API Changes

#### DataRepository / Service Layer
- `create_prompt()` no longer accepts `model_type` parameter
- `create_run()` now **requires** explicit `model_type` parameter
- `list_prompts()` no longer filters by `model_type`

#### Before (Old API):
```python
# Creating a prompt with model_type
prompt = service.create_prompt(
    model_type="transfer",  # ❌ No longer accepted
    prompt_text="...",
    inputs={...},
    parameters={...}
)

# Creating a run (model_type was optional/inherited)
run = service.create_run(
    prompt_id="...",
    execution_config={...}
    # model_type was optional or inherited from prompt
)
```

#### After (New API):
```python
# Creating a prompt without model_type
prompt = service.create_prompt(
    prompt_text="...",  # ✅ No model_type parameter
    inputs={...},
    parameters={...}
)

# Creating a run with explicit model_type
run = service.create_run(
    prompt_id="...",
    execution_config={...},
    model_type="transfer"  # ✅ Must be explicit now
)
```

### CLI Changes
- `cosmos create prompt` no longer accepts or displays model_type
- `cosmos list prompts` no longer shows Model column
- `cosmos list runs` still shows Model column (runs have model_type)

### Test Updates
All unit and integration tests have been updated to reflect the new API signatures:
- ✅ 527/527 unit tests passing
- ✅ 60/60 integration tests passing (5 skipped - require environment)

### Benefits
1. **Flexibility**: Same prompt can be run with different models
2. **Simplicity**: Prompts focus on content, runs focus on execution
3. **Future-proof**: Easy to add new model types without changing prompt structure

### Files Modified
- `cosmos_workflow/database/models.py` - Removed model_type column from Prompt
- `cosmos_workflow/services/data_repository.py` - Updated create_prompt/create_run signatures
- `cosmos_workflow/api/cosmos_api.py` - Explicit model_type="transfer" in all create_run calls
- `cosmos_workflow/cli/*.py` - Removed model_type from prompt commands
- `cosmos_workflow/ui/gradio_app.py` - Removed model_type UI elements
- All test files updated to use new API

### Container Naming
Container naming remains unchanged - still uses format: `cosmos_{model_type}_{timestamp}`