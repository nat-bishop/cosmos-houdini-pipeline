"""Tests for Phase 2 database schema updates - log_path and error_message fields."""

import pytest
from sqlalchemy import String, Text, create_engine
from sqlalchemy.orm import sessionmaker

from cosmos_workflow.database.models import Base, Prompt, Run


class TestPhase2RunModelUpdates:
    """Test the new log_path and error_message fields in Run model."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory database session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def sample_prompt(self, db_session):
        """Create a sample prompt for testing."""
        prompt = Prompt(
            id="ps_test123",
            prompt_text="Test prompt",
            inputs={"video": "/path/to/video.mp4"},
            parameters={"num_steps": 10},
        )
        db_session.add(prompt)
        db_session.commit()
        return prompt

    def test_run_model_has_log_path_field(self):
        """Test that Run model has log_path field."""
        assert hasattr(Run, "log_path"), "Run model should have log_path field"

        # Check field type and properties
        log_path_column = Run.__table__.columns.get("log_path")
        assert log_path_column is not None, "log_path should be a column"
        assert isinstance(log_path_column.type, String), "log_path should be String type"
        assert log_path_column.nullable is True, "log_path should be nullable"

    def test_run_model_has_error_message_field(self):
        """Test that Run model has error_message field."""
        assert hasattr(Run, "error_message"), "Run model should have error_message field"

        # Check field type and properties
        error_msg_column = Run.__table__.columns.get("error_message")
        assert error_msg_column is not None, "error_message should be a column"
        assert isinstance(error_msg_column.type, Text), "error_message should be Text type"
        assert error_msg_column.nullable is True, "error_message should be nullable"

    def test_create_run_with_log_path(self, db_session, sample_prompt):
        """Test creating a run with log_path."""
        run = Run(
            id="rs_test456",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="completed",
            execution_config={"gpu": "A100"},
            outputs={"video": "/output/video.mp4"},
            run_metadata={},
            log_path="outputs/run_rs_test456/logs/rs_rs_test456.log",
        )

        db_session.add(run)
        db_session.commit()

        # Retrieve and verify
        retrieved_run = db_session.query(Run).filter_by(id="rs_test456").first()
        assert retrieved_run is not None
        assert retrieved_run.log_path == "outputs/run_rs_test456/logs/rs_rs_test456.log"

    def test_create_run_with_error_message(self, db_session, sample_prompt):
        """Test creating a run with error_message."""
        error_msg = "Docker container failed to start: insufficient GPU memory"
        run = Run(
            id="rs_test789",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="failed",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
            error_message=error_msg,
        )

        db_session.add(run)
        db_session.commit()

        # Retrieve and verify
        retrieved_run = db_session.query(Run).filter_by(id="rs_test789").first()
        assert retrieved_run is not None
        assert retrieved_run.error_message == error_msg

    def test_run_with_both_log_path_and_error_message(self, db_session, sample_prompt):
        """Test run can have both log_path and error_message."""
        run = Run(
            id="rs_test_both",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="failed",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
            log_path="outputs/run_rs_test_both/logs/rs_rs_test_both.log",
            error_message="Process terminated unexpectedly",
        )

        db_session.add(run)
        db_session.commit()

        # Retrieve and verify
        retrieved_run = db_session.query(Run).filter_by(id="rs_test_both").first()
        assert retrieved_run is not None
        assert retrieved_run.log_path == "outputs/run_rs_test_both/logs/rs_rs_test_both.log"
        assert retrieved_run.error_message == "Process terminated unexpectedly"

    def test_update_existing_run_with_log_path(self, db_session, sample_prompt):
        """Test updating an existing run with log_path."""
        # Create run without log_path
        run = Run(
            id="rs_update_log",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="running",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
        )
        db_session.add(run)
        db_session.commit()

        # Update with log_path
        run.log_path = "outputs/run_rs_update_log/logs/rs_rs_update_log.log"
        run.status = "completed"
        db_session.commit()

        # Retrieve and verify
        retrieved_run = db_session.query(Run).filter_by(id="rs_update_log").first()
        assert retrieved_run.log_path == "outputs/run_rs_update_log/logs/rs_rs_update_log.log"
        assert retrieved_run.status == "completed"

    def test_update_existing_run_with_error_message(self, db_session, sample_prompt):
        """Test updating an existing run with error_message."""
        # Create run without error_message
        run = Run(
            id="rs_update_error",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="running",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
        )
        db_session.add(run)
        db_session.commit()

        # Update with error_message
        run.error_message = "Out of memory error"
        run.status = "failed"
        db_session.commit()

        # Retrieve and verify
        retrieved_run = db_session.query(Run).filter_by(id="rs_update_error").first()
        assert retrieved_run.error_message == "Out of memory error"
        assert retrieved_run.status == "failed"

    def test_log_path_nullable(self, db_session, sample_prompt):
        """Test that log_path can be null."""
        run = Run(
            id="rs_null_log",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="pending",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
        )

        db_session.add(run)
        db_session.commit()

        retrieved_run = db_session.query(Run).filter_by(id="rs_null_log").first()
        assert retrieved_run.log_path is None

    def test_error_message_nullable(self, db_session, sample_prompt):
        """Test that error_message can be null."""
        run = Run(
            id="rs_null_error",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="completed",
            execution_config={"gpu": "A100"},
            outputs={"video": "/output/video.mp4"},
            run_metadata={},
        )

        db_session.add(run)
        db_session.commit()

        retrieved_run = db_session.query(Run).filter_by(id="rs_null_error").first()
        assert retrieved_run.error_message is None

    def test_long_error_message(self, db_session, sample_prompt):
        """Test storing a long error message."""
        # Create a very long error message
        long_error = "Error: " + "x" * 5000  # 5000+ character error message

        run = Run(
            id="rs_long_error",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="failed",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
            error_message=long_error,
        )

        db_session.add(run)
        db_session.commit()

        retrieved_run = db_session.query(Run).filter_by(id="rs_long_error").first()
        assert retrieved_run.error_message == long_error
        assert len(retrieved_run.error_message) > 5000

    def test_log_path_with_special_characters(self, db_session, sample_prompt):
        """Test log_path with special characters in path."""
        special_path = "outputs/run-2024_01_07@15:30:45/logs/run.log"

        run = Run(
            id="rs_special_path",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="completed",
            execution_config={"gpu": "A100"},
            outputs={},
            run_metadata={},
            log_path=special_path,
        )

        db_session.add(run)
        db_session.commit()

        retrieved_run = db_session.query(Run).filter_by(id="rs_special_path").first()
        assert retrieved_run.log_path == special_path
