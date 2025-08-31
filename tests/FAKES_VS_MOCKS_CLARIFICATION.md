# Fakes vs Mocks: The Real Difference

## You're Right - I Was Confusing the Issue

The problem isn't "fakes vs mocks" - it's **WHAT you're replacing**.

## The Key Distinction

### Mocks vs Fakes (for External Dependencies)
Both replace **external dependencies** (SSH, databases, APIs):

```python
# MOCK - You configure expected behavior
mock_ssh = Mock()
mock_ssh.exec_command.return_value = (0, "success", "")

# FAKE - Pre-built realistic behavior
fake_ssh = FakeSSHClient()  # Has built-in realistic responses
```

**Both are fine for external dependencies!** Fakes are often better because they're more realistic.

### The REAL Problem: What Are You Replacing?

```python
# ❌ BAD - Replacing YOUR OWN CODE with fake/mock
def test_with_fake_of_your_code():
    orchestrator = FakeWorkflowOrchestrator()  # NOT testing your code!
    
# ❌ BAD - Same problem with mock
def test_with_mock_of_your_code():
    orchestrator = Mock(spec=WorkflowOrchestrator)  # NOT testing your code!
    
# ✅ GOOD - Testing YOUR REAL CODE, only faking/mocking externals
def test_your_real_code():
    orchestrator = WorkflowOrchestrator()  # YOUR REAL CODE
    orchestrator.ssh_client = FakeSSHClient()  # Fake only the external part
```

## Why People Say "Fakes > Mocks"

They're talking about **external dependencies**, not your own code:

### Mock Problems (for externals)
```python
# Mock - You have to specify everything
mock_ssh.exec_command.return_value = (0, "success", "")
mock_ssh.connect.return_value = None
mock_ssh.close.return_value = None
# Easy to miss something, unrealistic behavior
```

### Fake Advantages (for externals)
```python
# Fake - Behaves like real SSH
class FakeSSHClient:
    def connect(self, hostname, username, key_filename):
        if not hostname:
            raise ValueError("Hostname required")  # Realistic!
        self.connected = True
    
    def exec_command(self, cmd):
        if not self.connected:
            raise RuntimeError("Not connected")  # Realistic!
        return (0, f"Executed: {cmd}", "")
```

## The Confusion in My Previous Explanation

I incorrectly suggested the problem was:
- "Fakes bad, mocks good"

The ACTUAL problem was:
- You were faking **your own WorkflowOrchestrator** instead of testing it
- Whether you use fake or mock for **external dependencies** is a separate choice

## The Correct Testing Strategy

### 1. Always Use Your Real Code
```python
orchestrator = WorkflowOrchestrator()  # REAL
validator = PromptValidator()  # REAL
executor = DockerExecutor()  # REAL
```

### 2. Replace Only External Dependencies
```python
# Option A: Use Fakes (often better)
orchestrator.ssh_client = FakeSSHClient()
orchestrator.docker_client = FakeDockerClient()

# Option B: Use Mocks (sometimes easier)
orchestrator.ssh_client = Mock(spec=SSHClient)
orchestrator.docker_client = Mock(spec=DockerClient)
```

### 3. The Test Looks Like This
```python
def test_workflow_orchestrator():
    # Your REAL orchestrator
    orchestrator = WorkflowOrchestrator()
    
    # With fake/mock external dependencies
    orchestrator.ssh_client = FakeSSHClient()  # or Mock()
    
    # Now you're testing YOUR code with controlled externals
    result = orchestrator.run_workflow(spec)
    assert result.status == "completed"
```

## Example: Both Approaches Work

### Approach 1: Real Code + Fake Externals
```python
def test_with_fake_ssh():
    orchestrator = WorkflowOrchestrator()  # REAL
    orchestrator.ssh_client = FakeSSHClient()  # FAKE external
    
    result = orchestrator.run_workflow(spec)
    # Tests your real validation, retry logic, etc.
    assert result.status == "completed"
```

### Approach 2: Real Code + Mock Externals  
```python
def test_with_mock_ssh():
    orchestrator = WorkflowOrchestrator()  # REAL
    orchestrator.ssh_client = Mock()  # MOCK external
    orchestrator.ssh_client.exec_command.return_value = (0, "success", "")
    
    result = orchestrator.run_workflow(spec)
    # Tests your real validation, retry logic, etc.
    assert result.status == "completed"
```

**Both test your real code!** The fake vs mock choice is just about how you simulate SSH.

## The Bottom Line

1. **Always test your real code** (WorkflowOrchestrator, etc.)
2. **Replace external dependencies** (SSH, Docker, APIs)
3. **Fakes are usually better than mocks** for the external parts (more realistic)
4. **The problem in the refactored tests** was faking WorkflowOrchestrator itself

You were right to question my explanation. The issue isn't "fakes bad" - it's "don't fake your own code that you're trying to test."