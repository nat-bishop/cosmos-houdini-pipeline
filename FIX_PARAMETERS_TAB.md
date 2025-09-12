# FIX: Run History Parameters Tab

## Problem
The Parameters tab in Run History > Run Details is not working correctly. It's trying to access `run.get("parameters")` but the actual data is stored in `run.get("execution_config")`. Additionally, separating Control Weights from other parameters is problematic since execution_config structure varies by model type (transfer, upscale, enhance).

## Solution
Display the entire execution_config as a single JSON object, which will work regardless of model type.

## Implementation Details

### File to Edit: `cosmos_workflow/ui/app.py`

### Change 1: Update UI Components (Lines ~1627-1645)

**REPLACE THIS:**
```python
                                # Parameters Tab
                                with gr.Tab("Parameters"):
                                    gr.Markdown("#### Control Weights")
                                    with gr.Row():
                                        history_weight_vis = gr.Textbox(
                                            label="Visual", interactive=False, scale=1
                                        )
                                        history_weight_edge = gr.Textbox(
                                            label="Edge", interactive=False, scale=1
                                        )
                                        history_weight_depth = gr.Textbox(
                                            label="Depth", interactive=False, scale=1
                                        )
                                        history_weight_seg = gr.Textbox(
                                            label="Segmentation", interactive=False, scale=1
                                        )

                                    gr.Markdown("#### Inference Parameters")
                                    history_params = gr.JSON(label="", container=False)
```

**WITH THIS:**
```python
                                # Parameters Tab
                                with gr.Tab("Parameters"):
                                    gr.Markdown("#### Execution Configuration")
                                    history_execution_config = gr.JSON(
                                        label="",
                                        container=False,
                                        elem_classes=["json-display"]
                                    )
```

### Change 2: Fix Data Extraction (Lines ~2040-2058)

**REPLACE THIS:**
```python
                # Get parameters
                params = run.get("parameters", {})
                weights = params.get("weights", {})

                # Extract individual weight values
                weight_vis = str(weights.get("vis", ""))
                weight_edge = str(weights.get("edge", ""))
                weight_depth = str(weights.get("depth", ""))
                weight_seg = str(weights.get("seg", ""))

                inference_params = {
                    "num_steps": params.get("num_steps", 35),
                    "guidance_scale": params.get("guidance_scale", 7.0),
                    "seed": params.get("seed", 1),
                    "fps": params.get("fps", 24),
                    "sigma_max": params.get("sigma_max", 70.0),
                    "blur_strength": params.get("blur_strength", "medium"),
                    "canny_threshold": params.get("canny_threshold", "medium"),
                }
```

**WITH THIS:**
```python
                # Get execution config directly from run
                execution_config = run.get("execution_config", {})
```

### Change 3: Update Success Return Statement (Lines ~2073-2091)

**REPLACE THIS:**
```python
                return [
                    gr.update(value=run_id),  # history_run_id
                    gr.update(value=status),  # history_status
                    gr.update(value=duration),  # history_duration
                    gr.update(value=run_type),  # history_run_type (NEW)
                    gr.update(value=prompt_name),  # history_prompt_name
                    gr.update(value=prompt_text),  # history_prompt_text
                    gr.update(value=created),  # history_created
                    gr.update(value=completed),  # history_completed
                    gr.update(value=weight_vis),  # history_weight_vis (NEW)
                    gr.update(value=weight_edge),  # history_weight_edge (NEW)
                    gr.update(value=weight_depth),  # history_weight_depth (NEW)
                    gr.update(value=weight_seg),  # history_weight_seg (NEW)
                    gr.update(value=inference_params),  # history_params
                    gr.update(value=log_path),  # history_log_path
                    gr.update(value=log_content),  # history_log_content
                    gr.update(value=output_video),  # history_output_video
                    gr.update(value=output_path),  # history_output_path
                ]
```

**WITH THIS:**
```python
                return [
                    gr.update(value=run_id),  # history_run_id
                    gr.update(value=status),  # history_status
                    gr.update(value=duration),  # history_duration
                    gr.update(value=run_type),  # history_run_type
                    gr.update(value=prompt_name),  # history_prompt_name
                    gr.update(value=prompt_text),  # history_prompt_text
                    gr.update(value=created),  # history_created
                    gr.update(value=completed),  # history_completed
                    gr.update(value=execution_config),  # history_execution_config
                    gr.update(value=log_path),  # history_log_path
                    gr.update(value=log_content),  # history_log_content
                    gr.update(value=output_video),  # history_output_video
                    gr.update(value=output_path),  # history_output_path
                ]
```

### Change 4: Update ALL Empty Return Statements

Find all return statements in the `select_run_from_history` function that return empty values (there are several for error cases).

**For each one, REPLACE:**
- Lines with `history_weight_vis`, `history_weight_edge`, `history_weight_depth`, `history_weight_seg`
- Line with `history_params`

**WITH:**
- A single line with `history_execution_config` returning `{}`

Example:
```python
                    gr.update(value=""),  # history_run_id
                    gr.update(value=""),  # history_status
                    gr.update(value=""),  # history_duration
                    gr.update(value=""),  # history_run_type
                    gr.update(value=""),  # history_prompt_name
                    gr.update(value=""),  # history_prompt_text
                    gr.update(value=""),  # history_created
                    gr.update(value=""),  # history_completed
                    gr.update(value={}),  # history_execution_config  <-- CHANGED
                    gr.update(value=""),  # history_log_path
                    gr.update(value=""),  # history_log_content
                    gr.update(value=None),  # history_output_video
                    gr.update(value=""),  # history_output_path
```

### Change 5: Update Event Handler Outputs (Lines ~2656-2670)

**REPLACE THIS:**
```python
                history_run_type,  # NEW
                history_prompt_name,
                history_prompt_text,
                history_created,
                history_completed,
                history_weight_vis,  # NEW
                history_weight_edge,  # NEW
                history_weight_depth,  # NEW
                history_weight_seg,  # NEW
                history_params,
                history_log_path,
                history_log_content,
                history_output_video,
                history_output_path,
```

**WITH THIS:**
```python
                history_run_type,
                history_prompt_name,
                history_prompt_text,
                history_created,
                history_completed,
                history_execution_config,
                history_log_path,
                history_log_content,
                history_output_video,
                history_output_path,
```

## Expected Result

After these changes, the Parameters tab will display the full execution_config as a JSON object. For example:

For a transfer model run:
```json
{
  "weights": {"vis": 0.0, "edge": 0.1, "depth": 0.3, "seg": 0.5},
  "num_steps": 35,
  "guidance": 7.0,
  "seed": 1,
  "sigma_max": 70.0,
  "blur_strength": "medium",
  "canny_threshold": "medium",
  "fps": 24
}
```

For an upscale model run:
```json
{
  "input_video_source": "/path/to/video.mp4",
  "control_weight": 0.7,
  "source_run_id": "run_abc123",
  "prompt": "upscale to 4K"
}
```

This approach is more flexible and will work with any model type or future configuration changes.

## Testing Steps

1. Start the UI: `cosmos ui`
2. Navigate to the "Run History" tab
3. Click on any run in the table
4. Click on the "Parameters" tab in the Run Details section
5. Verify that the execution configuration is displayed as a formatted JSON
6. Test with different model types (transfer, upscale, enhance) to ensure all display correctly