"""Database models for cosmos workflow.

Flexible schema supporting multiple AI models (transfer, reason, predict).
Uses JSON columns for model-specific data to enable easy extensibility.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
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
    progress = relationship("Progress", back_populates="run", cascade="all, delete-orphan")

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


class Progress(Base):
    """Progress model for real-time tracking of run execution.

    Records progress updates during different stages of execution
    (uploading, inference, downloading) for dashboard visualization.
    """

    __tablename__ = "progress"
    __table_args__ = (
        CheckConstraint("percentage >= 0.0 AND percentage <= 100.0", name="check_percentage_range"),
    )

    # Core fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Progress information
    stage = Column(String, nullable=False)  # uploading, inference, downloading
    percentage = Column(Float, nullable=False)  # 0.0 to 100.0
    message = Column(Text, nullable=False)  # Human-readable status message

    # Relationships
    run = relationship("Run", back_populates="progress")

    @validates("percentage")
    def validate_percentage(self, key, value):
        """Validate that percentage is between 0 and 100.

        Args:
            key: Name of the field being validated.
            value: Value being assigned to the field.

        Returns:
            The validated value if it passes validation.

        Raises:
            ValueError: If the value is None or outside the 0.0-100.0 range.
        """
        if value is None:
            raise ValueError("Percentage cannot be None")
        if not 0.0 <= value <= 100.0:
            raise ValueError(f"Percentage must be between 0 and 100, got {value}")
        return value

    @validates("stage", "message")
    def validate_required_strings(self, key, value):
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
        return f"<Progress(run={self.run_id}, stage={self.stage}, {self.percentage}%)>"
