"""Database models for cosmos workflow.

Flexible schema supporting multiple AI models (transfer, reason, predict).
Uses JSON columns for model-specific data to enable easy extensibility.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, validates

Base = declarative_base()


class Prompt(Base):
    """Prompt model with flexible schema for multiple AI models.

    Supports transfer, reason, predict and future model types through
    flexible JSON columns for inputs, parameters, and configurations.
    """

    __tablename__ = "prompts"

    # Core fields common to all AI models
    id = Column(String, primary_key=True)
    model_type = Column(String, nullable=False)  # transfer, reason, predict, etc.
    prompt_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Flexible JSON fields for model-specific data
    inputs = Column(JSON, nullable=False)  # Video paths, images, frames, etc.
    parameters = Column(JSON, nullable=False)  # num_steps, cfg_scale, temperature, etc.

    # Relationships
    runs = relationship("Run", back_populates="prompt", cascade="all, delete-orphan")

    @validates("inputs", "parameters")
    def validate_json_fields(self, key, value):
        """Validate that JSON fields are not None.

        Args:
            key: Name of the field being validated.
            value: Value being assigned to the field.

        Returns:
            The validated value if it passes validation.

        Raises:
            ValueError: If the value is None.
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")
        return value

    @validates("model_type", "prompt_text")
    def validate_required_fields(self, key, value):
        """Validate that required string fields are not empty.

        Args:
            key: Name of the field being validated.
            value: Value being assigned to the field.

        Returns:
            The validated value if it passes validation.

        Raises:
            ValueError: If the value is None or empty string.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{key} cannot be None or empty")
        return value

    def __repr__(self):
        return f"<Prompt(id={self.id}, model={self.model_type}, text={self.prompt_text[:50]}...)>"


class Run(Base):
    """Run model for tracking executions of prompts.

    Each run represents one execution attempt of a prompt, with flexible
    JSON columns to store execution configurations and outputs.
    """

    __tablename__ = "runs"

    # Core fields
    id = Column(String, primary_key=True)
    prompt_id = Column(String, ForeignKey("prompts.id"), nullable=False)
    model_type = Column(String, nullable=False)
    status = Column(
        String, nullable=False
    )  # pending, uploading, running, downloading, completed, failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Flexible JSON fields
    execution_config = Column(JSON, nullable=False)  # GPU node, docker image, weights, etc.
    outputs = Column(JSON, nullable=False)  # Result paths, metrics, logs, etc.
    run_metadata = Column("metadata", JSON, nullable=False)  # User info, priority, session, etc.

    # Relationships
    prompt = relationship("Prompt", back_populates="runs")

    @validates("execution_config", "outputs", "run_metadata")
    def validate_json_fields(self, key, value):
        """Validate that JSON fields are not None.

        Args:
            key: Name of the field being validated.
            value: Value being assigned to the field.

        Returns:
            The validated value if it passes validation.

        Raises:
            ValueError: If the value is None.
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")
        return value

    @validates("status")
    def validate_status(self, key, value):
        """Validate that status is not empty.

        Args:
            key: Name of the field being validated.
            value: Value being assigned to the field.

        Returns:
            The validated value if it passes validation.

        Raises:
            ValueError: If the value is None or empty string.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{key} cannot be None or empty")
        return value

    def __repr__(self):
        return f"<Run(id={self.id}, prompt={self.prompt_id}, status={self.status})>"
