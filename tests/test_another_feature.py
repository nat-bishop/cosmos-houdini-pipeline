"""Test for a user authentication feature."""


def test_validate_email():
    """Test email validation."""
    from cosmos_workflow.auth import validate_email

    assert validate_email("user@example.com") is True
    assert validate_email("invalid-email") is False
