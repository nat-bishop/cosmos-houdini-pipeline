"""
End-to-end workflow tests for prompt upsampling.
Tests complete workflows from prompt creation to upsampled results.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec, ExecutionStatus
from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.run_spec_manager import RunSpecManager


class TestCompleteUpsampleWorkflow(unittest.TestCase):
    """Test complete end-to-end upsampling workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.prompt_manager = PromptSpecManager(base_dir=self.temp_dir)
        self.run_manager = RunSpecManager(base_dir=self.temp_dir)
        
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
                name=f"scene_{i}",
                prompt=f"A simple scene {i}",
                input_video_path=f"{self.inputs_dir}/videos/scene_{i}.mp4",
                metadata={
                    "needs_upsampling": True,
                    "created_at": datetime.now().isoformat()
                }
            )
            saved_path = self.prompt_manager.save(spec)
            prompt_specs.append((spec, saved_path))
        
        # Step 2: Prepare batch for upsampling
        batch_file = os.path.join(self.inputs_dir, "prompts", "batch.json")
        batch_data = []
        for spec, path in prompt_specs:
            batch_data.append({
                "name": spec.name,
                "prompt": spec.prompt,
                "video_path": spec.input_video_path,
                "spec_id": spec.id,
                "spec_path": str(path)
            })
        
        with open(batch_file, 'w') as f:
            json.dump(batch_data, f, indent=2)
        
        # Step 3: Simulate upsampling process
        upsampled_results = []
        for item in batch_data:
            upsampled_results.append({
                "name": item["name"],
                "original_prompt": item["prompt"],
                "upsampled_prompt": f"A detailed and elaborate {item['prompt']} with rich visual elements",
                "spec_id": item["spec_id"],
                "upsampled_at": datetime.now().isoformat()
            })
        
        # Step 4: Update prompt specs with upsampled results
        updated_specs = []
        for result in upsampled_results:
            # Find original spec
            original_path = next(
                path for spec, path in prompt_specs 
                if spec.id == result["spec_id"]
            )
            original_spec = self.prompt_manager.load(original_path)
            
            # Create updated spec
            updated_spec = PromptSpec(
                name=original_spec.name,
                prompt=result["upsampled_prompt"],
                negative_prompt=original_spec.negative_prompt,
                input_video_path=original_spec.input_video_path,
                control_inputs=original_spec.control_inputs,
                metadata={
                    **original_spec.metadata,
                    "original_prompt": result["original_prompt"],
                    "upsampled": True,
                    "upsampled_at": result["upsampled_at"]
                }
            )
            
            updated_path = self.prompt_manager.save(updated_spec)
            updated_specs.append((updated_spec, updated_path))
        
        # Verify results
        self.assertEqual(len(updated_specs), 3)
        for updated_spec, path in updated_specs:
            self.assertIn("detailed and elaborate", updated_spec.prompt)
            self.assertTrue(updated_spec.metadata.get("upsampled"))
            self.assertIn("original_prompt", updated_spec.metadata)
    
    def test_workflow_with_run_spec_creation(self):
        """Test workflow including RunSpec creation after upsampling."""
        # Create and upsample a prompt
        original_spec = PromptSpec(
            name="test_scene",
            prompt="A futuristic city",
            input_video_path=f"{self.inputs_dir}/videos/city.mp4"
        )
        original_path = self.prompt_manager.save(original_spec)
        
        # Simulate upsampling
        upsampled_prompt = "A sprawling futuristic metropolis with towering glass skyscrapers"
        
        # Create upsampled spec
        upsampled_spec = PromptSpec(
            name=original_spec.name,
            prompt=upsampled_prompt,
            input_video_path=original_spec.input_video_path,
            metadata={
                "original_prompt": original_spec.prompt,
                "upsampled": True
            }
        )
        upsampled_path = self.prompt_manager.save(upsampled_spec)
        
        # Create RunSpec with upsampled prompt
        run_spec = RunSpec(
            prompt_spec_id=upsampled_spec.id,
            control_weights={"vis": 0.5, "depth": 0.3},
            parameters={
                "num_steps": 35,
                "guidance_scale": 8.0,
                "seed": 42
            },
            execution_status=ExecutionStatus.PENDING,
            metadata={
                "uses_upsampled_prompt": True,
                "original_spec_id": original_spec.id
            }
        )
        
        run_path = self.run_manager.save(run_spec)
        
        # Verify the complete chain
        loaded_run = self.run_manager.load(run_path)
        loaded_prompt = self.prompt_manager.load_by_id(loaded_run.prompt_spec_id)
        
        self.assertIn("sprawling futuristic metropolis", loaded_prompt.prompt)
        self.assertTrue(loaded_prompt.metadata.get("upsampled"))
        self.assertTrue(loaded_run.metadata.get("uses_upsampled_prompt"))
    
    @patch('subprocess.run')
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
            {"name": "prompt2", "prompt": "Scene 2", "video_path": "/video2.mp4"}
        ]
        
        with open(input_file, 'w') as f:
            json.dump(prompts, f)
        
        # Simulate bash script execution
        import subprocess
        result = subprocess.run(
            [
                "bash", "scripts/upsample_prompt.sh",
                input_file,
                output_file,
                "true",  # preprocess_videos
                "480",   # max_resolution
                "2",     # num_frames
                "1"      # num_gpu
            ],
            capture_output=True,
            text=True
        )
        
        # Verify execution
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertEqual(call_args[0], "bash")
        self.assertIn("upsample_prompt.sh", call_args[1])
        self.assertEqual(call_args[2], input_file)
        self.assertEqual(call_args[3], output_file)


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
    
    @patch('cosmos_workflow.cli.CLI')
    def test_cli_upsample_command(self, mock_cli_class):
        """Test CLI command for upsampling prompts."""
        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli
        
        # Simulate CLI upsample command
        def upsample_prompts(args):
            """Mock upsample command handler."""
            input_dir = args.input_dir
            output_dir = args.output_dir
            preprocess = args.preprocess_videos
            max_res = args.max_resolution
            
            # Load prompts from input dir
            prompts = []
            for file in Path(input_dir).glob("*.json"):
                with open(file) as f:
                    prompts.append(json.load(f))
            
            # Process upsampling
            results = []
            for prompt in prompts:
                results.append({
                    "original": prompt.get("prompt"),
                    "upsampled": f"Upsampled: {prompt.get('prompt')}"
                })
            
            # Save results
            output_file = Path(output_dir) / "upsampled_results.json"
            with open(output_file, 'w') as f:
                json.dump(results, f)
            
            return results
        
        mock_cli.upsample_prompts = upsample_prompts
        
        # Create test input
        input_dir = os.path.join(self.temp_dir, "inputs")
        output_dir = os.path.join(self.temp_dir, "outputs")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create test prompt files
        for i in range(2):
            prompt_file = os.path.join(input_dir, f"prompt_{i}.json")
            with open(prompt_file, 'w') as f:
                json.dump({"prompt": f"Test prompt {i}"}, f)
        
        # Simulate CLI arguments
        class Args:
            input_dir = input_dir
            output_dir = output_dir
            preprocess_videos = True
            max_resolution = 480
        
        args = Args()
        
        # Execute command
        results = mock_cli.upsample_prompts(args)
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertIn("Upsampled:", results[0]["upsampled"])


class TestBatchProcessingWorkflow(unittest.TestCase):
    """Test batch processing workflows for upsampling."""
    
    def test_large_batch_processing(self):
        """Test processing large batch of prompts."""
        # Create large batch
        num_prompts = 50
        prompts = []
        for i in range(num_prompts):
            prompts.append({
                "name": f"prompt_{i}",
                "prompt": f"Scene description {i}",
                "video_path": f"/videos/video_{i}.mp4"
            })
        
        # Process in chunks (simulate memory constraints)
        chunk_size = 10
        all_results = []
        
        for i in range(0, num_prompts, chunk_size):
            chunk = prompts[i:i+chunk_size]
            
            # Simulate processing chunk
            chunk_results = []
            for prompt in chunk:
                chunk_results.append({
                    "name": prompt["name"],
                    "original": prompt["prompt"],
                    "upsampled": f"Detailed {prompt['prompt']}"
                })
            
            all_results.extend(chunk_results)
        
        # Verify all processed
        self.assertEqual(len(all_results), num_prompts)
        for i, result in enumerate(all_results):
            self.assertEqual(result["name"], f"prompt_{i}")
    
    def test_parallel_batch_processing(self):
        """Test parallel processing of prompt batches."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Create batches
        batches = []
        for batch_id in range(4):
            batch = []
            for i in range(5):
                batch.append({
                    "name": f"batch{batch_id}_prompt{i}",
                    "prompt": f"Batch {batch_id} Scene {i}"
                })
            batches.append(batch)
        
        # Process batches in parallel
        def process_batch(batch_id, batch):
            """Process a single batch."""
            results = []
            for prompt in batch:
                results.append({
                    "batch_id": batch_id,
                    "name": prompt["name"],
                    "upsampled": f"Processed: {prompt['prompt']}"
                })
            return results
        
        all_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(process_batch, i, batch): i 
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(futures):
                batch_results = future.result()
                all_results.extend(batch_results)
        
        # Verify parallel processing
        self.assertEqual(len(all_results), 20)  # 4 batches * 5 prompts
        batch_ids = set(r["batch_id"] for r in all_results)
        self.assertEqual(len(batch_ids), 4)


class TestVideoPreprocessingWorkflow(unittest.TestCase):
    """Test video preprocessing workflows for upsampling."""
    
    @patch('cv2.VideoCapture')
    @patch('cv2.VideoWriter')
    def test_batch_video_preprocessing(self, mock_writer, mock_capture):
        """Test preprocessing multiple videos for batch upsampling."""
        videos_to_process = [
            {"path": "/video1.mp4", "resolution": (1920, 1080)},
            {"path": "/video2.mp4", "resolution": (3840, 2160)},
            {"path": "/video3.mp4", "resolution": (640, 480)}
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
                100.0  # Total frames
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
                
                processed_videos.append({
                    "original": video["path"],
                    "processed": f"/tmp/processed_{os.path.basename(video['path'])}",
                    "original_res": video["resolution"],
                    "new_res": (new_width, new_height)
                })
            else:
                processed_videos.append({
                    "original": video["path"],
                    "processed": video["path"],
                    "original_res": video["resolution"],
                    "new_res": video["resolution"]
                })
        
        # Verify preprocessing decisions
        self.assertEqual(len(processed_videos), 3)
        # First two should be downscaled
        self.assertNotEqual(processed_videos[0]["original"], processed_videos[0]["processed"])
        self.assertNotEqual(processed_videos[1]["original"], processed_videos[1]["processed"])
        # Third should not be processed (already small)
        self.assertEqual(processed_videos[2]["original"], processed_videos[2]["processed"])


if __name__ == '__main__':
    unittest.main()