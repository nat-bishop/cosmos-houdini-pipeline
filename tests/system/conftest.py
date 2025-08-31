"""System test configuration.

All system tests are marked as optional by default since they:
1. Require actual NVIDIA Cosmos model
2. Need real GPU and Docker infrastructure
3. Are meant as smoke tests for production deployment
4. Not suitable for regular CI/CD

To run system tests explicitly:
    pytest tests/system/ -m "system and optional"

These tests should only be run in production-like environments.
"""

import pytest

# Mark all tests in this directory as optional
pytestmark = [pytest.mark.system, pytest.mark.optional]
