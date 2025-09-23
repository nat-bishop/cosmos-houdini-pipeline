# Gradio UI Improvement Plan

## Overview
This plan addresses critical issues identified in the code review of the Cosmos Workflow Gradio UI. Each phase is designed to be completed independently while building towards a more maintainable, performant, and secure application.

---

## Phase 1: Critical Fixes (Immediate Priority)

### ☐ 1.1 Fix Global State Management
**Current Issue:** The app uses global mutable variables (`api`, `queue_service`, `queue_handlers`) which violates the CLAUDE.md "No global state" principle and creates race conditions.

**Why This Matters:**
- **Race Conditions:** Multiple users accessing the UI simultaneously can interfere with each other's state
- **Testing Difficulty:** Global state makes unit testing nearly impossible
- **Memory Leaks:** Global objects can accumulate state over time
- **Debugging Complexity:** Hard to track state changes across requests

**Solution Architecture:**
```python
# New dependency injection pattern
class UIServices:
    """Encapsulates all services with proper lifecycle management."""
    def __init__(self, config: ConfigManager):
        self.config = config
        self.api = CosmosAPI()
        self.db_connection = DatabaseConnection("outputs/cosmos.db")
        self.queue_service = SimplifiedQueueService(db_connection=self.db_connection)
        self.queue_handlers = QueueHandlers(self.queue_service)

    def cleanup(self):
        """Proper resource cleanup."""
        self.queue_service.shutdown()
        self.db_connection.close()

def create_ui(services: UIServices = None):
    """Create UI with injected services."""
    if services is None:
        services = UIServices(ConfigManager())

    # Pass services to components
    app, components = build_ui_components(services.config)

    # Use Gradio State for per-session data
    with app:
        session_state = gr.State({"user_id": None, "preferences": {}})
        wire_all_events(app, components, services, session_state)

    return app, services
```

**Benefits:**
- Thread-safe concurrent access
- Easy unit testing with mock services
- Clear resource lifecycle management
- Per-session state isolation

### ☐ 1.2 Improve Exception Handling
**Files to Update:**
- `app.py`: Lines 80-82
- `queue_handlers.py`: Lines 82, 101, 151
- All handler functions in `tabs/`

**Implementation:**
```python
# Create exception classifier
class ErrorHandler:
    @staticmethod
    def handle_error(e: Exception, context: str) -> str:
        """Classify and sanitize errors per CLAUDE.md guidelines."""
        if isinstance(e, ValueError):
            logger.error("Validation error in %s: %s", context, str(e))
            return "Invalid input. Please check your data format."
        elif isinstance(e, DatabaseError):
            logger.error("Database error in %s: %s", context, str(e))
            return "Database operation failed. Please try again."
        elif isinstance(e, ConnectionError):
            logger.error("Connection error in %s: %s", context, str(e))
            return "Connection failed. Please check network settings."
        elif isinstance(e, PermissionError):
            logger.error("Permission error in %s: %s", context, str(e))
            return "Access denied. Please check permissions."
        else:
            # Never expose internal errors
            logger.error("Unexpected error in %s: %s", context, str(e))
            return "An unexpected error occurred. Please contact support."
```

### ☐ 1.3 Add Component Validation
**Current Issue:** Components are accessed with `.get()` without validation, causing silent failures when components are missing.

**Why This Matters:**
- **Silent Failures:** Missing components cause features to silently not work
- **Difficult Debugging:** No clear error messages when UI is misconfigured
- **Runtime Surprises:** Errors only appear when users interact with broken features
- **Maintenance Issues:** Hard to track which components are required vs optional

**Solution:**
```python
class ComponentValidator:
    """Validates UI components at startup and runtime."""

    @staticmethod
    def validate_startup(components: dict, required_components: list[str]):
        """Validate all required components exist at startup."""
        missing = [key for key in required_components if key not in components]
        if missing:
            raise ValueError(f"Missing required UI components: {missing}")

    @staticmethod
    def get_component(components: dict, key: str, component_type=None):
        """Safely get a component with validation."""
        if key not in components:
            raise KeyError(f"Component '{key}' not found in UI")

        component = components[key]
        if component_type and not isinstance(component, component_type):
            raise TypeError(f"Component '{key}' is not of type {component_type}")

        return component

    @staticmethod
    def wire_event_safely(components: dict, component_key: str,
                         event: str, handler, inputs=None, outputs=None):
        """Wire event with automatic validation and None filtering."""
        try:
            component = ComponentValidator.get_component(components, component_key)

            # Filter None components
            safe_inputs = [c for c in (inputs or []) if c is not None]
            safe_outputs = [c for c in (outputs or []) if c is not None]

            # Wire the event
            getattr(component, event)(
                fn=handler,
                inputs=safe_inputs,
                outputs=safe_outputs
            )
            logger.debug("Wired event %s.%s successfully", component_key, event)
        except (KeyError, AttributeError) as e:
            logger.error("Failed to wire event: %s", e)
            raise
```

**Benefits:**
- Fail fast at startup rather than runtime
- Clear error messages for missing components
- Type safety for component operations
- Easier debugging and maintenance

---

## Phase 2: Code Quality Improvements

### ☐ 2.1 Eliminate Code Duplication
**Target:** Remove 32 instances of `filter_none_components()` calls

**Create Wrapper:**
```python
# In ui/core/utils.py
def wire_events_batch(components: dict, wiring_config: list[dict]):
    """Wire multiple events with automatic validation and filtering."""
    for config in wiring_config:
        ComponentValidator.wire_event_safely(
            components=components,
            component_key=config["component"],
            event=config["event"],
            handler=config["handler"],
            inputs=config.get("inputs"),
            outputs=config.get("outputs")
        )
```

### ☐ 2.2 Add Comprehensive Type Hints
**Files to Update:** All handler functions in `tabs/`, `queue_handlers.py`, helper functions

**Example:**
```python
from typing import Optional, List, Dict, Any, Tuple
import gradio as gr

def handle_prompt_create(
    description: str,
    input_dir: str,
    model_type: str,
    parameters: Dict[str, Any]
) -> Tuple[str, gr.update, gr.update]:
    """Create a new prompt with type-safe parameters."""
    # Implementation
```

### ☐ 2.3 Fix Error Classification
**Update:** `simple_queue_service.py` lines 140-142
- Change warnings to errors for critical failures
- Add proper error propagation
- Implement retry logic where appropriate

### ☐ 2.4 Improve Resource Cleanup
**Implement context managers:**
```python
from contextlib import contextmanager

@contextmanager
def managed_ui_services(config: ConfigManager):
    """Context manager for UI services lifecycle."""
    services = UIServices(config)
    try:
        yield services
    finally:
        services.cleanup()
```

---

## Phase 3: Architecture Improvements

### ☐ 3.1 Refactor Monolithic Event Wiring
**Target:** Break down 277+ line functions in `builder.py`

**New Structure:**
```
ui/core/wiring/
    ├── __init__.py
    ├── base.py          # Base wiring utilities
    ├── prompts.py       # Prompts tab wiring
    ├── runs.py          # Runs tab wiring
    ├── inputs.py        # Inputs tab wiring
    ├── jobs.py          # Jobs tab wiring
    └── navigation.py    # Cross-tab navigation
```

### ☐ 3.2 Extract Magic Values to Configuration
**Create constants file:**
```python
# ui/constants.py
class UIConstants:
    # Timeouts
    DEFAULT_TIMEOUT_MS = 120000
    QUEUE_CHECK_INTERVAL = 2

    # Limits
    MAX_GALLERY_ITEMS = 50
    MAX_TABLE_ROWS = 100

    # Sizes
    THUMBNAIL_SIZE = (384, 216)
    VIDEO_PREVIEW_SIZE = (1920, 1080)
```

### ☐ 3.3 Add Input Validation Layer
**Create validation module:**
```python
# ui/validation.py
from pydantic import BaseModel, validator

class PromptInput(BaseModel):
    description: str
    input_dir: str
    model_type: str

    @validator('description')
    def validate_description(cls, v):
        if len(v) < 3:
            raise ValueError("Description must be at least 3 characters")
        return v

    @validator('input_dir')
    def validate_path(cls, v):
        # Prevent path traversal
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid path")
        return v
```

### ☐ 3.4 Optimize Data Loading
**Implement pagination:**
```python
class PaginatedDataLoader:
    def __init__(self, page_size: int = 50):
        self.page_size = page_size

    def load_runs_page(self, page: int, filters: dict) -> tuple[list, int]:
        """Load a single page of runs with total count."""
        offset = page * self.page_size
        runs = api.query_runs(
            limit=self.page_size,
            offset=offset,
            filters=filters
        )
        total_count = api.count_runs(filters=filters)
        return runs, total_count
```

---

## Phase 4: Performance & Security Enhancements

### ☐ 4.1 Implement Caching Layer
```python
from functools import lru_cache
from datetime import datetime, timedelta

class UICache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache = {}

    def get_or_compute(self, key: str, compute_fn):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value

        value = compute_fn()
        self.cache[key] = (value, datetime.now())
        return value
```

### ☐ 4.2 Add Rate Limiting
```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)

    def check_rate_limit(self, user_id: str) -> bool:
        now = time()
        # Clean old requests
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if now - t < self.window
        ]

        if len(self.requests[user_id]) >= self.max_requests:
            return False

        self.requests[user_id].append(now)
        return True
```

### ☐ 4.3 Path Validation Security
```python
import os
from pathlib import Path

def validate_safe_path(user_path: str, base_dir: str) -> Path:
    """Validate path is within allowed directory."""
    base = Path(base_dir).resolve()
    target = (base / user_path).resolve()

    # Check if target is within base directory
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal attempt detected")

    return target
```

### ☐ 4.4 Add CSRF Protection
```python
import secrets
from datetime import datetime, timedelta

class CSRFProtection:
    def __init__(self):
        self.tokens = {}

    def generate_token(self, session_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.tokens[session_id] = (token, datetime.now())
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        if session_id not in self.tokens:
            return False

        stored_token, timestamp = self.tokens[session_id]
        # Token expires after 1 hour
        if datetime.now() - timestamp > timedelta(hours=1):
            del self.tokens[session_id]
            return False

        return secrets.compare_digest(stored_token, token)
```

---

## Phase 5: Testing & Documentation

### ☐ 5.1 Add Unit Tests
- Test each handler function with mock data
- Test error handling paths
- Test validation logic
- Test state management

### ☐ 5.2 Add Integration Tests
- Test event wiring
- Test cross-tab navigation
- Test queue operations
- Test data persistence

### ☐ 5.3 Update Documentation
- Add architecture documentation
- Document component dependencies
- Add troubleshooting guide
- Update CLAUDE.md with UI patterns

### ☐ 5.4 Clean Up Legacy Code
- Remove `app_old.py` (2063 lines)
- Remove commented code
- Remove unused imports
- Consolidate duplicate utilities

---

## Completion Metrics

### Success Criteria:
- [ ] All critical issues resolved
- [ ] No global state usage
- [ ] All exceptions properly handled
- [ ] Component validation in place
- [ ] Type hints on all public functions
- [ ] No code duplication (DRY)
- [ ] All magic values extracted
- [ ] Input validation implemented
- [ ] Tests passing
- [ ] Documentation updated

### Performance Targets:
- Page load time < 2 seconds
- Gallery render < 500ms for 50 items
- Queue updates < 100ms
- Memory usage stable over time

### Security Checklist:
- [ ] Path traversal prevention
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Input sanitization
- [ ] Error message sanitization

---

## Notes
- **Thumbnail functionality remains unchanged** as requested
- Each phase can be completed independently
- Focus on maintaining backward compatibility
- Test thoroughly after each phase