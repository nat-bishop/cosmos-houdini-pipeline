# Cosmos Workflow Architecture Refactoring Plan

## 📋 Executive Summary

This document outlines a comprehensive refactoring of the Cosmos Workflow system to address current pain points and enable future scalability. The refactoring moves from a file-based, tightly-coupled CLI to a service-oriented architecture with database persistence and optional web UI.

### Key Changes
- **Replace JSON files with SQLite database** for prompt/run tracking
- **Introduce service layer** to decouple business logic from CLI
- **Add unified `cosmos run` command** to simplify workflow from 5 steps to 1
- **Enable web UI** through FastAPI without duplicating logic
- **No backwards compatibility** - fresh start for simplicity

### Timeline: 2-3 weeks total
- Week 1: Foundation (database, services, basic CLI)
- Week 2: Features (smart defaults, search, progress tracking, API)
- Week 3: Optional web UI

---

## 🔴 Current Problems

### Pain Points Identified
1. **Manual Directory Management**: Users must manually specify paths like `inputs/videos/city_scene_20250830_203504/`
2. **No Discovery**: Can't search or list previous prompts/runs
3. **Complex Multi-Step Process**:
   ```bash
   cosmos prepare ./renders/
   cosmos create prompt "text" inputs/videos/xxx
   cosmos inference prompt_spec.json
   ```
4. **No Progress Visibility**: Can't track what's running or see history
5. **Scattered JSON Files**: Prompts organized by date folders, hard to find
6. **Tight CLI Coupling**: Business logic mixed with presentation

### Technical Debt
- CLI directly instantiates orchestrator
- No abstraction between storage and business logic
- File I/O scattered throughout codebase
- No concurrent access protection

---

## 🏗️ Proposed Architecture

### Clean Architecture Principles
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│     CLI     │  │   Web UI    │  │     API     │  <- Presentation
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       └─────────────────┴─────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Service Layer     │              <- Business Logic
              │  WorkflowService    │
              │  PromptService      │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   SQLAlchemy ORM    │              <- Data Access
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │      SQLite DB      │              <- Storage
              └─────────────────────┘
```

### Database Schema
```sql
-- Core tables
CREATE TABLE prompts (
    id VARCHAR PRIMARY KEY,
    name VARCHAR,
    prompt_text TEXT,
    negative_prompt TEXT,
    video_path VARCHAR,
    control_inputs JSON,
    created_at TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_created (created_at),
    FULLTEXT INDEX idx_prompt_text (prompt_text)
);

CREATE TABLE runs (
    id VARCHAR PRIMARY KEY,
    prompt_id VARCHAR REFERENCES prompts(id),
    status VARCHAR, -- 'pending', 'running', 'success', 'failed'
    output_path VARCHAR,
    metrics JSON, -- timing, GPU usage, etc
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_prompt (prompt_id)
);

CREATE TABLE run_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR REFERENCES runs(id),
    stage VARCHAR, -- 'uploading', 'inference', 'downloading'
    progress FLOAT, -- 0.0 to 1.0
    message TEXT,
    timestamp TIMESTAMP
);
```

---

## 📝 Implementation Plan

### Phase 0: Foundation (3 days)

#### Day 1: Database Setup
**File**: `cosmos_workflow/database/models.py`
```python
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Prompt(Base):
    __tablename__ = 'prompts'

    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    prompt_text = Column(Text)
    negative_prompt = Column(Text)
    video_path = Column(String)
    control_inputs = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("Run", back_populates="prompt")

class Run(Base):
    __tablename__ = 'runs'

    id = Column(String, primary_key=True)
    prompt_id = Column(String, ForeignKey('prompts.id'))
    status = Column(String)
    output_path = Column(String)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    prompt = relationship("Prompt", back_populates="runs")
    progress = relationship("RunProgress", back_populates="run")
```

#### Day 2: Service Layer
**File**: `cosmos_workflow/services/workflow_service.py`
```python
class WorkflowService:
    def __init__(self, db_session):
        self.db = db_session
        self.orchestrator = WorkflowOrchestrator()

    def create_and_run(self, prompt_text: str, video_dir: Path) -> Run:
        """Single method to handle entire workflow"""
        # Create prompt, create run, execute, track progress
        pass

    def list_recent_runs(self, limit: int = 10) -> List[Run]:
        return self.db.query(Run).order_by(Run.created_at.desc()).limit(limit).all()

    def search_prompts(self, query: str) -> List[Prompt]:
        return self.db.query(Prompt).filter(
            Prompt.prompt_text.contains(query)
        ).all()
```

#### Day 3: Refactored CLI
**File**: `cosmos_workflow/cli/commands.py`
```python
@click.command()
@click.argument('prompt_text')
@click.argument('video_dir', required=False)
def run(prompt_text, video_dir):
    """Single command to run entire workflow"""
    service = get_workflow_service()
    run = service.create_and_run(prompt_text, video_dir)
    console.print(f"✅ Complete! Output: {run.output_path}")

@click.command()
def list():
    """List recent runs with their status"""
    service = get_workflow_service()
    runs = service.list_recent_runs()
    # Display pretty table

@click.command()
@click.argument('query')
def search(query):
    """Search prompts by text"""
    service = get_workflow_service()
    results = service.search_prompts(query)
    # Display results
```

### Phase 1: Core Features (3 days)

#### Smart Defaults
```python
class WorkflowService:
    def smart_run(self, text: str, video_path: str = None):
        """Intelligently handle missing parameters"""
        if not video_path:
            # Use most recent video or prompt for path
            video_path = self.find_most_recent_video()

        # Auto-generate name from prompt
        name = generate_smart_name(text)

        # Use optimal defaults based on video characteristics
        params = self.get_optimal_params_for_video(video_path)

        return self.create_and_run(text, video_path, params)
```

#### Progress Tracking
```python
class ProgressTracker:
    def update(self, run_id: str, stage: str, progress: float, message: str = ""):
        """Update run progress in database"""
        progress = RunProgress(
            run_id=run_id,
            stage=stage,
            progress=progress,
            message=message,
            timestamp=datetime.utcnow()
        )
        self.db.add(progress)
        self.db.commit()

        # Emit websocket event if connected
        if self.websocket_manager:
            self.websocket_manager.broadcast(run_id, {
                'stage': stage,
                'progress': progress,
                'message': message
            })
```

### Phase 2: API Layer (2 days)

**File**: `cosmos_workflow/api/app.py`
```python
from fastapi import FastAPI, WebSocket
from cosmos_workflow.services import WorkflowService

app = FastAPI()

@app.post("/api/run")
async def run_workflow(prompt: str, video_path: str = None):
    """Start a new workflow run"""
    run = service.smart_run(prompt, video_path)
    return {"run_id": run.id, "status": run.status}

@app.get("/api/runs")
async def list_runs(skip: int = 0, limit: int = 20):
    """List recent runs"""
    runs = service.list_recent_runs(skip, limit)
    return runs

@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """Get run details with progress"""
    run = service.get_run_with_progress(run_id)
    return run

@app.websocket("/ws/progress/{run_id}")
async def progress_websocket(websocket: WebSocket, run_id: str):
    """Stream real-time progress updates"""
    await websocket.accept()
    async for progress in service.stream_progress(run_id):
        await websocket.send_json(progress)
```

### Phase 3: Web UI (Optional, 3-4 days)

**Simple HTML + Alpine.js Interface**
```html
<!DOCTYPE html>
<html>
<head>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <title>Cosmos Workflow</title>
</head>
<body>
    <div x-data="cosmosApp()">
        <!-- Prompt Input Section -->
        <section class="prompt-input">
            <h2>Generate Video</h2>
            <textarea x-model="prompt" placeholder="Describe your vision..."></textarea>
            <input type="file" @change="selectVideo($event)" accept="video/*">
            <button @click="runWorkflow()" :disabled="running">
                <span x-show="!running">Generate</span>
                <span x-show="running">Running...</span>
            </button>
        </section>

        <!-- Progress Display -->
        <section x-show="currentRun" class="progress">
            <h3>Progress</h3>
            <div class="progress-bar">
                <div :style="`width: ${progress}%`"></div>
            </div>
            <p x-text="statusMessage"></p>
        </section>

        <!-- Gallery -->
        <section class="gallery">
            <h2>Recent Runs</h2>
            <div class="grid">
                <template x-for="run in recentRuns">
                    <div class="card">
                        <video :src="`/outputs/${run.output_path}`" controls></video>
                        <h4 x-text="run.prompt.name"></h4>
                        <p x-text="run.prompt.prompt_text"></p>
                        <small x-text="run.created_at"></small>
                    </div>
                </template>
            </div>
        </section>
    </div>

    <script>
    function cosmosApp() {
        return {
            prompt: '',
            videoPath: null,
            running: false,
            currentRun: null,
            progress: 0,
            statusMessage: '',
            recentRuns: [],
            ws: null,

            async init() {
                await this.loadRecentRuns();
            },

            async runWorkflow() {
                this.running = true;

                const response = await fetch('/api/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        prompt: this.prompt,
                        video_path: this.videoPath
                    })
                });

                const data = await response.json();
                this.currentRun = data.run_id;
                this.connectWebSocket(data.run_id);
            },

            connectWebSocket(runId) {
                this.ws = new WebSocket(`ws://localhost:8000/ws/progress/${runId}`);
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.progress = data.progress * 100;
                    this.statusMessage = data.message;

                    if (data.status === 'completed') {
                        this.running = false;
                        this.loadRecentRuns();
                    }
                };
            },

            async loadRecentRuns() {
                const response = await fetch('/api/runs');
                this.recentRuns = await response.json();
            }
        }
    }
    </script>
</body>
</html>
```

---

## 🧪 Testing Strategy

### Unit Tests
```python
def test_workflow_service_create_and_run():
    # Use in-memory SQLite for tests
    service = WorkflowService(test_db_session)
    run = service.create_and_run("test prompt", Path("test/video"))
    assert run.status == "success"
    assert run.prompt.prompt_text == "test prompt"

def test_search_prompts():
    service = WorkflowService(test_db_session)
    # Add test data
    service.create_prompt("cyberpunk city", ...)
    service.create_prompt("foggy morning", ...)

    results = service.search_prompts("cyberpunk")
    assert len(results) == 1
    assert "cyberpunk" in results[0].prompt_text
```

### Integration Tests
```python
def test_full_workflow_with_mocked_ssh():
    # Mock SSH/Docker but test full flow
    with mock_ssh_connection():
        service = WorkflowService(test_db)
        run = service.smart_run("test prompt")
        assert run.output_path.exists()
```

### API Tests
```python
def test_api_run_endpoint():
    client = TestClient(app)
    response = client.post("/api/run", json={"prompt": "test"})
    assert response.status_code == 200
    assert "run_id" in response.json()
```

---

## 📊 Success Metrics

### Immediate Wins (Week 1)
- ✅ `cosmos run "prompt"` works end-to-end
- ✅ `cosmos list` shows recent runs
- ✅ Database tracks all operations

### Medium Term (Week 2)
- ✅ Full-text search across all prompts
- ✅ Real-time progress tracking
- ✅ API endpoints functional
- ✅ Smart defaults reduce input requirements by 70%

### Long Term (Week 3+)
- ✅ Web UI provides visual feedback
- ✅ Gallery view for browsing outputs
- ✅ Workflow time reduced from 5 commands to 1

---

## 🚨 Risk Mitigation

### Technical Risks
1. **Database Corruption**: Regular backups, WAL mode for SQLite
2. **Concurrent Access**: Use database transactions, row-level locking
3. **Large Files**: Stream video uploads, chunked transfers
4. **Network Issues**: Retry logic with exponential backoff

### Migration Risks
- **No automatic migration** - manually import important prompts if needed
- **Keep old JSON files** as backup until confident in new system
- **Parallel operation** - can run old and new systems side by side initially

---

## 📅 Development Schedule

### Week 1: Foundation
- **Monday**: Database schema and models
- **Tuesday**: Service layer implementation
- **Wednesday**: Basic CLI commands (run, list, search)
- **Thursday**: Unit tests and integration tests
- **Friday**: Bug fixes and documentation

### Week 2: Enhancement
- **Monday**: Smart defaults and auto-discovery
- **Tuesday**: Progress tracking system
- **Wednesday**: Output organization
- **Thursday**: FastAPI implementation
- **Friday**: API testing and polish

### Week 3: UI (Optional)
- **Monday**: HTML template and styling
- **Tuesday**: JavaScript functionality
- **Wednesday**: WebSocket integration
- **Thursday**: Gallery and comparison views
- **Friday**: Final testing and deployment

---

## 🎯 Key Decisions

### Why SQLite?
- Zero configuration
- Single file database
- Full-text search built-in
- Good enough for single user
- Easy testing with in-memory DB

### Why No Backwards Compatibility?
- Reduces complexity by 50%
- Faster implementation (2-3 weeks vs 6-8)
- Cleaner codebase
- Solo project with no external users

### Why Service Layer?
- Enables multiple frontends (CLI, API, UI)
- Testable business logic
- Single source of truth
- Future extensibility

### Why Simple UI?
- No build process needed
- Fast to implement
- Good enough for visual feedback
- Can enhance later if needed

---

## 📝 Next Steps

1. **Review and approve this plan** ✅
2. **Create feature branch**: `git checkout -b refactor/service-architecture`
3. **Start with database schema** (most critical piece)
4. **Implement incrementally** with tests at each step
5. **Deploy when Phase 1 complete** (usable at that point)

---

## 📚 Appendix

### File Structure After Refactoring
```
cosmos_workflow/
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models
│   └── connection.py      # Database setup
├── services/
│   ├── __init__.py
│   ├── workflow_service.py
│   ├── prompt_service.py
│   └── progress_tracker.py
├── api/
│   ├── __init__.py
│   ├── app.py            # FastAPI application
│   └── websocket.py      # WebSocket handlers
├── cli/
│   ├── __init__.py
│   └── commands.py       # Simplified CLI commands
├── web/
│   ├── index.html        # Simple web UI
│   └── static/
└── tests/
    ├── test_services.py
    ├── test_api.py
    └── test_cli.py
```

### Example Usage After Refactoring

**Before (current)**:
```bash
cosmos prepare ./renders/city_scene/
cosmos create prompt "cyberpunk transformation" inputs/videos/city_scene_20250830_203504
cosmos inference inputs/prompts/2025-09-03/cyberpunk_transformation_ps_abc123.json
# Check status in another terminal
cosmos status
# Manually find output files later
```

**After (new)**:
```bash
cosmos run "cyberpunk transformation" ./renders/city_scene/
# That's it! Progress shown inline, output path returned
```

Or for repeat/exploration:
```bash
cosmos list                          # See recent runs
cosmos search "cyberpunk"            # Find old prompts
cosmos run --like ps_abc123          # Rerun with same settings
cosmos compare run_123 run_456       # Compare two outputs
```

---

This document represents a complete architectural overhaul that solves the identified pain points while maintaining simplicity and fast implementation timeline. The plan is modular - each phase delivers value independently.