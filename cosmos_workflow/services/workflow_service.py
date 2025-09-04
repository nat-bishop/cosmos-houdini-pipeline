"""Workflow service for managing prompts and runs.

Provides business logic for creating, retrieving and managing AI model
prompts and their execution runs. Supports multiple model types through
flexible database schema.
"""

import hashlib
import logging
import uuid
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.database.models import Prompt, Run

logger = logging.getLogger(__name__)

# Supported AI model types
SUPPORTED_MODEL_TYPES = {"transfer", "reason", "predict"}
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
        prompt_id = self._generate_prompt_id(model_type, prompt_text, inputs)

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

    def _generate_prompt_id(self, model_type: str, prompt_text: str, inputs: dict[str, Any]) -> str:
        """Generate unique ID for a prompt.

        Args:
            model_type: Type of AI model
            prompt_text: The prompt text
            inputs: Input data

        Returns:
            Unique ID string starting with 'ps_'
        """
        # Create deterministic string representation
        content = f"{model_type}|{prompt_text}|{sorted(inputs.items())}"

        # Generate hash
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()[:20]  # Increased from 12 to reduce collision risk

        return f"ps_{hash_hex}"

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
