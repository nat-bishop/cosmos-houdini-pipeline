"""Performance test configuration.

Performance tests are marked as optional by default since they:
1. Require CUDA for GPU performance tests
2. Test deterministic execution which needs actual torch/numpy setup
3. Are meant for benchmarking, not regular testing

To run performance tests explicitly:
    pytest tests/performance/ -m "benchmark and optional"

These tests should be run when:
- Performance regression testing is needed
- Benchmarking changes to the codebase
- Validating GPU/CUDA functionality
"""

import pytest

# Mark all tests in this directory as optional
pytestmark = [pytest.mark.benchmark, pytest.mark.optional]
