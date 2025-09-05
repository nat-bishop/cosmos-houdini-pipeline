"""Gradio UI for Cosmos Workflow."""

import logging
import threading
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

# Global initialization (NVIDIA's pattern)
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


def tail_log_file(run_id: str, num_lines: int = 100) -> str:
    """Read last N lines from log file - NVIDIA's efficient approach."""
    if not run_id:
        return "No run selected"

    log_path = Path(f"logs/runs/{run_id}.log")

    if not log_path.exists():
        return f"Waiting for run {run_id} to start..."

    try:
        with open(log_path, "rb") as f:
            # NVIDIA's seek-based approach for efficiency
            BLOCK_SIZE = 1024
            f.seek(0, 2)
            file_length = f.tell()

            if file_length == 0:
                return "Starting..."

            # Read from end
            seek_pos = max(0, file_length - BLOCK_SIZE * 10)
            f.seek(seek_pos)
            content = f.read().decode("utf-8", errors="ignore")

            lines = content.splitlines()
            return "\n".join(lines[-num_lines:])

    except Exception as e:
        return f"Error reading log: {e}"


def list_runs_html():
    """Generate HTML table of runs."""
    runs = service.list_runs(limit=20)

    if not runs:
        return "<p>No runs yet</p>"

    html = "<table style='width:100%'>"
    html += "<tr><th>ID</th><th>Status</th><th>Created</th></tr>"

    for run in runs:
        color = {"completed": "green", "running": "orange", "failed": "red"}.get(
            run["status"], "gray"
        )

        html += "<tr>"
        html += f"<td><code>{run['id'][:12]}...</code></td>"
        html += f"<td style='color:{color}'>{run['status']}</td>"
        html += f"<td>{run['created_at']}</td>"
        html += "</tr>"

    html += "</table>"
    return html


def get_completed_videos():
    """Get paths to completed videos for gallery."""
    runs = service.list_runs(status="completed", limit=10)
    videos = []

    for run in runs:
        output_path = run.get("outputs", {}).get("output_path")
        if output_path:
            local_path = Path(output_path)
            if local_path.exists():
                prompt = service.get_prompt(run["prompt_id"])
                videos.append(
                    (str(local_path), f"{prompt['prompt_text'][:30]}... ({run['id'][:8]})")
                )

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

        # Get GPU status
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
                status_text += "✅ Docker is running\n\n"

                # Parse running containers
                containers = docker_status.get("running_containers", "")
                if "CONTAINER ID" in containers:
                    lines = containers.split("\n")
                    if len(lines) > 1:  # Has containers
                        status_text += f"**Active Containers:** {len(lines) - 1}\n"
                else:
                    status_text += "**Active Containers:** 0\n"
            else:
                status_text += "### Docker Status\n"
                status_text += "❌ Docker is not running\n"

            return status_text

    except Exception as e:
        return f"### Status Check Failed\n\nError: {e}\n\nMake sure the GPU instance is running."


def enhance_prompts(prompts_text: str, batch_name: str = "ui_batch"):
    """Enhance multiple prompts using Pixtral model."""
    try:
        # Parse prompts (one per line)
        prompts = [p.strip() for p in prompts_text.strip().split("\n") if p.strip()]

        if not prompts:
            return "Please enter at least one prompt", ""

        enhanced_results = []

        for prompt_text in prompts:
            # Create prompt in database
            prompt = service.create_prompt(
                model_type="enhancement",
                prompt_text=prompt_text,
                inputs={},
                parameters={"batch_name": batch_name},
            )

            # Create enhancement run
            run = service.create_run(prompt_id=prompt["id"], execution_config={"enhancement": True})

            run_id = run["id"]

            # Execute enhancement (this would normally call the enhancement workflow)
            # For now, we'll simulate it
            enhanced_results.append(f"[{run_id[:8]}] Enhancing: {prompt_text[:50]}...")

        return "\n".join(enhanced_results), "Enhancement jobs queued successfully"

    except Exception as e:
        return "", f"Error: {e}"


def browse_files(directory: str = "outputs"):
    """Browse files in the specified directory."""
    try:
        base_path = Path(directory)
        if not base_path.exists():
            return f"Directory {directory} does not exist"

        files_html = f"<h3>Files in {directory}/</h3>\n"
        files_html += "<table style='width:100%'>\n"
        files_html += "<tr><th>Name</th><th>Size</th><th>Modified</th></tr>\n"

        # List directories first
        for item in sorted(base_path.iterdir()):
            if item.is_dir():
                files_html += "<tr>"
                files_html += f"<td>📁 {item.name}/</td>"
                files_html += "<td>-</td>"
                files_html += f"<td>{item.stat().st_mtime}</td>"
                files_html += "</tr>\n"

        # Then list files
        for item in sorted(base_path.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                size_str = f"{size:,} bytes" if size < 1024 else f"{size / 1024:.1f} KB"
                if size > 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                files_html += "<tr>"
                files_html += f"<td>📄 {item.name}</td>"
                files_html += f"<td>{size_str}</td>"
                files_html += f"<td>{item.stat().st_mtime}</td>"
                files_html += "</tr>\n"

        files_html += "</table>"
        return files_html

    except Exception as e:
        return f"Error browsing files: {e}"


def create_and_run_advanced(
    prompt_text: str,
    negative_prompt: str = "",
    model_type: str = "transfer",
    vis_weight: float = 0.25,
    edge_weight: float = 0.25,
    enable_upscaling: bool = False,
    upscale_weight: float = 0.5,
):
    """Create and run with advanced configuration options."""
    try:
        # Create prompt with specified model type
        prompt = service.create_prompt(
            model_type=model_type,
            prompt_text=prompt_text,
            inputs={},
            parameters={"negative_prompt": negative_prompt},
        )

        # Create run with custom weights
        execution_config = {
            "weights": {"vis": vis_weight, "edge": edge_weight},
            "upscaling": {"enabled": enable_upscaling, "weight": upscale_weight},
        }

        run = service.create_run(prompt_id=prompt["id"], execution_config=execution_config)

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
            except Exception:
                service.update_run_status(run_id, "failed")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

        config_summary = f"Model: {model_type}, Weights: vis={vis_weight}, edge={edge_weight}"
        if enable_upscaling:
            config_summary += f", Upscaling: {upscale_weight}"

        return run_id, f"Started run {run_id}", config_summary

    except Exception as e:
        return "", f"Error: {e}", ""


def create_and_run(prompt_text: str, negative_prompt: str = ""):
    """Create prompt and start run (non-blocking)."""
    try:
        # Create prompt
        prompt = service.create_prompt(
            model_type="transfer",
            prompt_text=prompt_text,
            inputs={},
            parameters={"negative_prompt": negative_prompt},
        )

        # Create run
        run = service.create_run(
            prompt_id=prompt["id"], execution_config={"weights": {"vis": 0.25, "edge": 0.25}}
        )

        run_id = run["id"]

        # Execute in background (our improvement over NVIDIA)
        def execute():
            try:
                service.update_run_status(run_id, "running")
                # Enable logging for UI runs
                result = orchestrator.execute_run(run, prompt, enable_logging=True)
                service.update_run(run_id, outputs=result or {})
                service.update_run_status(run_id, "completed")
            except Exception:
                service.update_run_status(run_id, "failed")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

        return run_id, f"Started run {run_id}"

    except Exception as e:
        return "", f"Error: {e}"


def create_interface():
    with gr.Blocks(title="Cosmos Workflow") as interface:
        gr.Markdown("# Cosmos Transfer Workflow")

        with gr.Tabs():
            with gr.TabItem("Generate"):
                with gr.Row():
                    with gr.Column():
                        prompt_input = gr.Textbox(label="Prompt", lines=3, value="cyberpunk city")
                        negative_input = gr.Textbox(
                            label="Negative Prompt", lines=2, value="blurry, low quality"
                        )
                        generate_btn = gr.Button("Generate Video", variant="primary")

                    with gr.Column():
                        run_id_output = gr.Textbox(label="Run ID")
                        status_output = gr.Textbox(label="Status")

                        # Add log viewer
                        with gr.Column(visible=False) as log_section:
                            gr.Markdown("### Live Logs")
                            logs = gr.Textbox(label="Docker Output", lines=20, autoscroll=True)

                            # Timer for auto-refresh (NVIDIA's pattern)
                            timer = gr.Timer(value=1.0, active=True)
                            timer.tick(
                                fn=lambda rid: tail_log_file(rid) if rid else "",
                                inputs=[run_id_output],
                                outputs=[logs],
                            )

                # Update button to show logs
                def create_and_run_with_logs(prompt_text, negative):
                    run_id, status = create_and_run(prompt_text, negative)
                    return run_id, status, gr.update(visible=True)  # Show logs

                generate_btn.click(
                    fn=create_and_run_with_logs,
                    inputs=[prompt_input, negative_input],
                    outputs=[run_id_output, status_output, log_section],
                )

            with gr.TabItem("Runs"):
                runs_table = gr.HTML()
                refresh_btn = gr.Button("Refresh")

                # Load on tab open
                interface.load(fn=list_runs_html, outputs=[runs_table])
                refresh_btn.click(fn=list_runs_html, outputs=[runs_table])

            with gr.TabItem("Gallery"):
                gr.Markdown("### Completed Videos")
                gallery = gr.Gallery(
                    label="Generated Videos",
                    show_label=False,
                    elem_id="gallery",
                    columns=3,
                    rows=2,
                    object_fit="contain",
                    height="auto",
                )
                refresh_gallery = gr.Button("Refresh Gallery")
                refresh_gallery.click(fn=get_completed_videos, outputs=[gallery])

                # Load on tab open
                interface.load(fn=get_completed_videos, outputs=[gallery])

            with gr.TabItem("Enhance"):
                gr.Markdown("### Prompt Enhancement")
                gr.Markdown("Use AI to enhance your prompts with more detail and creativity")

                with gr.Row():
                    with gr.Column():
                        enhance_input = gr.Textbox(
                            label="Prompts to Enhance (one per line)",
                            lines=10,
                            placeholder="cyberpunk city\nfuturistic spaceship\nabstract art",
                        )
                        batch_name_input = gr.Textbox(
                            label="Batch Name", value="ui_enhancement_batch"
                        )
                        enhance_btn = gr.Button("Enhance Prompts", variant="primary")

                    with gr.Column():
                        enhance_output = gr.Textbox(
                            label="Enhancement Results", lines=10, interactive=False
                        )
                        enhance_status = gr.Textbox(label="Status", interactive=False)

                enhance_btn.click(
                    fn=enhance_prompts,
                    inputs=[enhance_input, batch_name_input],
                    outputs=[enhance_output, enhance_status],
                )

            with gr.TabItem("Status"):
                gr.Markdown("### System Status")
                status_display = gr.Markdown()
                status_refresh = gr.Button("Refresh Status")

                # Auto-refresh every 5 seconds
                status_timer = gr.Timer(value=5.0, active=True)
                status_timer.tick(fn=get_gpu_status, outputs=[status_display])

                status_refresh.click(fn=get_gpu_status, outputs=[status_display])

                # Load on startup
                interface.load(fn=get_gpu_status, outputs=[status_display])

            with gr.TabItem("Files"):
                gr.Markdown("### File Browser")

                with gr.Row():
                    directory_input = gr.Textbox(
                        label="Directory", value="outputs", placeholder="Enter directory path"
                    )
                    browse_btn = gr.Button("Browse")

                files_display = gr.HTML()

                browse_btn.click(fn=browse_files, inputs=[directory_input], outputs=[files_display])

                # Load outputs directory on startup
                interface.load(fn=lambda: browse_files("outputs"), outputs=[files_display])

            with gr.TabItem("Advanced"):
                gr.Markdown("### Advanced Generation Options")

                with gr.Row():
                    with gr.Column():
                        adv_prompt = gr.Textbox(
                            label="Prompt", lines=3, value="futuristic landscape"
                        )
                        adv_negative = gr.Textbox(
                            label="Negative Prompt", lines=2, value="blurry, low quality"
                        )

                        with gr.Row():
                            model_type = gr.Dropdown(
                                label="Model Type",
                                choices=["transfer", "upscale", "enhancement"],
                                value="transfer",
                            )

                        gr.Markdown("#### Weight Configuration")
                        with gr.Row():
                            vis_weight = gr.Slider(
                                label="Visual Weight",
                                minimum=0.0,
                                maximum=1.0,
                                value=0.25,
                                step=0.05,
                            )
                            edge_weight = gr.Slider(
                                label="Edge Weight", minimum=0.0, maximum=1.0, value=0.25, step=0.05
                            )

                        gr.Markdown("#### Upscaling Options")
                        enable_upscaling = gr.Checkbox(label="Enable 4K Upscaling", value=False)
                        upscale_weight = gr.Slider(
                            label="Upscale Weight",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.5,
                            step=0.05,
                            visible=False,
                        )

                        # Show/hide upscale weight based on checkbox
                        enable_upscaling.change(
                            fn=lambda x: gr.update(visible=x),
                            inputs=[enable_upscaling],
                            outputs=[upscale_weight],
                        )

                        adv_generate_btn = gr.Button(
                            "Generate with Advanced Settings", variant="primary"
                        )

                    with gr.Column():
                        adv_run_id = gr.Textbox(label="Run ID")
                        adv_status = gr.Textbox(label="Status")
                        adv_config = gr.Textbox(label="Configuration")

                        # Advanced log viewer
                        with gr.Column(visible=False) as adv_log_section:
                            gr.Markdown("### Live Logs")
                            adv_logs = gr.Textbox(label="Docker Output", lines=15, autoscroll=True)

                            adv_timer = gr.Timer(value=1.0, active=True)
                            adv_timer.tick(
                                fn=lambda rid: tail_log_file(rid) if rid else "",
                                inputs=[adv_run_id],
                                outputs=[adv_logs],
                            )

                def start_advanced_with_logs(*args):
                    run_id, status, config = create_and_run_advanced(*args)
                    return run_id, status, config, gr.update(visible=True if run_id else False)

                adv_generate_btn.click(
                    fn=start_advanced_with_logs,
                    inputs=[
                        adv_prompt,
                        adv_negative,
                        model_type,
                        vis_weight,
                        edge_weight,
                        enable_upscaling,
                        upscale_weight,
                    ],
                    outputs=[adv_run_id, adv_status, adv_config, adv_log_section],
                )

    return interface


if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_port=7860, inbrowser=True)
