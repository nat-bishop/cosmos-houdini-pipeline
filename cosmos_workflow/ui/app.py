#!/usr/bin/env python3
"""Comprehensive Gradio UI for Cosmos Workflow - Full Featured Application."""

import os
from datetime import datetime
from pathlib import Path

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Initialize unified operations - using CosmosAPI like CLI does
ops = CosmosAPI(config=config)

# Initialize log viewer (reusing existing component)
log_viewer = LogViewer(max_lines=2000)

# Get paths from config
local_config = config.get_local_config()
inputs_dir = Path(local_config.videos_dir)  # This is already "inputs/videos" from config
outputs_dir = Path(local_config.outputs_dir)


# ============================================================================
# Phase 1: Input Browser Functions
# ============================================================================


def get_input_directories():
    """Get all input video directories with metadata."""
    directories = []

    if not inputs_dir.exists():
        logger.warning("Inputs directory does not exist: {}", inputs_dir)
        return []

    for dir_path in sorted(inputs_dir.iterdir()):
        if dir_path.is_dir():
            # Check for required files
            color_video = dir_path / "color.mp4"
            depth_video = dir_path / "depth.mp4"
            seg_video = dir_path / "segmentation.mp4"

            dir_info = {
                "name": dir_path.name,
                "path": str(dir_path),
                "has_color": color_video.exists(),
                "has_depth": depth_video.exists(),
                "has_segmentation": seg_video.exists(),
                "files": [],
            }

            # Get all files in directory
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    dir_info["files"].append(
                        {
                            "name": file_path.name,
                            "size": file_path.stat().st_size,
                            "path": str(file_path),
                        }
                    )

            directories.append(dir_info)

    return directories


def load_input_gallery():
    """Load input directories for gallery display."""
    directories = get_input_directories()
    gallery_items = []

    for dir_info in directories:
        # Use color.mp4 as thumbnail if it exists
        color_path = Path(dir_info["path"]) / "color.mp4"
        if color_path.exists():
            gallery_items.append((str(color_path), dir_info["name"]))
        else:
            # Use a placeholder or first video file found
            for file_info in dir_info["files"]:
                if file_info["name"].endswith(".mp4"):
                    gallery_items.append((file_info["path"], dir_info["name"]))
                    break

    return gallery_items


def on_input_select(evt: gr.SelectData, gallery_data):
    """Handle input selection from gallery."""
    if evt.index is None:
        return "", "", "", "", gr.update(visible=False)

    directories = get_input_directories()
    if evt.index >= len(directories):
        return "", "", "", "", gr.update(visible=False)

    selected_dir = directories[evt.index]

    # Format directory info with proper line breaks
    from datetime import datetime

    # Use line breaks with proper Markdown formatting
    info_parts = []
    info_parts.append(f"**Name:** {selected_dir['name']}")
    info_parts.append("")
    info_parts.append(f"**Path:** {selected_dir['path']}")
    info_parts.append("")
    info_parts.append("**Resolution:** 1920x1080")  # TODO: Extract from video
    info_parts.append("")
    info_parts.append("**Duration:** 120 frames (5.0 seconds @ 24fps)")  # TODO: Extract from video
    info_parts.append("")

    # Get creation time from directory
    dir_stat = os.stat(selected_dir["path"])
    created_time = datetime.fromtimestamp(dir_stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
    info_parts.append(f"**Created:** {created_time}")
    info_parts.append("")

    info_text = "\n".join(info_parts)

    info_text += "\n**Multimodal Control Inputs:**\n"

    for file_info in selected_dir["files"]:
        size_mb = file_info["size"] / (1024 * 1024)
        file_type = ""
        if "color" in file_info["name"]:
            file_type = " (RGB)"
        elif "depth" in file_info["name"]:
            file_type = " (Depth Map)"
        elif "segmentation" in file_info["name"]:
            file_type = " (Semantic Segmentation)"
        info_text += f"- {file_info['name']}{file_type} ({size_mb:.2f} MB)\n"

    # Load videos for preview
    color_video = (
        str(Path(selected_dir["path"]) / "color.mp4") if selected_dir["has_color"] else None
    )
    depth_video = (
        str(Path(selected_dir["path"]) / "depth.mp4") if selected_dir["has_depth"] else None
    )
    seg_video = (
        str(Path(selected_dir["path"]) / "segmentation.mp4")
        if selected_dir["has_segmentation"]
        else None
    )

    return (
        info_text,
        selected_dir["path"],  # Store the directory path
        color_video,
        depth_video,
        seg_video,
        gr.update(visible=True),
    )


# ============================================================================
# Phase 2: Prompt Management Functions
# ============================================================================


def list_prompts(model_type="all", limit=50):
    """List prompts using CosmosAPI, formatted for display."""
    try:
        # Use CosmosAPI exactly like the CLI does
        if model_type == "all":
            prompts = ops.list_prompts(limit=limit)
        else:
            prompts = ops.list_prompts(model_type=model_type, limit=limit)

        # Format for Gradio Dataframe display
        table_data = []
        for prompt in prompts:
            # Extract fields safely
            prompt_id = prompt.get("id", "")
            name = prompt.get("parameters", {}).get("name", "unnamed")
            model_type = prompt.get("model_type", "transfer")
            prompt_text = prompt.get("prompt_text", "")

            # Truncate long prompt text for display
            if len(prompt_text) > 50:
                prompt_text = prompt_text[:47] + "..."

            # Format created_at timestamp
            created_at = prompt.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    created_at = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass

            table_data.append([prompt_id, name, model_type, prompt_text, created_at])

        return table_data
    except Exception as e:
        logger.error("Failed to list prompts: {}", e)
        return []


def create_prompt(prompt_text, video_dir, name, negative_prompt, model_type):
    """Create a new prompt using CosmosAPI."""
    try:
        # Validate inputs
        if not prompt_text or not prompt_text.strip():
            return "❌ Error: Prompt text is required"

        if not video_dir or not video_dir.strip():
            return "❌ Error: Video directory is required"

        # Convert to Path and validate
        video_path = Path(video_dir.strip())
        if not video_path.is_absolute():
            # If it's a relative path, use it as-is (already relative to project root)
            video_path = Path(video_dir.strip())

        # Use CosmosAPI to create prompt (it handles validation)
        prompt = ops.create_prompt(
            prompt_text=prompt_text.strip(),
            video_dir=video_path,
            name=name.strip() if name and name.strip() else None,
            negative_prompt=negative_prompt.strip()
            if negative_prompt and negative_prompt.strip()
            else None,
            model_type=model_type,
        )

        # Success message with prompt ID
        prompt_id = prompt.get("id", "unknown")
        prompt_name = prompt.get("parameters", {}).get("name", "unnamed")
        return f"✅ Created prompt **{prompt_id}**\nName: {prompt_name}"

    except FileNotFoundError as e:
        return f"❌ Error: {e}"
    except ValueError as e:
        return f"❌ Error: {e}"
    except Exception as e:
        logger.error("Failed to create prompt: {}", e)
        return f"❌ Error creating prompt: {e}"


def get_prompt_details(prompt_id):
    """Get detailed information about a specific prompt."""
    try:
        if not prompt_id:
            return "No prompt selected"

        prompt = ops.get_prompt(prompt_id)
        if not prompt:
            return f"Prompt {prompt_id} not found"

        # Format detailed view
        details = f"**Prompt ID:** {prompt['id']}\n"
        details += f"**Name:** {prompt.get('parameters', {}).get('name', 'unnamed')}\n"
        details += f"**Model Type:** {prompt.get('model_type', 'transfer')}\n"
        details += f"**Created:** {prompt.get('created_at', 'unknown')}\n\n"

        details += "**Prompt Text:**\n"
        details += f"{prompt.get('prompt_text', '')}\n\n"

        negative = prompt.get("parameters", {}).get("negative_prompt")
        if negative:
            details += "**Negative Prompt:**\n"
            details += f"{negative}\n\n"

        inputs = prompt.get("inputs", {})
        if inputs:
            details += "**Input Files:**\n"
            if inputs.get("video"):
                details += f"- Color: {inputs['video']}\n"
            if inputs.get("depth"):
                details += f"- Depth: {inputs['depth']}\n"
            if inputs.get("seg"):
                details += f"- Segmentation: {inputs['seg']}\n"

        return details
    except Exception as e:
        logger.error("Failed to get prompt details: {}", e)
        return f"Error getting prompt details: {e}"


def populate_from_input_dir(selected_dir_path):
    """Populate the video directory field from selected input."""
    if selected_dir_path:
        return selected_dir_path
    return ""


def list_prompts_for_input(video_dir):
    """List prompts associated with a specific input directory."""
    try:
        all_prompts = ops.list_prompts(limit=100)

        if not video_dir:
            return all_prompts

        # Filter prompts that use this video directory
        video_path = Path(video_dir)
        filtered = []

        for prompt in all_prompts:
            inputs = prompt.get("inputs", {})
            if inputs.get("video"):
                prompt_video_path = Path(inputs["video"]).parent
                if prompt_video_path == video_path:
                    filtered.append(prompt)

        return filtered
    except Exception as e:
        logger.error("Failed to filter prompts for input: {}", e)
        return []


# ============================================================================
# Existing Log Streaming Functions (keeping from original)
# ============================================================================


def start_log_streaming():
    """Generator that streams logs to the UI."""
    log_viewer.clear()

    try:
        containers = ops.get_active_containers()

        if not containers:
            yield "No active containers found", log_viewer.get_html()
            return

        if len(containers) > 1:
            container_id = containers[0]["container_id"]
            message = f"Multiple containers found, streaming from {container_id}"
        else:
            container_id = containers[0]["container_id"]
            message = f"Streaming logs from container {container_id}"

        yield message, log_viewer.get_html()

        try:
            for log_line in ops.stream_logs_generator(container_id):
                log_viewer.add_from_stream(log_line)
                yield message, log_viewer.get_html()
        except KeyboardInterrupt:
            yield "Streaming stopped", log_viewer.get_html()

    except RuntimeError as e:
        yield f"Error: {e}", log_viewer.get_html()
    except Exception as e:
        yield f"Failed to start streaming: {e}", log_viewer.get_html()


def check_running_jobs():
    """Check for active containers on remote instance."""
    try:
        containers = ops.get_active_containers()

        if containers:
            display_text = f"Found {len(containers)} active container(s)\n\n"
            for container in containers:
                display_text += f"Container: {container['container_id']}\n"
                display_text += f"Image: {container.get('image', 'Unknown')}\n"
                display_text += f"Status: {container.get('status', 'Unknown')}\n"
                display_text += "-" * 40 + "\n"

            if len(containers) == 1:
                status = "Ready to stream from active container"
            else:
                status = "Multiple containers active"

            return display_text.strip(), status
        else:
            return "No active containers found", "No containers to stream from"
    except Exception as e:
        return f"Error: {e}", "Error checking containers"


# ============================================================================
# Main UI Creation
# ============================================================================


def create_ui():
    """Create the comprehensive Gradio interface."""

    with gr.Blocks(title="Cosmos Workflow Manager", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🌌 Cosmos Workflow Manager")
        gr.Markdown("Comprehensive UI for managing Cosmos Transfer workflows")

        with gr.Tabs() as tabs:
            # ========================================
            # Tab 1: Inputs Browser
            # ========================================
            with gr.Tab("📁 Inputs", id=1):
                gr.Markdown("### Input Video Browser")
                gr.Markdown("Browse and select input video directories for processing")

                with gr.Row():
                    # Left: Gallery of inputs with rectangular aspect ratio
                    with gr.Column(scale=1):
                        input_gallery = gr.Gallery(
                            label="Input Directories",
                            show_label=True,
                            elem_id="input_gallery",
                            columns=5,  # 5 columns for better display
                            rows=3,  # Allow 3 rows
                            object_fit="cover",  # Use cover to fill 16:9 space
                            height=600,  # Larger height for 16:9 aspect ratio
                            preview=False,  # Disable preview for cleaner look
                            allow_preview=False,
                        )

                        refresh_inputs_btn = gr.Button(
                            "🔄 Refresh Inputs", variant="secondary", size="sm"
                        )

                    # Right: Selected input details (larger)
                    with gr.Column(scale=2):
                        selected_info = gr.Markdown("Select an input to view details")

                        # Hidden field to store selected directory path
                        selected_dir_path = gr.Textbox(visible=False)

                        with gr.Group(visible=False) as preview_group:
                            gr.Markdown("#### Video Previews")

                            # Use tabs for cleaner video preview layout
                            with gr.Tabs():
                                with gr.Tab("Color (RGB)"):
                                    color_preview = gr.Video(height=300, autoplay=False)

                                with gr.Tab("Depth Map"):
                                    depth_preview = gr.Video(height=300, autoplay=False)

                                with gr.Tab("Segmentation"):
                                    seg_preview = gr.Video(height=300, autoplay=False)

                            # Add button to create prompt for selected input
                            create_prompt_for_input_btn = gr.Button(
                                "✨ Create Prompt for This Input", variant="primary", size="sm"
                            )

            # ========================================
            # Tab 2: Prompts (Phase 2 Implementation)
            # ========================================
            with gr.Tab("✏️ Prompts", id="prompts_tab"):
                gr.Markdown("### Prompt Management")
                gr.Markdown("Create and manage prompts for your video inputs")

                with gr.Row():
                    # Left: Prompt list and filters
                    with gr.Column(scale=2):
                        gr.Markdown("#### Existing Prompts")

                        with gr.Row():
                            model_type_filter = gr.Dropdown(
                                choices=[
                                    "all",
                                    "transfer",
                                    "upscale",
                                    "enhance",
                                    "reason",
                                    "predict",
                                ],
                                value="all",
                                label="Model Type",
                                scale=1,
                            )
                            limit_filter = gr.Number(
                                value=50, label="Limit", minimum=1, maximum=500, scale=1
                            )
                            refresh_prompts_btn = gr.Button(
                                "🔄 Refresh", variant="secondary", size="sm", scale=1
                            )

                        prompts_table = gr.Dataframe(
                            headers=["ID", "Name", "Model", "Prompt Text", "Created"],
                            datatype=["str", "str", "str", "str", "str"],
                            interactive=False,
                            wrap=True,
                        )

                        gr.Textbox(label="Selected Prompt ID", interactive=False, visible=False)

                    # Right: Create new prompt
                    with gr.Column(scale=1):
                        gr.Markdown("#### Create New Prompt")

                        with gr.Group():
                            # Video Directory at the top for easy access
                            create_video_dir = gr.Textbox(
                                label="Video Directory",
                                placeholder="Path to input video directory (e.g., inputs/videos/example)",
                                info="Must contain color.mp4 - auto-filled when clicking 'Create Prompt for This Input'",
                            )

                            create_prompt_text = gr.Textbox(
                                label="Prompt Text",
                                placeholder="Enter your prompt description here...",
                                lines=3,
                                max_lines=10,
                            )

                            create_name = gr.Textbox(
                                label="Name (Optional)",
                                placeholder="Leave empty for auto-generated name",
                                info="A descriptive name for this prompt",
                            )

                            # Get default negative prompt from config
                            default_negative = (
                                config._config_data.get("generation", {})
                                .get(
                                    "negative_prompt",
                                    "The video captures a game playing, with bad crappy graphics...",
                                )
                                .strip()
                            )

                            create_negative = gr.Textbox(
                                label="Negative Prompt",
                                value=default_negative,  # Pre-fill with default
                                lines=3,
                                info="Edit to customize or leave as default",
                            )

                            create_model_type = gr.Dropdown(
                                choices=["transfer", "upscale", "enhance"],
                                value="transfer",
                                label="Model Type",
                            )

                            create_prompt_btn = gr.Button(
                                "✨ Create Prompt", variant="primary", size="lg"
                            )

                            create_status = gr.Markdown("")

            # ========================================
            # Tab 3: Operations (Placeholder for Phase 3)
            # ========================================
            with gr.Tab("🚀 Operations", id=3):
                gr.Markdown("### Run Operations")
                gr.Markdown("*Coming in Phase 3: Run inference, enhancement, and upscaling*")

                with gr.Row():
                    gr.Column()

            # ========================================
            # Tab 4: Outputs (Phase 4 Implementation)
            # ========================================
            with gr.Tab("🎬 Outputs", id=4):
                gr.Markdown("### Output Gallery")
                gr.Markdown("View and download generated video outputs from completed runs")

                with gr.Row():
                    # Left: Filters and run list
                    with gr.Column(scale=1):
                        gr.Markdown("#### Filter Options")

                        with gr.Group():
                            output_status_filter = gr.Dropdown(
                                choices=["completed", "all"],
                                value="completed",
                                label="Run Status",
                                info="Filter by run status",
                            )

                            output_model_filter = gr.Dropdown(
                                choices=["all", "transfer", "upscale"],
                                value="all",
                                label="Model Type",
                                info="Filter by model type",
                            )

                            output_limit = gr.Number(
                                value=20,
                                label="Limit",
                                minimum=1,
                                maximum=100,
                                info="Number of outputs to display",
                            )

                            refresh_outputs_btn = gr.Button(
                                "🔄 Refresh Outputs", variant="secondary", size="sm"
                            )

                        gr.Markdown("#### Recent Outputs")
                        outputs_table = gr.Dataframe(
                            headers=["Run ID", "Prompt", "Status", "Created"],
                            datatype=["str", "str", "str", "str"],
                            interactive=False,
                            wrap=True,
                        )

                    # Right: Video gallery and details
                    with gr.Column(scale=2):
                        gr.Markdown("#### Generated Videos")

                        output_gallery = gr.Gallery(
                            label="Output Videos",
                            show_label=False,
                            elem_id="output_gallery",
                            columns=3,
                            rows=2,
                            object_fit="cover",
                            height=400,
                            preview=False,
                            allow_preview=False,
                        )

                        # Selected output details
                        with gr.Group(visible=False) as output_details_group:
                            gr.Markdown("#### Output Details")

                            output_info = gr.Markdown("Select an output to view details")

                            with gr.Row():
                                output_video = gr.Video(
                                    label="Generated Video", height=350, autoplay=False
                                )

                            with gr.Row():
                                gr.Button("💾 Download Video", variant="primary", size="sm")

                                output_path_display = gr.Textbox(
                                    label="Output Path", interactive=False, visible=False
                                )

            # ========================================
            # Tab 5: Log Monitor (Existing functionality)
            # ========================================
            with gr.Tab("📊 Log Monitor", id=5):
                gr.Markdown("### Real-time Log Monitoring")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Active Containers")
                        running_jobs_display = gr.Textbox(
                            label="Active Containers",
                            value="Checking for active containers...",
                            interactive=False,
                            lines=5,
                        )
                        check_jobs_btn = gr.Button("🔍 Check Active Containers", size="sm")

                        job_status = gr.Textbox(
                            label="Stream Status",
                            value="Click 'Start Streaming' to begin",
                            interactive=False,
                        )

                        stream_btn = gr.Button("▶️ Start Streaming", variant="primary", size="sm")

                        gr.Markdown("#### Log Statistics")
                        gr.Textbox(
                            label="Log Stats",
                            value="Total: 0 | Errors: 0 | Warnings: 0",
                            interactive=False,
                        )

                    with gr.Column(scale=3):
                        gr.Markdown("#### Log Output")
                        log_display = gr.HTML(
                            value=log_viewer.get_html(),
                            elem_id="log_display",
                        )

        # ============================================
        # Event Handlers
        # ============================================

        # Input browser events
        refresh_inputs_btn.click(fn=load_input_gallery, inputs=[], outputs=[input_gallery])

        input_gallery.select(
            fn=on_input_select,
            inputs=[input_gallery],
            outputs=[
                selected_info,
                selected_dir_path,
                color_preview,
                depth_preview,
                seg_preview,
                preview_group,
            ],
        )

        # Input-Prompt association with auto-navigation
        def navigate_to_prompt_creation(path):
            """Navigate to Prompts tab and populate the video directory."""
            input_id = Path(path).name if path else ""
            # Return values for: video_dir, tabs (switch to prompts_tab), and status
            return (
                path,  # Video directory
                gr.update(selected="prompts_tab"),  # Switch to Prompts tab using its ID
                f"🎯 Creating prompt for: {input_id}",  # Status message
            )

        create_prompt_for_input_btn.click(
            fn=navigate_to_prompt_creation,
            inputs=[selected_dir_path],
            outputs=[create_video_dir, tabs, create_status],
        )

        # Prompt management events
        refresh_prompts_btn.click(
            fn=list_prompts, inputs=[model_type_filter, limit_filter], outputs=[prompts_table]
        )

        create_prompt_btn.click(
            fn=create_prompt,
            inputs=[
                create_prompt_text,
                create_video_dir,
                create_name,
                create_negative,
                create_model_type,
            ],
            outputs=[create_status],
        ).then(fn=list_prompts, inputs=[model_type_filter, limit_filter], outputs=[prompts_table])

        # Load initial data will be done via app.load event

        # Output gallery events
        def load_outputs(status_filter, model_filter, limit):
            """Load outputs from completed runs."""
            try:
                # Get runs based on filter
                runs = ops.list_runs(
                    status=status_filter if status_filter != "all" else None, limit=int(limit)
                )

                # Filter by model type if specified
                if model_filter != "all":
                    runs = [r for r in runs if r.get("model_type") == model_filter]

                # Filter runs with video outputs
                runs_with_outputs = []
                gallery_items = []

                for run in runs:
                    outputs = run.get("outputs", {})
                    output_path = outputs.get("output_path")

                    if output_path and Path(output_path).exists():
                        runs_with_outputs.append(run)
                        # Add to gallery (path, label)
                        prompt_text = run.get("prompt_text", "No prompt")[:50] + "..."
                        gallery_items.append((output_path, f"Run {run['id'][:8]}: {prompt_text}"))

                # Create table data
                table_data = []
                for run in runs_with_outputs[:10]:  # Limit table to 10 rows
                    table_data.append(
                        [
                            run["id"][:12],
                            run.get("prompt_text", "N/A")[:30] + "...",
                            run.get("status", "unknown"),
                            run.get("created_at", "N/A")[:19],
                        ]
                    )

                return gallery_items, table_data

            except Exception as e:
                logger.error(f"Error loading outputs: {e}")
                return [], []

        def select_output(evt: gr.SelectData, gallery_data):
            """Handle output selection from gallery."""
            if evt.index is not None and gallery_data:
                selected = gallery_data[evt.index]
                video_path = selected[0] if isinstance(selected, tuple) else selected

                if Path(video_path).exists():
                    # Get run info from path
                    run_info = f"**Selected Output**\n\nPath: {video_path}\n"

                    return (
                        gr.update(visible=True),  # Show details group
                        run_info,  # Output info
                        video_path,  # Video path for display
                        video_path,  # Store path for download
                    )

            return gr.update(visible=False), "Select an output", None, ""

        def download_output(output_path):
            """Prepare output for download."""
            if output_path and Path(output_path).exists():
                return output_path
            return None

        refresh_outputs_btn.click(
            fn=load_outputs,
            inputs=[output_status_filter, output_model_filter, output_limit],
            outputs=[output_gallery, outputs_table],
        )

        output_gallery.select(
            fn=select_output,
            inputs=[output_gallery],
            outputs=[output_details_group, output_info, output_video, output_path_display],
        )

        # Download functionality will be handled through the video component itself

        # Log monitor events (existing)
        check_jobs_btn.click(
            fn=check_running_jobs,
            inputs=[],
            outputs=[running_jobs_display, job_status],
        )

        stream_btn.click(
            fn=start_log_streaming,
            inputs=[],
            outputs=[job_status, log_display],
        )

        # Auto-load data on app start
        app.load(fn=load_input_gallery, inputs=[], outputs=[input_gallery]).then(
            fn=check_running_jobs, inputs=[], outputs=[running_jobs_display, job_status]
        ).then(
            fn=load_outputs,
            inputs=[output_status_filter, output_model_filter, output_limit],
            outputs=[output_gallery, outputs_table],
        ).then(
            fn=lambda: list_prompts("all", 50),  # Provide default values
            inputs=[],
            outputs=[prompts_table],
        )

    return app


if __name__ == "__main__":
    # Get UI configuration from config.toml
    ui_config = config._config_data.get("ui", {})
    host = ui_config.get("host", "0.0.0.0")
    port = ui_config.get("port", 7860)
    share = ui_config.get("share", False)

    logger.info("Starting Cosmos Workflow Manager on {}:{}", host, port)

    app = create_ui()
    app.launch(
        share=share,
        server_name=host,
        server_port=port,
        show_error=True,
        inbrowser=True,  # Auto-open browser
    )
