"""Status checker for monitoring and syncing container execution status."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.execution.command_builder import RemoteCommandExecutor
from cosmos_workflow.utils.json_handler import JSONHandler
from cosmos_workflow.utils.logging import logger


class StatusChecker:
    """Checks container status and downloads outputs when complete."""

    def __init__(self, ssh_manager, config_manager, file_transfer_service):
        """Initialize StatusChecker with required dependencies.

        Args:
            ssh_manager: SSHManager instance for SSH connections
            config_manager: ConfigManager instance for configuration
            file_transfer_service: FileTransferService for file downloads
        """
        self.ssh_manager = ssh_manager
        self.config_manager = config_manager
        self.file_transfer = file_transfer_service

        # Create RemoteCommandExecutor wrapper
        self.remote_executor = RemoteCommandExecutor(self.ssh_manager)

        # Add execute method for compatibility if needed
        if not hasattr(self.remote_executor, "execute"):
            self.remote_executor.execute = self._execute_wrapper

        # Create JSONHandler for JSON operations
        self.json_handler = JSONHandler()

        # Cache for completed runs to avoid re-checking
        self._completed_cache = set()

    def _execute_wrapper(self, command: str) -> tuple:
        """Wrapper for execute_command to provide tuple return format.

        Args:
            command: Command to execute

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            # execute_command returns stdout on success
            stdout = self.remote_executor.execute_command(command)
            return (0, stdout, "")
        except RuntimeError as e:
            # On failure, execute_command raises RuntimeError
            return (1, "", str(e))

    def parse_completion_marker(self, log_content: str) -> int | None:
        """Parse completion marker from log content.

        Args:
            log_content: Log file content

        Returns:
            Exit code if found, None otherwise
        """
        pattern = r"\[COSMOS_COMPLETE\]\s+exit_code=(\d+)"
        match = re.search(pattern, log_content)
        if match:
            return int(match.group(1))
        return None

    def check_container_status(self, container_name: str) -> dict[str, Any]:
        """Check status of a Docker container.

        Args:
            container_name: Name of the container

        Returns:
            Dict with running status and exit code
        """
        command = f"sudo docker inspect {container_name} --format '{{{{json .State}}}}'"

        # Ensure remote_executor has execute method for tests
        if not hasattr(self.remote_executor, "execute"):
            self.remote_executor.execute = self.remote_executor.execute_command

        exit_code, stdout, stderr = self.remote_executor.execute(command)

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

        # Ensure remote_executor has execute method for tests
        if not hasattr(self.remote_executor, "execute"):
            self.remote_executor.execute = self.remote_executor.execute_command

        exit_code, stdout, stderr = self.remote_executor.execute(command)

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

            if model_type == "inference":
                # Download inference output video
                remote_file = f"{remote_dir}/outputs/run_{run_id}/output.mp4"
                local_file = outputs_dir / "output.mp4"

                if self.file_transfer.download_file(remote_file, local_file):
                    outputs["output_path"] = str(local_file)
                    logger.info("Downloaded inference output for %s", run_id)
                else:
                    logger.error("Failed to download inference output for %s", run_id)
                    return None

            elif model_type == "enhancement":
                # Download enhancement results JSON
                remote_file = f"{remote_dir}/outputs/run_{run_id}/batch_results.json"
                local_file = outputs_dir / "batch_results.json"

                if self.file_transfer.download_file(remote_file, local_file):
                    # Read JSON and extract enhanced text
                    results = self.json_handler.read_json(local_file)
                    if results and len(results) > 0:
                        outputs["enhanced_text"] = results[0].get("upsampled_prompt", "")
                    logger.info("Downloaded enhancement output for %s", run_id)
                else:
                    logger.error("Failed to download enhancement output for %s", run_id)
                    return None

            elif model_type == "upscaling":
                # Download upscaled video
                remote_file = f"{remote_dir}/outputs/run_{run_id}/output_4k.mp4"
                local_file = outputs_dir / "output_4k.mp4"

                if self.file_transfer.download_file(remote_file, local_file):
                    outputs["output_path"] = str(local_file)
                    logger.info("Downloaded upscaling output for %s", run_id)
                else:
                    logger.error("Failed to download upscaling output for %s", run_id)
                    return None

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

        # Check container status - use truncated ID to match existing codebase pattern
        container_name = f"cosmos_transfer_{run_id[:8]}"
        container_status = self.check_container_status(container_name)

        if container_status["running"]:
            # Still running
            return run_data

        # Container stopped, check exit code from logs
        exit_code = self.check_run_completion(run_id)

        if exit_code is None:
            # No completion marker yet, might still be writing
            return run_data

        # Determine final status based on exit code
        if exit_code == 0:
            new_status = "completed"
            # Download outputs
            outputs = self.download_outputs(run_data)
            if outputs:
                run_data["outputs"] = outputs
                data_service.update_run(run_id, outputs=outputs)
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
