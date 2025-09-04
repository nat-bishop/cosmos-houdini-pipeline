"""Database connection management for cosmos workflow.

Provides connection management, session handling, and database initialization.
Supports both file-based and in-memory SQLite databases for testing.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from cosmos_workflow.database.models import Base


class DatabaseConnection:
    """Manages database connections and sessions.

    Provides context managers for session handling with automatic
    commit/rollback and connection pooling.
    """

    def __init__(self, database_url: str):
        """Initialize database connection.

        Args:
            database_url: Path to database file or ":memory:" for in-memory DB
        """
        # Validate database URL
        if not database_url or database_url.isspace():
            raise ValueError("Database URL cannot be empty or whitespace")

        # Security: prevent path traversal
        if database_url != ":memory:" and ".." in database_url:
            raise ValueError("Path traversal not allowed in database URL")

        self.database_url = database_url
        self.closed = False
        self._create_engine()

    def _create_engine(self):
        """Create SQLAlchemy engine with appropriate settings."""
        if self.database_url == ":memory:":
            # In-memory database for testing
            self.engine = create_engine(
                "sqlite:///:memory:", connect_args={"check_same_thread": False}, echo=False
            )
        else:
            # File-based database
            # Ensure directory exists
            db_path = Path(self.database_url)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self.engine = create_engine(
                f"sqlite:///{self.database_url}",
                connect_args={"check_same_thread": False},
                echo=False,
            )

        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.

        Yields:
            Session: Database session that auto-commits on success,
                    auto-rollbacks on exception

        Raises:
            RuntimeError: If connection is closed
        """
        if self.closed:
            raise RuntimeError("Connection is closed")

        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Close the database connection."""
        self.closed = True
        self.engine.dispose()


def get_database_url() -> str:
    """Get database URL from environment or use default.

    Returns:
        str: Database URL path or ":memory:" for in-memory database

    Raises:
        ValueError: If environment variable contains invalid path
    """
    # Check environment variable first
    if "COSMOS_DATABASE_URL" in os.environ:
        url = os.environ["COSMOS_DATABASE_URL"]

        # Validate the URL from environment
        if not url or url.isspace():
            raise ValueError("COSMOS_DATABASE_URL cannot be empty or whitespace")

        # Security: prevent path traversal
        if url != ":memory:" and ".." in url:
            raise ValueError("Path traversal not allowed in COSMOS_DATABASE_URL")

        return url

    # Default to file in outputs directory
    default_path = Path("outputs") / "cosmos_workflow.db"
    # Ensure the path doesn't contain traversal attempts
    default_str = str(default_path.absolute())
    if ".." in default_str:
        raise ValueError("Path traversal detected in default database path")
    return default_str


def init_database(database_url: str | None = None) -> DatabaseConnection:
    """Initialize database with all tables.

    Args:
        database_url: Optional database URL, uses get_database_url() if not provided

    Returns:
        DatabaseConnection: Initialized database connection
    """
    if database_url is None:
        database_url = get_database_url()

    conn = DatabaseConnection(database_url)
    conn.create_tables()
    return conn
