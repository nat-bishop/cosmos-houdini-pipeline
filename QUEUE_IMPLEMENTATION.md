# Minimal Queue Implementation Using Gradio's Built-in Queue

## Core Concept
Use **Gradio State** for in-memory queue storage and Gradio's **built-in queue** for execution management. This requires minimal code changes and no database modifications.

## Implementation Phases

### Phase 1: Add Queue State Management
**Status:** 🔴 Not Started

**Files to modify:**
- `cosmos_workflow/ui/app.py`

**Changes:**
- Add `inference_queue` State component to store queue items
- Add `queue_counter` State to track queue size
- Create helper functions for queue management

**Code additions:**
```python
# After navigation_state (~line 1107)
inference_queue = gr.State([])  # List of queue items
queue_counter = gr.State(0)     # Track queue size
```

---

### Phase 2: Create Queue Management Functions
**Status:** 🔴 Not Started

**Files to modify:**
- `cosmos_workflow/ui/app.py`

**New functions to add:**
- `add_to_queue()` - Add selected prompts with current config to queue
- `remove_from_queue()` - Remove specific items from queue
- `clear_queue()` - Clear all queue items
- `get_queue_display()` - Format queue for display
- `group_queue_by_batch_key()` - Group compatible items for batching

**Key logic:**
```python
def calculate_batch_key(params):
    """Calculate batch key from parameters that must be identical."""
    return hash((
        params['num_steps'],
        params['guidance_scale'],
        params['seed'],
        params['fps'],
        params['sigma_max'],
        params['blur_strength'],
        params['canny_threshold']
    ))
```

---

### Phase 3: Modify Prompts Tab UI
**Status:** 🔴 Not Started

**Files to modify:**
- `cosmos_workflow/ui/tabs/prompts_ui.py`

**Changes:**
- Replace "Run Inference" button with "Add to Queue" button
- Add queue counter display next to button
- Keep controlnet weight sliders as-is
- Add "Clear Config" button to reset weights

---

### Phase 4: Create Queue Processing Function
**Status:** 🔴 Not Started

**Files to modify:**
- `cosmos_workflow/ui/app.py`

**New function:**
```python
def process_queue(queue_state, progress=gr.Progress()):
    """Process queue with smart batching."""
    # Group by batch_key
    # Process each batch using existing batch_inference
    # Update progress
    # Clear queue when done
```

**Integration:**
- Reuse existing `ops.batch_inference()`
- No changes needed to backend

---

### Phase 5: Enhance Queue Tab UI
**Status:** 🔴 Not Started

**Files to modify:**
- `cosmos_workflow/ui/tabs/jobs_ui.py`
- `cosmos_workflow/ui/tabs/jobs_handlers.py` (new file)

**New UI elements:**
- Queue items table with columns: [Prompt, Weights, Batch Group]
- "Start Queue" button
- "Pause Queue" button
- "Clear Queue" button
- Batch preview section showing groupings

---

### Phase 6: Connect Event Handlers
**Status:** 🔴 Not Started

**Files to modify:**
- `cosmos_workflow/ui/app.py`

**Event connections:**
- "Add to Queue" button → `add_to_queue()`
- "Start Queue" button → `process_queue()`
- "Clear Queue" button → `clear_queue()`
- Queue table selection → show details
- Auto-update queue display when items added/removed

---

### Phase 7: Testing & Polish
**Status:** 🔴 Not Started

**Testing scenarios:**
1. Add single prompt with different configs
2. Add multiple prompts with same config
3. Mixed batch scenarios
4. Queue persistence during session
5. Progress tracking during processing
6. Error handling

**Polish items:**
- Toast notifications for queue operations
- Estimated processing time
- Visual batch grouping indicators
- Queue operation animations

---

## Technical Details

### Batch Key Calculation
Parameters that MUST be identical for batching:
- `num_steps`
- `guidance_scale`
- `seed`
- `fps`
- `sigma_max`
- `blur_strength`
- `canny_threshold`

Parameters that CAN vary within a batch:
- ControlNet weights (`vis`, `edge`, `depth`, `seg`)
- Control input paths
- Prompt text (each prompt in batch can differ)

### Queue Item Structure
```python
{
    "prompt_id": "ps_xxxxx",
    "prompt_text": "...",
    "weights": {"vis": 0.5, "edge": 0.5, ...},
    "params": {"steps": 35, "guidance": 7.0, ...},
    "batch_key": 12345678,  # Hash of params
    "added_at": "2024-12-10 10:30:00"
}
```

### Benefits
- **Minimal code changes** (~300 lines vs 1000+)
- **No database changes** required
- **Reuses existing infrastructure**
- **Maintains backward compatibility**
- **Simple rollback** if needed

### Risks & Mitigations
- **Risk:** Queue lost on refresh
  - **Mitigation:** Add session persistence option later if needed

- **Risk:** Complex batching logic
  - **Mitigation:** Start simple, enhance incrementally

- **Risk:** UI complexity
  - **Mitigation:** Keep UI minimal initially

## Next Steps
1. Review and approve plan ✅
2. Start with Phase 1 (Queue State)
3. Test each phase before proceeding
4. Document as we go