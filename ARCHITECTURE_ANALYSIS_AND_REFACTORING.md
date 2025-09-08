# Architecture Analysis and Refactoring Recommendations

## Executive Summary

This document provides a deep architectural analysis of the Cosmos Workflow System, identifying coupling issues, cohesion problems, and violations of Python best practices. It includes detailed refactoring recommendations following SOLID principles and the Zen of Python.

---

## 1. Current Architecture Overview

### 1.1 System Layers

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Commands                        │
│         (cosmos_workflow/cli/*.py)                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌═════════════════════════════════════════════════════════┐
║                    CosmosAPI                            ║
║         Main Facade (879 lines)                         ║
║    • Prompt operations                                  ║
║    • Run orchestration                                  ║
║    • System management                                  ║
║    • Container operations                               ║
╚═════════════════════════════════════════════════════════╝
           │                                 │
           ▼                                 ▼
┌──────────────────────┐       ┌─────────────────────────┐
│   DataRepository     │       │      GPUExecutor        │
│    (985 lines)       │       │      (701 lines)       │
│ • CRUD operations    │       │ • Single runs           │
│ • Search/Query       │       │ • Batch processing      │
│ • Deletion logic     │       │ • Enhancement           │
│ • Preview operations │       │ • Container management  │
└──────────────────────┘       └─────────────────────────┘
           │                                 │
           ▼                                 ▼
    [SQLAlchemy DB]                  [SSH/Docker/Files]
```

### 1.2 Identified Architecture Problems

1. **Monolithic Classes**: Each major class handles 4-8 different responsibilities
2. **Tight Coupling**: Layers reach into each other's internals
3. **Mixed Abstraction Levels**: Business logic mixed with infrastructure
4. **Inconsistent Patterns**: Different approaches for similar operations
5. **Poor Separation of Concerns**: System operations mixed with business logic

---

## 2. Coupling and Cohesion Analysis

### 2.1 High Coupling Issues

#### Issue 1: CosmosAPI Creates Internal Components Directly
```python
# CURRENT (Tight Coupling)
class CosmosAPI:
    def __init__(self, config=None):
        db = init_database(str(db_path))  # Creates database directly
        self.service = DataRepository(db, config)  # Creates service directly
        self.orchestrator = GPUExecutor(service=self.service)  # WRONG parameter!
```

**Problem**: Can't test or replace components without modifying CosmosAPI

#### Issue 2: CosmosAPI Reaches Into GPUExecutor Internals
```python
# CURRENT (Violates Encapsulation)
def get_active_containers(self):
    self.orchestrator._initialize_services()  # Private method!
    with self.orchestrator.ssh_manager:  # Internal field!
        containers = self.orchestrator.docker_executor.get_containers()
```

**Problem**: Changes to GPUExecutor internals break CosmosAPI

#### Issue 3: Tests Import Internal Components
```python
# tests/integration/test_database_workflow.py
from cosmos_workflow.execution.gpu_executor import GPUExecutor
from cosmos_workflow.services import DataRepository
```

**Problem**: Tests coupled to implementation, not behavior

### 2.2 Low Cohesion Issues

#### DataRepository (985 lines) - Too Many Responsibilities:
1. **Prompt CRUD** (create_prompt, get_prompt, update_prompt)
2. **Run CRUD** (create_run, get_run, update_run)
3. **Query Operations** (list_prompts, list_runs, search_prompts)
4. **Deletion Logic** (delete_prompt, delete_run, preview operations)
5. **ID Generation** (_generate_prompt_id, _generate_run_id)
6. **Data Conversion** (_prompt_to_dict, _run_to_dict)

#### CosmosAPI (879 lines) - Mixed Concerns:
1. **Prompt Management** (create_prompt, get_prompt)
2. **Inference Operations** (quick_inference, batch_inference)
3. **Enhancement Operations** (enhance_prompt)
4. **System Operations** (check_status, verify_integrity)
5. **Container Management** (get_active_containers, kill_containers)
6. **Configuration Building** (_build_execution_config)

#### GPUExecutor (701 lines) - Multiple Execution Types:
1. **Single Run Execution** (execute_run)
2. **Batch Processing** (execute_batch_runs)
3. **Enhancement Runs** (execute_enhancement_run)
4. **Container Management** (kill_container, get_gpu_status)
5. **Output Management** (_download_outputs, _split_batch_outputs)

---

## 3. Violations of Python Best Practices

### 3.1 Zen of Python Violations

#### "Simple is better than complex"
**Violation**: 136-line methods doing multiple things
```python
def enhance_prompt(self, prompt_id: str, create_new: bool = True,
                  enhancement_model: str = "pixtral") -> dict[str, Any]:
    # 136 lines of mixed validation, execution, error handling
```

#### "Flat is better than nested"
**Violation**: Deep nesting in methods
```python
try:
    with self.ssh_manager:
        try:
            if condition:
                for item in items:
                    if another_condition:
                        # Actual logic buried here
```

#### "Explicit is better than implicit"
**Violation**: Hidden side effects
```python
def _initialize_services(self):  # Called implicitly, creates connections
```

#### "There should be one-- and preferably only one --obvious way to do it"
**Violation**: Multiple ways to update runs
```python
update_run()
update_run_with_log()  # DEPRECATED but still exists
update_run_error()     # DEPRECATED but still exists
```

### 3.2 SOLID Principle Violations

#### Single Responsibility Principle (SRP)
- DataRepository handles 6+ responsibilities
- CosmosAPI mixes business logic with system operations
- GPUExecutor handles execution AND container management

#### Open/Closed Principle (OCP)
- Adding new operation types requires modifying existing classes
- No extension points for new functionality

#### Dependency Inversion Principle (DIP)
- High-level modules depend on concrete implementations
- No interfaces or abstractions

---

## 4. Confusing and Convoluted Code

### 4.1 Complex Conditional Logic
```python
# cosmos_workflow/api/cosmos_api.py - enhance_prompt method
if create_new:
    enhanced = self.service.create_prompt(...)
    if original_video_path and original_video_path.exists():
        # Complex video copying logic
    enhanced_prompt_id = enhanced["id"]
else:
    self.service.update_prompt(...)
    enhanced_prompt_id = prompt_id
```

### 4.2 Mixed Abstraction Levels
```python
# High-level operation mixed with low-level details
def quick_inference(self, prompt_id: str, ...):
    # Business logic
    prompt = self.get_prompt(prompt_id)

    # Low-level configuration building
    if blur_strength == "very_low":
        blur_kernel = 3
    elif blur_strength == "low":
        blur_kernel = 5
    # ... etc
```

### 4.3 Unclear Method Names
- `quick_inference` vs `create_and_run` - What's the difference?
- `_build_execution_config` - Does it build or validate?
- `update_run` vs `update_run_status` - Overlapping responsibilities

---

## 5. Detailed Refactoring Plan

### 5.1 Phase 1: Critical Fixes (Immediate)

#### Fix 1: GPUExecutor Constructor Bug
```python
# CURRENT (BROKEN)
self.orchestrator = GPUExecutor(service=self.service)

# FIXED
self.orchestrator = GPUExecutor(self.config_manager)
```

#### Fix 2: Add Dependency Injection
```python
class CosmosAPI:
    def __init__(self,
                 data_repository: DataRepository = None,
                 gpu_executor: GPUExecutor = None,
                 config: ConfigManager = None):
        self.config = config or ConfigManager()
        self.data_repository = data_repository or self._create_default_repository()
        self.gpu_executor = gpu_executor or self._create_default_executor()
```

### 5.2 Phase 2: Extract Responsibilities (1-2 weeks)

#### Split DataRepository into Focused Repositories

```python
# prompt_repository.py
class PromptRepository:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def create(self, model_type: str, prompt_text: str,
               inputs: dict, parameters: dict) -> str:
        # Only prompt creation logic
        pass

    def get(self, prompt_id: str) -> dict | None:
        # Only prompt retrieval
        pass

    def update(self, prompt_id: str, **kwargs) -> dict | None:
        # Only prompt updates
        pass

# run_repository.py
class RunRepository:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def create(self, prompt_id: str, execution_config: dict) -> str:
        # Only run creation
        pass

    def get(self, run_id: str) -> dict | None:
        # Only run retrieval
        pass

    def update_status(self, run_id: str, status: str) -> dict | None:
        # Only status updates
        pass

# query_service.py
class QueryService:
    def __init__(self, prompt_repo: PromptRepository, run_repo: RunRepository):
        self.prompt_repo = prompt_repo
        self.run_repo = run_repo

    def search_prompts(self, query: str, limit: int = 50) -> list[dict]:
        # Search logic only
        pass

    def list_prompts(self, model_type: str = None, limit: int = 50) -> list[dict]:
        # Listing logic only
        pass
```

#### Split CosmosAPI into Domain-Specific APIs

```python
# prompt_api.py
class PromptAPI:
    def __init__(self, prompt_repo: PromptRepository):
        self.prompt_repo = prompt_repo

    def create_prompt(self, prompt_text: str, video_dir: Path) -> dict:
        # Only prompt operations
        pass

# inference_api.py
class InferenceAPI:
    def __init__(self, run_repo: RunRepository, gpu_executor: GPUExecutor):
        self.run_repo = run_repo
        self.gpu_executor = gpu_executor

    def run_inference(self, prompt_id: str, config: dict) -> dict:
        # Only inference operations
        pass

# system_api.py
class SystemAPI:
    def __init__(self, gpu_executor: GPUExecutor):
        self.gpu_executor = gpu_executor

    def get_status(self) -> dict:
        # Only system operations
        pass

    def kill_containers(self) -> int:
        # Only container management
        pass

# Main facade combines them
class CosmosAPI:
    def __init__(self, config: ConfigManager = None):
        # Initialize sub-APIs
        self.prompts = PromptAPI(...)
        self.inference = InferenceAPI(...)
        self.system = SystemAPI(...)

    # Delegate to sub-APIs for backward compatibility
    def create_prompt(self, *args, **kwargs):
        return self.prompts.create_prompt(*args, **kwargs)
```

### 5.3 Phase 3: Implement Design Patterns (1 month)

#### Command Pattern for Operations

```python
# command.py
from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self) -> dict:
        pass

    @abstractmethod
    def validate(self) -> bool:
        pass

# inference_command.py
class InferenceCommand(Command):
    def __init__(self, prompt_id: str, config: dict,
                 run_repo: RunRepository, gpu_executor: GPUExecutor):
        self.prompt_id = prompt_id
        self.config = config
        self.run_repo = run_repo
        self.gpu_executor = gpu_executor

    def validate(self) -> bool:
        # Validate prompt exists and config is valid
        return True

    def execute(self) -> dict:
        # Create run
        run = self.run_repo.create(self.prompt_id, self.config)

        # Update status
        self.run_repo.update_status(run['id'], 'running')

        # Execute on GPU
        try:
            result = self.gpu_executor.execute_run(run, prompt)
            self.run_repo.update_status(run['id'], 'completed')
            return result
        except Exception as e:
            self.run_repo.update_status(run['id'], 'failed')
            raise

# enhancement_command.py
class EnhancementCommand(Command):
    # Similar structure for enhancement
    pass
```

#### Builder Pattern for Configuration

```python
# execution_config_builder.py
class ExecutionConfigBuilder:
    def __init__(self):
        self.config = {
            'weights': {'visual': 0.25, 'edge': 0.25, 'depth': 0.25, 'semantic': 0.25},
            'num_steps': 35,
            'guidance': 7.0,
            'seed': 1,
        }

    def with_weights(self, visual: float, edge: float,
                     depth: float, semantic: float) -> 'ExecutionConfigBuilder':
        # Validate weights sum to 1.0
        total = visual + edge + depth + semantic
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.config['weights'] = {
            'visual': visual,
            'edge': edge,
            'depth': depth,
            'semantic': semantic
        }
        return self

    def with_steps(self, num_steps: int) -> 'ExecutionConfigBuilder':
        if not 1 <= num_steps <= 100:
            raise ValueError(f"Steps must be 1-100, got {num_steps}")
        self.config['num_steps'] = num_steps
        return self

    def build(self) -> dict:
        return self.config.copy()
```

#### Strategy Pattern for Execution Types

```python
# execution_strategy.py
from abc import ABC, abstractmethod

class ExecutionStrategy(ABC):
    @abstractmethod
    def execute(self, run: dict, prompt: dict) -> dict:
        pass

class SingleRunStrategy(ExecutionStrategy):
    def __init__(self, ssh_manager, file_transfer, docker_executor):
        self.ssh_manager = ssh_manager
        self.file_transfer = file_transfer
        self.docker_executor = docker_executor

    def execute(self, run: dict, prompt: dict) -> dict:
        # Single run execution logic
        pass

class BatchRunStrategy(ExecutionStrategy):
    def execute(self, runs: list[dict], prompts: list[dict]) -> dict:
        # Batch execution logic
        pass

class EnhancementStrategy(ExecutionStrategy):
    def execute(self, run: dict, prompt: dict) -> dict:
        # Enhancement execution logic
        pass

# gpu_executor.py refactored
class GPUExecutor:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.strategies = {
            'single': SingleRunStrategy(...),
            'batch': BatchRunStrategy(...),
            'enhancement': EnhancementStrategy(...)
        }

    def execute(self, strategy_type: str, **kwargs) -> dict:
        strategy = self.strategies[strategy_type]
        return strategy.execute(**kwargs)
```

### 5.4 Phase 4: Improve Testability (Ongoing)

#### Use Dependency Injection Throughout

```python
# test_cosmos_api.py
def test_create_prompt():
    # Create test doubles
    mock_prompt_repo = Mock(spec=PromptRepository)
    mock_run_repo = Mock(spec=RunRepository)
    mock_gpu_executor = Mock(spec=GPUExecutor)

    # Inject test doubles
    api = CosmosAPI(
        prompt_repo=mock_prompt_repo,
        run_repo=mock_run_repo,
        gpu_executor=mock_gpu_executor
    )

    # Test behavior, not implementation
    result = api.create_prompt("test prompt", "video_dir")

    # Verify interactions
    mock_prompt_repo.create.assert_called_once()
```

#### Extract Complex Methods

```python
# BEFORE: 136-line method
def enhance_prompt(self, prompt_id: str, create_new: bool = True):
    # 136 lines of mixed logic
    pass

# AFTER: Small, focused methods
def enhance_prompt(self, prompt_id: str, create_new: bool = True):
    prompt = self._validate_prompt_for_enhancement(prompt_id)
    run = self._create_enhancement_run(prompt)

    try:
        enhanced_text = self._execute_enhancement(run, prompt)
        return self._handle_enhancement_success(prompt, enhanced_text, create_new)
    except Exception as e:
        return self._handle_enhancement_failure(run, e)

def _validate_prompt_for_enhancement(self, prompt_id: str) -> dict:
    # 10 lines of validation
    pass

def _create_enhancement_run(self, prompt: dict) -> dict:
    # 15 lines of run creation
    pass

def _execute_enhancement(self, run: dict, prompt: dict) -> str:
    # 20 lines of execution
    pass
```

---

## 6. Migration Strategy

### 6.1 Backward Compatibility

Maintain the existing CosmosAPI interface while refactoring internals:

```python
class CosmosAPI:
    """Facade maintaining backward compatibility."""

    def __init__(self, config: ConfigManager = None):
        # Initialize new components
        self._prompt_api = PromptAPI(...)
        self._inference_api = InferenceAPI(...)
        self._system_api = SystemAPI(...)

    # Delegate to new components
    def create_prompt(self, *args, **kwargs):
        return self._prompt_api.create_prompt(*args, **kwargs)

    def quick_inference(self, *args, **kwargs):
        return self._inference_api.run_inference(*args, **kwargs)

    # Deprecate confusing methods
    @deprecated("Use create_prompt() followed by quick_inference()")
    def create_and_run(self, *args, **kwargs):
        # Keep for compatibility but discourage use
        pass
```

### 6.2 Incremental Refactoring Steps

1. **Week 1**: Fix critical bugs (constructor, imports)
2. **Week 2**: Extract validation and configuration building
3. **Week 3**: Split DataRepository into focused repositories
4. **Week 4**: Implement command pattern for operations
5. **Month 2**: Complete architectural refactoring
6. **Ongoing**: Improve test coverage with proper test doubles

---

## 7. Expected Benefits

### 7.1 Immediate Benefits
- **Bug Fixes**: Constructor issue resolved
- **Better Testing**: Dependency injection enables proper mocking
- **Clearer Code**: Extracted methods are easier to understand

### 7.2 Long-term Benefits
- **Maintainability**: Small, focused classes are easier to modify
- **Extensibility**: New operations can be added without changing existing code
- **Performance**: Optimizations can be applied to specific components
- **Team Productivity**: Clear separation of concerns reduces cognitive load
- **Reliability**: Better testing leads to fewer bugs

### 7.3 Metrics for Success
- **Reduced Method Length**: No method > 50 lines (from 136)
- **Reduced Class Size**: No class > 300 lines (from 985)
- **Improved Test Coverage**: >90% (from current ~80%)
- **Reduced Coupling**: Each class depends on <3 other classes
- **Increased Cohesion**: Each class has single responsibility

---

## 8. Conclusion

The Cosmos Workflow System has a solid foundation but suffers from architectural debt typical of rapidly evolved codebases. The main issues are:

1. **Monolithic classes** trying to do too much
2. **Tight coupling** between layers
3. **Mixed abstraction levels** within methods
4. **Violations of Python best practices**

The refactoring plan addresses these issues incrementally:
- **Phase 1**: Critical bug fixes (immediate)
- **Phase 2**: Extract responsibilities (1-2 weeks)
- **Phase 3**: Implement design patterns (1 month)
- **Phase 4**: Improve testability (ongoing)

By following this plan, the codebase will become more maintainable, testable, and aligned with Python best practices and the Zen of Python. The key is to maintain backward compatibility while gradually improving the internal architecture.