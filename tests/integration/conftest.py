"""Integration test configuration.

Integration tests verify component interactions with mocked external dependencies.
Some tests remain as examples for future infrastructure testing needs.

Removed tests (2025-08-31):
- test_workflow_orchestration.py - Used outdated architecture methods
- test_workflow_orchestration_refactored.py - Used outdated architecture
- test_prompt_smart_naming.py - Used outdated CLI structure

Remaining tests:
- SFTP workflow tests - Partially working, good examples for future
- Upsample integration - Working examples of integration patterns
- AI functionality - Examples of mocking complex dependencies
"""

import pytest

# Mark all tests in this directory as integration tests
pytestmark = pytest.mark.integration
