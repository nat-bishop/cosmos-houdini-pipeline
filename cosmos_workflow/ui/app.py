"""Gradio UI for Cosmos Workflow - Fixed Version."""

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

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

        return prompt["id"], f"Created prompt: {prompt['id']} - {prompt['name']}"

    except Exception as e:
        return "", f"Error creating prompt: {e}"


def list_prompts_for_dropdown():
    """Get list of prompts for dropdown selection."""
    try:
        prompts = service.list_prompts(limit=100)
        # Return list of tuples (display_name, value)
        choices = []
        for p in prompts:
            # Get name from parameters or use default
            name = p.get("parameters", {}).get("name", "unnamed")
            display = f"{p['id'][:8]}... - {name} - {p['prompt_text'][:50]}..."
            choices.append((display, p["id"]))
        return choices
    except Exception as e:
        logger.error("Error listing prompts for dropdown: %s", e)
        return []


def get_prompt_details(prompt_id):
    """Get details of selected prompt."""
    if not prompt_id:
        return "No prompt selected"

    try:
        prompt = service.get_prompt(prompt_id)

        details = f"**ID:** {prompt['id']}\n"
        name = prompt.get("parameters", {}).get("name", "unnamed")
        details += f"**Name:** {name}\n"
        details += f"**Text:** {prompt['prompt_text']}\n"
        details += f"**Negative:** {prompt.get('parameters', {}).get('negative_prompt', 'None')}\n"

        # Show video inputs with full paths and status
        inputs = prompt.get("inputs", {})
        if inputs:
            details += "\n**Video Inputs:**\n"

            # Always show color video (required)
            color_path = inputs.get("video", "")
            if color_path:
                exists = "[OK]" if Path(color_path).exists() else "[MISSING]"
                details += f"- **Color**: `{color_path}` {exists}\n"
            else:
                details += "- **Color**: Not provided [ERROR]\n"

            # Show depth video (optional)
            depth_path = inputs.get("depth", "")
            if depth_path:
                exists = "[OK]" if Path(depth_path).exists() else "[MISSING]"
                details += f"- **Depth**: `{depth_path}` {exists}\n"
            else:
                details += "- **Depth**: Not provided (optional)\n"

            # Show segmentation video (optional)
            seg_path = inputs.get("seg", "")
            if seg_path:
                exists = "[OK]" if Path(seg_path).exists() else "[MISSING]"
                details += f"- **Segmentation**: `{seg_path}` {exists}\n"
            else:
                details += "- **Segmentation**: Not provided (optional)\n"
        else:
            details += "\n**Video Inputs:** None provided [ERROR]\n"

        return details

    except Exception as e:
        return f"Error loading prompt: {e}"


def run_inference_on_prompt(
    prompt_id,
    vis_weight=0.25,
    edge_weight=0.25,
    depth_weight=0.25,
    seg_weight=0.25,
    enable_upscaling=False,
    upscale_weight=0.5,
):
    """Run inference on selected prompt."""
    if not prompt_id:
        return "", "", "Please select a prompt first"

    try:
        # Get prompt
        prompt = service.get_prompt(prompt_id)

        # Create run with execution config with all 4 control weights
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

        # Execute in background
        def execute():
            try:
                service.update_run_status(run_id, "running")
                result = orchestrator.execute_run(
                    run,
                    prompt,
                    upscale=enable_upscaling,
                    upscale_weight=upscale_weight,
                    enable_logging=True,
                )
                service.update_run(run_id, outputs=result or {})
                service.update_run_status(run_id, "completed")
            except Exception as e:
                service.update_run_status(run_id, "failed")
                logger.error("Run failed: %s", e)

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


def tail_log_file(run_id, num_lines=100):
    """Efficiently read last N lines from log file using seek-based approach.

    This implementation is optimized for large files and only reads the necessary
    blocks from the end of the file, similar to Nvidia's approach.
    """
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


def list_runs_interactive():
    """Create interactive runs table."""
    runs = service.list_runs(limit=50)

    if not runs:
        return [], "No runs yet"

    # Prepare data for dataframe
    data = []
    for run in runs:
        try:
            prompt = service.get_prompt(run["prompt_id"])
            prompt_text = prompt["prompt_text"][:50] + "..."
        except Exception:
            prompt_text = "N/A"

        data.append(
            [
                run["id"][:12] + "...",
                prompt_text,
                run["status"],
                run["created_at"],
                run["id"],  # Full ID for actions
            ]
        )

    return data, ""


def delete_run(run_id):
    """Delete a run (if supported by service)."""
    try:
        # Check if service has delete method
        if hasattr(service, "delete_run"):
            service.delete_run(run_id)
            return "Run deleted successfully"
        else:
            return "Delete not supported by service"
    except Exception as e:
        return f"Error deleting run: {e}"


def list_prompts_table():
    """Create prompts table for management with improved video status display."""
    prompts = service.list_prompts(limit=100)

    if not prompts:
        return [], "No prompts yet"

    data = []
    for prompt in prompts:
        # Check which videos exist and count them
        inputs = prompt.get("inputs", {})
        missing_videos = []
        existing_videos = []

        if inputs:
            for video_type, path in inputs.items():
                if path:
                    if Path(path).exists():
                        existing_videos.append(video_type)
                    else:
                        missing_videos.append(video_type)

        # Create video status with warning if any missing
        if missing_videos:
            # Show warning with count (ASCII-safe for Windows)
            video_status = f"[!] Missing ({len(missing_videos)})"
        elif existing_videos:
            # Show OK with count of videos provided
            video_status = f"[OK] ({len(existing_videos)} videos)"
        else:
            video_status = "No videos"

        # Get name from parameters or use default
        name = prompt.get("parameters", {}).get("name", "unnamed")

        data.append(
            [
                prompt["id"][:12] + "...",
                name,
                prompt["prompt_text"][:50] + "...",
                video_status,
                prompt["created_at"],
                prompt["id"],  # Full ID for actions
            ]
        )

    return data, ""


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


def create_interface():
    with gr.Blocks(title="Cosmos Workflow", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🚀 Cosmos Transfer Workflow")

        with gr.Tabs():
            # GENERATE TAB - Redesigned with proper workflow
            with gr.TabItem("🎬 Generate"):
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

                            upload_btn = gr.Button("📤 Upload Videos", variant="secondary")
                            upload_status = gr.Textbox(label="Upload Status", interactive=False)
                            video_dir = gr.Textbox(visible=False)  # Hidden field to store path

                        with gr.Group():
                            prompt_text = gr.Textbox(
                                label="Prompt Text",
                                lines=3,
                                placeholder="A futuristic city at night with neon lights...",
                            )
                            negative_prompt = gr.Textbox(
                                label="Negative Prompt",
                                lines=2,
                                value="blurry, low quality, distorted",
                            )
                            prompt_name = gr.Textbox(
                                label="Prompt Name (Optional)", placeholder="my_awesome_prompt"
                            )

                            create_prompt_btn = gr.Button("Create Prompt", variant="primary")
                            prompt_id_output = gr.Textbox(
                                label="Created Prompt ID", interactive=False
                            )
                            prompt_status = gr.Textbox(label="Status", interactive=False)

                    # RIGHT COLUMN - Run Inference
                    with gr.Column():
                        gr.Markdown("### Step 2: Run Inference")

                        with gr.Group():
                            gr.Markdown("**Select Existing Prompt**")
                            prompt_dropdown = gr.Dropdown(
                                label="Select Prompt",
                                choices=list_prompts_for_dropdown(),
                                interactive=True,
                            )
                            refresh_prompts_btn = gr.Button("🔄 Refresh List", variant="secondary")

                            prompt_details = gr.Markdown("No prompt selected")

                        with gr.Group():
                            gr.Markdown("**Inference Settings**")

                            with gr.Row():
                                vis_weight = gr.Slider(
                                    label="Visual Weight",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )
                                edge_weight = gr.Slider(
                                    label="Edge Weight",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )

                            with gr.Row():
                                depth_weight = gr.Slider(
                                    label="Depth Weight",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )
                                seg_weight = gr.Slider(
                                    label="Segmentation Weight",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )

                            with gr.Accordion("🔧 Advanced Settings", open=False):
                                enable_upscaling = gr.Checkbox(
                                    label="Enable 4K Upscaling", value=False
                                )
                                upscale_weight = gr.Slider(
                                    label="Upscale Weight",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.5,
                                    step=0.05,
                                    visible=False,
                                )
                                enable_upscaling.change(
                                    fn=lambda x: gr.update(visible=x),
                                    inputs=[enable_upscaling],
                                    outputs=[upscale_weight],
                                )

                            run_inference_btn = gr.Button(
                                "🚀 Run Inference", variant="primary", size="lg"
                            )

                            run_id_output = gr.Textbox(label="Run ID", interactive=False)
                            run_status = gr.Textbox(label="Status", interactive=False)
                            run_config = gr.Textbox(label="Configuration", interactive=False)

                        # Log viewer
                        with gr.Column(visible=False) as log_section:
                            gr.Markdown("### 📊 Live Logs")
                            logs = gr.Textbox(
                                label="Docker Output", lines=15, autoscroll=True, interactive=False
                            )

                            log_timer = gr.Timer(value=1.0, active=True)
                            log_timer.tick(
                                fn=lambda rid: tail_log_file(rid) if rid else "",
                                inputs=[run_id_output],
                                outputs=[logs],
                            )

                # Event handlers for Generate tab
                upload_btn.click(
                    fn=handle_video_uploads,
                    inputs=[color_upload, depth_upload, seg_upload],
                    outputs=[video_dir, upload_status],
                )

                create_prompt_btn.click(
                    fn=create_prompt_with_videos,
                    inputs=[prompt_text, negative_prompt, video_dir, prompt_name],
                    outputs=[prompt_id_output, prompt_status],
                ).then(
                    fn=lambda: gr.update(choices=list_prompts_for_dropdown()),
                    outputs=[prompt_dropdown],
                )

                refresh_prompts_btn.click(
                    fn=lambda: gr.update(choices=list_prompts_for_dropdown()),
                    outputs=[prompt_dropdown],
                )

                prompt_dropdown.change(
                    fn=get_prompt_details, inputs=[prompt_dropdown], outputs=[prompt_details]
                )

                def run_and_show_logs(prompt_id, vis, edge, depth, seg, upscale, up_weight):
                    run_id, status, config = run_inference_on_prompt(
                        prompt_id, vis, edge, depth, seg, upscale, up_weight
                    )
                    return run_id, status, config, gr.update(visible=bool(run_id))

                run_inference_btn.click(
                    fn=run_and_show_logs,
                    inputs=[
                        prompt_dropdown,
                        vis_weight,
                        edge_weight,
                        depth_weight,
                        seg_weight,
                        enable_upscaling,
                        upscale_weight,
                    ],
                    outputs=[run_id_output, run_status, run_config, log_section],
                )

            # PROMPTS TAB - New management interface
            with gr.TabItem("📝 Prompts"):
                gr.Markdown("### Prompt Management")

                prompts_df = gr.Dataframe(
                    headers=["ID", "Name", "Text", "Videos", "Created", "Full ID"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    col_count=6,
                    interactive=False,
                )

                with gr.Row():
                    refresh_prompts_table_btn = gr.Button("🔄 Refresh", variant="secondary")
                    prompts_message = gr.Textbox(label="Message", interactive=False)

                refresh_prompts_table_btn.click(
                    fn=list_prompts_table, outputs=[prompts_df, prompts_message]
                )

                interface.load(fn=list_prompts_table, outputs=[prompts_df, prompts_message])

            # RUNS TAB - Enhanced with interactive features
            with gr.TabItem("📊 Runs"):
                gr.Markdown("### Run Management")

                runs_df = gr.Dataframe(
                    headers=["ID", "Prompt", "Status", "Created", "Full ID"],
                    datatype=["str", "str", "str", "str", "str"],
                    col_count=5,
                    interactive=False,
                )

                with gr.Row():
                    refresh_runs_btn = gr.Button("🔄 Refresh", variant="secondary")
                    runs_message = gr.Textbox(label="Message", interactive=False)

                refresh_runs_btn.click(fn=list_runs_interactive, outputs=[runs_df, runs_message])

                interface.load(fn=list_runs_interactive, outputs=[runs_df, runs_message])

            # GALLERY TAB - Fixed to show actual videos
            with gr.TabItem("🎨 Gallery"):
                gr.Markdown("### Completed Videos")

                gallery = gr.Gallery(
                    label="Generated Videos",
                    show_label=False,
                    columns=3,
                    rows=2,
                    object_fit="contain",
                    height="auto",
                )

                with gr.Row():
                    refresh_gallery_btn = gr.Button("🔄 Refresh Gallery", variant="secondary")
                    gr.Markdown("*Auto-refreshes every 10 seconds*")

                # Auto-refresh timer for gallery
                gallery_timer = gr.Timer(value=10.0, active=True)
                gallery_timer.tick(fn=get_completed_videos, outputs=[gallery])

                refresh_gallery_btn.click(fn=get_completed_videos, outputs=[gallery])

                interface.load(fn=get_completed_videos, outputs=[gallery])

            # STATUS TAB
            with gr.TabItem("🖥️ Status"):
                gr.Markdown("### System Status")
                status_display = gr.Markdown()

                status_timer = gr.Timer(value=5.0, active=True)
                status_timer.tick(fn=get_gpu_status, outputs=[status_display])

                interface.load(fn=get_gpu_status, outputs=[status_display])

        # Load initial data
        interface.load(
            fn=lambda: gr.update(choices=list_prompts_for_dropdown()), outputs=[prompt_dropdown]
        )

    return interface


if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_port=7860, inbrowser=True)
