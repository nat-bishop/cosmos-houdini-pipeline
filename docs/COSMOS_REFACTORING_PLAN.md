# Cosmos Workflow Complete Architecture Refactoring Plan v3

## 🎯 Executive Summary

Complete architectural overhaul replacing JSON file-based system with SQLAlchemy database and service layer. This is a **comprehensive change** that will touch ~60% of the codebase but is designed to be implemented **incrementally without breaking existing functionality**.

### Scope of Changes
- **Remove**: 5 manager classes (~800 lines)
- **Add**: Database layer + service layer (~400 lines)
- **Modify**: CLI commands to use service layer
- **Keep**: SSH, Docker, file transfer infrastructure

### Risk Level: MEDIUM
- Can be implemented incrementally on feature branch
- Each phase is independently testable
- Rollback strategy: Keep branch separate until fully working

---

## 🏗️ Final Architecture

```
BEFORE (Current):                    AFTER (Clean):
┌──────────────┐                    ┌──────────────┐
│     CLI      │                    │     CLI      │
└──────┬───────┘                    └──────┬───────┘
       │                                    │
       ├──> PromptSpecManager               │
       ├──> RunSpecManager                  ▼
       ├──> DirectoryManager         ┌──────────────┐
       └──> WorkflowOrchestrator     │WorkflowService│
                │                    └──────┬───────┘
                │                           │
                ▼                           ├──> SQLAlchemy DB
           JSON Files                       └──> RemoteExecutor
                                                    │
                                                    ▼
                                              SSH/Docker
```

---

## 📋 What Gets Removed vs Kept

### ❌ REMOVE (Replace with Service + DB)
```python
cosmos_workflow/prompts/
├── prompt_spec_manager.py  # ~150 lines - REMOVE
├── run_spec_manager.py     # ~140 lines - REMOVE
├── schemas.py              # ~400 lines - REMOVE most (keep utils)
└── (DirectoryManager)      # ~100 lines - REMOVE

# Total removed: ~800 lines
```

### ✅ KEEP (Infrastructure)
```python
cosmos_workflow/
├── config/config_manager.py       # KEEP - reads config.toml
├── connection/ssh_manager.py      # KEEP - SSH connections
├── transfer/file_transfer.py      # KEEP - SFTP operations
├── execution/docker_executor.py   # KEEP - Docker commands
├── utils/smart_naming.py          # KEEP - name generation
└── local_ai/                      # KEEP - AI utilities
```

### 🆕 ADD (New Clean Architecture)
```python
cosmos_workflow/
├── database/
│   ├── __init__.py
│   ├── models.py           # ~100 lines - SQLAlchemy models
│   └── connection.py       # ~30 lines - DB setup
├── services/
│   ├── __init__.py
│   └── workflow_service.py # ~300 lines - ALL business logic
└── execution/
    └── remote_executor.py  # RENAME from workflow_orchestrator
```

---

## 💻 Complete Implementation Guide

### Phase 0: Setup Database Layer (Day 1)

#### Step 1: Install SQLAlchemy
```bash
pip install sqlalchemy
```

#### Step 2: Create Database Models
```python
# cosmos_workflow/database/models.py
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Float, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()

class RunStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class Prompt(Base):
    __tablename__ = 'prompts'

    id = Column(String, primary_key=True)  # Generated hash
    name = Column(String, nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    video_path = Column(String, nullable=False)
    control_inputs = Column(JSON)  # {"depth": "path", "seg": "path"}
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    runs = relationship("Run", back_populates="prompt", cascade="all, delete-orphan")

class Run(Base):
    __tablename__ = 'runs'

    id = Column(String, primary_key=True)  # UUID
    prompt_id = Column(String, ForeignKey('prompts.id'), nullable=False)
    status = Column(Enum(RunStatus), default=RunStatus.PENDING)
    control_weights = Column(JSON)  # {"vis": 0.25, "edge": 0.25, ...}
    parameters = Column(JSON)  # {"num_steps": 35, "guidance": 7.0, ...}
    output_path = Column(String)
    error_message = Column(Text)
    metrics = Column(JSON)  # {"duration": 120, "gpu_usage": 0.95, ...}
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)

    # Relationships
    prompt = relationship("Prompt", back_populates="runs")
    progress_updates = relationship("Progress", back_populates="run", cascade="all, delete-orphan")

class Progress(Base):
    __tablename__ = 'progress'

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey('runs.id'), nullable=False)
    stage = Column(String)  # "uploading", "inference", "downloading"
    progress = Column(Float)  # 0.0 to 1.0
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("Run", back_populates="progress_updates")

# cosmos_workflow/database/connection.py
def get_db_engine(db_path="cosmos.db"):
    """Create database engine"""
    return create_engine(f'sqlite:///{db_path}', echo=False)

def init_database(engine):
    """Initialize database tables"""
    Base.metadata.create_all(engine)

def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
```

### Phase 1: Create Service Layer (Day 2)

```python
# cosmos_workflow/services/workflow_service.py
import hashlib
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from cosmos_workflow.database.models import Prompt, Run, Progress, RunStatus
from cosmos_workflow.utils.smart_naming import generate_smart_name
from cosmos_workflow.execution.remote_executor import RemoteExecutor
from cosmos_workflow.config.config_manager import ConfigManager

class WorkflowService:
    """Central service handling all business logic"""

    def __init__(self, db_session: Session, config_manager=None):
        self.db = db_session
        self.config = config_manager or ConfigManager()
        self.executor = None  # Lazy load

    def _get_executor(self):
        """Lazy load executor"""
        if not self.executor:
            self.executor = RemoteExecutor(self.config)
        return self.executor

    # === Prompt Management ===

    def create_prompt(self,
                     prompt_text: str,
                     video_dir: Path,
                     negative_prompt: str = None) -> Prompt:
        """Create a new prompt (replaces PromptSpecManager)"""

        # Validation
        video_dir = Path(video_dir)
        if not video_dir.exists():
            raise ValueError(f"Video directory not found: {video_dir}")

        color_video = video_dir / "color.mp4"
        if not color_video.exists():
            raise ValueError(f"Color video not found: {color_video}")

        # Generate smart name
        name = generate_smart_name(prompt_text, max_length=30)

        # Build paths
        control_inputs = {
            "depth": str(video_dir / "depth.mp4"),
            "seg": str(video_dir / "segmentation.mp4")
        }

        # Generate ID (hash of content)
        content = f"{prompt_text}:{video_dir}:{control_inputs}"
        prompt_id = f"ps_{hashlib.md5(content.encode()).hexdigest()[:12]}"

        # Check for duplicates
        existing = self.db.query(Prompt).filter_by(id=prompt_id).first()
        if existing:
            return existing

        # Create in database
        prompt = Prompt(
            id=prompt_id,
            name=name,
            prompt_text=prompt_text,
            negative_prompt=negative_prompt or self._get_default_negative(),
            video_path=str(color_video),
            control_inputs=control_inputs
        )

        self.db.add(prompt)
        self.db.commit()
        return prompt

    # === Run Management ===

    def create_run(self,
                  prompt_id: str,
                  control_weights: dict = None,
                  parameters: dict = None) -> Run:
        """Create a new run (replaces RunSpecManager)"""

        # Verify prompt exists
        prompt = self.db.query(Prompt).filter_by(id=prompt_id).first()
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_id}")

        # Use defaults if not provided
        if control_weights is None:
            control_weights = {
                "vis": 0.25, "edge": 0.25,
                "depth": 0.25, "seg": 0.25
            }

        if parameters is None:
            parameters = {
                "num_steps": 35,
                "guidance": 7.0,
                "seed": 1,
                "fps": 24
            }

        # Create run
        run = Run(
            id=str(uuid.uuid4())[:12],
            prompt_id=prompt_id,
            status=RunStatus.PENDING,
            control_weights=control_weights,
            parameters=parameters
        )

        self.db.add(run)
        self.db.commit()
        return run

    # === Workflow Execution ===

    def execute_run(self, run_id: str) -> Run:
        """Execute a run on remote GPU"""
        run = self.db.query(Run).filter_by(id=run_id).first()
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        # Update status
        run.status = RunStatus.RUNNING
        self.db.commit()

        try:
            # Get executor
            executor = self._get_executor()

            # Execute remotely (executor handles SSH/Docker)
            result = executor.execute(
                prompt=run.prompt,
                control_weights=run.control_weights,
                parameters=run.parameters,
                progress_callback=lambda s, p: self._update_progress(run.id, s, p)
            )

            # Update run with results
            run.status = RunStatus.SUCCESS
            run.output_path = result['output_path']
            run.metrics = result['metrics']
            run.completed_at = datetime.utcnow()

        except Exception as e:
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            raise
        finally:
            self.db.commit()

        return run

    # === Unified Workflow ===

    def create_and_run(self,
                      prompt_text: str,
                      video_dir: Path = None) -> Run:
        """One-step workflow: create prompt and run inference"""

        # Auto-detect video if not provided
        if not video_dir:
            video_dir = self._find_most_recent_video()
            if not video_dir:
                raise ValueError("No video directory found")

        # Create prompt
        prompt = self.create_prompt(prompt_text, video_dir)

        # Create run
        run = self.create_run(prompt.id)

        # Execute
        return self.execute_run(run.id)

    # === Query Methods ===

    def list_prompts(self, limit: int = 20) -> List[Prompt]:
        """List recent prompts"""
        return (self.db.query(Prompt)
                .order_by(Prompt.created_at.desc())
                .limit(limit)
                .all())

    def list_runs(self, limit: int = 20) -> List[Run]:
        """List recent runs with prompt info"""
        return (self.db.query(Run)
                .join(Prompt)
                .order_by(Run.created_at.desc())
                .limit(limit)
                .all())

    def search_prompts(self, query: str) -> List[Prompt]:
        """Search prompts by text"""
        return (self.db.query(Prompt)
                .filter(Prompt.prompt_text.contains(query))
                .all())

    # === Helper Methods ===

    def _update_progress(self, run_id: str, stage: str, progress: float):
        """Update run progress"""
        prog = Progress(
            id=str(uuid.uuid4())[:12],
            run_id=run_id,
            stage=stage,
            progress=progress
        )
        self.db.add(prog)
        self.db.commit()

    def _find_most_recent_video(self) -> Optional[Path]:
        """Find most recently used video directory"""
        recent_prompt = (self.db.query(Prompt)
                        .order_by(Prompt.created_at.desc())
                        .first())
        if recent_prompt:
            video_path = Path(recent_prompt.video_path)
            return video_path.parent
        return None

    def _get_default_negative(self) -> str:
        """Get default negative prompt"""
        return "The video captures a game playing, with bad crappy graphics and cartoonish frames..."
```

### Phase 2: Refactor CLI (Day 3-4)

```python
# cosmos_workflow/cli/commands.py (NEW)
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from cosmos_workflow.database.connection import get_db_engine, init_database, get_session
from cosmos_workflow.services.workflow_service import WorkflowService
from cosmos_workflow.config.config_manager import ConfigManager

console = Console()

def get_service():
    """Get workflow service with database"""
    engine = get_db_engine()
    init_database(engine)
    session = get_session(engine)
    config = ConfigManager()
    return WorkflowService(session, config)

@click.command()
@click.argument('prompt_text')
@click.argument('video_dir', required=False)
def run(prompt_text, video_dir):
    """🚀 One-step workflow execution"""
    try:
        service = get_service()
        video_path = Path(video_dir) if video_dir else None
        run = service.create_and_run(prompt_text, video_path)
        console.print(f"✅ Success! Output: {run.output_path}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@click.command()
@click.option('--limit', default=10)
def list(limit):
    """📋 List recent runs"""
    service = get_service()
    runs = service.list_runs(limit)

    table = Table(title="Recent Runs")
    table.add_column("ID", style="cyan")
    table.add_column("Prompt", style="white")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")

    for run in runs:
        status_color = {
            'pending': 'yellow',
            'running': 'blue',
            'success': 'green',
            'failed': 'red'
        }.get(run.status.value, 'white')

        table.add_row(
            run.id,
            run.prompt.name[:30],
            f"[{status_color}]{run.status.value}[/{status_color}]",
            run.created_at.strftime("%Y-%m-%d %H:%M")
        )

    console.print(table)

@click.command()
@click.argument('query')
def search(query):
    """🔍 Search prompts"""
    service = get_service()
    prompts = service.search_prompts(query)

    if not prompts:
        console.print(f"No prompts found for: {query}")
        return

    for prompt in prompts:
        console.print(f"[cyan]{prompt.id}[/cyan]: {prompt.name}")
        console.print(f"  {prompt.prompt_text[:100]}...")
```

### Phase 3: Create Remote Executor (Day 4)

```python
# cosmos_workflow/execution/remote_executor.py
# (Simplified version of current WorkflowOrchestrator)
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.execution.docker_executor import DockerExecutor

class RemoteExecutor:
    """Handles remote GPU execution only - no business logic"""

    def __init__(self, config_manager):
        self.config = config_manager
        self.ssh = None
        self.transfer = None
        self.docker = None

    def execute(self, prompt, control_weights, parameters, progress_callback=None):
        """Execute inference on remote GPU"""

        # Initialize connections
        self._init_connections()

        with self.ssh:
            # Upload files
            if progress_callback:
                progress_callback("uploading", 0.2)
            self.transfer.upload_prompt_and_videos(prompt)

            # Run inference
            if progress_callback:
                progress_callback("inference", 0.5)
            result = self.docker.run_inference(
                prompt, control_weights, parameters
            )

            # Download results
            if progress_callback:
                progress_callback("downloading", 0.8)
            output_path = self.transfer.download_results(result)

            if progress_callback:
                progress_callback("complete", 1.0)

            return {
                'output_path': output_path,
                'metrics': {
                    'duration': result.get('duration'),
                    'gpu_usage': result.get('gpu_usage')
                }
            }

    def _init_connections(self):
        """Initialize SSH/Docker/Transfer services"""
        if not self.ssh:
            ssh_options = self.config.get_ssh_options()
            self.ssh = SSHManager(ssh_options)
            self.transfer = FileTransferService(self.ssh, self.config.remote_dir)
            self.docker = DockerExecutor(self.ssh, self.config.remote_dir, self.config.docker_image)
```

---

## 🧪 Testing Strategy

### Unit Tests (In-Memory SQLite)
```python
# tests/test_service.py
import pytest
from sqlalchemy import create_engine
from cosmos_workflow.database.connection import init_database, get_session
from cosmos_workflow.database.models import RunStatus
from cosmos_workflow.services.workflow_service import WorkflowService

def test_workflow_service():
    # Use in-memory database for tests
    engine = create_engine('sqlite:///:memory:')
    init_database(engine)
    session = get_session(engine)

    service = WorkflowService(session)

    # Test prompt creation
    prompt = service.create_prompt("test prompt", Path("test/video"))
    assert prompt.name
    assert prompt.id

    # Test run creation
    run = service.create_run(prompt.id)
    assert run.status == RunStatus.PENDING

    # Test search
    results = service.search_prompts("test")
    assert len(results) == 1
```

---

## ⚠️ Risk Assessment & Mitigation

### What Could Break?
1. **Existing CLI commands** → Keep old commands during migration
2. **File paths** → Database stores absolute paths, handle carefully
3. **SSH/Docker** → These remain unchanged, low risk
4. **Progress tracking** → Add gradually, not critical for v1

### Rollback Strategy
1. Develop on feature branch: `git checkout -b refactor/service-architecture`
2. Keep old code intact until new code fully works
3. Test extensively before merging
4. Database is just a file - can delete and start over

### Success Criteria
- [ ] `cosmos run "prompt"` executes full workflow
- [ ] `cosmos list` shows recent runs
- [ ] `cosmos search` finds prompts
- [ ] All tests pass
- [ ] No regression in existing functionality

---

## 📊 Implementation Checklist

### Week 1: Foundation
- [ ] Day 1: Create database models
- [ ] Day 1: Write database tests
- [ ] Day 2: Create WorkflowService
- [ ] Day 2: Write service tests
- [ ] Day 3: Add new CLI commands (run, list, search)
- [ ] Day 3: Test CLI commands
- [ ] Day 4: Create RemoteExecutor
- [ ] Day 4: Integration testing
- [ ] Day 5: Fix bugs, polish

### Week 2: Migration (Optional)
- [ ] Port old CLI commands to use service
- [ ] Remove old managers
- [ ] Add progress tracking
- [ ] Add error recovery
- [ ] Documentation

---

## 🎯 Why This Will Work

1. **Incremental**: Each phase works independently
2. **Testable**: In-memory DB for unit tests
3. **Reversible**: Feature branch until proven
4. **Clear boundaries**: Service/Database/Executor separation
5. **Proven patterns**: Standard SQLAlchemy + service layer

## 🚀 Quick Start Commands

```bash
# Start implementation
git checkout -b refactor/service-architecture
pip install sqlalchemy

# Create files
mkdir -p cosmos_workflow/database
mkdir -p cosmos_workflow/services
touch cosmos_workflow/database/__init__.py
touch cosmos_workflow/database/models.py
touch cosmos_workflow/database/connection.py
touch cosmos_workflow/services/__init__.py
touch cosmos_workflow/services/workflow_service.py

# Test as you go
pytest tests/test_database.py -xvs
pytest tests/test_service.py -xvs

# When ready
git add .
git commit -m "feat: add service layer architecture with SQLAlchemy"
git checkout main
git merge refactor/service-architecture
```

---

## 📝 Notes for Implementation

### Database Decisions
- **SQLAlchemy over Peewee**: Industry standard, better long-term
- **SQLite**: Simple, single file, good enough for single user
- **JSON columns**: For flexible storage of control_inputs, parameters

### Service Layer Decisions
- **Single WorkflowService**: Not separate Prompt/Run services
- **Lazy executor loading**: Only create SSH connection when needed
- **Progress as separate table**: Allows historical tracking

### CLI Decisions
- **New commands only initially**: Don't break existing workflow
- **Rich for output**: Better tables and formatting
- **Click for commands**: Already in use, familiar

This refactoring is comprehensive but manageable. The key is working incrementally on a feature branch and testing each phase before moving on.