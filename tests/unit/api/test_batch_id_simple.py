"""Test batch_id in execution config - simplified version."""

from cosmos_workflow.api.cosmos_api import CosmosAPI


class TestBatchIdSimple:
    """Test batch_id generation and format."""

    def test_generate_batch_id_format(self):
        """Test that _generate_batch_id creates proper UUID-based IDs."""
        # Generate several batch IDs
        batch_ids = [CosmosAPI._generate_batch_id() for _ in range(5)]

        for batch_id in batch_ids:
            # Check format: batch_{16_hex_chars}
            assert batch_id.startswith("batch_")
            unique_part = batch_id[6:]  # Remove "batch_" prefix

            # Should be 16 hex characters
            assert len(unique_part) == 16
            assert all(c in "0123456789abcdef" for c in unique_part)

        # All IDs should be unique
        assert len(set(batch_ids)) == len(batch_ids)

    def test_batch_id_uniqueness(self):
        """Test that batch IDs are truly unique."""
        # Generate a large number of IDs
        batch_ids = [CosmosAPI._generate_batch_id() for _ in range(1000)]

        # All should be unique
        assert len(set(batch_ids)) == 1000

    def test_build_execution_config_no_batch_id(self):
        """Test that regular execution config doesn't have batch_id."""
        config = CosmosAPI._build_execution_config()

        # Should have standard fields
        assert "num_steps" in config
        assert "guidance" in config
        assert "seed" in config

        # Should NOT have batch_id
        assert "batch_id" not in config
