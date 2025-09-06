# Database System Documentation

The Cosmos Workflow System uses a database-first architecture built on SQLAlchemy with no persistent JSON files. All data is stored in the database with flexible JSON columns supporting multiple AI models. This foundation enables seamless integration of current transfer and enhancement models, plus future AI models including reason and predict capabilities.

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

### Relationships

The models are connected through foreign key relationships with cascading operations:

- `Prompt` → `Run` (one-to-many): One prompt can have multiple execution attempts
- Cascade deletes ensure data integrity when removing parent records

## AI Model Support

### Current Model Support

#### Transfer Model (Cosmos Transfer)
Currently the primary model for video generation and transformation.

#### Enhancement Model (Prompt Enhancement)
Currently supported for AI-powered prompt improvement using Pixtral model.

```python
# Example enhancement model prompt
enhancement_prompt = Prompt(
    id="ps_enhanced123",
    model_type="enhancement",
    prompt_text="A simple city scene",
    inputs={
        "original_prompt_id": "ps_abc123",
        "resolution": 480
    },
    parameters={
        "ai_model": "pixtral",
        "enhancement_type": "detailed_description"
    }
)
```
```python
# Example Prompt for transfer model
prompt = Prompt(
    id="ps_a1b2c3d4",  # Generated with ps_ prefix
    model_type="transfer",
    prompt_text="cyberpunk city at night",
    inputs={
        "video": "/inputs/videos/city.mp4",
        "depth": "/inputs/videos/city_depth.mp4",
        "segmentation": "/inputs/videos/city_seg.mp4"
    },
    parameters={
        "num_steps": 35,
        "guidance_scale": 8.0,
        "negative_prompt": "blurry, low quality, distorted"
    }
)
```

### Future Model Support

The flexible JSON schema allows easy addition of future AI models without database schema changes.

#### Reason Model (Cosmos Reason)
```python
# Example Prompt for enhancement model (currently supported)
prompt = Prompt(
    id="ps_x9y8z7w6",
    model_type="enhancement",
    prompt_text="A simple city scene",
    inputs={
        "original_prompt_id": "ps_a1b2c3d4",
        "resolution": 480
    },
    parameters={
        "ai_model": "pixtral",
        "enhancement_type": "detailed_description"
    }
)

# Example Prompt for future reason model
prompt = Prompt(
    id="ps_def456gh",
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
    id="ps_ghi789jk",
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

Default location: `cosmos_workflow.db` in the working directory

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
- **Foreign Key Integrity**: Relationships are enforced with proper constraints

### Transaction Safety

- Automatic rollback on exceptions prevents partial data corruption
- Session isolation ensures concurrent operations don't interfere
- Proper connection cleanup prevents resource leaks

## Query Capabilities

### List Operations
The database system provides comprehensive list operations with filtering and pagination:

- **Prompt Listing**: Filter by model type, paginate with limit/offset
- **Run Listing**: Filter by status and/or prompt_id
- **Ordering**: All lists ordered by created_at descending (newest first)
- **Error Handling**: Graceful fallback to empty results on database errors

### Search Functionality
Full-text search capabilities for prompts:

- **Case-Insensitive**: Uses ILIKE operator for flexible matching
- **Prompt Text Search**: Searches within prompt_text field
- **Result Limiting**: Default 50 results, configurable
- **CLI Integration**: Search results show highlighted matches

### Relationship Queries
Efficient queries for related data:

- **Eager Loading**: get_prompt_with_runs() loads runs efficiently
- **Joined Data**: Returns complete prompt details with all associated runs
- **Status Tracking**: Includes run status, timestamps, and outputs

### Example Queries

```python
from cosmos_workflow.services.workflow_service import WorkflowService

# List transfer model prompts
prompts = service.list_prompts(model_type="transfer", limit=10)

# Search for cyberpunk-themed prompts
results = service.search_prompts("cyberpunk")

# Get all runs for a specific prompt
runs = service.list_runs(prompt_id="ps_abc123")

# Get prompt with all its runs
details = service.get_prompt_with_runs("ps_abc123")

# List failed runs
failed = service.list_runs(status="failed", limit=100)
```

## Usage Patterns

### Service Layer (Recommended)

The `WorkflowService` provides a high-level business logic layer for database operations with comprehensive validation and error handling:

```python
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.config import ConfigManager

# Initialize service
db_connection = DatabaseConnection("outputs/cosmos_workflow.db")
db_connection.create_tables()
config_manager = ConfigManager()
service = WorkflowService(db_connection, config_manager)

# Create prompts with validation
prompt_data = service.create_prompt(
    model_type="transfer",
    prompt_text="A cyberpunk cityscape at night",
    inputs={"video_path": "/inputs/city.mp4"},
    parameters={"num_steps": 35, "cfg_scale": 7.5}
)
# Returns dictionary optimized for CLI display

# Create runs with transaction safety
run_data = service.create_run(
    prompt_id=prompt_data["id"],
    execution_config={"gpu_node": "gpu-001"},
    metadata={"user": "NAT"},
    initial_status="pending"
)

# Retrieve entities safely
prompt = service.get_prompt(prompt_data["id"])
run = service.get_run(run_data["id"])
```

**Benefits of Service Layer:**
- Transaction safety with automatic rollback on errors
- Comprehensive input validation with descriptive error messages
- Dictionary returns optimized for CLI display (not raw ORM objects)
- Deterministic ID generation for consistent identification
- Support for configurable initial status enabling queue management

### Basic Workflow Execution (Direct Database Access)

```python
from cosmos_workflow.database import init_database
from cosmos_workflow.database.models import Prompt, Run

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
from cosmos_workflow.database.models import Prompt, Run

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