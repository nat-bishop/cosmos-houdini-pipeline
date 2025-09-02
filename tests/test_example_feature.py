"""Test for a new calculate_discount feature that doesn't exist yet."""


def test_calculate_discount_basic():
    """Test basic discount calculation."""
    from cosmos_workflow.utils import calculate_discount

    # 10% discount on $100
    assert calculate_discount(100, 10) == 90


def test_calculate_discount_zero():
    """Test with zero discount."""
    from cosmos_workflow.utils import calculate_discount

    # No discount
    assert calculate_discount(100, 0) == 100


def test_calculate_discount_maximum():
    """Test with 100% discount."""
    from cosmos_workflow.utils import calculate_discount

    # Full discount
    assert calculate_discount(100, 100) == 0


def test_calculate_discount_invalid():
    """Test with invalid discount percentage."""
    from cosmos_workflow.utils import calculate_discount

    # Should raise ValueError for negative discount
    try:
        calculate_discount(100, -10)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid discount" in str(e)
