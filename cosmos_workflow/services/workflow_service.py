"""Workflow service for managing prompts and runs.

Provides business logic for creating, retrieving and managing AI model
prompts and their execution runs. Supports multiple model types through
flexible database schema.
"""

import hashlib
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.database.models import Prompt, Run
from cosmos_workflow.utils.logging import logger

# Supported AI model types
SUPPORTED_MODEL_TYPES = {"transfer", "reason", "predict", "enhancement"}
MAX_PROMPT_LENGTH = 10000


class PromptNotFoundError(ValueError):
    """Raised when a prompt is not found."""

    pass


class WorkflowService:
    """Service for managing workflow operations.

    Handles prompt and run creation, retrieval, and management
    with transaction safety and proper error handling.
    """

    def __init__(self, db_connection: DatabaseConnection, config_manager: ConfigManager):
        """Initialize the workflow service.

        Args:
            db_connection: Database connection instance
            config_manager: Configuration manager instance

        Raises:
            ValueError: If db_connection or config_manager is None
        """
        if db_connection is None:
            raise ValueError("db_connection cannot be None")
        if config_manager is None:
            raise ValueError("config_manager cannot be None")

        self.db = db_connection
        self.config = config_manager

    def create_prompt(
        self,
        model_type: str,
        prompt_text: str,
        inputs: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new prompt in the database.

        Args:
            model_type: Type of AI model (transfer, reason, predict, etc.)
            prompt_text: The prompt text
            inputs: Input data (video paths, images, etc.)
            parameters: Model-specific parameters

        Returns:
            Dictionary containing prompt data

        Raises:
            ValueError: If required fields are missing or invalid
        """
        logger.info("Creating prompt with model_type=%s", model_type)

        # Validate inputs
        if model_type is None:
            raise ValueError("model_type is required")
        if model_type not in SUPPORTED_MODEL_TYPES:
            raise ValueError(
                f"Unsupported model_type: {model_type}. Must be one of {SUPPORTED_MODEL_TYPES}"
            )
        if not prompt_text or prompt_text.isspace():
            raise ValueError("prompt_text cannot be empty")
        if len(prompt_text) > MAX_PROMPT_LENGTH:
            raise ValueError(f"prompt_text exceeds maximum length of {MAX_PROMPT_LENGTH}")
        # Sanitize prompt text
        prompt_text = prompt_text.replace("\x00", "").strip()

        if inputs is None:
            raise ValueError("inputs cannot be None")
        if parameters is None:
            raise ValueError("parameters cannot be None")

        # Generate prompt ID based on content
        prompt_id = self._generate_prompt_id(model_type, prompt_text, inputs, parameters)

        # Create prompt in database
        with self.db.get_session() as session:
            prompt = Prompt(
                id=prompt_id,
                model_type=model_type,
                prompt_text=prompt_text,
                inputs=inputs,
                parameters=parameters,
            )
            session.add(prompt)
            session.flush()  # Flush to get created_at populated

            # Extract data after flush but before commit for transaction safety
            result = {
                "id": prompt.id,
                "model_type": prompt.model_type,
                "prompt_text": prompt.prompt_text,
                "inputs": prompt.inputs,
                "parameters": prompt.parameters,
                "created_at": prompt.created_at.isoformat(),
            }

            session.commit()
            logger.info("Created prompt with id=%s", prompt.id)
            return result

    def create_run(
        self,
        prompt_id: str,
        execution_config: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        initial_status: str = "pending",
    ) -> dict[str, Any]:
        """Create a new run for a prompt.

        Args:
            prompt_id: ID of the prompt to run
            execution_config: Execution configuration (GPU node, weights, etc.)
            metadata: Optional metadata (user, priority, etc.)
            initial_status: Initial status for the run (default: "pending")

        Returns:
            Dictionary containing run data

        Raises:
            ValueError: If prompt not found or invalid parameters
        """
        logger.info("Creating run for prompt_id=%s", prompt_id)

        # Validate inputs
        if prompt_id is None:
            raise ValueError("prompt_id is required")
        if execution_config is None:
            raise ValueError("execution_config cannot be None")

        if metadata is None:
            metadata = {}

        with self.db.get_session() as session:
            # Check prompt exists
            prompt = session.query(Prompt).filter_by(id=prompt_id).first()
            if not prompt:
                raise PromptNotFoundError(f"Prompt not found: {prompt_id}")

            # Generate run ID
            run_id = self._generate_run_id(prompt_id, execution_config)

            # Create run
            run = Run(
                id=run_id,
                prompt_id=prompt_id,
                model_type=prompt.model_type,
                status=initial_status,
                execution_config=execution_config,
                outputs={},  # Empty initially
                run_metadata=metadata,
            )
            session.add(run)
            session.flush()  # Flush to get created_at populated

            # Extract data after flush but before commit for transaction safety
            result = {
                "id": run.id,
                "prompt_id": run.prompt_id,
                "model_type": run.model_type,
                "status": run.status,
                "execution_config": run.execution_config,
                "outputs": run.outputs,
                "metadata": run.run_metadata,
                "created_at": run.created_at.isoformat(),
            }

            session.commit()
            logger.info("Created run with id=%s for prompt=%s", run.id, prompt_id)
            return result

    def get_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        """Retrieve a prompt by ID.

        Args:
            prompt_id: The prompt ID to retrieve

        Returns:
            Dictionary containing prompt data, or None if not found

        Raises:
            ValueError: If prompt_id is None or empty
        """
        if prompt_id is None:
            raise ValueError("prompt_id is required")
        if not prompt_id or prompt_id.isspace():
            raise ValueError("prompt_id cannot be empty")

        logger.debug("Retrieving prompt with id=%s", prompt_id)

        with self.db.get_session() as session:
            prompt = session.query(Prompt).filter_by(id=prompt_id).first()
            if not prompt:
                return None

            return {
                "id": prompt.id,
                "model_type": prompt.model_type,
                "prompt_text": prompt.prompt_text,
                "inputs": prompt.inputs,
                "parameters": prompt.parameters,
                "created_at": prompt.created_at.isoformat(),
            }

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a run by ID.

        Args:
            run_id: The run ID to retrieve

        Returns:
            Dictionary containing run data, or None if not found

        Raises:
            ValueError: If run_id is None or empty
        """
        if run_id is None:
            raise ValueError("run_id is required")
        if not run_id or run_id.isspace():
            raise ValueError("run_id cannot be empty")

        logger.debug("Retrieving run with id=%s", run_id)

        with self.db.get_session() as session:
            run = session.query(Run).filter_by(id=run_id).first()
            if not run:
                return None

            result = {
                "id": run.id,
                "prompt_id": run.prompt_id,
                "model_type": run.model_type,
                "status": run.status,
                "execution_config": run.execution_config,
                "outputs": run.outputs,
                "metadata": run.run_metadata,
                "created_at": run.created_at.isoformat(),
                "updated_at": run.updated_at.isoformat(),
            }

            # Add optional timestamps
            if run.started_at:
                result["started_at"] = run.started_at.isoformat()
            if run.completed_at:
                result["completed_at"] = run.completed_at.isoformat()

            return result

    def _generate_prompt_id(
        self, model_type: str, prompt_text: str, inputs: dict[str, Any], parameters: dict[str, Any]
    ) -> str:
        """Generate unique ID for a prompt.

        Args:
            model_type: Type of AI model
            prompt_text: The prompt text
            inputs: Input data
            parameters: Model-specific parameters

        Returns:
            Unique ID string starting with 'ps_'
        """
        # Create deterministic string representation including parameters
        # This ensures enhanced prompts get different IDs even with same text
        content = (
            f"{model_type}|{prompt_text}|{sorted(inputs.items())}|{sorted(parameters.items())}"
        )

        # Generate hash
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()[:20]  # Increased from 12 to reduce collision risk

        return f"ps_{hash_hex}"

    def update_run_status(self, run_id: str, status: str) -> dict[str, Any] | None:
        """Update the status of a run.

        Args:
            run_id: The run ID to update
            status: New status (pending, running, completed, failed)

        Returns:
            Updated run data, or None if run not found

        Raises:
            ValueError: If run_id is None or status is invalid
        """
        if run_id is None:
            raise ValueError("run_id is required")
        if not run_id or run_id.isspace():
            raise ValueError("run_id cannot be empty")
        if status not in {"pending", "running", "completed", "failed"}:
            raise ValueError(
                f"Invalid status: {status}. Must be one of pending, running, completed, failed"
            )

        logger.info("Updating run status for id=%s to %s", run_id, status)

        with self.db.get_session() as session:
            run = session.query(Run).filter_by(id=run_id).first()
            if not run:
                return None

            run.status = status

            # Set timestamps based on status
            from datetime import datetime, timezone

            if status == "running" and run.started_at is None:
                run.started_at = datetime.now(timezone.utc)
            elif status in {"completed", "failed"} and run.completed_at is None:
                run.completed_at = datetime.now(timezone.utc)

            session.flush()  # Flush to ensure updated_at is set

            result = {
                "id": run.id,
                "prompt_id": run.prompt_id,
                "model_type": run.model_type,
                "status": run.status,
                "execution_config": run.execution_config,
                "outputs": run.outputs,
                "metadata": run.run_metadata,
                "created_at": run.created_at.isoformat(),
                "updated_at": run.updated_at.isoformat(),
            }

            # Add optional timestamps
            if run.started_at:
                result["started_at"] = run.started_at.isoformat()
            if run.completed_at:
                result["completed_at"] = run.completed_at.isoformat()

            session.commit()
            logger.info("Updated run %s status to %s", run_id, status)
            return result

    def update_run(self, run_id: str, **kwargs) -> dict[str, Any] | None:
        """Update run fields.

        Args:
            run_id: The run ID to update
            **kwargs: Fields to update (outputs, metadata, execution_config)

        Returns:
            Updated run data, or None if run not found

        Raises:
            ValueError: If run_id is None or invalid fields provided
        """
        if run_id is None:
            raise ValueError("run_id is required")
        if not run_id or run_id.isspace():
            raise ValueError("run_id cannot be empty")

        # Validate allowed fields (now includes log_path and error_message)
        allowed_fields = {
            "outputs",
            "metadata",
            "execution_config",
            "run_metadata",
            "log_path",
            "error_message",
        }
        invalid_fields = set(kwargs.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields: {invalid_fields}. Allowed: {allowed_fields}")

        logger.info("Updating run id=%s with fields: %s", run_id, list(kwargs.keys()))

        with self.db.get_session() as session:
            run = session.query(Run).filter_by(id=run_id).first()
            if not run:
                return None

            # Update fields with special handling
            for key, value in kwargs.items():
                if key == "metadata":
                    key = "run_metadata"  # Map to correct column name
                elif key == "error_message":
                    # Truncate error messages if too long
                    value = value[:1000] if value else value
                    # Also set status to failed when error_message is provided
                    if value:
                        run.status = "failed"
                        # Set completed timestamp if not already set
                        from datetime import datetime, timezone

                        if run.completed_at is None:
                            run.completed_at = datetime.now(timezone.utc)
                setattr(run, key, value)

            session.flush()  # Flush to ensure updated_at is set

            result = {
                "id": run.id,
                "prompt_id": run.prompt_id,
                "model_type": run.model_type,
                "status": run.status,
                "execution_config": run.execution_config,
                "outputs": run.outputs,
                "metadata": run.run_metadata,
                "created_at": run.created_at.isoformat(),
                "updated_at": run.updated_at.isoformat(),
            }

            # Add optional fields
            if run.log_path:
                result["log_path"] = run.log_path
            if run.error_message:
                result["error_message"] = run.error_message
            if run.started_at:
                result["started_at"] = run.started_at.isoformat()
            if run.completed_at:
                result["completed_at"] = run.completed_at.isoformat()

            session.commit()

            # Log appropriately based on what was updated
            if "error_message" in kwargs:
                logger.error("Run %s failed: %s", run_id, kwargs["error_message"][:100])
            else:
                logger.info("Updated run %s", run_id)
            return result

    # Simplified: These methods now just call update_run with the appropriate fields
    def update_run_with_log(self, run_id: str, log_path: str) -> dict[str, Any] | None:
        """Update run with log path.

        DEPRECATED: Use update_run(run_id, log_path=log_path) instead.
        Kept for backward compatibility.
        """
        return self.update_run(run_id, log_path=str(log_path))

    def update_run_error(self, run_id: str, error_message: str) -> dict[str, Any] | None:
        """Update run with error message and set status to failed.

        DEPRECATED: Use update_run(run_id, error_message=error_message) instead.
        Kept for backward compatibility.
        """
        return self.update_run(run_id, error_message=error_message)

    def _generate_run_id(self, prompt_id: str, execution_config: dict[str, Any]) -> str:
        """Generate unique ID for a run.

        Args:
            prompt_id: The prompt ID
            execution_config: Execution configuration

        Returns:
            Unique ID string starting with 'rs_'
        """
        # Use UUID4 for guaranteed uniqueness
        unique_id = str(uuid.uuid4()).replace("-", "")[:32]
        return f"rs_{unique_id}"

    def list_prompts(
        self, model_type: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List prompts with optional filtering and pagination.

        Args:
            model_type: Optional filter by model type
            limit: Maximum number of results to return (default: 50)
            offset: Number of results to skip (default: 0)

        Returns:
            List of prompt dictionaries
        """
        logger.debug(
            "Listing prompts with model_type=%s, limit=%s, offset=%s", model_type, limit, offset
        )

        try:
            with self.db.get_session() as session:
                query = session.query(Prompt)

                # Apply model type filter if specified
                if model_type:
                    query = query.filter(Prompt.model_type == model_type)

                # Order by created_at descending (newest first)
                query = query.order_by(Prompt.created_at.desc())

                # Apply pagination
                prompts = query.limit(limit).offset(offset).all()

                # Convert to dictionaries
                result = []
                for prompt in prompts:
                    result.append(
                        {
                            "id": prompt.id,
                            "model_type": prompt.model_type,
                            "prompt_text": prompt.prompt_text,
                            "inputs": prompt.inputs,
                            "parameters": prompt.parameters,
                            "created_at": prompt.created_at.isoformat(),
                        }
                    )

                return result
        except SQLAlchemyError as e:
            logger.error("Error listing prompts: %s", e)
            return []

    def list_runs(
        self,
        status: str | None = None,
        prompt_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List runs with optional filtering and pagination.

        Args:
            status: Optional filter by status
            prompt_id: Optional filter by prompt ID
            limit: Maximum number of results to return (default: 50)
            offset: Number of results to skip (default: 0)

        Returns:
            List of run dictionaries
        """
        logger.debug(
            "Listing runs with status=%s, prompt_id=%s, limit=%s, offset=%s",
            status,
            prompt_id,
            limit,
            offset,
        )

        try:
            with self.db.get_session() as session:
                query = session.query(Run)

                # Apply filters
                if status:
                    query = query.filter(Run.status == status)
                if prompt_id:
                    query = query.filter(Run.prompt_id == prompt_id)

                # Order by created_at descending (newest first)
                query = query.order_by(Run.created_at.desc())

                # Apply pagination
                runs = query.limit(limit).offset(offset).all()

                # Convert to dictionaries
                result = []
                for run in runs:
                    run_dict = {
                        "id": run.id,
                        "prompt_id": run.prompt_id,
                        "model_type": run.model_type,
                        "status": run.status,
                        "execution_config": run.execution_config,
                        "outputs": run.outputs,
                        "metadata": run.run_metadata,
                        "created_at": run.created_at.isoformat(),
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    }
                    result.append(run_dict)

                return result
        except SQLAlchemyError as e:
            logger.error("Error listing runs: %s", e)
            return []

    def search_prompts(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search prompts by text content.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 50)

        Returns:
            List of matching prompt dictionaries
        """
        if not query or not query.strip():
            logger.debug("Empty search query provided")
            return []

        logger.debug("Searching prompts with query=%s, limit=%s", query, limit)

        try:
            with self.db.get_session() as session:
                # Escape special characters for LIKE pattern to prevent SQL injection
                # Escape backslash first, then % and _ wildcards
                escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                search_pattern = f"%{escaped_query.lower()}%"

                # Search in prompt_text (case-insensitive)
                prompts = (
                    session.query(Prompt)
                    .filter(Prompt.prompt_text.ilike(search_pattern))
                    .order_by(Prompt.created_at.desc())
                    .limit(limit)
                    .all()
                )

                # Convert to dictionaries
                result = []
                for prompt in prompts:
                    result.append(
                        {
                            "id": prompt.id,
                            "model_type": prompt.model_type,
                            "prompt_text": prompt.prompt_text,
                            "inputs": prompt.inputs,
                            "parameters": prompt.parameters,
                            "created_at": prompt.created_at.isoformat(),
                        }
                    )

                return result
        except SQLAlchemyError as e:
            logger.error("Error searching prompts: %s", e)
            return []

    def _sanitize_input(self, text: str) -> str:
        """Sanitize input text by stripping whitespace."""
        return text.strip() if text else ""

    def update_prompt(self, prompt_id: str, **kwargs) -> dict[str, Any] | None:
        """Update an existing prompt's fields.

        Args:
            prompt_id: The prompt ID to update
            **kwargs: Fields to update (prompt_text, parameters)

        Returns:
            Updated prompt dictionary or None if not found
        """
        if not prompt_id or not prompt_id.strip():
            logger.debug("Empty prompt_id provided")
            return None

        logger.debug("Updating prompt %s with fields: %s", prompt_id, kwargs.keys())

        try:
            with self.db.get_session() as session:
                prompt = session.query(Prompt).filter_by(id=prompt_id).first()

                if not prompt:
                    logger.warning("Prompt not found: %s", prompt_id)
                    return None

                # Update allowed fields
                if "prompt_text" in kwargs:
                    prompt.prompt_text = self._sanitize_input(kwargs["prompt_text"])

                if "parameters" in kwargs:
                    # Merge parameters instead of replacing
                    existing_params = prompt.parameters or {}
                    updated_params = {**existing_params, **kwargs["parameters"]}
                    prompt.parameters = updated_params

                # Note: We don't allow updating inputs or model_type for data integrity

                session.commit()
                logger.info("Updated prompt %s", prompt_id)

                return self._prompt_to_dict(prompt)

        except SQLAlchemyError as e:
            logger.error("Error updating prompt %s: %s", prompt_id, e)
            return None

    def get_prompt_with_runs(self, prompt_id: str) -> dict[str, Any] | None:
        """Get a prompt with all its associated runs.

        Args:
            prompt_id: The prompt ID

        Returns:
            Dictionary containing prompt data with runs list, or None if not found
        """
        if not prompt_id or not prompt_id.strip():
            logger.debug("Empty prompt_id provided")
            return None

        logger.debug("Getting prompt with runs for prompt_id=%s", prompt_id)

        try:
            with self.db.get_session() as session:
                # Get prompt with eager loading of runs to avoid N+1 query issue
                prompt = (
                    session.query(Prompt)
                    .options(joinedload(Prompt.runs))
                    .filter(Prompt.id == prompt_id)
                    .first()
                )

                if not prompt:
                    return None

                # Build prompt dictionary
                result = {
                    "id": prompt.id,
                    "model_type": prompt.model_type,
                    "prompt_text": prompt.prompt_text,
                    "inputs": prompt.inputs,
                    "parameters": prompt.parameters,
                    "created_at": prompt.created_at.isoformat(),
                    "runs": [],
                }

                # Add runs if they exist
                for run in prompt.runs:
                    run_dict = {
                        "id": run.id,
                        "prompt_id": run.prompt_id,
                        "model_type": run.model_type,
                        "status": run.status,
                        "execution_config": run.execution_config,
                        "outputs": run.outputs,
                        "metadata": run.run_metadata,
                        "created_at": run.created_at.isoformat(),
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    }
                    result["runs"].append(run_dict)

                return result
        except SQLAlchemyError as e:
            logger.error("Error getting prompt with runs: %s", e)
            return None

    def preview_prompt_deletion(self, prompt_id: str) -> dict[str, Any]:
        """Preview what would be deleted if a prompt is removed.

        Args:
            prompt_id: The prompt ID to preview deletion for

        Returns:
            Dictionary containing:
            - prompt: Prompt details or None if not found
            - runs: List of runs that would be deleted
            - directories_to_delete: List of output directories that would be removed
            - error: Error message if prompt not found
        """
        logger.debug("Previewing deletion for prompt_id=%s", prompt_id)

        result = {
            "prompt": None,
            "runs": [],
            "directories_to_delete": [],
        }

        # Get prompt with runs
        prompt_data = self.get_prompt_with_runs(prompt_id)
        if not prompt_data:
            result["error"] = "Prompt not found"
            return result

        # Extract prompt info
        result["prompt"] = {
            "id": prompt_data["id"],
            "prompt_text": prompt_data["prompt_text"],
            "model_type": prompt_data["model_type"],
        }

        # Extract runs info
        result["runs"] = prompt_data.get("runs", [])

        # Determine directories that would be deleted
        outputs_dir = self.config.get_local_config().outputs_dir
        for run in result["runs"]:
            run_dir = outputs_dir / f"run_{run['id']}"
            result["directories_to_delete"].append(str(run_dir))

        return result

    def preview_run_deletion(self, run_id: str) -> dict[str, Any]:
        """Preview what would be deleted if a run is removed.

        Args:
            run_id: The run ID to preview deletion for

        Returns:
            Dictionary containing:
            - run: Run details or None if not found
            - directory_to_delete: Output directory that would be removed
            - error: Error message if run not found
        """
        logger.debug("Previewing deletion for run_id=%s", run_id)

        result = {
            "run": None,
            "directory_to_delete": None,
        }

        # Get run details
        run_data = self.get_run(run_id)
        if not run_data:
            result["error"] = "Run not found"
            return result

        # Extract run info
        result["run"] = run_data

        # Determine directory that would be deleted
        outputs_dir = self.config.get_local_config().outputs_dir
        result["directory_to_delete"] = str(outputs_dir / f"run_{run_id}")

        return result

    def delete_prompt(self, prompt_id: str) -> dict[str, Any]:
        """Delete a prompt and all associated runs.

        Args:
            prompt_id: The prompt ID to delete

        Returns:
            Dictionary containing:
            - success: Whether deletion succeeded
            - deleted: Information about what was deleted
            - error: Error message if failed
        """
        logger.info("Deleting prompt_id=%s", prompt_id)

        # Check if prompt exists
        prompt_data = self.get_prompt_with_runs(prompt_id)
        if not prompt_data:
            return {
                "success": False,
                "error": "Prompt not found",
            }

        # Check for running or uploading runs
        active_runs = [
            run for run in prompt_data.get("runs", []) if run["status"] in ("running", "uploading")
        ]
        if active_runs:
            return {
                "success": False,
                "error": f"Cannot delete prompt with active runs (running/uploading). Found {len(active_runs)} active runs.",
            }

        # Collect information about what will be deleted
        deleted_info = {
            "prompt_id": prompt_id,
            "run_ids": [run["id"] for run in prompt_data.get("runs", [])],
            "directories": [],
        }

        # Delete output directories
        import shutil

        outputs_dir = self.config.get_local_config().outputs_dir
        for run in prompt_data.get("runs", []):
            run_dir = outputs_dir / f"run_{run['id']}"
            deleted_info["directories"].append(str(run_dir))
            if run_dir.exists():
                try:
                    shutil.rmtree(run_dir)
                    logger.info("Deleted directory: %s", run_dir)
                except Exception as e:
                    logger.warning("Failed to delete directory %s: %s", run_dir, e)

        # Delete from database (cascade will delete runs)
        try:
            with self.db.get_session() as session:
                prompt = session.query(Prompt).filter_by(id=prompt_id).first()
                if prompt:
                    session.delete(prompt)
                    session.commit()
                    logger.info(
                        "Deleted prompt %s and %d runs from database",
                        prompt_id,
                        len(deleted_info["run_ids"]),
                    )
        except SQLAlchemyError as e:
            logger.error("Database error deleting prompt %s: %s", prompt_id, e)
            return {
                "success": False,
                "error": f"Database error: {e!s}",
            }

        return {
            "success": True,
            "deleted": deleted_info,
        }

    def delete_run(self, run_id: str) -> dict[str, Any]:
        """Delete a run and its output directory.

        Args:
            run_id: The run ID to delete

        Returns:
            Dictionary containing:
            - success: Whether deletion succeeded
            - deleted: Information about what was deleted
            - warnings: Any warnings during deletion
            - error: Error message if failed
        """
        logger.info("Deleting run_id=%s", run_id)

        # Check if run exists
        run_data = self.get_run(run_id)
        if not run_data:
            return {
                "success": False,
                "error": "Run not found",
            }

        # Check for running or uploading status
        if run_data["status"] in ("running", "uploading"):
            return {
                "success": False,
                "error": f"Cannot delete run with status '{run_data['status']}'. Wait for completion or cancel first.",
            }

        # Collect information about what will be deleted
        deleted_info = {
            "run_id": run_id,
            "directory": None,
        }
        warnings = []

        # Delete output directory
        import shutil

        outputs_dir = self.config.get_local_config().outputs_dir
        run_dir = outputs_dir / f"run_{run_id}"
        deleted_info["directory"] = str(run_dir)

        if run_dir.exists():
            try:
                shutil.rmtree(run_dir)
                logger.info("Deleted directory: %s", run_dir)
            except PermissionError as e:
                warnings.append(f"Could not delete directory due to permission error: {e!s}")
                logger.warning("Permission error deleting directory %s: %s", run_dir, e)
            except Exception as e:
                warnings.append(f"Failed to delete directory: {e!s}")
                logger.warning("Failed to delete directory %s: %s", run_dir, e)

        # Delete from database
        try:
            with self.db.get_session() as session:
                run = session.query(Run).filter_by(id=run_id).first()
                if run:
                    session.delete(run)
                    session.commit()
                    logger.info("Deleted run %s from database", run_id)
        except SQLAlchemyError as e:
            logger.error("Database error deleting run %s: %s", run_id, e)
            return {
                "success": False,
                "error": f"Database error: {e!s}",
            }

        result = {
            "success": True,
            "deleted": deleted_info,
        }
        if warnings:
            result["warnings"] = warnings

        return result
