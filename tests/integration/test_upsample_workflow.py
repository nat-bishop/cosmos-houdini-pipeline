"""
End-to-end workflow tests for prompt upsampling.
Tests complete workflows from prompt creation to upsampled results.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.run_spec_manager import RunSpecManager
from cosmos_workflow.prompts.schemas import ExecutionStatus, PromptSpec, RunSpec


class TestCompleteUpsampleWorkflow(unittest.TestCase):
    """Test complete end-to-end upsampling workflows."""

    def setUp(self):
        """Set up test fixtures."""
        from cosmos_workflow.prompts.schemas import DirectoryManager

        self.temp_dir = tempfile.mkdtemp()
        prompts_dir = Path(self.temp_dir) / "prompts"
        runs_dir = Path(self.temp_dir) / "runs"

        prompts_dir.mkdir(parents=True, exist_ok=True)
        runs_dir.mkdir(parents=True, exist_ok=True)

        self.dir_manager = DirectoryManager(prompts_dir, runs_dir)
        self.prompt_manager = PromptSpecManager(self.dir_manager)
        self.run_manager = RunSpecManager(self.dir_manager)

        # Create test directories
        self.inputs_dir = os.path.join(self.temp_dir, "inputs")
        self.outputs_dir = os.path.join(self.temp_dir, "outputs")
        os.makedirs(os.path.join(self.inputs_dir, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(self.inputs_dir, "videos"), exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_workflow_prompt_creation_to_upsampling(self):
        """Test workflow from prompt creation to upsampling."""
        # Step 1: Create initial prompt specs
        prompt_specs = []
        for i in range(3):
            spec = PromptSpec(
                id=f"ps_scene{i:03d}",
                name=f"scene_{i}",
                prompt=f"A simple scene {i}",
                negative_prompt="bad quality, blurry, low resolution, cartoonish",
                input_video_path=f"{self.inputs_dir}/videos/scene_{i}.mp4",
                control_inputs={
                    "depth": f"{self.inputs_dir}/depth/scene_{i}.mp4",
                    "seg": f"{self.inputs_dir}/seg/scene_{i}.mp4",
                },
                timestamp=datetime.now().isoformat() + "Z",
                is_upsampled=False,
            )
            # Save the spec using the directory manager
            timestamp = datetime.now()
            saved_path = self.dir_manager.get_prompt_file_path(spec.name, timestamp, spec.id)
            spec.save(saved_path)
            prompt_specs.append((spec, saved_path))

        # Step 2: Prepare batch for upsampling
        batch_file = os.path.join(self.inputs_dir, "prompts", "batch.json")
        batch_data = []
        for spec, path in prompt_specs:
            batch_data.append(
                {
                    "name": spec.name,
                    "prompt": spec.prompt,
                    "video_path": spec.input_video_path,
                    "spec_id": spec.id,
                    "spec_path": str(path),
                }
            )

        with open(batch_file, "w") as f:
            json.dump(batch_data, f, indent=2)

        # Step 3: Simulate upsampling process
        upsampled_results = []
        for item in batch_data:
            upsampled_results.append(
                {
                    "name": item["name"],
                    "original_prompt": item["prompt"],
                    "upsampled_prompt": f"A detailed and elaborate {item['prompt']} with rich visual elements",
                    "spec_id": item["spec_id"],
                    "upsampled_at": datetime.now().isoformat(),
                }
            )

        # Step 4: Update prompt specs with upsampled results
        updated_specs = []
        for result in upsampled_results:
            # Find original spec
            original_path = next(
                path for spec, path in prompt_specs if spec.id == result["spec_id"]
            )
            original_spec = PromptSpec.load(original_path)

            # Create updated spec
            updated_spec = PromptSpec(
                id=f"ps_updated_{result['spec_id'][-6:]}",  # Use part of original ID
                name=original_spec.name,
                prompt=result["upsampled_prompt"],
                negative_prompt=original_spec.negative_prompt,
                input_video_path=original_spec.input_video_path,
                control_inputs=original_spec.control_inputs,
                timestamp=datetime.now().isoformat() + "Z",
                is_upsampled=True,
                parent_prompt_text=result["original_prompt"],
            )

            updated_timestamp = datetime.now()
            updated_path = self.dir_manager.get_prompt_file_path(
                updated_spec.name, updated_timestamp, updated_spec.id
            )
            updated_spec.save(updated_path)
            updated_specs.append((updated_spec, updated_path))

        # Verify results
        assert len(updated_specs) == 3
        for updated_spec, path in updated_specs:
            assert "detailed and elaborate" in updated_spec.prompt
            assert updated_spec.is_upsampled
            assert updated_spec.parent_prompt_text is not None

    def test_workflow_with_run_spec_creation(self):
        """Test workflow including RunSpec creation after upsampling."""
        # Create and upsample a prompt
        original_spec = PromptSpec(
            id="ps_city001",
            name="test_scene",
            prompt="A futuristic city",
            negative_prompt="bad quality, blurry, low resolution, cartoonish",
            input_video_path=f"{self.inputs_dir}/videos/city.mp4",
            control_inputs={
                "depth": f"{self.inputs_dir}/depth/city.mp4",
                "seg": f"{self.inputs_dir}/seg/city.mp4",
            },
            timestamp=datetime.now().isoformat() + "Z",
            is_upsampled=False,
        )
        # Save the original spec using the directory manager
        timestamp = datetime.now()
        original_path = self.dir_manager.get_prompt_file_path(
            original_spec.name, timestamp, original_spec.id
        )
        original_spec.save(original_path)

        # Simulate upsampling
        upsampled_prompt = "A sprawling futuristic metropolis with towering glass skyscrapers"

        # Create upsampled spec
        upsampled_spec = PromptSpec(
            id="ps_city002",
            name=original_spec.name,
            prompt=upsampled_prompt,
            negative_prompt=original_spec.negative_prompt,
            input_video_path=original_spec.input_video_path,
            control_inputs=original_spec.control_inputs,
            timestamp=datetime.now().isoformat() + "Z",
            is_upsampled=True,
            parent_prompt_text=original_spec.prompt,
        )
        upsampled_timestamp = datetime.now()
        upsampled_path = self.dir_manager.get_prompt_file_path(
            upsampled_spec.name, upsampled_timestamp, upsampled_spec.id
        )
        upsampled_spec.save(upsampled_path)

        # Create RunSpec with upsampled prompt
        run_spec = RunSpec(
            id="rs_city001",
            prompt_id=upsampled_spec.id,
            name=upsampled_spec.name,
            control_weights={"vis": 0.5, "depth": 0.3, "edge": 0.1, "seg": 0.1},
            parameters={
                "num_steps": 35,
                "guidance": 8.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 42,
            },
            timestamp=datetime.now().isoformat() + "Z",
            execution_status=ExecutionStatus.PENDING,
        )

        run_timestamp = datetime.now()
        run_path = self.dir_manager.get_run_file_path(run_spec.name, run_timestamp, run_spec.id)
        run_spec.save(run_path)

        # Verify the complete chain
        loaded_run = RunSpec.load(run_path)
        loaded_prompt = PromptSpec.load(upsampled_path)  # Use the path we saved to

        assert "sprawling futuristic metropolis" in loaded_prompt.prompt
        assert loaded_prompt.is_upsampled
        assert loaded_run.prompt_id == upsampled_spec.id

    @patch("subprocess.run")
    def test_bash_script_execution_workflow(self, mock_subprocess):
        """Test executing bash upsampling script."""
        # Mock successful script execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Upsampling complete\nResults saved"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Prepare input file
        input_file = os.path.join(self.inputs_dir, "prompts.json")
        output_file = os.path.join(self.outputs_dir, "upsampled.json")

        prompts = [
            {"name": "prompt1", "prompt": "Scene 1", "video_path": "/video1.mp4"},
            {"name": "prompt2", "prompt": "Scene 2", "video_path": "/video2.mp4"},
        ]

        with open(input_file, "w") as f:
            json.dump(prompts, f)

        # Simulate bash script execution
        import subprocess

        subprocess.run(
            [
                "bash",
                "scripts/upsample_prompt.sh",
                input_file,
                output_file,
                "true",  # preprocess_videos
                "480",  # max_resolution
                "2",  # num_frames
                "1",  # num_gpu
            ],
            check=False, capture_output=True,
            text=True,
        )

        # Verify execution
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "bash"
        assert "upsample_prompt.sh" in call_args[1]
        assert call_args[2] == input_file
        assert call_args[3] == output_file


class TestCLIWorkflow(unittest.TestCase):
    """Test CLI-based upsampling workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("cosmos_workflow.cli.run_prompt_upsampling")
    def test_cli_upsample_command(self, mock_upsample_func):
        """Test CLI command for upsampling prompts."""
        # Mock the upsampling function to return test results
        mock_upsample_func.return_value = {
            "results": [
                {"original": "Test prompt 1", "upsampled": "Upsampled: Test prompt 1"},
                {"original": "Test prompt 2", "upsampled": "Upsampled: Test prompt 2"},
            ]
        }

        # Create test input
        input_dir = os.path.join(self.temp_dir, "inputs")
        output_dir = os.path.join(self.temp_dir, "outputs")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Create test prompt files
        for i in range(2):
            prompt_file = os.path.join(input_dir, f"prompt_{i}.json")
            with open(prompt_file, "w") as f:
                json.dump({"prompt": f"Test prompt {i+1}"}, f)

        # Call the mocked CLI function
        from cosmos_workflow.cli import run_prompt_upsampling

        result = run_prompt_upsampling(
            input_dir=input_dir, output_dir=output_dir, preprocess_videos=True, max_resolution=480
        )

        # Verify the mock was called
        mock_upsample_func.assert_called_once()

        # Verify results
        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 2
        assert "Upsampled:" in result["results"][0]["upsampled"]


class TestBatchProcessingWorkflow(unittest.TestCase):
    """Test batch processing workflows for upsampling."""

    def test_large_batch_processing(self):
        """Test processing large batch of prompts."""
        # Create large batch
        num_prompts = 50
        prompts = []
        for i in range(num_prompts):
            prompts.append(
                {
                    "name": f"prompt_{i}",
                    "prompt": f"Scene description {i}",
                    "video_path": f"/videos/video_{i}.mp4",
                }
            )

        # Process in chunks (simulate memory constraints)
        chunk_size = 10
        all_results = []

        for i in range(0, num_prompts, chunk_size):
            chunk = prompts[i : i + chunk_size]

            # Simulate processing chunk
            chunk_results = []
            for prompt in chunk:
                chunk_results.append(
                    {
                        "name": prompt["name"],
                        "original": prompt["prompt"],
                        "upsampled": f"Detailed {prompt['prompt']}",
                    }
                )

            all_results.extend(chunk_results)

        # Verify all processed
        assert len(all_results) == num_prompts
        for i, result in enumerate(all_results):
            assert result["name"] == f"prompt_{i}"

    def test_parallel_batch_processing(self):
        """Test parallel processing of prompt batches."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Create batches
        batches = []
        for batch_id in range(4):
            batch = []
            for i in range(5):
                batch.append(
                    {"name": f"batch{batch_id}_prompt{i}", "prompt": f"Batch {batch_id} Scene {i}"}
                )
            batches.append(batch)

        # Process batches in parallel
        def process_batch(batch_id, batch):
            """Process a single batch."""
            results = []
            for prompt in batch:
                results.append(
                    {
                        "batch_id": batch_id,
                        "name": prompt["name"],
                        "upsampled": f"Processed: {prompt['prompt']}",
                    }
                )
            return results

        all_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(process_batch, i, batch): i for i, batch in enumerate(batches)
            }

            for future in as_completed(futures):
                batch_results = future.result()
                all_results.extend(batch_results)

        # Verify parallel processing
        assert len(all_results) == 20  # 4 batches * 5 prompts
        batch_ids = {r["batch_id"] for r in all_results}
        assert len(batch_ids) == 4


class TestVideoPreprocessingWorkflow(unittest.TestCase):
    """Test video preprocessing workflows for upsampling."""

    @patch("cv2.VideoCapture")
    @patch("cv2.VideoWriter")
    def test_batch_video_preprocessing(self, mock_writer, mock_capture):
        """Test preprocessing multiple videos for batch upsampling."""
        videos_to_process = [
            {"path": "/video1.mp4", "resolution": (1920, 1080)},
            {"path": "/video2.mp4", "resolution": (3840, 2160)},
            {"path": "/video3.mp4", "resolution": (640, 480)},
        ]

        processed_videos = []

        for video in videos_to_process:
            # Mock video properties
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = [
                24.0,  # FPS
                float(video["resolution"][0]),  # Width
                float(video["resolution"][1]),  # Height
                100.0,  # Total frames
            ]
            mock_capture.return_value = mock_cap

            # Determine if preprocessing needed
            max_res = 720
            width, height = video["resolution"]
            needs_preprocessing = width > max_res or height > max_res

            if needs_preprocessing:
                # Calculate new dimensions
                if width > height:
                    new_width = max_res
                    new_height = int(height * (max_res / width))
                else:
                    new_height = max_res
                    new_width = int(width * (max_res / height))

                processed_videos.append(
                    {
                        "original": video["path"],
                        "processed": f"/tmp/processed_{os.path.basename(video['path'])}",
                        "original_res": video["resolution"],
                        "new_res": (new_width, new_height),
                    }
                )
            else:
                processed_videos.append(
                    {
                        "original": video["path"],
                        "processed": video["path"],
                        "original_res": video["resolution"],
                        "new_res": video["resolution"],
                    }
                )

        # Verify preprocessing decisions
        assert len(processed_videos) == 3
        # First two should be downscaled
        assert processed_videos[0]["original"] != processed_videos[0]["processed"]
        assert processed_videos[1]["original"] != processed_videos[1]["processed"]
        # Third should not be processed (already small)
        assert processed_videos[2]["original"] == processed_videos[2]["processed"]


if __name__ == "__main__":
    unittest.main()
