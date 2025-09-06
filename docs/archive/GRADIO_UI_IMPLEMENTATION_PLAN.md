# Gradio UI Implementation Plan - Final Version

**Date:** 2025-01-09
**Author:** NAT
**Status:** Ready for Implementation
**Estimated Time:** 3-4 hours (incremental features)
**Replaces:** Original Chunk 5 (Progress Tracking)

## Executive Summary

This plan creates a Gradio UI following NVIDIA's proven pattern, adapted for our service architecture. The UI directly instantiates WorkflowService and WorkflowOrchestrator (no CLI coupling), captures real Docker logs from remote GPU, and adds incremental database management features.

## Critical Design Decisions

1. **Direct Service Usage** - No CLIContext (that's CLI-specific)
2. **Real Docker Log Capture** - Must capture SSH stream, not local prints
3. **Threading for UX** - Non-blocking execution (unlike NVIDIA's blocking)
4. **Incremental Features** - Start simple, add management features as needed

## Implementation Steps

---

### Step 1: Create Basic Gradio UI (30 minutes)

**Goal:** Get a minimal UI working that can create prompts and start runs

**File:** `cosmos_workflow/ui/app.py`

```python
"""Gradio UI for Cosmos Workflow."""

import gradio as gr
import threading
from pathlib import Path
from datetime import datetime

# Direct service imports (no CLI coupling)
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.workflows import WorkflowOrchestrator
from cosmos_workflow.database import init_database
from cosmos_workflow.config import ConfigManager

# Global initialization (NVIDIA's pattern)
print("Initializing Cosmos services...")
config = ConfigManager()
local_config = config.get_local_config()
db_path = local_config.outputs_dir / "cosmos.db"
db = init_database(str(db_path))

service = WorkflowService(db, config)
orchestrator = WorkflowOrchestrator()

def create_and_run(prompt_text: str, negative_prompt: str = ""):
    """Create prompt and start run (non-blocking)."""
    try:
        # Create prompt
        prompt = service.create_prompt(
            model_type="transfer",
            prompt_text=prompt_text,
            inputs={},
            parameters={"negative_prompt": negative_prompt}
        )

        # Create run
        run = service.create_run(
            prompt_id=prompt['id'],
            execution_config={"weights": {"vis": 0.25, "edge": 0.25}}
        )

        run_id = run['id']

        # Execute in background (our improvement over NVIDIA)
        def execute():
            try:
                service.update_run_status(run_id, "running")
                # Note: This will NOT capture logs yet - Step 2 fixes that
                result = orchestrator.execute_run(run, prompt)
                service.update_run(run_id, outputs=result or {})
                service.update_run_status(run_id, "completed")
            except Exception as e:
                service.update_run_status(run_id, "failed")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

        return run_id, f"Started run {run_id}"

    except Exception as e:
        return "", f"Error: {e}"

def create_interface():
    with gr.Blocks(title="Cosmos Workflow") as interface:
        gr.Markdown("# Cosmos Transfer Workflow")

        with gr.Row():
            with gr.Column():
                prompt_input = gr.Textbox(
                    label="Prompt",
                    lines=3,
                    value="cyberpunk city"
                )
                negative_input = gr.Textbox(
                    label="Negative Prompt",
                    lines=2,
                    value="blurry, low quality"
                )
                generate_btn = gr.Button("Generate Video", variant="primary")

            with gr.Column():
                run_id_output = gr.Textbox(label="Run ID")
                status_output = gr.Textbox(label="Status")

        generate_btn.click(
            fn=create_and_run,
            inputs=[prompt_input, negative_input],
            outputs=[run_id_output, status_output]
        )

    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_port=7860, inbrowser=True)
```

**Verification:**
```bash
# Test the UI launches
python cosmos_workflow/ui/app.py

# In browser:
1. Should see the UI at http://localhost:7860
2. Enter a prompt and click "Generate Video"
3. Should get back a run ID like "rs_abc123..."
4. Check database: cosmos list runs (should see new run)
5. Note: Logs won't work yet - that's Step 2
```

---

### Step 2: Add Docker Log Capture to File (45 minutes)

**Goal:** Capture real Docker logs from remote GPU to log files

**File to modify:** `cosmos_workflow/execution/docker_executor.py`

**Add this method:**
```python
def run_inference_with_logging(self, prompt_file: Path,
                              num_gpu: int = 1,
                              cuda_devices: str = "0",
                              log_path: str = None) -> None:
    """Run inference with optional log file capture."""

    prompt_name = prompt_file.stem
    logger.info("Running inference for %s", prompt_name)

    # Create output directory
    remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
    self.remote_executor.create_directory(remote_output_dir)

    # Execute inference
    logger.info("Starting inference...")
    self._run_inference_script(prompt_name, num_gpu, cuda_devices)

    # If log_path provided, capture Docker logs
    if log_path:
        # Get container ID (most recent for our image)
        cmd = f'sudo docker ps -l -q --filter "ancestor={self.docker_image}"'
        container_id = self.ssh_manager.execute_command_success(
            cmd, stream_output=False
        ).strip()

        if container_id:
            logger.info("Capturing logs from container %s to %s", container_id, log_path)

            # Stream logs to file
            with open(log_path, 'w') as log_file:
                # Get logs (not following, just current state)
                logs_cmd = f"sudo docker logs {container_id}"
                exit_code, stdout, stderr = self.ssh_manager.execute_command(
                    logs_cmd,
                    timeout=60,
                    stream_output=False
                )

                # Write to file
                log_file.write(stdout)
                if stderr:
                    log_file.write(f"\n=== STDERR ===\n{stderr}")
                log_file.flush()

                # Now follow new logs
                follow_cmd = f"sudo docker logs -f {container_id}"

                # Custom streaming to file
                stdin, stdout_stream, stderr_stream = self.ssh_manager.ssh_client.exec_command(follow_cmd)

                # Stream to file in real-time
                for line in stdout_stream:
                    line = line.strip()
                    if line:
                        print(f"  {line}")  # Console
                        log_file.write(f"{line}\n")
                        log_file.flush()  # Real-time

    logger.info("Inference completed for %s", prompt_name)
```

**File to modify:** `cosmos_workflow/workflows/workflow_orchestrator.py`

**Modify execute_run to use logging:**
```python
def execute_run(self, run_dict: dict, prompt_dict: dict, **kwargs) -> dict:
    """Execute run with Docker log capture."""
    run_id = run_dict['id']

    # Create log directory and file
    log_dir = Path("logs/runs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.log"

    # Write initial info to log
    with open(log_path, 'w') as f:
        f.write(f"[{datetime.now()}] Starting run {run_id}\n")
        f.write(f"Prompt: {prompt_dict['prompt_text']}\n")
        f.write(f"Model: {run_dict['model_type']}\n")
        f.write("="*50 + "\n")

    try:
        # Your existing code to prepare files, etc...

        # Call inference WITH log capture
        self.docker_executor.run_inference_with_logging(
            prompt_file=prompt_spec_path,
            num_gpu=1,
            log_path=str(log_path)  # Pass log file path!
        )

        # Rest of your code...

    except Exception as e:
        # Log errors too
        with open(log_path, 'a') as f:
            f.write(f"\n[ERROR] {e}\n")
        raise
```

**Verification:**
```bash
# Run inference from CLI to test log capture
cosmos inference rs_abc123

# Check log file was created and has Docker output:
cat logs/runs/rs_abc123.log

# Should see:
# [2025-01-09 ...] Starting run rs_abc123
# Prompt: cyberpunk city
# ====================
# [INFO] Loading checkpoints...
# Step 1/35 [=>.........................]
# Step 15/35 [=============>.............]
# etc.

# If logs only show initial lines but no Docker output,
# the capture isn't working correctly
```

---

### Step 3: Add Log Viewer to UI (30 minutes)

**Goal:** Display real-time logs in Gradio UI

**File:** `cosmos_workflow/ui/app.py`

**Add log tailing function (copy NVIDIA's approach):**
```python
def tail_log_file(run_id: str, num_lines: int = 100) -> str:
    """Read last N lines from log file - NVIDIA's efficient approach."""
    if not run_id:
        return "No run selected"

    log_path = Path(f"logs/runs/{run_id}.log")

    if not log_path.exists():
        return f"Waiting for run {run_id} to start..."

    try:
        with open(log_path, 'rb') as f:
            # NVIDIA's seek-based approach for efficiency
            BLOCK_SIZE = 1024
            f.seek(0, 2)
            file_length = f.tell()

            if file_length == 0:
                return "Starting..."

            # Read from end
            seek_pos = max(0, file_length - BLOCK_SIZE * 10)
            f.seek(seek_pos)
            content = f.read().decode('utf-8', errors='ignore')

            lines = content.splitlines()
            return '\n'.join(lines[-num_lines:])

    except Exception as e:
        return f"Error reading log: {e}"
```

**Update create_interface to include log viewer:**
```python
def create_interface():
    with gr.Blocks(title="Cosmos Workflow") as interface:
        gr.Markdown("# Cosmos Transfer Workflow")

        with gr.Row():
            # ... existing inputs ...

            with gr.Column():
                run_id_output = gr.Textbox(label="Run ID")
                status_output = gr.Textbox(label="Status")

                # Add log viewer
                with gr.Column(visible=False) as log_section:
                    gr.Markdown("### Live Logs")
                    logs = gr.Textbox(
                        label="Docker Output",
                        lines=20,
                        autoscroll=True
                    )

                    # Timer for auto-refresh (NVIDIA's pattern)
                    timer = gr.Timer(value=1.0, active=True)
                    timer.tick(
                        fn=lambda rid: tail_log_file(rid) if rid else "",
                        inputs=[run_id_output],
                        outputs=[logs]
                    )

        # Update button to show logs
        def create_and_run_with_logs(prompt_text, negative):
            run_id, status = create_and_run(prompt_text, negative)
            return run_id, status, gr.update(visible=True)  # Show logs

        generate_btn.click(
            fn=create_and_run_with_logs,
            inputs=[prompt_input, negative_input],
            outputs=[run_id_output, status_output, log_section]
        )
```

**Verification:**
```bash
# Launch UI
python cosmos_workflow/ui/app.py

# In browser:
1. Create a new run
2. Log viewer should appear
3. Watch logs update every second
4. Should see actual Docker output:
   - "Step 1/35..."
   - "Step 15/35..."
   - NOT just "Starting run..."

# If you only see initial messages, Docker log capture isn't working
# If you see nothing, check logs/runs/{run_id}.log exists
```

---

### Step 4: Add Run Management Tab (30 minutes)

**Goal:** View all runs and their status

**File:** `cosmos_workflow/ui/app.py`

**Add management functions:**
```python
def list_runs_html():
    """Generate HTML table of runs."""
    runs = service.list_runs(limit=20)

    if not runs:
        return "<p>No runs yet</p>"

    html = "<table style='width:100%'>"
    html += "<tr><th>ID</th><th>Status</th><th>Created</th></tr>"

    for run in runs:
        color = {
            'completed': 'green',
            'running': 'orange',
            'failed': 'red'
        }.get(run['status'], 'gray')

        html += f"<tr>"
        html += f"<td><code>{run['id'][:12]}...</code></td>"
        html += f"<td style='color:{color}'>{run['status']}</td>"
        html += f"<td>{run['created_at']}</td>"
        html += f"</tr>"

    html += "</table>"
    return html
```

**Update interface with tabs:**
```python
def create_interface():
    with gr.Blocks(title="Cosmos Workflow") as interface:
        gr.Markdown("# Cosmos Transfer Workflow")

        with gr.Tabs():
            with gr.TabItem("Generate"):
                # ... existing generation UI ...

            with gr.TabItem("Runs"):
                runs_table = gr.HTML()
                refresh_btn = gr.Button("Refresh")

                # Load on tab open
                interface.load(fn=list_runs_html, outputs=[runs_table])
                refresh_btn.click(fn=list_runs_html, outputs=[runs_table])
```

**Verification:**
```bash
# With UI running:
1. Click "Runs" tab
2. Should see table of all runs with status colors
3. Click Refresh to update
4. Create new run in Generate tab
5. Go back to Runs tab, click Refresh
6. Should see new run in table
```

---

### Step 5: Add CLI Command (15 minutes)

**Goal:** Launch UI with `cosmos ui` command

**File:** `cosmos_workflow/cli/ui.py` (NEW)

```python
"""UI command for launching Gradio interface."""

import click

@click.command()
@click.option('--port', default=7860, help='Port number')
@click.option('--share', is_flag=True, help='Create public link')
def ui(port, share):
    """Launch web interface for workflow management."""
    from cosmos_workflow.ui.app import create_interface

    click.echo(f"Starting Gradio UI on port {port}...")
    click.echo(f"Open browser to: http://localhost:{port}")

    interface = create_interface()
    interface.launch(
        server_port=port,
        share=share,
        inbrowser=True
    )
```

**File:** `cosmos_workflow/cli/__init__.py`

**Add to imports and commands:**
```python
from .ui import ui

# In create_cli() or where commands are registered:
cli.add_command(ui)
```

**Verification:**
```bash
# Test CLI command
cosmos ui

# Should:
1. Print "Starting Gradio UI on port 7860..."
2. Open browser automatically
3. Show the UI

# Test with options
cosmos ui --port 8000 --share

# Should use port 8000 and show public URL if --share
```

---

### Step 6: Add Gallery Feature (30 minutes) [OPTIONAL]

**Goal:** View completed output videos

**Add to app.py:**
```python
def get_completed_videos():
    """Get paths to completed videos."""
    runs = service.list_runs(status="completed", limit=10)
    videos = []

    for run in runs:
        output_path = run.get('outputs', {}).get('video_path')
        if output_path and Path(output_path).exists():
            prompt = service.get_prompt(run['prompt_id'])
            videos.append((
                output_path,
                f"{prompt['prompt_text'][:30]}... ({run['id'][:8]})"
            ))

    return videos

# In interface, add gallery tab:
with gr.TabItem("Gallery"):
    gallery = gr.Gallery(
        label="Completed Videos",
        columns=3
    )
    refresh_gallery = gr.Button("Refresh")
    refresh_gallery.click(
        fn=get_completed_videos,
        outputs=[gallery]
    )
```

**Verification:**
```bash
# After completing some runs:
1. Click Gallery tab
2. Should see video thumbnails
3. Click to view full size
4. Refresh to see new completions
```

---

## Testing Checklist

### After Step 1 (Basic UI):
- [ ] UI launches at localhost:7860
- [ ] Can create prompt and run
- [ ] Returns run ID
- [ ] Run appears in database (`cosmos list runs`)

### After Step 2 (Log Capture):
- [ ] Log file created at `logs/runs/{run_id}.log`
- [ ] Contains Docker output ("Step X/35")
- [ ] Not just local prints

### After Step 3 (Log Viewer):
- [ ] Logs appear in UI
- [ ] Update every second
- [ ] Show real Docker progress

### After Step 4 (Management):
- [ ] Runs tab shows all runs
- [ ] Status colors work
- [ ] Refresh updates table

### After Step 5 (CLI):
- [ ] `cosmos ui` launches interface
- [ ] Port and share options work

### After Step 6 (Gallery):
- [ ] Videos display in gallery
- [ ] Can view completed outputs

---

## Critical Success Factors

1. **Log Capture Must Work** - Without real Docker logs, the UI is useless
2. **Threading Required** - Blocking UI for 10+ minutes is unacceptable
3. **Database Integration** - Must use existing WorkflowService
4. **No CLI Coupling** - Direct service instantiation only

---

## Common Issues & Solutions

**Issue:** Logs only show "Starting run..." but no Docker output
**Solution:** Docker log capture not working. Check Step 2 implementation.

**Issue:** UI freezes during inference
**Solution:** Threading not working. Check execute() is in thread.

**Issue:** Can't find services
**Solution:** Import paths wrong. Check cosmos_workflow structure.

**Issue:** Database not found
**Solution:** Check ConfigManager paths, ensure cosmos.db exists.

---

## Summary

This plan delivers a working Gradio UI in ~2 hours (Steps 1-3), with additional management features adding another 1-2 hours. The critical part is **Step 2** - capturing real Docker logs from the remote GPU. Without this, the UI provides no value over the CLI.