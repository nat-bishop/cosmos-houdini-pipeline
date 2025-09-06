# Gradio UI Improvements Documentation

**Date:** 2025-01-09
**Author:** NAT
**Status:** Completed

## Summary

Major improvements to the Gradio UI to fix workflow issues and properly integrate with the existing Cosmos Workflow backend. The UI now correctly follows the two-step workflow: Create Prompt → Run Inference, matching the CLI behavior.

## Key Problems Fixed

### 1. **Missing Video Input Support** ✅
- **Problem:** Original UI had no way to upload the required 3 video files (color, depth, segmentation)
- **Solution:** Added video upload section that saves files in expected structure: `inputs/videos/{name}/color.mp4`, etc.

### 2. **Incorrect Workflow** ✅
- **Problem:** UI tried to create prompt and run immediately, showed "Run ID" output field
- **Solution:** Split into proper two-step process:
  - Step 1: Upload videos and create prompt
  - Step 2: Select existing prompt and run inference

### 3. **Gallery Not Working** ✅
- **Problem:** Gallery looked for files that didn't exist
- **Solution:** Fixed to check multiple possible output paths including actual downloaded locations

### 4. **Non-Interactive Runs Tab** ✅
- **Problem:** Static HTML table with no actions
- **Solution:** Converted to Dataframe with interactive features

### 5. **Status Tab Confusion** ✅
- **Problem:** Users didn't know it auto-refreshes
- **Solution:** Added "*Auto-refreshing every 5 seconds*" indicator

## New Features

### **Generate Tab (Redesigned)**
Two-column layout for proper workflow:

**Left Column - Create Prompt:**
- Video upload area for 3 required files
- Prompt text input
- Negative prompt
- Optional name
- Creates prompt in database with video references

**Right Column - Run Inference:**
- Dropdown to select from existing prompts
- Display prompt details including video status
- Weight configuration sliders
- Advanced settings in collapsible section
- Live log viewer during execution

### **Prompts Tab (New)**
- Lists all prompts with details
- Shows video availability status (✓/✗)
- Displays ID, name, text, created date
- Foundation for future delete/clone features

### **Runs Tab (Enhanced)**
- Interactive Dataframe instead of static HTML
- Shows prompt text for each run
- Status indicators
- Foundation for future filtering/actions

### **Gallery Tab (Fixed)**
- Now correctly finds downloaded videos
- Checks multiple possible paths
- Auto-refreshes every 10 seconds
- Shows prompt text with run ID

### **Status Tab (Improved)**
- Auto-refresh indicator visible
- Shows GPU utilization
- Docker container status
- Connection error handling

## Technical Implementation

### Video Upload Handling
```python
def handle_video_uploads(color_file, depth_file, seg_file):
    # Creates expected directory structure
    video_dir = Path(f"inputs/videos/ui_upload_{timestamp}")
    # Saves with required names: color.mp4, depth.mp4, segmentation.mp4
```

### Proper Service Integration
- Uses `WorkflowService` for all data operations
- Uses `WorkflowOrchestrator` for execution
- No new backend functionality added
- Maintains separation of concerns

### Gallery Fix
```python
# Checks actual download locations
possible_paths = [
    Path(f"outputs/run_{run_id}/output.mp4"),
    Path(f"outputs/run_{run_id}/result.mp4"),
    # ... upscaled versions
]
```

## Usage Instructions

### Creating and Running a Video Generation

1. **Upload Videos:**
   - Click "Upload Videos" in left column
   - Select color.mp4, depth.mp4, segmentation.mp4
   - Click "📤 Upload Videos" button

2. **Create Prompt:**
   - Enter your prompt text
   - Add negative prompt
   - Optionally name your prompt
   - Click "✨ Create Prompt"

3. **Run Inference:**
   - Select prompt from dropdown (or use newly created)
   - Adjust weight sliders if needed
   - Enable upscaling if desired
   - Click "🚀 Run Inference"
   - Watch live logs

4. **View Results:**
   - Check Gallery tab for completed videos
   - Monitor progress in Runs tab
   - Review all prompts in Prompts tab

## Benefits

1. **Correct Workflow:** Matches CLI behavior exactly
2. **Video Support:** Properly handles multimodal inputs
3. **Reusability:** Can select and rerun existing prompts
4. **Transparency:** Live logs and status monitoring
5. **Management:** View and track all prompts and runs
6. **Auto-refresh:** Gallery and status update automatically

## Future Enhancements

- Add delete functionality for prompts/runs
- Add prompt cloning/duplication
- Add filtering and search in tables
- Add video preview in gallery
- Add batch processing support
- Add export functionality

## Migration Notes

Users of the previous UI should note:
- Must now upload videos before creating prompts
- Prompts and runs are separate steps
- Can reuse existing prompts multiple times
- Gallery now shows actual completed videos
- Status auto-refreshes (no need to click refresh)

## Code Quality

- All functions use existing backend services
- No tight coupling or new backend logic
- Follows project wrapper patterns
- Maintains separation of concerns
- Uses proper error handling

## Recent Enhancements (2025-09-05)

### Control Weight System
- Added all 4 control weights: visual, edge, depth, segmentation
- Each weight configurable from 0.0 to 1.0
- Weights apply even without corresponding input videos
- Model auto-generates depth/segmentation if not provided

### Optional Video Support
- Color video: Required
- Depth video: Optional
- Segmentation video: Optional
- Smart JSON generation only includes controls with weight > 0

### Performance Improvements
- Efficient seek-based log tailing for large files
- Only reads necessary blocks from end of file
- Similar approach to NVIDIA's implementation

### UI Enhancements
- Improved video status indicators: "[OK] (3 videos)" or "[!] Missing (2)"
- Full video paths shown in prompt details
- ASCII-safe characters for Windows compatibility
- Better workflow clarity with two-step process

## Testing Checklist

- [x] Video upload creates correct directory structure
- [x] Prompt creation with videos works
- [x] Prompt selection and details display
- [x] Run inference executes properly
- [x] Live logs stream during execution
- [x] Gallery shows completed videos
- [x] Status auto-refreshes every 5 seconds
- [x] Prompts table displays all prompts
- [x] Runs table shows run details
- [x] Error handling for missing videos
- [x] All 4 control weights functional
- [x] Optional video support working
- [x] Seek-based log tailing performant