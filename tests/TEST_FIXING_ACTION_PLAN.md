# Action Plan: Fix Tests to Actually Catch Bugs

## The Verdict
**The test refactoring was a mistake for your needs.** The behavior-testing approach with fakes is completely wrong for a solo developer using AI to code quickly. You need tests that actually verify your code works.

## Quick Fixes (Do These First)

### 1. Revert the Three Refactored Test Files
```bash
# These files were better before refactoring:
git checkout HEAD~2 -- tests/integration/test_workflow_orchestration.py
git checkout HEAD~2 -- tests/integration/test_docker_executor.py  
git checkout HEAD~2 -- tests/integration/test_sftp_workflow.py
```

The original tests with mocks actually tested your real code. They may have been "brittle" but they would catch bugs!

### 2. Keep the Contract Tests
The contract tests are still useful to ensure any fakes match reality:
```bash
# Keep this - it's valuable:
tests/contracts/test_fake_contracts.py
```

### 3. Fix the Integration Tests That Are Failing
Focus on making the existing 547/560 tests pass. These tests use real implementations and will actually catch bugs.

## New Testing Rules for Your Project

### Rule 1: Test Real Code
```python
# ❌ WRONG for your needs:
def test_with_fake(fake_orchestrator):
    result = fake_orchestrator.run()  # Tests nothing!

# ✅ RIGHT for your needs:
def test_with_real(real_orchestrator, mock_ssh):
    result = real_orchestrator.run()  # Tests actual code!
```

### Rule 2: Mock Only What You Must
```python
# Mock these (external boundaries):
- paramiko.SSHClient
- docker.from_env()  
- boto3.client()
- requests.get()
- datetime.now()  # For deterministic tests

# DON'T mock these (your code):
- WorkflowOrchestrator
- PromptValidator
- DockerExecutor (except its SSH client)
- Your business logic
- Your error handling
```

### Rule 3: Mutation Score is Your North Star
- Run mutation testing regularly
- Target 80%+ kill rate
- If mutations survive, add tests to kill them
- This proves your tests actually work

## Practical Test Template for Your Project

```python
import pytest
from unittest.mock import Mock, patch
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

class TestWorkflowOrchestratorIntegration:
    """Integration tests that actually catch bugs."""
    
    @pytest.fixture
    def mock_ssh(self):
        """Mock only the SSH boundary."""
        mock = Mock()
        mock.exec_command.return_value = (0, "success", "")
        mock.open_sftp.return_value = Mock()  # Mock SFTP
        return mock
    
    @pytest.fixture
    def real_orchestrator(self, mock_ssh):
        """Real orchestrator with mocked SSH."""
        with patch('paramiko.SSHClient') as mock_client:
            mock_client.return_value = mock_ssh
            
            # Use REAL implementation
            orch = WorkflowOrchestrator({
                'ssh': {'host': 'test', 'user': 'test'},
                'docker': {'image': 'test:latest'}
            })
            yield orch
    
    def test_validation_logic_actually_works(self, real_orchestrator):
        """This WILL catch bugs in your validation."""
        # Test with invalid spec
        with pytest.raises(ValueError) as exc:
            real_orchestrator.validate_spec({})
        assert "prompt" in str(exc.value)
        
        # Test with valid spec  
        valid_spec = {
            "prompt": "test",
            "name": "test",
            "id": "test_001"
        }
        result = real_orchestrator.validate_spec(valid_spec)
        assert result is True
    
    def test_retry_mechanism_actually_retries(self, real_orchestrator, mock_ssh):
        """This WILL catch bugs in retry logic."""
        call_count = 0
        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network issue")
            return (0, "success", "")
        
        mock_ssh.exec_command.side_effect = side_effect
        
        # Should retry and eventually succeed
        result = real_orchestrator.run_with_retry("spec.json")
        assert result is True
        assert call_count == 3  # Proves retry logic worked
    
    def test_error_handling_actually_handles(self, real_orchestrator):
        """This WILL catch bugs in error handling."""
        with patch.object(real_orchestrator, 'load_spec') as mock_load:
            mock_load.side_effect = FileNotFoundError("Not found")
            
            result = real_orchestrator.run_workflow("missing.json")
            
            # Should handle gracefully
            assert result.status == "failed"
            assert "Not found" in result.error
```

## What to Do with Fakes

### Keep Fakes For:
1. **External services you can't test against**
   - Real SSH servers
   - Real Docker daemons
   - Production APIs
   
2. **Slow operations** (but make them realistic)
   - File uploads (simulate time)
   - Network requests (simulate latency)

### Use Fakes Correctly:
```python
class FakeSSHClient:
    """Fake for boundary we can't test."""
    def __init__(self):
        self.connected = False
        self.commands = []
    
    def connect(self, **kwargs):
        # Simulate REAL behavior
        if not kwargs.get('hostname'):
            raise ValueError("Hostname required")  # Like real SSH!
        self.connected = True
    
    def exec_command(self, cmd):
        if not self.connected:
            raise RuntimeError("Not connected")  # Like real SSH!
        self.commands.append(cmd)
        return (0, "success", "")
```

## The 80/20 Rule for Your Tests

### 80% - Integration Tests with Boundary Mocks
- Test real implementations
- Mock only external services
- High mutation scores
- Actually catch bugs

### 20% - Pure Unit Tests
- Test algorithms in isolation
- Test data transformations
- No mocks needed
- Very fast

### 0% - Behavior Tests with Full Fakes
- Don't waste time on these
- They don't catch bugs
- False sense of security

## Success Metrics

You'll know your tests are working when:

1. **Mutation score > 80%** on your core logic
2. **Tests fail when you break code** (try it!)
3. **Claude's mistakes get caught** by tests
4. **You feel confident** deploying after tests pass

## Next Steps

1. **Revert the refactored test files** (they were better before)
2. **Fix the 13 failing tests** to use real implementations  
3. **Run mutation testing** on the fixed tests
4. **Achieve 80%+ mutation score** by adding tests for surviving mutations
5. **Document the testing approach** in CLAUDE.md for future sessions

## The Bottom Line

For your use case (solo dev + AI coding):
- **Coupled tests that catch bugs > Decoupled tests that don't**
- **80% mutation score > 0% mutation score**  
- **Some mock usage > All fakes**
- **Brittle but effective > Flexible but useless**

Your instinct was correct - the tests need to actually catch issues in the code. The "best practice" I followed was wrong for your context.