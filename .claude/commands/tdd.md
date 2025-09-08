<role>
You are implementing features using Test-Driven Development (TDD). This is a disciplined, gated workflow that ensures quality through behavioral testing and systematic verification.
</role>

<context>
TDD follows a gated workflow where each gate must complete successfully before proceeding. Tests become contracts that define expected behavior.

The architecture uses established wrappers described in <architecture> below. Code conventions follow the patterns in <conventions>.
</context>

<critical_notes>
Gates are sequential - each gate builds on the previous one's success
Tests are contracts - once committed, they define the expected behavior
Behavioral testing - test what the system does, how users interact with it
Use established APIs - leverage existing abstractions for external services
Generalization pressure - comprehensive test cases ensure robust solutions
Clean workspace - organize temporary files in .claude/workspace/
</critical_notes>

<workflow>
## Phase 1: Understanding

<instructions>
Explore and understand what needs to be built. Consider:
- How does this feature fit the existing architecture?
- Which modules and patterns should I follow?
- What are different implementation approaches?
- What's the most maintainable design?
- Which existing code can serve as reference?
</instructions>

## Phase 2: Gated Implementation

### Gate 1 — Write Failing Tests

<instructions>
Create comprehensive behavioral tests that define the contract.
- Identify or create test files following existing patterns
- Write tests covering happy path, boundaries, and error conditions
- Use fakes/wrappers for determinism
- Ensure tests are behavioral - implementation changes won't break them
- Expected: All new tests fail with meaningful errors
</instructions>

### Gate 2 — Verify Tests Fail

<instructions>
Confirm tests fail appropriately before proceeding.
Run: pytest [specific_test_files] -xvs
Verify:
- All new tests fail with meaningful error messages
- Existing tests remain unmodified and passing
- Failures indicate missing functionality
</instructions>

### Gate 3 — Commit Failing Tests

<instructions>
Lock in the test contract with:
git add [test_files]
git commit -m "test: add failing tests for [feature] (TDD Gate 3)"
</instructions>

<critical_notes>
Tests are now immutable - they define the contract
</critical_notes>

### Gate 4 — Make Tests Pass

<instructions>
Implement minimal solution that satisfies all tests.
- Write minimal code to pass tests
- Keep tests unchanged
- Run: pytest [test_files] -xvs
- Launch overfit-verifier agent to ensure generalization
- Expected: All tests pass with general solution
</instructions>

### Gate 5 — Document

<instructions>
Launch doc-drafter agent to update API docs, README, CHANGELOG, and docstrings.
</instructions>

### Gate 6 — Final Review

<instructions>
Run these checks in parallel:
- Launch code-reviewer agent for quality check
- Run ruff check . && ruff format . for linting
- Run pytest --cov --cov-report=term-missing for coverage
- Verify coverage meets requirements (>80%)
</instructions>
</workflow>

<examples>
<example>
Feature: Add a new CLI command to list all active workflows

<thinking>
I need to understand the existing CLI structure first. Let me explore:
1. How are current CLI commands structured in cosmos_workflow/cli/?
2. What's the pattern for database queries in services/?
3. What behavioral tests would verify this feature works correctly?

Looking at existing commands, I see they use Click framework and call CosmosAPI methods. The list command should query active workflows and display them in a structured format.
</thinking>

Gate 1 - Writing failing behavioral tests in tests/integration/test_cli_workflows.py:
```python
def test_list_active_workflows_shows_running_workflows():
    """Test that users can see their active workflows."""
    # Arrange - Set up test data through public API
    api = CosmosAPI(test_config)
    prompt_id = api.create_prompt("test prompt", "/test/videos")
    run_id = api.execute_inference(prompt_id)

    # Act - User runs the command
    result = runner.invoke(cli, ['list', '--active'])

    # Assert - Verify user-observable behavior
    assert result.exit_code == 0
    # Parse the structured output (JSON or table)
    output_data = parse_cli_output(result.output)
    assert len(output_data) >= 1
    active_run = next(r for r in output_data if r['id'] == run_id)
    assert active_run['status'] in ['running', 'pending']

def test_list_workflows_when_none_exist():
    """Test that users get helpful message when no workflows exist."""
    # Arrange - Ensure clean state
    api = CosmosAPI(test_config)
    api.clear_test_data()

    # Act
    result = runner.invoke(cli, ['list', '--active'])

    # Assert - Verify helpful user feedback
    assert result.exit_code == 0
    assert "no active workflows" in result.output.lower()

def test_list_workflows_recovers_from_connection_issues():
    """Test that temporary connection issues are handled gracefully."""
    # Arrange - Use test double that simulates network issues
    with FlakyNetworkSimulator(failure_rate=0.5, max_retries=3):
        api = CosmosAPI(test_config)
        api.create_prompt("test", "/test/videos")

        # Act - Command should retry internally
        result = runner.invoke(cli, ['list', '--active'])

        # Assert - User sees results despite network issues
        assert result.exit_code == 0
        output_data = parse_cli_output(result.output)
        assert len(output_data) >= 0  # Success even with flaky network
```

Gate 2 - Verify tests fail:
Running: pytest tests/integration/test_cli_workflows.py -xvs
All tests fail - command doesn't exist yet.

Gate 3 - Commit: git commit -m "test: add failing tests for list active workflows command (TDD Gate 3)"

Gate 4 - Implementation focuses on behavior, not specific format.

Tests now verify behavior through public APIs without coupling to implementation.
</example>

<example>
Feature: Implement retry logic for failed GPU executions

<thinking>
This is a resilience feature. I need to:
1. Understand how GPU executions currently fail in execution/gpu_executor.py
2. Design behavioral tests that verify retry behavior without testing implementation
3. Consider edge cases: successful retry, exhausted retries, non-retryable errors

The tests should verify user-observable outcomes, not internal mechanics.
</thinking>

Gate 1 - Writing behavioral tests for retry logic:
```python
def test_gpu_execution_succeeds_despite_transient_failures():
    """Test that transient GPU failures don't prevent successful execution."""
    # Arrange - Use test double that simulates transient failures
    gpu_simulator = FakeGPUExecutor(
        failure_pattern=[GPUMemoryError(), GPUMemoryError(), Success()]
    )
    api = CosmosAPI(test_config, gpu_executor=gpu_simulator)

    # Act - Execute inference (retries handled internally)
    prompt_id = api.create_prompt("test", "/videos")
    result = api.execute_inference(prompt_id)

    # Assert - Verify successful completion despite failures
    assert result['status'] == 'completed'
    assert result['output_path'].exists()
    # User doesn't care about retry count - they care about success

def test_gpu_execution_fails_after_persistent_errors():
    """Test that persistent failures eventually fail the job."""
    # Arrange - Simulate persistent GPU issues
    gpu_simulator = FakeGPUExecutor(
        failure_pattern=[GPUMemoryError()] * 10  # Always fails
    )
    api = CosmosAPI(test_config, gpu_executor=gpu_simulator)

    # Act & Assert - Job should fail with clear error
    prompt_id = api.create_prompt("test", "/videos")
    with pytest.raises(ExecutionFailedError) as exc:
        api.execute_inference(prompt_id, timeout=30)

    assert "gpu memory" in str(exc.value).lower()
    assert exc.value.retriable is True  # Indicates transient issue

def test_gpu_execution_fails_immediately_for_configuration_errors():
    """Test that config errors fail fast without retries."""
    # Arrange - Invalid model configuration
    gpu_simulator = FakeGPUExecutor(
        failure_pattern=[ModelNotFoundError("model.ckpt")]
    )
    api = CosmosAPI(test_config, gpu_executor=gpu_simulator)

    # Act & Assert - Should fail immediately
    prompt_id = api.create_prompt("test", "/videos")
    start_time = time.time()

    with pytest.raises(ConfigurationError) as exc:
        api.execute_inference(prompt_id)

    elapsed = time.time() - start_time
    assert elapsed < 2  # Failed fast, no retries
    assert "model.ckpt" in str(exc.value)
    assert exc.value.retriable is False  # Not retriable

def test_gpu_execution_respects_timeout_during_retries():
    """Test that retries respect overall timeout constraints."""
    # Arrange - Slow GPU that will exceed timeout
    gpu_simulator = FakeGPUExecutor(
        failure_pattern=[GPUMemoryError()],
        recovery_time=15  # Each retry takes 15 seconds
    )
    api = CosmosAPI(test_config, gpu_executor=gpu_simulator)

    # Act & Assert - Should timeout before exhausting retries
    prompt_id = api.create_prompt("test", "/videos")
    with pytest.raises(TimeoutError) as exc:
        api.execute_inference(prompt_id, timeout=10)

    assert "timeout" in str(exc.value).lower()
```

Gate 2 - All tests fail - retry behavior doesn't exist
Gate 3 - Commit failing tests as contract
Gate 4 - Implement retry logic that satisfies behavioral requirements
</example>

<example>
Feature: Add container health monitoring to track GPU utilization

<thinking>
Health monitoring needs to:
1. Track GPU metrics during execution without affecting performance
2. Store metrics for analysis and debugging
3. Alert users when thresholds are exceeded

I'll focus on behavioral tests that verify observable monitoring outcomes.
</thinking>

Gate 1 - Writing behavioral tests for health monitoring:
```python
def test_execution_with_monitoring_captures_gpu_metrics():
    """Test that GPU metrics are available after monitored execution."""
    # Arrange - Configure monitoring thresholds
    config = test_config.with_monitoring(gpu_threshold=90)
    api = CosmosAPI(config)

    # Act - Run inference with monitoring enabled
    prompt_id = api.create_prompt("test", "/videos")
    run_id = api.execute_inference(prompt_id, enable_monitoring=True)
    api.wait_for_completion(run_id)

    # Assert - Metrics are available for analysis
    metrics = api.get_execution_metrics(run_id)
    assert metrics['peak_gpu_utilization'] > 0
    assert metrics['average_gpu_utilization'] > 0
    assert metrics['total_gpu_memory_used'] > 0
    assert 'metrics_timeline' in metrics  # For detailed analysis

def test_monitoring_alerts_on_threshold_violations():
    """Test that users are notified when GPU usage exceeds thresholds."""
    # Arrange - Set low threshold to trigger alerts
    config = test_config.with_monitoring(gpu_threshold=50)
    api = CosmosAPI(config)

    # Act - Run GPU-intensive task
    prompt_id = api.create_prompt("complex_prompt", "/videos")
    run_id = api.execute_inference(prompt_id, enable_monitoring=True)

    # Assert - Check for threshold alerts
    result = api.wait_for_completion(run_id)
    alerts = api.get_alerts(run_id)

    assert len(alerts) > 0
    assert any('gpu threshold exceeded' in alert['message'].lower()
               for alert in alerts)
    # Result still succeeds - monitoring doesn't break execution
    assert result['status'] == 'completed'

def test_monitoring_disabled_has_no_performance_impact():
    """Test that disabled monitoring doesn't affect execution time."""
    api = CosmosAPI(test_config)
    prompt_id = api.create_prompt("test", "/videos")

    # Measure execution without monitoring
    start = time.time()
    run_id_no_monitor = api.execute_inference(prompt_id, enable_monitoring=False)
    api.wait_for_completion(run_id_no_monitor)
    time_without = time.time() - start

    # Measure execution with monitoring
    start = time.time()
    run_id_monitor = api.execute_inference(prompt_id, enable_monitoring=True)
    api.wait_for_completion(run_id_monitor)
    time_with = time.time() - start

    # Assert - Performance impact is negligible (< 5%)
    assert time_with < time_without * 1.05

def test_monitoring_survives_container_restart():
    """Test that monitoring handles container lifecycle changes."""
    # Arrange - Use simulator that restarts container mid-execution
    docker_sim = FakeDockerExecutor(restart_after_seconds=5)
    api = CosmosAPI(test_config, docker_executor=docker_sim)

    # Act - Long-running task with container restart
    prompt_id = api.create_prompt("long_task", "/videos")
    run_id = api.execute_inference(prompt_id, enable_monitoring=True)
    result = api.wait_for_completion(run_id)

    # Assert - Monitoring captured metrics despite restart
    metrics = api.get_execution_metrics(run_id)
    assert result['status'] == 'completed'
    assert metrics['container_restarts'] == 1
    assert metrics['total_gpu_memory_used'] > 0  # Still collected metrics

def test_metrics_queryable_after_execution():
    """Test that historical metrics can be queried for analysis."""
    api = CosmosAPI(test_config)

    # Run multiple executions
    run_ids = []
    for i in range(3):
        prompt_id = api.create_prompt(f"test_{i}", "/videos")
        run_id = api.execute_inference(prompt_id, enable_monitoring=True)
        api.wait_for_completion(run_id)
        run_ids.append(run_id)

    # Query aggregate metrics
    stats = api.get_execution_statistics(
        start_date=datetime.now() - timedelta(hours=1)
    )

    assert stats['total_executions'] >= 3
    assert stats['average_gpu_utilization'] > 0
    assert all(rid in stats['execution_ids'] for rid in run_ids)
```

Gate 2 - Verify all monitoring tests fail
Gate 3 - Commit the test contract
Gate 4 - Implement monitoring that satisfies behavioral requirements
</example>
</examples>

<completion_checklist>
Before marking complete, verify:
- All 6 gates passed successfully
- Tests cover all behavioral requirements
- Implementation is general, not overfitted
- Documentation is updated
- Code passes review, lint, and coverage
- Temporary files cleaned from .claude/workspace/
- Final implementation committed
- ROADMAP.md updated if feature is complete
</completion_checklist>

<task>
Implement the following feature using the TDD workflow described in <workflow>:
$ARGUMENTS
</task>