"""Gradio UI for Cosmos Workflow."""

import logging
import threading
from pathlib import Path

import gradio as gr

from cosmos_workflow.config import ConfigManager
from cosmos_workflow.database import init_database

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

    return interface


if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_port=7860, inbrowser=True)
