# Simple Explanation: Fakes vs Real Code in Tests

## What Are Fakes?

A "fake" is a completely separate implementation that pretends to be your real code:

```python
# This is a FAKE - it's NOT your real code:
class FakeWorkflowOrchestrator:
    def run_workflow(self, spec):
        # This doesn't run ANY of your actual code!
        self.workflows_run.append(spec)
        return {"status": "completed"}

# This is your REAL code:
class WorkflowOrchestrator:
    def run_workflow(self, spec):
        # Your actual logic: validation, SSH, Docker, retry logic, etc.
        self.validate_spec(spec)
        self.connect_ssh()
        self.upload_files()
        self.run_docker_container()
        # ... 100 more lines of real logic
```

## The Problem: Fakes Don't Test Your Code!

When you test with a fake:
```python
def test_with_fake():
    fake = FakeWorkflowOrchestrator()  # NOT your real code
    result = fake.run_workflow("spec.json")
    assert result["status"] == "completed"
```

**This test passes even if your REAL WorkflowOrchestrator is completely broken!**

## What You Actually Want: Integration Tests with Real Code

```python
def test_with_real_code():
    # Use your REAL WorkflowOrchestrator
    orchestrator = WorkflowOrchestrator(config)
    
    # Only mock the parts you CAN'T test (external services)
    with mock.patch('paramiko.SSHClient') as mock_ssh:
        mock_ssh.return_value.exec_command.return_value = (0, "success", "")
        
        # This runs YOUR REAL CODE - validation, retry logic, everything!
        result = orchestrator.run_workflow("spec.json")
        
        # Now you're testing that YOUR CODE actually works
        assert result["status"] == "completed"
```

## Why This Matters for You

### With Fakes (BAD for your needs):
- ❌ Tests pass even if your code is broken
- ❌ Bugs in your validation logic? Tests won't catch them
- ❌ Retry logic broken? Tests won't know
- ❌ Claude introduces a bug? Tests pass anyway

### With Real Code + Boundary Mocks (GOOD for your needs):
- ✅ Tests fail if your code is broken
- ✅ Catches bugs in your validation logic
- ✅ Verifies retry logic actually works
- ✅ Claude's mistakes get caught

## Simple Rule for Your Project

**Use your REAL code in tests. Only mock things you can't control:**

```python
# Mock these (you can't control them):
- SSH connections (paramiko.SSHClient)
- Docker daemon (docker.from_env)
- File system (for speed)
- Network requests
- Current time (for deterministic tests)

# Use REAL code for these (your actual implementation):
- WorkflowOrchestrator
- DockerExecutor  
- PromptValidator
- All your business logic
- All your error handling
```

## Example: Testing Your Real Validation Logic

```python
def test_validation_actually_works():
    # Use REAL orchestrator with your REAL validation code
    orchestrator = WorkflowOrchestrator(test_config)
    
    # Test with invalid spec - your REAL validation should catch this
    with pytest.raises(ValueError) as exc:
        orchestrator.validate_spec({"missing": "prompt"})
    
    # If your validation logic has a bug, this test WILL fail
    assert "prompt is required" in str(exc.value)
```

If you used a fake, this test wouldn't verify anything about your actual validation logic!

## The Bottom Line

For your situation (solo dev using AI to code fast):
- **Don't use fakes** - they don't test your actual code
- **Use real implementations** - test what you actually wrote
- **Mock only external services** - things you can't control
- **Integration tests are your friend** - they catch real bugs

This gives you confidence that when tests pass, your code actually works!