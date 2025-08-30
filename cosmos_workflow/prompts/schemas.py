#!/usr/bin/env python3
"""
Schema definitions for the refactored prompt management system.
Defines PromptSpec and RunSpec data structures and utilities.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum


class ExecutionStatus(Enum):
    """Execution status for runs."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BlurStrength(Enum):
    """Valid blur strength values for vis controlnet."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class CannyThreshold(Enum):
    """Valid canny threshold values for edge controlnet."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass(frozen=True)
class PromptSpec:
    """Specification for a prompt without execution parameters."""
    id: str
    name: str
    prompt: str
    negative_prompt: str
    input_video_path: str
    control_inputs: Dict[str, str]  # modality -> file_path
    timestamp: str  # ISO format
    is_upsampled: bool = False
    parent_prompt_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptSpec':
        """Create PromptSpec from dictionary."""
        return cls(**data)
    
    def save(self, file_path: Path) -> None:
        """Save PromptSpec to JSON file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, file_path: Path) -> 'PromptSpec':
        """Load PromptSpec from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass(frozen=True)
class RunSpec:
    """Specification for an inference run with all parameters."""
    id: str
    prompt_id: str
    name: str  # Run name (e.g., prompt_name_timestamp)
    control_weights: Dict[str, float]  # modality -> weight
    parameters: Dict[str, Any]  # All other parameters
    timestamp: str  # ISO format
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    output_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['execution_status'] = self.execution_status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RunSpec':
        """Create RunSpec from dictionary."""
        # Convert execution_status string back to enum
        if 'execution_status' in data and isinstance(data['execution_status'], str):
            data['execution_status'] = ExecutionStatus(data['execution_status'])
        return cls(**data)
    
    def save(self, file_path: Path) -> None:
        """Save RunSpec to JSON file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, file_path: Path) -> 'RunSpec':
        """Load RunSpec from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class SchemaUtils:
    """Utility functions for schema operations."""
    
    @staticmethod
    def generate_prompt_id(prompt_text: str, input_video_path: str, 
                          control_inputs: Dict[str, str]) -> str:
        """
        Generate unique ID for PromptSpec.
        
        Args:
            prompt_text: The text prompt
            input_video_path: Path to input video
            control_inputs: Dictionary of modality -> file_path
            
        Returns:
            Unique ID string
        """
        # Create deterministic string representation
        content = f"{prompt_text}|{input_video_path}|{sorted(control_inputs.items())}"
        
        # Generate hash
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:12]  # Use first 12 chars for readability
        
        return f"ps_{hash_hex}"
    
    @staticmethod
    def generate_run_id(prompt_id: str, control_weights: Dict[str, float], 
                       parameters: Dict[str, Any]) -> str:
        """
        Generate unique ID for RunSpec.
        
        Args:
            prompt_id: The PromptSpec ID
            control_weights: Control weights dictionary
            parameters: All other parameters
            
        Returns:
            Unique ID string
        """
        # Create deterministic string representation including all parameters
        weights_str = "|".join(f"{k}={v}" for k, v in sorted(control_weights.items()))
        params_str = "|".join(f"{k}={v}" for k, v in sorted(parameters.items()))
        
        content = f"{prompt_id}|{weights_str}|{params_str}"
        
        # Generate hash
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:12]  # Use first 12 chars for readability
        
        return f"rs_{hash_hex}"
    
    @staticmethod
    def get_default_parameters() -> Dict[str, Any]:
        """Get default parameters for inference runs."""
        return {
            "num_steps": 35,
            "guidance": 7.0,
            "sigma_max": 70.0,
            "blur_strength": BlurStrength.MEDIUM.value,
            "canny_threshold": CannyThreshold.MEDIUM.value,
            "fps": 24,
            "seed": 1
        }
    
    @staticmethod
    def get_default_control_weights() -> Dict[str, float]:
        """Get default control weights."""
        return {
            "vis": 0.25,
            "edge": 0.25,
            "depth": 0.25,
            "seg": 0.25
        }
    
    @staticmethod
    def validate_control_weights(weights: Dict[str, float]) -> bool:
        """Validate that control weights are valid."""
        if not weights:
            return False
        
        # Check that all required keys are present and no extra keys
        required_keys = {"vis", "edge", "depth", "seg"}
        if set(weights.keys()) != required_keys:
            return False
        
        # Check that all weights are positive numbers
        for weight in weights.values():
            if not isinstance(weight, (int, float)) or weight < 0:
                return False
        
        return True
    
    @staticmethod
    def validate_parameters(parameters: Dict[str, Any]) -> bool:
        """Validate that parameters are within valid ranges."""
        if parameters is None:
            return False
            
        defaults = SchemaUtils.get_default_parameters()
        
        # Check required parameters
        for param in defaults.keys():
            if param not in parameters:
                return False
        
        # Validate specific parameters with type checking
        try:
            if not isinstance(parameters["num_steps"], int) or not (1 <= parameters["num_steps"] <= 100):
                return False
            
            if not isinstance(parameters["guidance"], (int, float)) or not (1.0 <= parameters["guidance"] <= 20.0):
                return False
            
            if not isinstance(parameters["sigma_max"], (int, float)) or not (0.0 <= parameters["sigma_max"] <= 80.0):
                return False
            
            if not isinstance(parameters["blur_strength"], str) or parameters["blur_strength"] not in [e.value for e in BlurStrength]:
                return False
            
            if not isinstance(parameters["canny_threshold"], str) or parameters["canny_threshold"] not in [e.value for e in CannyThreshold]:
                return False
            
            if not isinstance(parameters["fps"], int) or not (1 <= parameters["fps"] <= 60):
                return False
            
            if not isinstance(parameters["seed"], int) or not (1 <= parameters["seed"] <= 2**32 - 1):
                return False
            
            return True
        except (KeyError, TypeError):
            return False


class DirectoryManager:
    """Manages date-based directory structure for prompts and runs."""
    
    def __init__(self, base_prompts_dir: Path, base_runs_dir: Path):
        """
        Initialize directory manager.
        
        Args:
            base_prompts_dir: Base directory for prompts
            base_runs_dir: Base directory for runs
        """
        self.base_prompts_dir = Path(base_prompts_dir)
        self.base_runs_dir = Path(base_runs_dir)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for all operating systems."""
        # Replace invalid characters with underscores
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Remove or replace other potentially problematic characters
        filename = filename.replace('(', '_').replace(')', '_')
        filename = filename.replace('[', '_').replace(']', '_')
        filename = filename.replace('{', '_').replace('}', '_')
        
        # Clean up multiple consecutive underscores
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        
        # Ensure filename is not too long
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def get_date_subdirectory(self, timestamp: Union[str, datetime]) -> str:
        """Get date subdirectory name from timestamp."""
        if isinstance(timestamp, str):
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        
        return dt.strftime("%Y-%m-%d")
    
    def get_prompt_file_path(self, prompt_name: str, timestamp: Union[str, datetime], prompt_hash: str) -> Path:
        """Get file path for a PromptSpec."""
        date_dir = self.get_date_subdirectory(timestamp)
        
        # Convert timestamp to filename-safe format
        if isinstance(timestamp, str):
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        
        # Create filename-safe timestamp (replace colons and spaces with hyphens)
        safe_timestamp = dt.strftime("%Y-%m-%dT%H-%M-%S")
        
        # Sanitize the prompt name
        safe_prompt_name = self._sanitize_filename(prompt_name)
        
        # Create descriptive filename with hash for uniqueness
        filename = f"{safe_prompt_name}_{safe_timestamp}_{prompt_hash}.json"
        
        return self.base_prompts_dir / date_dir / filename
    
    def get_run_file_path(self, prompt_name: str, timestamp: Union[str, datetime], run_hash: str) -> Path:
        """Get file path for a RunSpec."""
        date_dir = self.get_date_subdirectory(timestamp)
        
        # Convert timestamp to filename-safe format
        if isinstance(timestamp, str):
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        
        # Create filename-safe timestamp (replace colons and spaces with hyphens)
        safe_timestamp = dt.strftime("%Y-%m-%dT%H-%M-%S")
        
        # Sanitize the prompt name
        safe_prompt_name = self._sanitize_filename(prompt_name)
        
        # Create descriptive filename with hash for uniqueness
        filename = f"{safe_prompt_name}_{safe_timestamp}_{run_hash}.json"
        
        return self.base_runs_dir / date_dir / filename
    
    def ensure_directories_exist(self) -> None:
        """Ensure base directories exist."""
        self.base_prompts_dir.mkdir(parents=True, exist_ok=True)
        self.base_runs_dir.mkdir(parents=True, exist_ok=True)
    
    def ensure_date_directories_exist(self, timestamp: Union[str, datetime]) -> None:
        """Ensure date subdirectories exist for a given timestamp."""
        date_dir = self.get_date_subdirectory(timestamp)
        
        prompt_date_dir = self.base_prompts_dir / date_dir
        run_date_dir = self.base_runs_dir / date_dir
        
        prompt_date_dir.mkdir(parents=True, exist_ok=True)
        run_date_dir.mkdir(parents=True, exist_ok=True)
    
    def list_date_directories(self, base_dir: Path) -> List[str]:
        """List all date subdirectories in a base directory."""
        if not base_dir.exists():
            return []
        
        date_dirs = []
        for item in base_dir.iterdir():
            if item.is_dir() and self._is_valid_date_format(item.name):
                date_dirs.append(item.name)
        
        return sorted(date_dirs, reverse=True)  # Most recent first
    
    def _is_valid_date_format(self, dirname: str) -> bool:
        """Check if directory name follows YYYY-MM-DD format."""
        # Use regex to ensure strict YYYY-MM-DD format with leading zeros
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, dirname):
            return False
        
        # Additional validation to ensure valid date
        try:
            datetime.strptime(dirname, "%Y-%m-%d")
            return True
        except ValueError:
            return False

