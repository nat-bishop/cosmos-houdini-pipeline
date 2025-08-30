#!/usr/bin/env python3
"""
Tests for the CLI interface.
"""

import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

from cosmos_workflow.cli import (
    setup_logging,
    validate_prompt_file,
    run_full_cycle,
    run_inference_only,
    run_upscaling_only,
    check_status,
    create_prompt_spec,
    create_run_spec,
    main
)
from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec


class TestCLIHelpers:
    """Test CLI helper functions."""
    
    def test_setup_logging_normal(self):
        """Test normal logging setup."""
        with patch('cosmos_workflow.cli.logging.basicConfig') as mock_config:
            setup_logging(verbose=False)
            mock_config.assert_called_once()
            args = mock_config.call_args[1]
            assert args['level'] == 20  # INFO level
    
    def test_setup_logging_verbose(self):
        """Test verbose logging setup."""
        with patch('cosmos_workflow.cli.logging.basicConfig') as mock_config:
            setup_logging(verbose=True)
            mock_config.assert_called_once()
            args = mock_config.call_args[1]
            assert args['level'] == 10  # DEBUG level
    
    def test_validate_prompt_file_exists(self):
        """Test validating existing prompt file."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.close()  # Close the file before validating
            try:
                result = validate_prompt_file(str(tmp_path))
                assert result == tmp_path
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
    
    def test_validate_prompt_file_not_exists(self):
        """Test validating non-existent prompt file."""
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            validate_prompt_file("non_existent_file.json")


class TestRunCommands:
    """Test run commands."""
    
    @patch('cosmos_workflow.cli.WorkflowOrchestrator')
    @patch('cosmos_workflow.cli.setup_logging')
    def test_run_full_cycle_success(self, mock_logging, mock_orchestrator_class):
        """Test successful full cycle run."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_full_cycle.return_value = {"status": "success"}
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
            tmp_path = Path(tmp.name)
            
            run_full_cycle(
                prompt_file=tmp_path,
                videos_subdir="test_videos",
                no_upscale=False,
                upscale_weight=0.5,
                num_gpu=2,
                cuda_devices="0,1",
                verbose=True
            )
            
            mock_orchestrator.run_full_cycle.assert_called_once_with(
                prompt_file=tmp_path,
                videos_subdir="test_videos",
                no_upscale=False,
                upscale_weight=0.5,
                num_gpu=2,
                cuda_devices="0,1"
            )
    
    @patch('cosmos_workflow.cli.WorkflowOrchestrator')
    @patch('cosmos_workflow.cli.setup_logging')
    def test_run_full_cycle_failure(self, mock_logging, mock_orchestrator_class):
        """Test full cycle run with failure."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_full_cycle.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
            tmp_path = Path(tmp.name)
            
            with pytest.raises(SystemExit) as exc_info:
                run_full_cycle(
                    prompt_file=tmp_path,
                    videos_subdir=None,
                    no_upscale=True,
                    upscale_weight=0.5,
                    num_gpu=1,
                    cuda_devices="0",
                    verbose=False
                )
            
            assert exc_info.value.code == 1
    
    @patch('cosmos_workflow.cli.WorkflowOrchestrator')
    @patch('cosmos_workflow.cli.setup_logging')
    def test_run_inference_only_success(self, mock_logging, mock_orchestrator_class):
        """Test successful inference only run."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_inference_only.return_value = {"status": "success"}
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
            tmp_path = Path(tmp.name)
            
            run_inference_only(
                prompt_file=tmp_path,
                videos_subdir="test_videos",
                num_gpu=1,
                cuda_devices="0",
                verbose=False
            )
            
            mock_orchestrator.run_inference_only.assert_called_once()
    
    @patch('cosmos_workflow.cli.WorkflowOrchestrator')
    @patch('cosmos_workflow.cli.setup_logging')
    def test_run_upscaling_only_success(self, mock_logging, mock_orchestrator_class):
        """Test successful upscaling only run."""
        mock_orchestrator = Mock()
        mock_orchestrator.run_upscaling_only.return_value = {"status": "success"}
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
            tmp_path = Path(tmp.name)
            
            run_upscaling_only(
                prompt_file=tmp_path,
                upscale_weight=0.7,
                num_gpu=1,
                cuda_devices="0",
                verbose=False
            )
            
            mock_orchestrator.run_upscaling_only.assert_called_once()


class TestStatusCommand:
    """Test status command."""
    
    @patch('cosmos_workflow.cli.WorkflowOrchestrator')
    @patch('cosmos_workflow.cli.setup_logging')
    def test_check_status_connected(self, mock_logging, mock_orchestrator_class):
        """Test status check when connected."""
        mock_orchestrator = Mock()
        mock_orchestrator.check_remote_status.return_value = {
            'ssh_status': 'connected',
            'remote_directory': '/home/ubuntu/cosmos',
            'remote_directory_exists': True,
            'docker_status': {
                'docker_running': True,
                'available_images': ['cosmos:latest'],
                'running_containers': ['cosmos_container']
            }
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        check_status(verbose=True)
        mock_orchestrator.check_remote_status.assert_called_once()
    
    @patch('cosmos_workflow.cli.WorkflowOrchestrator')
    @patch('cosmos_workflow.cli.setup_logging')
    def test_check_status_disconnected(self, mock_logging, mock_orchestrator_class):
        """Test status check when disconnected."""
        mock_orchestrator = Mock()
        mock_orchestrator.check_remote_status.return_value = {
            'ssh_status': 'disconnected',
            'error': 'Connection refused'
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        check_status(verbose=False)
        mock_orchestrator.check_remote_status.assert_called_once()


class TestCreateCommands:
    """Test create commands."""
    
    # These integration tests would require more complex mocking of the entire
    # create flow, which is better tested at the integration level
    pass


class TestMainFunction:
    """Test main CLI function."""
    
    @patch('sys.argv', ['cli.py'])
    def test_main_no_command(self):
        """Test main with no command."""
        with patch('cosmos_workflow.cli.argparse.ArgumentParser.print_help') as mock_help:
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            mock_help.assert_called_once()
            assert exc_info.value.code == 1
    
    @patch('sys.argv', ['cli.py', 'run', 'test.json'])
    @patch('cosmos_workflow.cli.validate_prompt_file')
    @patch('cosmos_workflow.cli.run_full_cycle')
    def test_main_run_command(self, mock_run, mock_validate):
        """Test main with run command."""
        mock_validate.return_value = Path("test.json")
        
        main()
        
        mock_validate.assert_called_once_with("test.json")
        mock_run.assert_called_once()
    
    @patch('sys.argv', ['cli.py', 'inference', 'test.json', '--num-gpu', '2'])
    @patch('cosmos_workflow.cli.validate_prompt_file')
    @patch('cosmos_workflow.cli.run_inference_only')
    def test_main_inference_command(self, mock_inference, mock_validate):
        """Test main with inference command."""
        mock_validate.return_value = Path("test.json")
        
        main()
        
        mock_validate.assert_called_once_with("test.json")
        mock_inference.assert_called_once()
        call_args = mock_inference.call_args[1]
        assert call_args['num_gpu'] == 2
    
    @patch('sys.argv', ['cli.py', 'upscale', 'test.json', '--upscale-weight', '0.7'])
    @patch('cosmos_workflow.cli.validate_prompt_file')
    @patch('cosmos_workflow.cli.run_upscaling_only')
    def test_main_upscale_command(self, mock_upscale, mock_validate):
        """Test main with upscale command."""
        mock_validate.return_value = Path("test.json")
        
        main()
        
        mock_validate.assert_called_once_with("test.json")
        mock_upscale.assert_called_once()
        call_args = mock_upscale.call_args[1]
        assert call_args['upscale_weight'] == 0.7
    
    @patch('sys.argv', ['cli.py', 'status', '--verbose'])
    @patch('cosmos_workflow.cli.check_status')
    def test_main_status_command(self, mock_status):
        """Test main with status command."""
        main()
        
        mock_status.assert_called_once_with(True)
    
    @patch('sys.argv', ['cli.py', 'create-spec', 'test_shot', 'Test prompt'])
    @patch('cosmos_workflow.cli.create_prompt_spec')
    def test_main_create_spec_command(self, mock_create):
        """Test main with create-spec command."""
        main()
        
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        assert call_args['name'] == 'test_shot'
        assert call_args['prompt_text'] == 'Test prompt'
    
    @patch('sys.argv', ['cli.py', 'create-run', 'prompt.json', '--weights', '0.3', '0.3', '0.2', '0.2'])
    @patch('cosmos_workflow.cli.create_run_spec')
    def test_main_create_run_command(self, mock_create):
        """Test main with create-run command."""
        main()
        
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        assert call_args['prompt_spec_path'] == 'prompt.json'
        assert call_args['control_weights'] == [0.3, 0.3, 0.2, 0.2]
    
    @patch('sys.argv', ['cli.py', 'run', 'test.json'])
    @patch('cosmos_workflow.cli.validate_prompt_file')
    @patch('cosmos_workflow.cli.run_full_cycle')
    def test_main_keyboard_interrupt(self, mock_run, mock_validate):
        """Test main with keyboard interrupt."""
        mock_validate.return_value = Path("test.json")
        mock_run.side_effect = KeyboardInterrupt()
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
    
    @patch('sys.argv', ['cli.py', 'run', 'test.json', '--verbose'])
    @patch('cosmos_workflow.cli.validate_prompt_file')
    @patch('cosmos_workflow.cli.run_full_cycle')
    def test_main_unexpected_error_verbose(self, mock_run, mock_validate):
        """Test main with unexpected error in verbose mode."""
        mock_validate.return_value = Path("test.json")
        mock_run.side_effect = Exception("Unexpected error")
        
        with pytest.raises(SystemExit) as exc_info:
            with patch('traceback.print_exc'):
                main()
        
        assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__])