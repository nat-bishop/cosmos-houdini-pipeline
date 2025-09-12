"""Test to verify CLI tests are properly isolated and don't affect production database."""

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli


class TestCLIIsolation:
    """Verify that CLI tests don't create real database entries."""
    
    @pytest.fixture
    def db_path(self):
        """Get the production database path."""
        return Path("outputs/cosmos.db")
    
    @pytest.fixture
    def get_counts(self, db_path):
        """Helper to get database counts."""
        def _get_counts():
            if not db_path.exists():
                return {"prompts": 0, "runs": 0}
            
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM prompts")
            prompt_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM runs")
            run_count = cur.fetchone()[0]
            
            conn.close()
            return {"prompts": prompt_count, "runs": run_count}
        
        return _get_counts
    
    def test_create_prompt_with_mock_does_not_affect_database(self, mock_cli_context, get_counts):
        """Verify that creating a prompt with mocking doesn't affect the real database."""
        # Get counts before
        counts_before = get_counts()
        
        # Run a CLI command that would normally create a database entry
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a test video directory
            video_dir = Path("test_videos")
            video_dir.mkdir()
            (video_dir / "color.mp4").write_text("mock video")
            
            # Run the command
            result = runner.invoke(
                cli, 
                ["create", "prompt", "test isolation prompt", str(video_dir)]
            )
            
            # Command should succeed (with mock)
            assert result.exit_code == 0
        
        # Get counts after
        counts_after = get_counts()
        
        # Verify no changes to database
        assert counts_after["prompts"] == counts_before["prompts"], \
            f"Prompt count changed from {counts_before['prompts']} to {counts_after['prompts']}"
        assert counts_after["runs"] == counts_before["runs"], \
            f"Run count changed from {counts_before['runs']} to {counts_after['runs']}"
    
    def test_multiple_cli_commands_remain_isolated(self, mock_cli_context, get_counts):
        """Test that multiple CLI operations remain isolated from the database."""
        counts_before = get_counts()
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create test directory
            video_dir = Path("videos")
            video_dir.mkdir()
            (video_dir / "color.mp4").write_text("mock")
            
            # Run multiple commands that would normally affect the database
            for i in range(5):
                result = runner.invoke(
                    cli,
                    ["create", "prompt", f"test prompt {i}", str(video_dir)]
                )
                assert result.exit_code == 0
        
        counts_after = get_counts()
        
        # Database should be unchanged
        assert counts_after["prompts"] == counts_before["prompts"]
        assert counts_after["runs"] == counts_before["runs"]
    
    def test_cli_without_mock_would_affect_database(self, db_path):
        """Document that CLI without mocking WOULD affect the database.
        
        This test is skipped by default to avoid polluting the database.
        It exists to document the expected behavior without mocking.
        """
        pytest.skip("This test would pollute the database - skipping to maintain isolation")
        
        # This is what would happen WITHOUT the mock:
        # runner = CliRunner()
        # result = runner.invoke(cli, ["create", "prompt", "real prompt", "videos/"])
        # # This would create a real database entry!