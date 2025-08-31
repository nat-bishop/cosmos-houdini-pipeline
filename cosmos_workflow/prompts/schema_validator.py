#!/usr/bin/env python3
"""Schema validation system for Cosmos-Transfer1 workflow.
Handles validation of PromptSpec and RunSpec objects.
"""

import json
from pathlib import Path

from .schemas import SchemaUtils


class SchemaValidator:
    """Validates PromptSpec and RunSpec schemas."""

    @staticmethod
    def validate_prompt_spec(prompt_path: str | Path) -> bool:
        """Validate a PromptSpec JSON file.

        Args:
            prompt_path: Path to PromptSpec JSON file

        Returns:
            True if valid, False otherwise
        """
        prompt_path = Path(prompt_path)

        try:
            with open(prompt_path) as f:
                prompt_data = json.load(f)

            # Check required fields
            required_fields = [
                "id",
                "name",
                "prompt",
                "negative_prompt",
                "input_video_path",
                "timestamp",
            ]
            for field in required_fields:
                if field not in prompt_data:
                    print(f"[ERROR] Missing required field: {field}")
                    return False

            # Check ID format
            if not prompt_data["id"].startswith("ps_"):
                print(f"[ERROR] Invalid ID format: {prompt_data['id']}")
                return False

            print("[SUCCESS] PromptSpec validation passed")
            return True

        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Validation error: {e}")
            return False

    @staticmethod
    def validate_run_spec(run_path: str | Path) -> bool:
        """Validate a RunSpec JSON file.

        Args:
            run_path: Path to RunSpec JSON file

        Returns:
            True if valid, False otherwise
        """
        run_path = Path(run_path)

        try:
            with open(run_path) as f:
                run_data = json.load(f)

            # Check required fields
            required_fields = [
                "id",
                "prompt_id",
                "name",
                "control_weights",
                "parameters",
                "timestamp",
                "execution_status",
            ]
            for field in required_fields:
                if field not in run_data:
                    print(f"[ERROR] Missing required field: {field}")
                    return False

            # Check ID format
            if not run_data["id"].startswith("rs_"):
                print(f"[ERROR] Invalid ID format: {run_data['id']}")
                return False

            # Check prompt_id format
            if not run_data["prompt_id"].startswith("ps_"):
                print(f"[ERROR] Invalid prompt_id format: {run_data['prompt_id']}")
                return False

            # Check execution status
            valid_statuses = ["pending", "running", "success", "failed"]
            if run_data["execution_status"] not in valid_statuses:
                print(f"[ERROR] Invalid execution status: {run_data['execution_status']}")
                return False

            # Validate control weights
            if not SchemaUtils.validate_control_weights(run_data["control_weights"]):
                print(f"[ERROR] Invalid control weights: {run_data['control_weights']}")
                return False

            # Validate parameters
            if not SchemaUtils.validate_parameters(run_data["parameters"]):
                print(f"[ERROR] Invalid parameters: {run_data['parameters']}")
                return False

            print("[SUCCESS] RunSpec validation passed")
            return True

        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Validation error: {e}")
            return False

    @staticmethod
    def validate_control_weights(weights: dict) -> bool:
        """Validate control weights dictionary.

        Args:
            weights: Control weights dictionary

        Returns:
            True if valid, False otherwise
        """
        return SchemaUtils.validate_control_weights(weights)

    @staticmethod
    def validate_parameters(parameters: dict) -> bool:
        """Validate parameters dictionary.

        Args:
            parameters: Parameters dictionary

        Returns:
            True if valid, False otherwise
        """
        return SchemaUtils.validate_parameters(parameters)
