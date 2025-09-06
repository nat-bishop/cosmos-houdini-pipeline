"""Gradio UI for Cosmos Workflow - Enhanced Version with Prompt Management."""

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr
import pandas as pd

from cosmos_workflow.config import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.database import init_database
from cosmos_workflow.execution.docker_executor import DockerExecutor

# Direct service imports (no CLI coupling)
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.workflows import WorkflowOrchestrator

logger = logging.getLogger(__name__)

# Global initialization
logger.info("Initializing Cosmos services...")
config = ConfigManager()
local_config = config.get_local_config()
db_path = local_config.outputs_dir / "cosmos.db"
db = init_database(str(db_path))

service = WorkflowService(db, config)
orchestrator = WorkflowOrchestrator()

# For GPU status monitoring
ssh_manager = None
docker_executor = None

# Global state for live logs
active_run_logs = {}
log_lock = threading.Lock()


def handle_video_uploads(color_file, depth_file, seg_file, name_prefix="ui_upload"):
    """Handle video file uploads and save in expected structure.

    Color video is required, depth and segmentation are optional.
    """
    if not color_file:
        return None, "Color video is required"

    try:
        # Create directory structure expected by CLI
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        video_dir = Path(f"inputs/videos/{name_prefix}_{timestamp}")
        video_dir.mkdir(parents=True, exist_ok=True)

        # Save color video (required)
        color_path = video_dir / "color.mp4"
        with open(color_path, "wb") as f:
            f.write(color_file)

        # Save depth video if provided (optional)
        if depth_file:
            depth_path = video_dir / "depth.mp4"
            with open(depth_path, "wb") as f:
                f.write(depth_file)

        # Save segmentation video if provided (optional)
        if seg_file:
            seg_path = video_dir / "segmentation.mp4"
            with open(seg_path, "wb") as f:
                f.write(seg_file)

        # Create status message
        uploaded_files = ["color"]
        if depth_file:
            uploaded_files.append("depth")
        if seg_file:
            uploaded_files.append("segmentation")

        status = f"Uploaded {', '.join(uploaded_files)} video(s) to {video_dir}"
        return str(video_dir), status

    except Exception as e:
        return None, f"Error uploading videos: {e}"


def create_prompt_with_videos(prompt_text, negative_prompt, video_dir, name=None):
    """Create a prompt using uploaded videos."""
    if not video_dir:
        return "", "Please upload videos first"

    if not prompt_text:
        return "", "Please enter a prompt"

    try:
        video_path = Path(video_dir)

        # Build inputs dictionary with full paths
        # Always include color (required), only add depth/seg if they exist
        inputs = {
            "video": str(video_path / "color.mp4"),
        }

        # Add depth path only if the file exists
        depth_path = video_path / "depth.mp4"
        if depth_path.exists():
            inputs["depth"] = str(depth_path)

        # Add segmentation path only if the file exists
        seg_path = video_path / "segmentation.mp4"
        if seg_path.exists():
            inputs["seg"] = str(seg_path)

        # Create prompt using service
        prompt = service.create_prompt(
            model_type="transfer",
            prompt_text=prompt_text,
            inputs=inputs,
            parameters={
                "negative_prompt": negative_prompt,
                "name": name or f"ui_prompt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            },
        )

        return prompt["id"], f"Created prompt: {prompt['id']}"

    except Exception as e:
        return "", f"Error creating prompt: {e}"


def list_prompts_for_table():
    """Get list of prompts formatted for the enhanced table with selection."""
    try:
        prompts = service.list_prompts(limit=200)

        if not prompts:
            return pd.DataFrame(), [], "No prompts yet"

        data = []
        prompt_ids = []

        for prompt in prompts:
            # Get name from parameters or use default
            name = prompt.get("parameters", {}).get("name", "unnamed")

            # Check if this is an enhanced/upsampled prompt
            is_enhanced = prompt.get("parameters", {}).get("enhanced", False)

            # Get parent prompt ID if this is enhanced
            parent_id = prompt.get("parameters", {}).get("parent_prompt_id", "")
            if parent_id:
                parent_id = parent_id[:8] + "..."

            # Format the prompt text to avoid cutoff
            prompt_text = prompt["prompt_text"]
            if len(prompt_text) > 100:
                prompt_text = prompt_text[:97] + "..."

            # Format date without T and seconds
            created_date = prompt["created_at"][:16].replace("T", " ")  # YYYY-MM-DD HH:MM

            data.append(
                {
                    "Select": False,
                    "Name": name,
                    "Prompt Text": prompt_text,
                    "Enhanced": "Yes" if is_enhanced else "No",
                    "Parent": parent_id if parent_id else "-",
                    "Model": prompt.get("model_type", "transfer"),
                    "Created": created_date,
                    "ID": prompt["id"][:12] + "...",
                }
            )
            prompt_ids.append(prompt["id"])

        df = pd.DataFrame(data)
        return df, prompt_ids, ""

    except Exception as e:
        logger.error("Error listing prompts for table: %s", e)
        return pd.DataFrame(), [], f"Error: {e}"


def get_prompt_details_with_videos(selected_prompt_id):
    """Get detailed view of a prompt including input videos."""
    if not selected_prompt_id:
        return gr.update(visible=False), "", "", "", "", []

    try:
        prompt = service.get_prompt(selected_prompt_id)
        if not prompt:
            return gr.update(visible=False), "Prompt not found", "", "", "", []

        # Build additional info string
        additional_info = f"**ID:** {prompt['id']}\n"
        additional_info += f"**Model Type:** {prompt.get('model_type', 'transfer')}\n"
        additional_info += f"**Created:** {prompt['created_at'][:19].replace('T', ' ')}\n"

        # Check if enhanced
        params = prompt.get("parameters", {})
        if params.get("enhanced"):
            additional_info += "**Enhanced:** Yes\n"
            if params.get("parent_prompt_id"):
                additional_info += f"**Parent Prompt:** {params['parent_prompt_id'][:12]}...\n"
            if params.get("enhancement_model"):
                additional_info += f"**Enhancement Model:** {params['enhancement_model']}\n"
            if params.get("enhanced_at"):
                additional_info += (
                    f"**Enhanced At:** {params['enhanced_at'][:19].replace('T', ' ')}\n"
                )
        else:
            additional_info += "**Enhanced:** No\n"

        # Count associated runs
        runs = service.list_runs(prompt_id=selected_prompt_id, limit=100)
        additional_info += f"**Associated Runs:** {len(runs)}\n"

        # Check video files status
        inputs = prompt.get("inputs", {})
        video_count = 0
        missing_videos = []
        if inputs:
            for video_type, path in [
                ("color", inputs.get("video")),
                ("depth", inputs.get("depth")),
                ("segmentation", inputs.get("seg")),
            ]:
                if path:
                    if Path(path).exists():
                        video_count += 1
                    else:
                        missing_videos.append(video_type)

        additional_info += f"**Videos:** {video_count} available"
        if missing_videos:
            additional_info += f" (Missing: {', '.join(missing_videos)})"

        # Get name for title
        name = params.get("name", "unnamed")

        # Full prompt text
        full_prompt_text = prompt["prompt_text"]

        # Negative prompt
        neg_prompt = params.get("negative_prompt", "")

        # Prepare video previews with proper paths
        video_previews = []
        if inputs:
            for video_type, path in [
                ("Color", inputs.get("video")),
                ("Depth", inputs.get("depth")),
                ("Segmentation", inputs.get("seg")),
            ]:
                if path and Path(path).exists():
                    video_previews.append((str(path), video_type))

        return (
            gr.update(visible=True, open=True),
            name,
            full_prompt_text,
            neg_prompt,
            additional_info,
            video_previews,
        )

    except Exception as e:
        return gr.update(visible=False), f"Error: {e}", "", "", "", []


def run_prompt_enhancer(
    selected_prompts: list[str], overwrite_mode: bool, model: str = "pixtral"
) -> tuple[str, str]:
    """Run prompt enhancement on selected prompts."""
    if not selected_prompts:
        return "", "Please select at least one prompt"

    try:
        results = []
        errors = []

        for prompt_id in selected_prompts:
            # Get the original prompt
            original_prompt = service.get_prompt(prompt_id)
            if not original_prompt:
                errors.append(f"Prompt {prompt_id} not found")
                continue

            if overwrite_mode:
                # Check if prompt has associated runs
                runs = service.list_runs(prompt_id=prompt_id, limit=1)
                if runs:
                    errors.append(
                        f"Cannot overwrite {prompt_id[:12]}... - has {len(runs)} associated run(s). "
                        "Delete runs first or use 'Create New' mode."
                    )
                    continue

            # Create enhancement run
            try:
                enhancement_run = service.create_run(
                    prompt_id=prompt_id,
                    execution_config={
                        "model": model,
                        "type": "enhancement",
                        "temperature": 0.7,
                    },
                    metadata={"purpose": "prompt_enhancement"},
                )

                # Update status
                service.update_run_status(enhancement_run["id"], "running")

                # Run enhancement
                enhanced_text = orchestrator.run_prompt_upsampling(
                    prompt_text=original_prompt["prompt_text"],
                    model=model,
                )

                if overwrite_mode:
                    # Update existing prompt
                    service.update_prompt(
                        prompt_id,
                        prompt_text=enhanced_text,
                        parameters={
                            **original_prompt.get("parameters", {}),
                            "enhanced": True,
                            "enhancement_model": model,
                            "enhanced_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    results.append(f"Updated {prompt_id[:12]}...")
                else:
                    # Create new enhanced prompt
                    name = original_prompt.get("parameters", {}).get("name", "unnamed")
                    enhanced_prompt = service.create_prompt(
                        model_type="transfer",
                        prompt_text=enhanced_text,
                        inputs=original_prompt["inputs"],
                        parameters={
                            **original_prompt.get("parameters", {}),
                            "name": f"{name}_enhanced",
                            "enhanced": True,
                            "parent_prompt_id": prompt_id,
                            "enhancement_model": model,
                        },
                    )
                    results.append(
                        f"Created {enhanced_prompt['id'][:12]}... from {prompt_id[:12]}..."
                    )

                # Update run status
                service.update_run_status(enhancement_run["id"], "completed")
                service.update_run(
                    enhancement_run["id"],
                    outputs={
                        "type": "text_enhancement",
                        "enhanced_text": enhanced_text[:500],
                        "model_used": model,
                    },
                )

            except Exception as e:
                errors.append(f"Failed to enhance {prompt_id[:12]}...: {e}")

        # Format results
        status = ""
        if results:
            status += f"Successfully enhanced {len(results)} prompt(s):\n"
            status += "\n".join(f"  - {r}" for r in results)

        if errors:
            if status:
                status += "\n\n"
            status += f"Errors ({len(errors)}):\n"
            status += "\n".join(f"  - {e}" for e in errors)

        return status, "Enhancement complete" if results else "Enhancement failed"

    except Exception as e:
        return "", f"Error running enhancement: {e}"


def preview_prompt_deletion_ui(selected_prompts: list[str]) -> str:
    """Preview what will be deleted for selected prompts."""
    if not selected_prompts:
        return "No prompts selected"

    try:
        preview_text = "### Deletion Preview\n\n"
        total_runs = 0
        total_dirs = 0

        for prompt_id in selected_prompts:
            preview = service.preview_prompt_deletion(prompt_id)

            if preview.get("error"):
                preview_text += f"**{prompt_id[:12]}...:** {preview['error']}\n\n"
                continue

            prompt_info = preview["prompt"]
            runs = preview.get("runs", [])
            dirs = preview.get("directories_to_delete", [])

            preview_text += f"**Prompt {prompt_id[:12]}...:**\n"
            preview_text += f"  - Text: {prompt_info['prompt_text'][:50]}...\n"
            preview_text += f"  - Runs to delete: {len(runs)}\n"
            preview_text += f"  - Directories to delete: {len(dirs)}\n\n"

            total_runs += len(runs)
            total_dirs += len(dirs)

        preview_text += "\n**Total Impact:**\n"
        preview_text += f"  - Prompts: {len(selected_prompts)}\n"
        preview_text += f"  - Runs: {total_runs}\n"
        preview_text += f"  - Directories: {total_dirs}\n"

        return preview_text

    except Exception as e:
        return f"Error generating preview: {e}"


def run_inference_with_live_logs(
    prompt_id: str,
    vis_weight: float = 0.25,
    edge_weight: float = 0.25,
    depth_weight: float = 0.25,
    seg_weight: float = 0.25,
    enable_upscaling: bool = False,
    upscale_weight: float = 0.5,
) -> tuple[str, str, str]:
    """Run inference on selected prompt with live log streaming."""
    if not prompt_id:
        return "", "Please select a prompt first", ""

    try:
        # Get prompt
        prompt = service.get_prompt(prompt_id)
        if not prompt:
            return "", "Prompt not found", ""

        # Create run with execution config
        execution_config = {
            "weights": {
                "vis": vis_weight,
                "edge": edge_weight,
                "depth": depth_weight,
                "seg": seg_weight,
            }
        }

        run = service.create_run(prompt_id=prompt_id, execution_config=execution_config)
        run_id = run["id"]

        # Initialize log tracking
        with log_lock:
            active_run_logs[run_id] = []

        # Execute in background
        def execute():
            try:
                service.update_run_status(run_id, "running")

                # Add log entry
                with log_lock:
                    active_run_logs[run_id].append(
                        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Starting inference..."
                    )

                result = orchestrator.execute_run(
                    run,
                    prompt,
                    upscale=enable_upscaling,
                    upscale_weight=upscale_weight,
                    enable_logging=True,
                )

                service.update_run(run_id, outputs=result or {})
                service.update_run_status(run_id, "completed")

                with log_lock:
                    active_run_logs[run_id].append(
                        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Inference completed!"
                    )

            except Exception as e:
                service.update_run_status(run_id, "failed")
                logger.error("Run failed: %s", e)

                with log_lock:
                    active_run_logs[run_id].append(
                        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] ERROR: {e}"
                    )

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

        config_summary = (
            f"Weights: vis={vis_weight}, edge={edge_weight}, depth={depth_weight}, seg={seg_weight}"
        )
        if enable_upscaling:
            config_summary += f", Upscaling: {upscale_weight}"

        return run_id, f"Started run {run_id}", config_summary

    except Exception as e:
        return "", f"Error: {e}", ""


def get_live_logs(run_id: str) -> str:
    """Get live logs for a running inference."""
    if not run_id:
        return "No run selected"

    # Check memory logs first
    with log_lock:
        if run_id in active_run_logs:
            return "\n".join(active_run_logs[run_id][-100:])  # Last 100 lines

    # Fall back to log file
    log_path = Path(f"logs/runs/{run_id}.log")

    if not log_path.exists():
        return f"Waiting for run {run_id} to start..."

    try:
        return tail_log_file(run_id, 100)
    except Exception as e:
        return f"Error reading log: {e}"


def tail_log_file(run_id, num_lines=100):
    """Efficiently read last N lines from log file."""
    if not run_id:
        return "No run selected"

    log_path = Path(f"logs/runs/{run_id}.log")

    if not log_path.exists():
        return f"Waiting for run {run_id} to start..."

    try:
        with open(log_path, "rb") as f:
            # Start from the end of the file
            f.seek(0, 2)
            file_length = f.tell()

            if file_length == 0:
                return "Starting..."

            # Read blocks from the end until we have enough lines
            BLOCK_SIZE = 1024
            blocks = []
            lines_found = 0
            block_end_byte = file_length
            block_number = -1

            while lines_found < num_lines and block_end_byte > 0:
                # Calculate how much to read
                if block_end_byte - BLOCK_SIZE > 0:
                    # Read a full block
                    f.seek(block_number * BLOCK_SIZE, 2)
                    blocks.append(f.read(BLOCK_SIZE))
                else:
                    # Read from beginning of file
                    f.seek(0, 0)
                    blocks.append(f.read(block_end_byte))

                # Count lines in this block
                lines_found += blocks[-1].count(b"\n")
                block_end_byte -= BLOCK_SIZE
                block_number -= 1

            # Combine blocks in correct order and decode
            all_text = b"".join(reversed(blocks))
            text = all_text.decode("utf-8", errors="replace")

            # Return only the last num_lines
            lines = text.splitlines()
            return "\n".join(lines[-num_lines:])

    except Exception as e:
        return f"Error reading log: {e}"


def get_completed_videos():
    """Get paths to completed videos for gallery."""
    runs = service.list_runs(status="completed", limit=20)
    videos = []

    for run in runs:
        outputs = run.get("outputs", {})

        # Skip non-video runs (e.g., text enhancement)
        if outputs.get("type") == "text_enhancement":
            continue

        # Use the output_path from the run outputs
        output_path = outputs.get("output_path")
        if not output_path:
            # Fallback for older runs without output_path
            run_name = f"run_{run['id']}"
            output_path = f"outputs/{run_name}/output.mp4"

        # Check if the file actually exists
        if Path(output_path).exists():
            try:
                prompt = service.get_prompt(run["prompt_id"])
                label = f"{prompt['prompt_text'][:30]}... (Run: {run['id'][:8]})"
            except Exception:
                label = f"Run {run['id'][:8]}"

            videos.append((str(output_path), label))

    return videos


def get_gpu_status():
    """Get current GPU and Docker status."""
    global ssh_manager, docker_executor

    try:
        if not ssh_manager:
            remote_config = config.get_remote_config()
            ssh_options = config.get_ssh_options()
            ssh_manager = SSHManager(ssh_options)
            docker_executor = DockerExecutor(
                ssh_manager, remote_config.remote_dir, remote_config.docker_image
            )

        with ssh_manager:
            gpu_output = ssh_manager.execute_command_success(
                "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader",
                stream_output=False,
            )

            docker_status = docker_executor.get_docker_status()

            status_text = "### GPU Status\n"
            status_text += "```\n" + gpu_output + "```\n\n"

            if docker_status["docker_running"]:
                status_text += "### Docker Status\n"
                status_text += "[OK] Docker is running\n\n"

                containers = docker_status.get("running_containers", "")
                if "CONTAINER ID" in containers:
                    lines = containers.split("\n")
                    if len(lines) > 1:
                        status_text += f"**Active Containers:** {len(lines) - 1}\n"
                else:
                    status_text += "**Active Containers:** 0\n"
            else:
                status_text += "### Docker Status\n"
                status_text += "[ERROR] Docker is not running\n"

            status_text += "\n*Auto-refreshing every 5 seconds*"
            return status_text

    except Exception as e:
        return f"### Status Check Failed\n\nError: {e}\n\nMake sure the GPU instance is running.\n\n*Auto-refreshing every 5 seconds*"


def handle_prompt_selection(df: pd.DataFrame, evt: gr.SelectData):
    """Handle clicking on a row in the prompts table."""
    if evt.index[0] is not None:
        # Get the full prompt ID from the hidden column
        prompt_id = df.iloc[evt.index[0]]["ID"]
        # Remove the "..." suffix if present
        if prompt_id.endswith("..."):
            prompt_id = prompt_id[:-3]
            # Need to get the full ID from service
            prompts = service.list_prompts(limit=200)
            for p in prompts:
                if p["id"].startswith(prompt_id):
                    prompt_id = p["id"]
                    break

        # Get prompt details
        details_visible, name, full_text, neg_prompt, additional_info, video_previews = (
            get_prompt_details_with_videos(prompt_id)
        )

        return (
            prompt_id,
            df,
            details_visible,
            gr.update(value=name),
            gr.update(value=full_text),
            gr.update(value=neg_prompt),
            gr.update(value=additional_info),
            gr.update(value=video_previews if video_previews else []),
        )

    return (
        "",
        df,
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=""),
        gr.update(value=[]),
    )


def create_interface():
    """Create the enhanced Gradio interface."""
    with gr.Blocks(title="Cosmos Workflow", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# Cosmos Transfer Workflow - Enhanced UI")

        # Hidden state for selected prompt
        selected_prompt_state = gr.State("")

        with gr.Tabs():
            # PROMPTS TAB - Enhanced with selection and details
            with gr.TabItem("Prompts"):
                with gr.Row():
                    # Left side - Prompts table
                    with gr.Column(scale=2):
                        gr.Markdown("### Prompt Management")

                        # Prompts table with checkbox selection
                        prompts_df, prompt_ids_state, prompts_message = list_prompts_for_table()

                        prompts_table = gr.Dataframe(
                            value=prompts_df,
                            headers=[
                                "Select",
                                "Name",
                                "Prompt Text",
                                "Enhanced",
                                "Parent",
                                "Model",
                                "Created",
                                "ID",
                            ],
                            datatype=["bool", "str", "str", "str", "str", "str", "str", "str"],
                            col_count=(8, "fixed"),
                            interactive=True,
                            wrap=True,
                        )

                        prompt_ids_hidden = gr.State(prompt_ids_state)

                        with gr.Row():
                            refresh_prompts_btn = gr.Button(
                                "Refresh", variant="secondary", size="sm"
                            )
                            delete_selected_btn = gr.Button(
                                "Delete Selected", variant="stop", size="sm"
                            )
                            prompts_status = gr.Textbox(
                                label="Status",
                                value=prompts_message,
                                interactive=False,
                                max_lines=2,
                            )

                        # Deletion confirmation dialog
                        with gr.Group(visible=False) as deletion_confirmation_dialog:
                            deletion_preview_text = gr.Markdown("")
                            selected_ids_for_deletion = gr.State([])

                            with gr.Row():
                                confirm_delete_btn = gr.Button("Confirm Delete", variant="stop")
                                cancel_delete_btn = gr.Button("Cancel", variant="secondary")

                # Right side - Details and actions
                with gr.Column(scale=1):
                    # Prompt Details Section - Collapsible Accordion
                    with gr.Accordion(
                        "Prompt Details", open=False, visible=False
                    ) as prompt_details_accordion:
                        prompt_name_display = gr.Textbox(label="Name", interactive=False)

                        # Full Text and Negative Prompt
                        full_prompt_text = gr.Textbox(
                            label="Full Text", lines=3, max_lines=5, interactive=False
                        )

                        negative_prompt_display = gr.Textbox(
                            label="Negative Prompt", lines=2, interactive=False
                        )

                        # Additional info display
                        additional_info_display = gr.Markdown("")

                        # Video Inputs Section
                        gr.Markdown("**Video Inputs:**")
                        input_videos_gallery = gr.Gallery(
                            label="",
                            show_label=False,
                            columns=3,
                            rows=1,
                            object_fit="contain",
                            height=200,
                            preview=True,
                        )

                    # Action Tabs and Live Logs in a Row
                    with gr.Row():
                        # Left side - Tabs for Run Inference and Run Prompt Upsampler
                        with gr.Column(scale=1):
                            with gr.Tabs():
                                # Run Inference Tab
                                with gr.TabItem("Run Inference"):
                                    gr.Markdown("**Inference Settings**")

                                    with gr.Row():
                                        vis_weight = gr.Slider(
                                            label="Visual Weight",
                                            minimum=0,
                                            maximum=1,
                                            value=0.25,
                                            step=0.05,
                                        )
                                        edge_weight = gr.Slider(
                                            label="Edge Weight",
                                            minimum=0,
                                            maximum=1,
                                            value=0.25,
                                            step=0.05,
                                        )

                                    with gr.Row():
                                        depth_weight = gr.Slider(
                                            label="Depth Weight",
                                            minimum=0,
                                            maximum=1,
                                            value=0.25,
                                            step=0.05,
                                        )
                                        seg_weight = gr.Slider(
                                            label="Segmentation Weight",
                                            minimum=0,
                                            maximum=1,
                                            value=0.25,
                                            step=0.05,
                                        )

                                    enable_upscaling = gr.Checkbox(
                                        label="Enable 4K Upscaling", value=False
                                    )
                                    upscale_weight = gr.Slider(
                                        label="Upscale Weight",
                                        minimum=0,
                                        maximum=1,
                                        value=0.5,
                                        step=0.05,
                                        visible=False,
                                    )

                                    run_inference_btn = gr.Button(
                                        "Run Inference", variant="primary", size="lg"
                                    )
                                    inference_status = gr.Textbox(
                                        label="Status", interactive=False, max_lines=2
                                    )

                                # Run Prompt Upsampler Tab
                                with gr.TabItem("Run Prompt Upsampler"):
                                    gr.Markdown("**Enhancement Settings**")

                                    enhancement_model = gr.Dropdown(
                                        label="Model",
                                        choices=["pixtral", "gpt-4", "claude-3"],
                                        value="pixtral",
                                    )

                                    overwrite_mode = gr.Radio(
                                        label="Mode",
                                        choices=["Create New", "Overwrite"],
                                        value="Create New",
                                    )

                                    # Warning message for overwrite mode
                                    overwrite_warning = gr.Markdown(
                                        "⚠️ **Warning:** Overwriting prompts with associated runs is not allowed.",
                                        visible=False,
                                    )

                                    enhance_btn = gr.Button(
                                        "Enhance Selected Prompts", variant="primary", size="lg"
                                    )
                                    enhance_status = gr.Textbox(
                                        label="Status", interactive=False, max_lines=3
                                    )

                                    # Deletion preview
                                    with gr.Accordion("Deletion Preview", open=False):
                                        deletion_preview = gr.Markdown("No prompts selected")

                        # Right side - Live Logs (larger)
                        with gr.Column(scale=2):
                            gr.Markdown("### Live Logs")
                            live_logs = gr.Textbox(
                                label="Execution Logs",
                                lines=20,
                                max_lines=30,
                                autoscroll=True,
                                interactive=False,
                            )
                            run_id_state = gr.State("")

            # GENERATE TAB - Original functionality
            with gr.TabItem("Generate"):
                with gr.Row():
                    # LEFT COLUMN - Create Prompt
                    with gr.Column():
                        gr.Markdown("### Step 1: Create New Prompt")

                        with gr.Group():
                            gr.Markdown("**Upload Video Files**")
                            color_upload = gr.File(
                                label="Color Video (color.mp4) - Required", file_types=["video"]
                            )
                            depth_upload = gr.File(
                                label="Depth Video (depth.mp4) - Optional", file_types=["video"]
                            )
                            seg_upload = gr.File(
                                label="Segmentation Video (segmentation.mp4) - Optional",
                                file_types=["video"],
                            )

                            upload_btn = gr.Button("Upload Videos", variant="secondary")
                            upload_status = gr.Textbox(label="Upload Status", interactive=False)
                            video_dir = gr.Textbox(visible=False)

                        with gr.Group():
                            gen_prompt_text = gr.Textbox(
                                label="Prompt Text",
                                lines=3,
                                placeholder="A futuristic city at night with neon lights...",
                            )
                            gen_negative_prompt = gr.Textbox(
                                label="Negative Prompt",
                                lines=2,
                                value="blurry, low quality, distorted",
                            )
                            gen_prompt_name = gr.Textbox(
                                label="Prompt Name (Optional)", placeholder="my_awesome_prompt"
                            )

                            create_prompt_btn = gr.Button("Create Prompt", variant="primary")
                            gen_prompt_id_output = gr.Textbox(
                                label="Created Prompt ID", interactive=False
                            )
                            gen_prompt_status = gr.Textbox(label="Status", interactive=False)

            # RUNS TAB
            with gr.TabItem("Runs"):
                gr.Markdown("### Run Management")

                runs_data = []
                runs = service.list_runs(limit=50)
                for run in runs:
                    try:
                        prompt = service.get_prompt(run["prompt_id"])
                        prompt_text = prompt["prompt_text"][:50] + "..."
                    except Exception:
                        prompt_text = "N/A"

                    runs_data.append(
                        [
                            run["id"][:12] + "...",
                            prompt_text,
                            run["status"],
                            run["created_at"],
                            run["id"],
                        ]
                    )

                runs_df = gr.Dataframe(
                    value=runs_data,
                    headers=["ID", "Prompt", "Status", "Created", "Full ID"],
                    datatype=["str", "str", "str", "str", "str"],
                    col_count=5,
                    interactive=False,
                )

                with gr.Row():
                    refresh_runs_btn = gr.Button("Refresh", variant="secondary")
                    runs_message = gr.Textbox(label="Message", interactive=False)

            # GALLERY TAB
            with gr.TabItem("Gallery"):
                gr.Markdown("### Completed Videos")

                gallery = gr.Gallery(
                    label="Generated Videos",
                    show_label=False,
                    columns=3,
                    rows=2,
                    object_fit="contain",
                    height="auto",
                    value=get_completed_videos(),
                )

                with gr.Row():
                    refresh_gallery_btn = gr.Button("Refresh Gallery", variant="secondary")
                    gr.Markdown("*Auto-refreshes every 10 seconds*")

                # Auto-refresh timer for gallery
                gallery_timer = gr.Timer(value=10.0, active=True)
                gallery_timer.tick(fn=get_completed_videos, outputs=[gallery])

            # STATUS TAB
            with gr.TabItem("Status"):
                gr.Markdown("### System Status")
                status_display = gr.Markdown(value=get_gpu_status())

                status_timer = gr.Timer(value=5.0, active=True)
                status_timer.tick(fn=get_gpu_status, outputs=[status_display])

        # Event handlers

        # Prompts tab - table selection
        prompts_table.select(
            fn=handle_prompt_selection,
            inputs=[prompts_table],
            outputs=[
                selected_prompt_state,
                prompts_table,
                prompt_details_accordion,
                prompt_name_display,
                full_prompt_text,
                negative_prompt_display,
                additional_info_display,
                input_videos_gallery,
            ],
        )

        # Refresh prompts
        def refresh_prompts():
            df, ids, msg = list_prompts_for_table()
            return df, ids, msg

        refresh_prompts_btn.click(
            fn=refresh_prompts, outputs=[prompts_table, prompt_ids_hidden, prompts_status]
        )

        # Run inference from prompts tab
        def run_inference_from_prompt(prompt_id, vis, edge, depth, seg, upscale, up_weight):
            if not prompt_id:
                return "", "Please select a prompt first", ""
            run_id, status, config = run_inference_with_live_logs(
                prompt_id, vis, edge, depth, seg, upscale, up_weight
            )
            return run_id, status, config

        run_inference_btn.click(
            fn=run_inference_from_prompt,
            inputs=[
                selected_prompt_state,
                vis_weight,
                edge_weight,
                depth_weight,
                seg_weight,
                enable_upscaling,
                upscale_weight,
            ],
            outputs=[run_id_state, inference_status, live_logs],
        )

        # Enable/disable upscale weight slider
        enable_upscaling.change(
            fn=lambda x: gr.update(visible=x), inputs=[enable_upscaling], outputs=[upscale_weight]
        )

        # Show/hide overwrite warning
        overwrite_mode.change(
            fn=lambda mode: gr.update(visible=(mode == "Overwrite")),
            inputs=[overwrite_mode],
            outputs=[overwrite_warning],
        )

        # Prompt enhancement
        def enhance_selected_prompts(df, overwrite, model):
            # Get selected prompts
            selected = []
            for _i, row in df.iterrows():
                if row["Select"]:
                    # Get full ID from hidden state
                    prompt_id = row["ID"]
                    if prompt_id.endswith("..."):
                        # Need to match with full IDs
                        prompts = service.list_prompts(limit=200)
                        for p in prompts:
                            if p["id"].startswith(prompt_id[:-3]):
                                selected.append(p["id"])
                                break
                    else:
                        selected.append(prompt_id)

            if not selected:
                return "", "Please select prompts to enhance"

            # Check for overwrites with runs
            if overwrite == "Overwrite":
                warnings = []
                for pid in selected:
                    preview = service.preview_prompt_deletion(pid)
                    if preview.get("runs"):
                        warnings.append(f"{pid[:12]}... has {len(preview['runs'])} run(s)")

                if warnings:
                    return "", "Cannot overwrite prompts with runs:\n" + "\n".join(warnings)

            status, msg = run_prompt_enhancer(selected, overwrite == "Overwrite", model)
            return status, msg

        enhance_btn.click(
            fn=enhance_selected_prompts,
            inputs=[prompts_table, overwrite_mode, enhancement_model],
            outputs=[enhance_status, prompts_status],
        ).then(fn=refresh_prompts, outputs=[prompts_table, prompt_ids_hidden, prompts_status])

        # Deletion preview
        def update_deletion_preview(df):
            selected = []
            for _i, row in df.iterrows():
                if row["Select"]:
                    prompt_id = row["ID"]
                    if prompt_id.endswith("..."):
                        prompts = service.list_prompts(limit=200)
                        for p in prompts:
                            if p["id"].startswith(prompt_id[:-3]):
                                selected.append(p["id"])
                                break
                    else:
                        selected.append(prompt_id)

            if selected:
                return preview_prompt_deletion_ui(selected)
            return "No prompts selected"

        prompts_table.change(
            fn=update_deletion_preview, inputs=[prompts_table], outputs=[deletion_preview]
        )

        # Delete selected prompts with confirmation
        def prepare_deletion_confirmation(df):
            selected = []
            for _i, row in df.iterrows():
                if row["Select"]:
                    prompt_id = row["ID"]
                    if prompt_id.endswith("..."):
                        prompts = service.list_prompts(limit=200)
                        for p in prompts:
                            if p["id"].startswith(prompt_id[:-3]):
                                selected.append(p["id"])
                                break
                    else:
                        selected.append(prompt_id)

            if not selected:
                return (
                    gr.update(visible=False),
                    gr.update(value=""),
                    "No prompts selected for deletion",
                )

            # Generate detailed deletion preview
            preview_text = "### ⚠️ Deletion Confirmation\n\n"
            preview_text += f"You are about to delete **{len(selected)} prompt(s)**.\n\n"

            total_runs = 0
            total_dirs = 0

            for prompt_id in selected:
                preview = service.preview_prompt_deletion(prompt_id)
                if not preview.get("error"):
                    runs = preview.get("runs", [])
                    dirs = preview.get("directories_to_delete", [])
                    total_runs += len(runs)
                    total_dirs += len(dirs)

                    prompt_info = preview["prompt"]
                    preview_text += (
                        f"**{prompt_id[:12]}...**: {prompt_info['prompt_text'][:50]}...\n"
                    )
                    if runs:
                        preview_text += f"  - Will delete {len(runs)} run(s)\n"
                    if dirs:
                        preview_text += f"  - Will delete {len(dirs)} output director(y/ies)\n"
                    preview_text += "\n"

            preview_text += "\n**Total Impact:**\n"
            preview_text += f"- **{len(selected)}** prompts will be deleted\n"
            preview_text += f"- **{total_runs}** runs will be deleted\n"
            preview_text += f"- **{total_dirs}** output directories will be deleted\n\n"
            preview_text += "**This action cannot be undone!**"

            # Store selected IDs for actual deletion
            return gr.update(visible=True), gr.update(value=preview_text), gr.update(value=selected)

        def execute_deletion(selected_ids):
            if not selected_ids:
                return "No prompts selected", gr.update(visible=False)

            deleted = 0
            errors = []
            for pid in selected_ids:
                result = service.delete_prompt(pid)
                if result["success"]:
                    deleted += 1
                else:
                    errors.append(f"{pid[:12]}...: {result.get('error', 'Unknown error')}")

            status = f"Successfully deleted {deleted} prompt(s)"
            if errors:
                status += "\n\nErrors:\n" + "\n".join(errors)

            return status, gr.update(visible=False)

        def cancel_deletion():
            return "Deletion cancelled", gr.update(visible=False)

        delete_selected_btn.click(
            fn=prepare_deletion_confirmation,
            inputs=[prompts_table],
            outputs=[
                deletion_confirmation_dialog,
                deletion_preview_text,
                selected_ids_for_deletion,
            ],
        )

        confirm_delete_btn.click(
            fn=execute_deletion,
            inputs=[selected_ids_for_deletion],
            outputs=[prompts_status, deletion_confirmation_dialog],
        ).then(fn=refresh_prompts, outputs=[prompts_table, prompt_ids_hidden, prompts_status])

        cancel_delete_btn.click(
            fn=cancel_deletion, outputs=[prompts_status, deletion_confirmation_dialog]
        )

        # Live logs timer
        log_timer = gr.Timer(value=1.0, active=True)
        log_timer.tick(fn=get_live_logs, inputs=[run_id_state], outputs=[live_logs])

        # Generate tab handlers
        upload_btn.click(
            fn=handle_video_uploads,
            inputs=[color_upload, depth_upload, seg_upload],
            outputs=[video_dir, upload_status],
        )

        create_prompt_btn.click(
            fn=create_prompt_with_videos,
            inputs=[gen_prompt_text, gen_negative_prompt, video_dir, gen_prompt_name],
            outputs=[gen_prompt_id_output, gen_prompt_status],
        ).then(fn=refresh_prompts, outputs=[prompts_table, prompt_ids_hidden, prompts_status])

        # Runs tab refresh
        def refresh_runs():
            runs_data = []
            runs = service.list_runs(limit=50)
            for run in runs:
                try:
                    prompt = service.get_prompt(run["prompt_id"])
                    prompt_text = prompt["prompt_text"][:50] + "..."
                except Exception:
                    prompt_text = "N/A"

                runs_data.append(
                    [
                        run["id"][:12] + "...",
                        prompt_text,
                        run["status"],
                        run["created_at"],
                        run["id"],
                    ]
                )
            return runs_data, f"Showing {len(runs_data)} runs"

        refresh_runs_btn.click(fn=refresh_runs, outputs=[runs_df, runs_message])

        # Gallery refresh
        refresh_gallery_btn.click(fn=get_completed_videos, outputs=[gallery])

        # Initial data load
        interface.load(
            fn=refresh_prompts, outputs=[prompts_table, prompt_ids_hidden, prompts_status]
        )
        interface.load(fn=refresh_runs, outputs=[runs_df, runs_message])

    return interface


if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_port=7860, inbrowser=True)
