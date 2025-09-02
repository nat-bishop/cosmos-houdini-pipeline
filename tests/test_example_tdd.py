"""Example TDD test to demonstrate workflow."""

import pytest


def test_calculate_tokens():
    """Test token calculation for video generation."""
    from cosmos_workflow.utils import calculate_tokens

    # Basic calculation
    assert calculate_tokens(320, 180, 2) == pytest.approx(1990.08, rel=0.01)

    # Edge cases
    assert calculate_tokens(0, 0, 0) == 0
    assert calculate_tokens(1920, 1080, 16) == pytest.approx(573833.28, rel=0.01)

    # Negative values should raise ValueError
    with pytest.raises(ValueError, match="dimensions must be positive"):
        calculate_tokens(-1, 100, 2)
