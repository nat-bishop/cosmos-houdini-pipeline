"""
TEST-ONLY STUB CLASSES

WARNING: These are minimal stubs to allow tests to run after the prompts module
was deleted during refactoring. They do NOT represent production functionality.

These stubs exist ONLY to:
1. Allow tests to import without errors
2. Provide minimal attributes for test fixtures

DO NOT use these in production code!
"""


class ExecutionStatus:
    """Test stub for ExecutionStatus enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptSpec:
    """Test stub for PromptSpec.

    This is a minimal implementation that allows tests to create
    fixtures but does NOT implement real PromptSpec behavior.
    """

    def __init__(self, **kwargs):
        # Store all kwargs as attributes
        self.id = kwargs.get("id", "test_ps_000")
        self.name = kwargs.get("name", "test")
        self.prompt = kwargs.get("prompt", "")
        self.negative_prompt = kwargs.get("negative_prompt", "")
        self.input_video_path = kwargs.get("input_video_path", "")
        self.control_inputs = kwargs.get("control_inputs", {})
        self.timestamp = kwargs.get("timestamp", "")
        self.is_upsampled = kwargs.get("is_upsampled", False)
        self.parent_prompt_text = kwargs.get("parent_prompt_text", None)

        # Store raw kwargs for to_dict
        self._kwargs = kwargs

    def to_dict(self):
        """Return dictionary representation for test compatibility."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "input_video_path": self.input_video_path,
            "control_inputs": self.control_inputs,
            "timestamp": self.timestamp,
            "is_upsampled": self.is_upsampled,
            "parent_prompt_text": self.parent_prompt_text,
        }


class RunSpec:
    """Test stub for RunSpec.

    This is a minimal implementation that allows tests to create
    fixtures but does NOT implement real RunSpec behavior.
    """

    def __init__(self, **kwargs):
        # Store all kwargs as attributes
        self.id = kwargs.get("id", "test_rs_000")
        self.prompt_id = kwargs.get("prompt_id", "test_ps_000")
        self.name = kwargs.get("name", "test_run")
        self.control_weights = kwargs.get("control_weights", {})
        self.parameters = kwargs.get("parameters", {})
        self.timestamp = kwargs.get("timestamp", "")
        self.execution_status = kwargs.get("execution_status", ExecutionStatus.PENDING)
        self.output_path = kwargs.get("output_path", "")

        # Store raw kwargs for to_dict
        self._kwargs = kwargs

    def to_dict(self):
        """Return dictionary representation for test compatibility."""
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "name": self.name,
            "control_weights": self.control_weights,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "execution_status": self.execution_status,
            "output_path": self.output_path,
        }


# WARNING: DirectoryManager is also referenced in some tests
class DirectoryManager:
    """Test stub for DirectoryManager."""

    def __init__(self, prompts_dir, runs_dir):
        self.prompts_dir = prompts_dir
        self.runs_dir = runs_dir
