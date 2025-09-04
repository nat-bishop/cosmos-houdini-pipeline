# Database System Documentation

The Cosmos Workflow System uses a flexible database architecture built on SQLAlchemy that supports multiple AI models through extensible JSON schemas. This foundation enables seamless integration of current and future AI models including transfer, reason, and predict capabilities.

## Overview

The database system is designed with flexibility and extensibility as core principles:

- **Multi-Model Support**: Single schema supports different AI models (transfer, reason, predict, future models)
- **Flexible JSON Storage**: Model-specific data stored in JSON columns for easy extensibility
- **Security First**: Path traversal protection, input validation, and transaction safety
- **Real-Time Tracking**: Granular progress monitoring through all execution stages
- **Production Ready**: Comprehensive test coverage with TDD-driven development

## Architecture

### Core Components

```
cosmos_workflow/database/
├── __init__.py          # Module exports
├── connection.py        # Database connection management
└── models.py           # SQLAlchemy model definitions
```

### Database Models

The system uses three core models that work together to track AI workflow execution:

#### 1. Prompt Model
Stores AI prompts with flexible schema supporting any model type.

**Key Features:**
- Supports multiple AI models through `model_type` field
- JSON `inputs` column for model-specific input data (videos, images, frames, etc.)
- JSON `parameters` column for model-specific parameters (steps, temperature, etc.)
- Built-in validation for required fields and JSON integrity

**Schema:**
```python
class Prompt(Base):
    id = Column(String, primary_key=True)
    model_type = Column(String, nullable=False)  # transfer, reason, predict, etc.
    prompt_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True))
    inputs = Column(JSON, nullable=False)       # Flexible input data
    parameters = Column(JSON, nullable=False)   # Flexible parameters
```

#### 2. Run Model
Tracks execution attempts of prompts with lifecycle management.

**Key Features:**
- Links to parent prompt via foreign key relationship
- Status tracking through execution lifecycle (pending → uploading → running → downloading → completed/failed)
- JSON `execution_config` for runtime configuration (GPU nodes, Docker images, etc.)
- JSON `outputs` for flexible result storage (file paths, metrics, logs)
- Automatic timestamp management for created/updated/started/completed times

**Schema:**
```python
class Run(Base):
    id = Column(String, primary_key=True)
    prompt_id = Column(String, ForeignKey("prompts.id"), nullable=False)
    model_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    # Timestamps
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Flexible JSON storage
    execution_config = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=False)
    run_metadata = Column("metadata", JSON, nullable=False)
```

#### 3. Progress Model
Provides real-time progress tracking for dashboard visualization.

**Key Features:**
- Granular progress tracking through different execution stages
- Percentage-based progress (0.0-100.0) with built-in validation
- Human-readable status messages for user feedback
- Chronological ordering for progress timeline visualization

**Schema:**
```python
class Progress(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True))
    stage = Column(String, nullable=False)      # uploading, inference, downloading
    percentage = Column(Float, nullable=False)   # 0.0 to 100.0
    message = Column(Text, nullable=False)      # Human-readable status
```

### Relationships

The models are connected through foreign key relationships with cascading operations:

- `Prompt` → `Run` (one-to-many): One prompt can have multiple execution attempts
- `Run` → `Progress` (one-to-many): One run can have multiple progress updates
- Cascade deletes ensure data integrity when removing parent records

## AI Model Support

### Current Model Support

#### Transfer Model (Cosmos Transfer)
```python
# Example Prompt for transfer model
prompt = Prompt(
    id="ps_20250104_120000_abc123",
    model_type="transfer",
    prompt_text="cyberpunk city at night",
    inputs={
        "video": "/inputs/videos/city.mp4",
        "depth": "/inputs/depth/city_depth.mp4"
    },
    parameters={
        "num_steps": 35,
        "cfg_scale": 7.5
    }
)
```

### Future Model Support

#### Reason Model (Cosmos Reason)
```python
# Example Prompt for future reason model
prompt = Prompt(
    id="ps_20250104_130000_def456",
    model_type="reason",
    prompt_text="What happens next in this scene?",
    inputs={
        "video": "/outputs/result.mp4",
        "context": "urban environment"
    },
    parameters={
        "reasoning_depth": 3,
        "temperature": 0.7
    }
)
```

#### Predict Model (Cosmos Predict)
```python
# Example Prompt for future predict model
prompt = Prompt(
    id="ps_20250104_140000_ghi789",
    model_type="predict",
    prompt_text="Continue this animation",
    inputs={
        "frames": ["frame1.png", "frame2.png", "frame3.png"],
        "motion_vectors": "/inputs/motion.json"
    },
    parameters={
        "prediction_length": 60,
        "fps": 30
    }
)
```

### Extensibility

The JSON column design allows for unlimited extensibility:

```python
# Complex nested data structures supported
complex_inputs = {
    "videos": ["/v1.mp4", "/v2.mp4"],
    "metadata": {"resolution": "1920x1080", "codec": "h264"},
    "nested": {"level1": {"level2": {"data": "value"}}}
}

complex_params = {
    "model_config": {"layers": 12, "attention_heads": 8},
    "sampling": {"method": "ddpm", "steps": 50},
    "array_param": [1, 2, 3, 4, 5]
}
```

## Connection Management

### DatabaseConnection Class

The `DatabaseConnection` class provides secure connection management with automatic session handling:

```python
from cosmos_workflow.database.connection import DatabaseConnection

# Create connection
conn = DatabaseConnection("outputs/cosmos_workflow.db")
conn.create_tables()

# Use context manager for automatic cleanup
with conn.get_session() as session:
    prompt = Prompt(
        id="example_id",
        model_type="transfer",
        prompt_text="example prompt",
        inputs={},
        parameters={}
    )
    session.add(prompt)
    session.commit()
```

### Key Features

- **Automatic Session Management**: Context managers handle commit/rollback automatically
- **Connection Pooling**: Efficient connection reuse for high-performance operations
- **Transaction Safety**: Automatic rollback on exceptions prevents data corruption
- **Path Security**: Built-in path traversal protection for database URLs

### Environment Configuration

Database location can be configured via environment variable:

```bash
# Custom database location
export COSMOS_DATABASE_URL="/custom/path/cosmos.db"

# In-memory database for testing
export COSMOS_DATABASE_URL=":memory:"
```

Default location: `outputs/cosmos_workflow.db`

## Security Features

### Path Traversal Protection

The database system includes comprehensive security validation:

```python
# These are REJECTED with ValueError
DatabaseConnection("../../../etc/passwd")          # Path traversal
DatabaseConnection("/some/path/../../../etc")      # Path traversal in middle
DatabaseConnection("")                             # Empty path
DatabaseConnection("   ")                          # Whitespace only

# These are ALLOWED
DatabaseConnection(":memory:")                      # In-memory database
DatabaseConnection("/valid/path/database.db")      # Valid absolute path
```

### Input Validation

All models include comprehensive validation:

- **Required Fields**: Model type, prompt text, and JSON fields cannot be None or empty
- **JSON Validation**: All JSON fields are validated to ensure they are not None
- **Percentage Validation**: Progress percentages must be between 0.0 and 100.0
- **Foreign Key Integrity**: Relationships are enforced with proper constraints

### Transaction Safety

- Automatic rollback on exceptions prevents partial data corruption
- Session isolation ensures concurrent operations don't interfere
- Proper connection cleanup prevents resource leaks

## Usage Patterns

### Basic Workflow Execution

```python
from cosmos_workflow.database import init_database
from cosmos_workflow.database.models import Prompt, Run, Progress

# Initialize database
conn = init_database()

with conn.get_session() as session:
    # Create prompt
    prompt = Prompt(
        id="workflow_example",
        model_type="transfer",
        prompt_text="futuristic landscape",
        inputs={"video": "/inputs/landscape.mp4"},
        parameters={"num_steps": 50}
    )
    session.add(prompt)

    # Create run
    run = Run(
        id="run_example",
        prompt_id=prompt.id,
        model_type="transfer",
        status="pending",
        execution_config={"gpu_node": "gpu-002"},
        outputs={},
        run_metadata={"session": "example"}
    )
    session.add(run)

    # Add progress tracking
    progress = Progress(
        run_id=run.id,
        stage="uploading",
        percentage=0.0,
        message="Starting upload"
    )
    session.add(progress)

    session.commit()
```

### Status Tracking

```python
# Update run status through lifecycle
with conn.get_session() as session:
    run = session.get(Run, "run_example")

    # Update to running
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)

    # Add progress update
    progress = Progress(
        run_id=run.id,
        stage="inference",
        percentage=50.0,
        message="Processing frame 60/120"
    )
    session.add(progress)
    session.commit()
```

### Querying and Filtering

```python
from sqlalchemy import select

with conn.get_session() as session:
    # Get all transfer model prompts
    transfer_prompts = session.scalars(
        select(Prompt).where(Prompt.model_type == "transfer")
    ).all()

    # Get completed runs
    completed_runs = session.scalars(
        select(Run).where(Run.status == "completed")
    ).all()

    # Get recent progress for a run
    recent_progress = session.scalars(
        select(Progress)
        .where(Progress.run_id == "run_example")
        .order_by(Progress.timestamp.desc())
        .limit(10)
    ).all()
```

## Testing

The database system includes comprehensive test coverage following TDD principles:

### Test Categories

- **Model Tests**: Validation, relationships, JSON flexibility
- **Connection Tests**: Session management, transactions, concurrency
- **Security Tests**: Path traversal protection, input validation
- **Integration Tests**: Full workflow lifecycle testing

### Running Tests

```bash
# Run all database tests
pytest tests/unit/database/ -v

# Run with coverage
pytest tests/unit/database/ --cov=cosmos_workflow.database --cov-report=html
```

### Test Database

Tests use in-memory SQLite databases for fast, isolated execution:

```python
@pytest.fixture
def session():
    """Create in-memory database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

## Performance Considerations

### Indexing Strategy

Consider adding indexes for frequently queried columns:

```sql
-- Example indexes for production use
CREATE INDEX idx_prompts_model_type ON prompts(model_type);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_prompt_id ON runs(prompt_id);
CREATE INDEX idx_progress_run_id ON progress(run_id);
CREATE INDEX idx_progress_timestamp ON progress(timestamp);
```

### JSON Column Performance

- SQLite JSON functions enable efficient querying of JSON columns
- Consider extracting frequently queried JSON fields to dedicated columns for better performance
- Use JSON_EXTRACT for complex queries on JSON data

### Connection Pooling

For high-throughput applications:

```python
# Configure connection pool settings
engine = create_engine(
    "sqlite:///cosmos_workflow.db",
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600
)
```

## Migration Considerations

### Schema Evolution

The flexible JSON design minimizes schema migrations:

- New AI models can be added without schema changes
- New input/parameter types stored in existing JSON columns
- Database migrations only needed for core schema changes

### Future Enhancements

Potential future improvements:

- **Partitioning**: Table partitioning for large datasets by model_type or date
- **Archiving**: Automated archiving of old runs and progress data
- **Monitoring**: Database performance monitoring and query optimization
- **Replication**: Read replica support for high-availability deployments

## Best Practices

### Development

- Always use the DatabaseConnection context manager for session management
- Validate input data before database operations
- Use proper exception handling around database operations
- Write tests for all database interactions

### Production

- Pin specific database versions for reproducibility
- Monitor database performance and query patterns
- Implement backup and recovery procedures
- Use environment variables for database configuration
- Consider connection pooling for high-throughput scenarios

### Security

- Never expose database URLs in logs or error messages
- Use environment variables for sensitive configuration
- Validate all user inputs before database storage
- Implement proper access controls and authentication

## Troubleshooting

### Common Issues

**Connection Errors:**
```python
# Check database file permissions
# Verify parent directories exist
# Confirm no path traversal in database URL
```

**Validation Errors:**
```python
# Ensure required fields are not None or empty
# Verify JSON fields contain valid data
# Check percentage values are in 0.0-100.0 range
```

**Performance Issues:**
```python
# Add appropriate indexes for query patterns
# Consider connection pooling for concurrent access
# Monitor JSON column query performance
```

### Debugging

Enable SQLAlchemy logging for detailed database operations:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## API Reference

### Main Functions

```python
from cosmos_workflow.database import init_database, get_database_url
from cosmos_workflow.database.connection import DatabaseConnection
from cosmos_workflow.database.models import Prompt, Run, Progress

# Initialize database with tables
conn = init_database(database_url=None)

# Get configured database URL
url = get_database_url()

# Create connection manually
conn = DatabaseConnection(database_url)
```

### Model Methods

Each model includes validation methods and proper `__repr__` implementations for debugging.

See the source code for complete API details and method signatures.