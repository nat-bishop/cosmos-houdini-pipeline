"""Workflow service for managing prompts and runs.

Provides business logic for creating, retrieving and managing AI model
prompts and their execution runs. Supports multiple model types through
flexible database schema.
"""

import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.database.models import Prompt, Run
from cosmos_workflow.execution.status_checker import StatusChecker
from cosmos_workflow.utils.logging import logger

# Supported AI model types
SUPPORTED_MODEL_TYPES = {"transfer", "reason", "predict", "enhance", "upscale"}
MAX_PROMPT_LENGTH = 10000


class PromptNotFoundError(ValueError):
    """Raised when a prompt is not found."""

    pass


class DataRepository:
    """Service for managing workflow operations.

    Handles prompt and run creation, retrieval, and management
    with transaction safety and proper error handling.
    """

    def __init__(self, db_connection: DatabaseConnection, config_manager: ConfigManager = None):
        """Initialize the workflow service.

        Args:
            db_connection: Database connection instance
            config_manager: Configuration manager instance (optional for backward compatibility)

        Raises:
            ValueError: If db_connection is None
        """
        if db_connection is None:
            raise ValueError("db_connection cannot be None")

        self.db = db_connection
        self.config = config_manager
        self.status_checker: StatusChecker | None = None

    def initialize_status_checker(self, ssh_manager, file_transfer_service):
        """Initialize the StatusChecker for lazy status synchronization.

        Args:
            ssh_manager: SSHManager instance for SSH connections
            file_transfer_service: FileTransferService for file downloads
        """
        if self.config is None:
            raise ValueError("config_manager must be set before initializing status checker")

        self.status_checker = StatusChecker(
            ssh_manager=ssh_manager,
            config_manager=self.config,
            file_transfer_service=file_transfer_service,
        )
        logger.info("StatusChecker initialized for lazy sync")

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

        # Generate prompt ID using UUID4
        prompt_id = self._generate_prompt_id()

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
        model_type: str | None = None,
    ) -> dict[str, Any]:
        """Create a new run for a prompt.

        Args:
            prompt_id: ID of the prompt to run
            execution_config: Execution configuration (GPU node, weights, etc.)
            metadata: Optional metadata (user, priority, etc.)
            initial_status: Initial status for the run (default: "pending")
            model_type: Override model type (default: use prompt's model_type)
                       Used for "enhance" and "upscale" runs

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
            run_id = self._generate_run_id()

            # Validate provided model_type if specified
            if model_type is not None and model_type not in SUPPORTED_MODEL_TYPES:
                raise ValueError(
                    f"Invalid model_type '{model_type}'. Must be one of: {SUPPORTED_MODEL_TYPES}"
                )

            # Use provided model_type or default to prompt's model_type
            run_model_type = model_type if model_type is not None else prompt.model_type

            # Create run
            run = Run(
                id=run_id,
                prompt_id=prompt_id,
                model_type=run_model_type,
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
            logger.info(
                "Created run with id=%s for prompt=%s with model_type=%s",
                run.id,
                prompt_id,
                run_model_type,
            )
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

            run_dict = self._run_to_dict(run)

            # Trigger lazy sync if status checker is available and run is running
            if self.status_checker and run_dict.get("status") == "running":
                try:
                    run_dict = self.status_checker.sync_run_status(run_dict, self)
                except Exception as e:
                    logger.warning("Failed to sync run status for %s: %s", run_id, e)

            return run_dict

    def _run_to_dict(self, run: Run) -> dict[str, Any]:
        """Convert Run model to dict with all fields.

        Args:
            run: Run model instance

        Returns:
            Dictionary containing all run fields
        """
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

        return result

    def _prompt_to_dict(self, prompt: Prompt) -> dict[str, Any]:
        """Convert Prompt model to dict.

        Args:
            prompt: Prompt model instance

        Returns:
            Dictionary containing prompt fields
        """
        return {
            "id": prompt.id,
            "model_type": prompt.model_type,
            "prompt_text": prompt.prompt_text,
            "inputs": prompt.inputs,
            "parameters": prompt.parameters,
            "created_at": prompt.created_at.isoformat(),
        }

    @staticmethod
    def _generate_prompt_id() -> str:
        """Generate unique ID for a prompt using UUID4.

        Returns:
            Unique ID string starting with 'ps_'
        """
        # Use UUID4 for guaranteed uniqueness
        unique_id = str(uuid.uuid4()).replace("-", "")[:32]
        return f"ps_{unique_id}"

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
            result = self._run_to_dict(run)
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
            result = self._run_to_dict(run)
            session.commit()

            # Log appropriately based on what was updated
            if "error_message" in kwargs:
                logger.error("Run %s failed: %s", run_id, kwargs["error_message"][:100])
            else:
                logger.info("Updated run %s", run_id)
            return result

    @staticmethod
    def _generate_run_id() -> str:
        """Generate unique ID for a run using UUID4.

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

                    # Trigger lazy sync if status checker is available and run is running
                    if self.status_checker and run_dict.get("status") == "running":
                        try:
                            run_dict = self.status_checker.sync_run_status(run_dict, self)
                        except Exception as e:
                            logger.warning(
                                "Failed to sync run status for %s: %s", run_dict["id"], e
                            )

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

    @staticmethod
    def _sanitize_input(text: str) -> str:
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

    def preview_prompt_deletion(self, prompt_id: str, keep_outputs: bool = True) -> dict[str, Any]:
        """Preview what would be deleted if a prompt is removed.

        Args:
            prompt_id: The prompt ID to preview deletion for
            keep_outputs: Whether to keep output files (default: True)

        Returns:
            Dictionary containing:
            - prompt: Prompt details or None if not found
            - runs: List of runs that would be deleted
            - directories_to_delete: List of output directories that would be removed
            - keep_outputs: Whether outputs will be kept
            - files_summary: Summary of files to be deleted (if not keeping outputs)
            - error: Error message if prompt not found
        """
        logger.debug("Previewing deletion for prompt_id=%s", prompt_id)

        result = {
            "prompt": None,
            "runs": [],
            "directories_to_delete": [],
            "keep_outputs": keep_outputs,
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
        if not keep_outputs:
            outputs_dir = self.config.get_local_config().outputs_dir
            total_files = 0
            total_size = 0
            files_by_type = {}

            for run in result["runs"]:
                run_dir = outputs_dir / f"run_{run['id']}"
                result["directories_to_delete"].append(str(run_dir))

                # Collect file statistics
                if run_dir.exists():
                    for file_path in run_dir.rglob("*"):
                        if file_path.is_file():
                            total_files += 1
                            size = file_path.stat().st_size
                            total_size += size
                            ext = file_path.suffix.lower().lstrip(".") or "other"
                            if ext not in files_by_type:
                                files_by_type[ext] = {"count": 0, "size": 0}
                            files_by_type[ext]["count"] += 1
                            files_by_type[ext]["size"] += size

            # Add file summary
            if total_files > 0:
                result["files_summary"] = {
                    "total_files": total_files,
                    "total_size": self._format_size(total_size),
                    "by_type": {
                        ext: {"count": info["count"], "size": self._format_size(info["size"])}
                        for ext, info in files_by_type.items()
                    },
                }

        return result

    def preview_run_deletion(self, run_id: str, keep_outputs: bool = True) -> dict[str, Any]:
        """Preview what would be deleted if a run is removed.

        Args:
            run_id: The run ID to preview deletion for
            keep_outputs: Whether to keep output files (default: True)

        Returns:
            Dictionary containing:
            - run: Run details or None if not found
            - directory_to_delete: Output directory that would be removed
            - keep_outputs: Whether outputs will be kept
            - files: Detailed file information (if not keeping outputs)
            - total_files: Total number of files
            - total_size: Total size of files
            - error: Error message if run not found
        """
        logger.debug("Previewing deletion for run_id=%s", run_id)

        result = {
            "run": None,
            "directory_to_delete": None,
            "keep_outputs": keep_outputs,
        }

        # Get run details
        run_data = self.get_run(run_id)
        if not run_data:
            result["error"] = "Run not found"
            return result

        # Extract run info
        result["run"] = run_data

        # Determine directory that would be deleted
        if not keep_outputs:
            outputs_dir = self.config.get_local_config().outputs_dir
            run_dir = outputs_dir / f"run_{run_id}"
            result["directory_to_delete"] = str(run_dir)

            # Collect detailed file information
            if run_dir.exists():
                files_by_type = {}
                total_files = 0
                total_size = 0

                for file_path in run_dir.rglob("*"):
                    if file_path.is_file():
                        total_files += 1
                        size = file_path.stat().st_size
                        total_size += size

                        ext = file_path.suffix.lower().lstrip(".") or "other"
                        if ext == "mp4":
                            ext = "video"
                        elif ext in ["jpg", "jpeg", "png", "gif"]:
                            ext = "image"
                        elif ext == "json":
                            ext = "json"

                        if ext not in files_by_type:
                            files_by_type[ext] = {"count": 0, "total_size": "0 B", "files": []}

                        files_by_type[ext]["count"] += 1
                        files_by_type[ext]["files"].append(
                            {"name": file_path.name, "size": self._format_size(size)}
                        )

                # Update totals for each type
                for ext, info in files_by_type.items():
                    type_size = sum(
                        file_path.stat().st_size
                        for file_path in run_dir.rglob("*")
                        if file_path.is_file() and self._get_file_type(file_path) == ext
                    )
                    info["total_size"] = self._format_size(type_size)
                    # Sort files by size (largest first)
                    info["files"].sort(key=lambda x: self._parse_size(x["size"]), reverse=True)

                result["files"] = files_by_type
                result["total_files"] = total_files
                result["total_size"] = self._format_size(total_size)

        return result

    def _get_file_type(self, file_path) -> str:
        """Get file type category from path."""
        ext = file_path.suffix.lower().lstrip(".") or "other"
        if ext == "mp4":
            return "video"
        elif ext in ["jpg", "jpeg", "png", "gif"]:
            return "image"
        elif ext == "json":
            return "json"
        return ext

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _parse_size(self, size_str: str) -> float:
        """Parse size string back to bytes for sorting."""
        parts = size_str.split()
        if len(parts) != 2:
            return 0
        value, unit = parts
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        return float(value) * units.get(unit, 1)

    def delete_prompt(self, prompt_id: str, keep_outputs: bool = True) -> dict[str, Any]:
        """Delete a prompt and all associated runs.

        Args:
            prompt_id: The prompt ID to delete
            keep_outputs: Whether to keep output files (default: True)

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

        # Check for running or uploading runs and log warning
        active_runs = [
            run for run in prompt_data.get("runs", []) if run["status"] in ("running", "uploading")
        ]
        if active_runs:
            logger.warning(
                "Deleting prompt %s with %d active runs (running/uploading). Proceeding anyway.",
                prompt_id,
                len(active_runs),
            )

        # Collect information about what will be deleted
        deleted_info = {
            "prompt_id": prompt_id,
            "run_ids": [run["id"] for run in prompt_data.get("runs", [])],
            "directories": [],
        }

        # Delete output directories if requested
        if not keep_outputs:
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

    def delete_run(self, run_id: str, keep_outputs: bool = True) -> dict[str, Any]:
        """Delete a run and its output directory.

        Args:
            run_id: The run ID to delete
            keep_outputs: Whether to keep output files (default: True)

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

        # Warn about running or uploading status but proceed
        if run_data["status"] in ("running", "uploading"):
            logger.warning(
                "Deleting run %s with active status '%s'. Proceeding anyway.",
                run_id,
                run_data["status"],
            )

        # Collect information about what will be deleted
        deleted_info = {
            "run_id": run_id,
            "directory": None,
        }
        warnings = []

        # Delete output directory if requested
        if not keep_outputs:
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

    def preview_all_runs_deletion(self) -> dict[str, Any]:
        """Preview deletion of all runs.

        Returns:
            Dictionary with all runs and summary information
        """
        logger.debug("Previewing deletion of all runs")

        runs = self.list_runs(limit=1000)  # Get all runs

        if not runs:
            return {
                "runs": [],
                "total_count": 0,
                "error": "No runs found",
            }

        # Calculate total output size and count active runs
        outputs_dir = self.config.get_local_config().outputs_dir
        total_size = 0
        directories = []
        active_runs = [r for r in runs if r.get("status") in ("running", "uploading")]

        for run in runs:
            run_dir = outputs_dir / f"run_{run['id']}"
            if run_dir.exists():
                directories.append(str(run_dir))
                for file_path in run_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size

        return {
            "runs": runs,
            "total_count": len(runs),
            "total_active_runs": len(active_runs),
            "total_size": self._format_size(total_size),
            "directories_to_delete": directories,
        }

    def delete_all_runs(self, keep_outputs: bool = True) -> dict[str, Any]:
        """Delete all runs.

        Args:
            keep_outputs: Whether to keep output files (default: True)

        Returns:
            Dictionary with deletion results
        """
        logger.info("Deleting all runs, keep_outputs=%s", keep_outputs)

        runs = self.list_runs(limit=1000)

        if not runs:
            return {
                "success": True,
                "deleted": {
                    "run_ids": [],
                    "directories": [],
                },
            }

        # Check for active runs and warn
        active_runs = [r for r in runs if r["status"] in ("running", "uploading")]
        if active_runs:
            logger.warning(
                "Deleting %d active runs (running/uploading). Proceeding anyway.", len(active_runs)
            )

        deleted_info = {
            "run_ids": [],
            "directories": [],
        }

        # Delete each run
        for run in runs:
            result = self.delete_run(run["id"], keep_outputs)
            if result["success"]:
                deleted_info["run_ids"].append(run["id"])
                if result["deleted"].get("directory"):
                    deleted_info["directories"].append(result["deleted"]["directory"])

        return {
            "success": True,
            "deleted": deleted_info,
        }

    def preview_all_prompts_deletion(self) -> dict[str, Any]:
        """Preview deletion of all prompts.

        Returns:
            Dictionary with all prompts and summary information
        """
        logger.debug("Previewing deletion of all prompts")

        prompts = self.list_prompts(limit=1000)

        if not prompts:
            return {
                "prompts": [],
                "total_prompt_count": 0,
                "total_run_count": 0,
                "error": "No prompts found",
            }

        # Count total runs, active runs, and calculate size
        total_runs = 0
        total_active_runs = 0
        total_size = 0
        outputs_dir = self.config.get_local_config().outputs_dir

        for prompt in prompts:
            runs = self.list_runs(prompt_id=prompt["id"])
            total_runs += len(runs)

            # Count active runs
            active_runs = [r for r in runs if r.get("status") in ("running", "uploading")]
            total_active_runs += len(active_runs)

            for run in runs:
                run_dir = outputs_dir / f"run_{run['id']}"
                if run_dir.exists():
                    for file_path in run_dir.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size

        return {
            "prompts": prompts,
            "total_prompt_count": len(prompts),
            "total_run_count": total_runs,
            "total_active_runs": total_active_runs,
            "total_size": self._format_size(total_size),
        }

    def delete_all_prompts(self, keep_outputs: bool = True) -> dict[str, Any]:
        """Delete all prompts and their runs.

        Args:
            keep_outputs: Whether to keep output files (default: True)

        Returns:
            Dictionary with deletion results
        """
        logger.info("Deleting all prompts, keep_outputs=%s", keep_outputs)

        prompts = self.list_prompts(limit=1000)

        if not prompts:
            return {
                "success": True,
                "deleted": {
                    "prompt_ids": [],
                    "run_ids": [],
                    "directories": [],
                },
            }

        # Check for active runs across all prompts and warn
        total_active = 0
        for prompt in prompts:
            runs = self.list_runs(prompt_id=prompt["id"])
            active_runs = [r for r in runs if r["status"] in ("running", "uploading")]
            if active_runs:
                total_active += len(active_runs)
                logger.warning(
                    "Prompt %s has %d active runs. Will delete anyway.",
                    prompt["id"],
                    len(active_runs),
                )

        if total_active > 0:
            logger.warning(
                "Deleting prompts with %d total active runs. Proceeding anyway.", total_active
            )

        deleted_info = {
            "prompt_ids": [],
            "run_ids": [],
            "directories": [],
        }

        # Delete each prompt
        for prompt in prompts:
            result = self.delete_prompt(prompt["id"], keep_outputs)
            if result["success"]:
                deleted_info["prompt_ids"].append(prompt["id"])
                deleted_info["run_ids"].extend(result["deleted"]["run_ids"])
                deleted_info["directories"].extend(result["deleted"]["directories"])

        return {
            "success": True,
            "deleted": deleted_info,
        }
