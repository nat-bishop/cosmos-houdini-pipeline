"""JSON handler wrapper for safe JSON operations.

This module provides a wrapper around JSON operations to ensure
consistent handling and validation across the codebase, following
the project's wrapper requirements.
"""

import json
from pathlib import Path
from typing import Any

from cosmos_workflow.utils.logging import logger


class JSONHandler:
    """Wrapper for JSON operations following project standards.

    All JSON operations must go through this wrapper to ensure
    consistency and proper error handling.
    """

    @staticmethod
    def write_json(data: dict[str, Any], file_path: Path | str, indent: int = 2) -> None:
        """Write JSON data to file with validation.

        Args:
            data: Dictionary to write as JSON
            file_path: Path to write JSON file
            indent: Indentation level for pretty printing

        Raises:
            ValueError: If data is not serializable
            IOError: If file cannot be written
        """
        file_path = Path(file_path)
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=indent)
            logger.debug("Wrote JSON to {}", file_path)
        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize data to JSON: {}", e)
            raise ValueError(f"Data not JSON serializable: {e}") from e
        except OSError as e:
            logger.error("Failed to write JSON file {}: {}", file_path, e)
            raise

    @staticmethod
    def read_json(file_path: Path | str) -> dict[str, Any]:
        """Read and validate JSON from file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file contains invalid JSON
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        try:
            with open(file_path) as f:
                data = json.load(f)
            logger.debug("Read JSON from {}", file_path)
            return data
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in file {}: {}", file_path, e)
            raise ValueError(f"Invalid JSON in {file_path}: {e}") from e
        except OSError as e:
            logger.error("Failed to read JSON file {}: {}", file_path, e)
            raise

    @staticmethod
    def dumps(data: Any, **kwargs) -> str:
        """Serialize data to JSON string.

        Args:
            data: Data to serialize
            **kwargs: Additional arguments for json.dumps

        Returns:
            JSON string

        Raises:
            ValueError: If data is not serializable
        """
        try:
            return json.dumps(data, **kwargs)
        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize data: {}", e)
            raise ValueError(f"Data not JSON serializable: {e}") from e

    @staticmethod
    def loads(json_string: str) -> Any:
        """Parse JSON string to Python object.

        Args:
            json_string: JSON string to parse

        Returns:
            Parsed data

        Raises:
            ValueError: If string contains invalid JSON
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON string: {}", e)
            raise ValueError(f"Invalid JSON: {e}") from e
