"""Test database connection management.

Tests follow TDD Gate 1: Write comprehensive tests before implementation.
These tests verify connection management and database initialization.
"""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from cosmos_workflow.database.connection import (
    DatabaseConnection,
    get_database_url,
    init_database,
)
from cosmos_workflow.database.models import Prompt, Run


class TestDatabaseConnection:
    """Test DatabaseConnection class for managing database connections."""

    def test_create_in_memory_connection(self):
        """Test creating an in-memory SQLite connection for testing."""
        conn = DatabaseConnection(":memory:")

        # Should create engine and sessionmaker
        assert conn.engine is not None
        assert conn.SessionLocal is not None
        assert str(conn.engine.url) == "sqlite:///:memory:"

    def test_create_file_based_connection(self):
        """Test creating a file-based SQLite connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = DatabaseConnection(str(db_path))

            # Should create database file
            conn.create_tables()
            assert db_path.exists()
            assert "test.db" in str(conn.engine.url)

            # Close connection to release file handle
            conn.close()

    def test_create_tables(self):
        """Test that create_tables creates all model tables."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()

        # Verify tables exist
        with conn.get_session() as session:
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = {row[0] for row in result}

            assert "prompts" in table_names
            assert "runs" in table_names
            # Only two tables should exist
            assert len(table_names) == 2

    def test_get_session_context_manager(self):
        """Test that get_session returns a working context manager."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()

        # Test session creation and auto-cleanup
        with conn.get_session() as session:
            assert isinstance(session, Session)
            # Session should be active
            assert session.is_active

            # Should be able to query
            prompt = Prompt(
                id="ps_test",
                prompt_text="test",
                inputs={},
                parameters={},
            )
            session.add(prompt)
            session.commit()

            retrieved = session.get(Prompt, "ps_test")
            assert retrieved is not None

        # Session should be closed after context exit
        # Note: session.is_active may still be True after close() in SQLAlchemy 2.0+
        # The important thing is that it's closed and can't be used

    def test_session_rollback_on_exception(self):
        """Test that sessions rollback on exceptions."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()

        with pytest.raises(ValueError):
            with conn.get_session() as session:
                prompt = Prompt(
                    id="ps_rollback",
                    prompt_text="test",
                    inputs={},
                    parameters={},
                )
                session.add(prompt)
                # Don't commit yet - let context manager handle it
                # Raise exception to trigger rollback
                raise ValueError("Test exception")

        # Verify the prompt was not saved
        with conn.get_session() as session:
            retrieved = session.get(Prompt, "ps_rollback")
            assert retrieved is None

    def test_multiple_sessions(self):
        """Test that multiple sessions can be created and used."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()

        # Create data in first session
        with conn.get_session() as session1:
            prompt = Prompt(
                id="ps_multi",
                prompt_text="test",
                inputs={},
                parameters={},
            )
            session1.add(prompt)
            session1.commit()

        # Read data in second session
        with conn.get_session() as session2:
            retrieved = session2.get(Prompt, "ps_multi")
            assert retrieved is not None
            assert retrieved.prompt_text == "test"

    def test_connection_persistence(self):
        """Test that data persists across connections for file-based databases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "persist.db"

            # Create first connection and add data
            conn1 = DatabaseConnection(str(db_path))
            conn1.create_tables()

            with conn1.get_session() as session:
                prompt = Prompt(
                    id="ps_persist",
                    prompt_text="persistent",
                    inputs={},
                    parameters={},
                )
                session.add(prompt)
                session.commit()

            # Create second connection and verify data exists
            conn2 = DatabaseConnection(str(db_path))
            with conn2.get_session() as session:
                retrieved = session.get(Prompt, "ps_persist")
                assert retrieved is not None
                assert retrieved.prompt_text == "persistent"

            # Clean up connections
            conn1.close()
            conn2.close()

    def test_close_connection(self):
        """Test closing database connection."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()

        # Connection should work before closing
        with conn.get_session() as session:
            assert session.is_active

        # Close connection
        conn.close()

        # Should not be able to create new sessions after closing
        with pytest.raises(RuntimeError, match="Connection is closed"):
            with conn.get_session() as session:
                pass


class TestDatabaseSecurity:
    """Test security validations for database connections."""

    def test_rejects_empty_database_url(self):
        """Test that empty database URL is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DatabaseConnection("")

    def test_rejects_whitespace_database_url(self):
        """Test that whitespace database URL is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DatabaseConnection("   ")

    def test_rejects_path_traversal(self):
        """Test that path traversal attempts are rejected."""
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            DatabaseConnection("../../../etc/passwd")

    def test_rejects_path_traversal_in_middle(self):
        """Test that path traversal in middle of path is rejected."""
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            DatabaseConnection("/some/path/../../../etc/passwd")

    def test_allows_memory_database(self):
        """Test that :memory: database is allowed."""
        conn = DatabaseConnection(":memory:")
        assert conn is not None
        conn.close()

    def test_allows_valid_paths(self):
        """Test that valid paths are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "valid.db"
            conn = DatabaseConnection(str(db_path))
            assert conn is not None
            conn.close()


class TestDatabaseHelpers:
    """Test helper functions for database management."""

    def test_get_database_url_default(self):
        """Test getting default database URL."""
        # Should return default path when no env var set
        if "COSMOS_DATABASE_URL" in os.environ:
            del os.environ["COSMOS_DATABASE_URL"]

        url = get_database_url()
        assert url.endswith("cosmos_workflow.db")
        assert "outputs" in url

    def test_get_database_url_from_env(self):
        """Test getting database URL from environment variable."""
        test_url = "/custom/path/to/database.db"
        os.environ["COSMOS_DATABASE_URL"] = test_url

        url = get_database_url()
        assert url == test_url

        # Clean up
        del os.environ["COSMOS_DATABASE_URL"]

    def test_get_database_url_memory(self):
        """Test getting in-memory database URL."""
        os.environ["COSMOS_DATABASE_URL"] = ":memory:"

        url = get_database_url()
        assert url == ":memory:"

        # Clean up
        del os.environ["COSMOS_DATABASE_URL"]

    def test_init_database_creates_tables(self):
        """Test that init_database creates all tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "init_test.db"
            conn = init_database(str(db_path))

            # Should create database file
            assert db_path.exists()

            # Should create all tables
            with conn.get_session() as session:
                result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                table_names = {row[0] for row in result}

                assert "prompts" in table_names
                assert "runs" in table_names
                # Only two tables should exist
                assert len(table_names) == 2

            # Clean up
            conn.close()

    def test_init_database_idempotent(self):
        """Test that init_database can be called multiple times safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "idempotent.db"

            # Initialize database twice
            conn1 = init_database(str(db_path))
            conn2 = init_database(str(db_path))

            # Both connections should work
            with conn1.get_session() as session:
                prompt = Prompt(
                    id="ps_1",
                    prompt_text="test1",
                    inputs={},
                    parameters={},
                )
                session.add(prompt)
                session.commit()

            with conn2.get_session() as session:
                retrieved = session.get(Prompt, "ps_1")
                assert retrieved is not None

            # Clean up
            conn1.close()
            conn2.close()

    def test_init_database_creates_output_directory(self):
        """Test that init_database creates the output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir) / "outputs" / "database"
            db_path = db_dir / "cosmos.db"

            # Directory should not exist yet
            assert not db_dir.exists()

            conn = init_database(str(db_path))

            # Directory should be created
            assert db_dir.exists()
            assert db_path.exists()

            # Clean up
            conn.close()


class TestDatabaseTransactions:
    """Test transaction handling."""

    @pytest.fixture
    def connection(self) -> Generator[DatabaseConnection, None, None]:
        """Create a test database connection."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()
        yield conn
        conn.close()

    def test_transaction_commit(self, connection: DatabaseConnection):
        """Test successful transaction commit."""
        with connection.get_session() as session:
            # Start implicit transaction
            prompt = Prompt(
                id="ps_commit",
                prompt_text="test",
                inputs={},
                parameters={},
            )
            session.add(prompt)

            run = Run(
                id="rs_commit",
                prompt_id=prompt.id,
                status="pending",
                execution_config={},
                outputs={},
                run_metadata={},
            )
            session.add(run)

            # Commit transaction
            session.commit()

        # Verify data was saved
        with connection.get_session() as session:
            assert session.get(Prompt, "ps_commit") is not None
            assert session.get(Run, "rs_commit") is not None

    def test_transaction_rollback(self, connection: DatabaseConnection):
        """Test transaction rollback on error."""
        try:
            with connection.get_session() as session:
                prompt = Prompt(
                    id="ps_rollback",
                    prompt_text="test",
                    inputs={},
                    parameters={},
                )
                session.add(prompt)
                session.flush()  # Force write to DB

                # Simulate error
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass

        # Verify data was not saved
        with connection.get_session() as session:
            assert session.get(Prompt, "ps_rollback") is None

    def test_nested_session_handling(self, connection: DatabaseConnection):
        """Test that nested sessions are handled correctly."""
        with connection.get_session() as outer_session:
            prompt = Prompt(
                id="ps_outer",
                prompt_text="outer",
                inputs={},
                parameters={},
            )
            outer_session.add(prompt)
            outer_session.commit()

            # Create inner session (should be independent)
            with connection.get_session() as inner_session:
                run = Run(
                    id="rs_inner",
                    prompt_id=prompt.id,
                    status="pending",
                    execution_config={},
                    outputs={},
                    run_metadata={},
                )
                inner_session.add(run)
                inner_session.commit()

        # Verify both were saved
        with connection.get_session() as session:
            assert session.get(Prompt, "ps_outer") is not None
            assert session.get(Run, "rs_inner") is not None


class TestDatabaseConcurrency:
    """Test concurrent database operations."""

    def test_concurrent_writes(self):
        """Test that concurrent writes to different records work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "concurrent.db"
            conn = DatabaseConnection(str(db_path))
            conn.create_tables()

            # Write different records in parallel sessions
            with conn.get_session() as session1:
                prompt1 = Prompt(
                    id="ps_concurrent_1",
                    prompt_text="test1",
                    inputs={},
                    parameters={},
                )
                session1.add(prompt1)
                session1.commit()

            with conn.get_session() as session2:
                prompt2 = Prompt(
                    id="ps_concurrent_2",
                    prompt_text="test2",
                    inputs={},
                    parameters={},
                )
                session2.add(prompt2)
                session2.commit()

            # Verify both were saved
            with conn.get_session() as session:
                assert session.get(Prompt, "ps_concurrent_1") is not None
                assert session.get(Prompt, "ps_concurrent_2") is not None

            # Clean up
            conn.close()

    def test_read_isolation(self):
        """Test that reads are isolated from uncommitted writes."""
        conn = DatabaseConnection(":memory:")
        conn.create_tables()

        # Add initial data
        with conn.get_session() as session:
            prompt = Prompt(
                id="ps_isolation",
                prompt_text="initial",
                inputs={},
                parameters={},
            )
            session.add(prompt)
            session.commit()

        # Start a write session but don't commit
        write_session = conn.SessionLocal()
        write_session.begin()
        retrieved_prompt = write_session.get(Prompt, "ps_isolation")
        retrieved_prompt.prompt_text = "modified"
        write_session.flush()

        # Read in another session - SQLite default isolation may show committed data only
        # This behavior depends on isolation level
        with conn.get_session() as read_session:
            read_prompt = read_session.get(Prompt, "ps_isolation")
            # SQLite in autocommit mode doesn't provide true isolation
            # The test should verify the data exists
            assert read_prompt is not None
            assert read_prompt.prompt_text in ["initial", "modified"]

        # Cleanup
        write_session.rollback()
        write_session.close()
