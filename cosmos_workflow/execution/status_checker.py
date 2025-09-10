"""Status checker for monitoring and syncing container execution status."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.connection import SSHManager
from cosmos_workflow.execution.command_builder import RemoteCommandExecutor
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.utils.json_handler import JSONHandler
from cosmos_workflow.utils.logging import logger


class StatusChecker:
    """Checks container status and downloads outputs when complete."""

    def __init__(self, config_manager):
        """Initialize StatusChecker with configuration.

        Args:
            config_manager: ConfigManager instance for configuration
        """
        self.config_manager = config_manager

        # Services are created per sync operation for simplicity
        self.ssh_manager = None
        self.file_transfer = None
        self.remote_executor = None

        # Create JSONHandler for JSON operations
        self.json_handler = JSONHandler()

        # Cache for completed runs to avoid re-checking
        self._completed_cache = set()

    def _create_services(self):
        """Create fresh SSH and FileTransfer services per sync operation.

        Following the pattern used by GPUExecutor for service creation.
        Services are created fresh per sync operation for simplicity and reliability.
        """
        # Initialize SSH and related services
        self.ssh_manager = SSHManager(self.config_manager.get_ssh_options())
        remote_config = self.config_manager.get_remote_config()
        self.file_transfer = FileTransferService(self.ssh_manager, remote_config.remote_dir)
        self.remote_executor = RemoteCommandExecutor(self.ssh_manager)

        # Add execute method for compatibility if needed
        if not hasattr(self.remote_executor, "execute"):
            self.remote_executor.execute = self._execute_wrapper

    def _execute_wrapper(self, command: str) -> tuple:
        """Wrapper for execute_command to provide tuple return format.

        Args:
            command: Command to execute

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        # Use ssh_manager directly with stream_output=False to avoid console output
        return self.ssh_manager.execute_command(command, stream_output=False)

    def parse_completion_marker(self, log_content: str) -> int | None:
        """Parse completion marker from log content.

        Args:
            log_content: Log file content

        Returns:
            Exit code if found, None otherwise
        """
        # Check for simple completion marker first
        if "[COSMOS_COMPLETE]" in log_content:
            # Look for exit code if provided
            pattern = r"\[COSMOS_COMPLETE\]\s+exit_code=(\d+)"
            match = re.search(pattern, log_content)
            if match:
                return int(match.group(1))
            # Default to success if marker present without exit code
            return 0
        return None

    def check_container_status(self, container_name: str) -> dict[str, Any]:
        """Check status of a Docker container.

        Args:
            container_name: Name of the container

        Returns:
            Dict with running status and exit code
        """
        command = f"sudo docker inspect {container_name} --format '{{{{json .State}}}}'"

        # Use ssh_manager directly with stream_output=False to avoid console output
        exit_code, stdout, stderr = self.ssh_manager.execute_command(command, stream_output=False)

        if exit_code != 0:
            # Container not found
            logger.warning("Container %s not found: %s", container_name, stderr)
            return {"running": False, "exit_code": -1}

        try:
            state = json.loads(stdout)
            return {
                "running": state.get("Running", False),
                "exit_code": state.get("ExitCode"),
            }
        except json.JSONDecodeError as e:
            logger.error("Failed to parse container state: %s", e)
            return {"running": False, "exit_code": -1}

    def check_run_completion(self, run_id: str) -> int | None:
        """Check if a run has completed by reading its log file.

        Args:
            run_id: Run ID to check

        Returns:
            Exit code if completed, None if still running
        """
        remote_config = self.config_manager.get_remote_config()
        log_path = f"{remote_config.remote_dir}/outputs/run_{run_id}/run.log"
        command = f"cat {log_path} 2>/dev/null || echo ''"

        # Use ssh_manager directly with stream_output=False to avoid console output
        exit_code, stdout, stderr = self.ssh_manager.execute_command(command, stream_output=False)

        if exit_code == 0 and stdout:
            return self.parse_completion_marker(stdout)
        return None

    def download_outputs(self, run_data: dict[str, Any]) -> dict[str, Any] | None:
        """Download output files for a completed run.

        Args:
            run_data: Run data dictionary with id and model_type

        Returns:
            Dict with output paths and completion timestamp, or None on failure
        """
        run_id = run_data["id"]
        model_type = run_data["model_type"]

        try:
            remote_config = self.config_manager.get_remote_config()
            remote_dir = remote_config.remote_dir

            # Create local directories
            run_dir = Path("outputs") / f"run_{run_id}"
            run_dir.mkdir(parents=True, exist_ok=True)
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(exist_ok=True)

            outputs = {"completed_at": datetime.now(timezone.utc).isoformat()}

            # Download all files from the remote output directory
            remote_output_dir = f"{remote_dir}/outputs/run_{run_id}"

            # List all files in remote directory
            command = f"ls -la {remote_output_dir} 2>/dev/null | grep '^-' | awk '{{print $9}}'"
            exit_code, stdout, stderr = self.ssh_manager.execute_command(
                command, stream_output=False
            )

            if exit_code != 0 or not stdout.strip():
                logger.warning("No output files found for %s", run_id)
                return outputs

            # Download each file
            files = stdout.strip().split("\n")
            downloaded_files = []

            for filename in files:
                if not filename:
                    continue

                remote_file = f"{remote_output_dir}/{filename}"
                local_file = outputs_dir / filename

                if self.file_transfer.download_file(remote_file, local_file):
                    downloaded_files.append(str(local_file))
                    logger.info("Downloaded %s for run %s", filename, run_id)
                else:
                    logger.error("Failed to download %s for run %s", filename, run_id)

            if downloaded_files:
                outputs["files"] = downloaded_files

                # Extract specific information based on model type
                if model_type == "enhancement":
                    # Try to extract enhanced text from batch_results.json if it exists
                    batch_results_file = outputs_dir / "batch_results.json"
                    if batch_results_file.exists():
                        results = self.json_handler.read_json(batch_results_file)
                        if results and len(results) > 0:
                            outputs["enhanced_text"] = results[0].get("upsampled_prompt", "")

                    # Also check prompt_upsampled.json
                    prompt_file = outputs_dir / "prompt_upsampled.json"
                    if prompt_file.exists():
                        prompt_data = self.json_handler.read_json(prompt_file)
                        if prompt_data:
                            outputs["prompt_data"] = prompt_data

                elif model_type == "inference":
                    # Look for output video
                    output_file = outputs_dir / "output.mp4"
                    if output_file.exists():
                        outputs["output_path"] = str(output_file)

                elif model_type == "upscale":
                    # Look for upscaled video
                    output_file = outputs_dir / "output_4k.mp4"
                    if output_file.exists():
                        outputs["output_path"] = str(output_file)

                logger.info("Downloaded %d files for %s", len(downloaded_files), run_id)
            else:
                logger.warning("No files downloaded for %s", run_id)

            return outputs

        except Exception as e:
            logger.error("Error downloading outputs for %s: %s", run_id, e)
            return None

    def sync_run_status(self, run_data: dict[str, Any], data_service: Any) -> dict[str, Any]:
        """Sync status of a running container and download outputs if complete.

        Args:
            run_data: Dictionary with run information
            data_service: DataRepository service for updating status

        Returns:
            Updated run data dictionary
        """
        run_id = run_data["id"]

        # Skip if already cached as completed
        if run_id in self._completed_cache:
            return run_data

        # Only sync if status is "running"
        if run_data.get("status") != "running":
            return run_data

        # Create services for this sync operation
        try:
            self._create_services()
        except Exception as e:
            logger.warning("Failed to create services for status sync: %s", e)
            return run_data

        try:
            # Check container status - use truncated ID to match existing codebase pattern
            # Handle transfer, enhance, and upscale container types
            model_type = run_data.get("model_type", "transfer")
            if model_type == "enhance":
                container_name = f"cosmos_enhance_{run_id[:8]}"
            elif model_type == "upscale":
                container_name = f"cosmos_upscale_{run_id[:8]}"
            else:
                container_name = f"cosmos_transfer_{run_id[:8]}"
            container_status = self.check_container_status(container_name)

            if container_status["running"]:
                # Still running
                return run_data

            # Container stopped, check exit code from logs
            exit_code = self.check_run_completion(run_id)
            logger.info("Checked completion for %s, exit_code=%s", run_id, exit_code)

            if exit_code is None:
                # No completion marker yet, might still be writing
                logger.info("No completion marker found for %s", run_id)
                return run_data

            # Determine final status based on exit code
            if exit_code == 0:
                new_status = "completed"
                # Download outputs
                logger.info("Downloading outputs for %s", run_id)
                outputs = self.download_outputs(run_data)
                if outputs:
                    logger.info("Downloaded outputs for %s: %s", run_id, outputs.keys())
                    run_data["outputs"] = outputs
                    data_service.update_run(run_id, outputs=outputs)
                else:
                    logger.warning("Failed to download outputs for %s", run_id)
            else:
                new_status = "failed"
                run_data["error_message"] = f"Container exited with code {exit_code}"
                data_service.update_run(run_id, error_message=run_data["error_message"])

            # Update status
            run_data["status"] = new_status
            data_service.update_run_status(run_id, new_status)

            # Cache completed runs
            self._completed_cache.add(run_id)

            logger.info("Synced status for %s: %s", run_id, new_status)
            return run_data

        except Exception as e:
            logger.warning("Failed to sync status for %s: %s", run_id, e)
            return run_data

        finally:
            # Clean up services - ensure SSH connections are properly closed
            if self.ssh_manager:
                try:
                    self.ssh_manager.close()
                except Exception as e:
                    logger.debug("Error closing SSH connection: %s", e)
            self.ssh_manager = None
            self.file_transfer = None
            self.remote_executor = None
