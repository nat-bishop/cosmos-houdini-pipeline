#!/usr/bin/env python3
"""
RunSpec management system for Cosmos-Transfer1 workflow.
Handles RunSpec creation, validation, and file operations.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
import json

from .schemas import RunSpec, PromptSpec, DirectoryManager, ExecutionStatus


class RunSpecManager:
    """Manages RunSpec creation, validation, and file operations."""
    
    def __init__(self, dir_manager: DirectoryManager):
        """Initialize RunSpec manager with directory manager."""
        self.dir_manager = dir_manager
    
    def create_run_spec(
        self,
        prompt_id: str,
        name: str,
        control_weights: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None
    ) -> RunSpec:
        """
        Create a new RunSpec for executing a prompt.
        
        Args:
            prompt_id: The PromptSpec ID to execute
            name: The run name
            control_weights: Optional custom control weights
            parameters: Optional custom parameters
            output_path: Optional custom output path
            
        Returns:
            RunSpec object
        """
        # Use defaults if not provided
        from .schemas import SchemaUtils
        if control_weights is None:
            control_weights = SchemaUtils.get_default_control_weights()
        
        if parameters is None:
            parameters = SchemaUtils.get_default_parameters()
        
        # Validate inputs
        if not SchemaUtils.validate_control_weights(control_weights):
            raise ValueError("Invalid control weights")
        
        if not SchemaUtils.validate_parameters(parameters):
            raise ValueError("Invalid parameters")
        
        # Generate unique run ID
        run_id = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)
        
        # Build output path
        if output_path:
            final_output_path = output_path
        else:
            final_output_path = f"outputs/{name}"
        
        # Create RunSpec
        timestamp = datetime.now().isoformat() + "Z"
        run_spec = RunSpec(
            id=run_id,
            prompt_id=prompt_id,
            name=name,
            control_weights=control_weights,
            parameters=parameters,
            timestamp=timestamp,
            execution_status=ExecutionStatus.PENDING,
            output_path=final_output_path
        )
        
        # Save to date-based directory
        file_path = self.dir_manager.get_run_file_path(name, timestamp, run_id)
        run_spec.save(file_path)
        
        print(f"[CREATED] RunSpec: {run_id}")
        print(f"   Saved to: {file_path}")
        print(f"   Prompt: {prompt_id}")
        print(f"   Control Weights: {control_weights}")
        print(f"   Output: {final_output_path}")
        
        return run_spec
    
    def list_runs(self, runs_dir: Path, pattern: Optional[str] = None) -> list[Path]:
        """
        List available RunSpec files.
        
        Args:
            runs_dir: Directory containing runs
            pattern: Optional pattern to filter runs
            
        Returns:
            List of RunSpec file paths
        """
        run_files = []
        
        # Search in date-based directories
        for date_dir in self.dir_manager.list_date_directories(runs_dir):
            date_path = runs_dir / date_dir
            for run_file in date_path.glob("*.json"):
                if pattern is None or pattern.lower() in run_file.stem.lower():
                    run_files.append(run_file)
        
        return sorted(run_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def get_run_info(self, run_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about a RunSpec file.
        
        Args:
            run_path: Path to RunSpec JSON file
            
        Returns:
            Dictionary with run information
        """
        run_path = Path(run_path)
        
        if not run_path.exists():
            raise FileNotFoundError(f"RunSpec file not found: {run_path}")
        
        with open(run_path, 'r') as f:
            run_data = json.load(f)
        
        return {
            "filename": run_path.name,
            "id": run_data.get("id", ""),
            "prompt_id": run_data.get("prompt_id", ""),
            "name": run_data.get("name", ""),
            "control_weights": run_data.get("control_weights", {}),
            "parameters": run_data.get("parameters", {}),
            "timestamp": run_data.get("timestamp", ""),
            "execution_status": run_data.get("execution_status", ""),
            "output_path": run_data.get("output_path", ""),
            "file_path": str(run_path),
            "file_size": run_path.stat().st_size,
            "created_time": datetime.fromtimestamp(run_path.stat().st_ctime)
        }
