#!/usr/bin/env python3
"""Run systematic prompt upsampling tests."""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


class UpsampleTester:
    """Manages and runs prompt upsampling tests."""

    def __init__(self, output_dir: str = "testing/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        self.log_file = self.output_dir / f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    def log(self, message: str):
        """Log message to console and file."""
        print(message)
        with open(self.log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")

    def run_upsample_command(
        self,
        input_path: str,
        save_dir: str | None = None,
        preprocess_videos: bool = True,
        max_resolution: int = 480,
        num_frames: int = 2,
        num_gpu: int = 1,
        cuda_devices: str = "0",
        verbose: bool = True,
    ) -> dict:
        """Run upsample command and capture results.

        Returns:
            Dict with success status, timing, and output
        """
        cmd = ["python", "-m", "cosmos_workflow.cli", "upsample", input_path]

        if save_dir:
            cmd.extend(["--save-dir", save_dir])

        if not preprocess_videos:
            cmd.append("--preprocess-videos")
            cmd.append("false")

        cmd.extend(
            [
                "--max-resolution",
                str(max_resolution),
                "--num-frames",
                str(num_frames),
                "--num-gpu",
                str(num_gpu),
                "--cuda-devices",
                cuda_devices,
            ]
        )

        if verbose:
            cmd.append("--verbose")

        self.log(f"Running: {' '.join(cmd)}")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        end_time = time.time()
        duration = end_time - start_time

        success = result.returncode == 0
        has_vocab_error = "vocab" in result.stderr.lower() or "vocabulary" in result.stderr.lower()

        return {
            "command": " ".join(cmd),
            "success": success,
            "duration": duration,
            "has_vocab_error": has_vocab_error,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def test_single_prompt(self, prompt_spec_path: str, test_name: str = "single_test"):
        """Test single prompt upsampling."""
        self.log(f"\n=== Testing Single Prompt: {test_name} ===")

        save_dir = self.output_dir / "single" / test_name
        save_dir.mkdir(parents=True, exist_ok=True)

        result = self.run_upsample_command(input_path=prompt_spec_path, save_dir=str(save_dir))

        self.results.append(
            {"test": test_name, "type": "single", "input": prompt_spec_path, **result}
        )

        if result["success"]:
            self.log(f"✓ Success in {result['duration']:.2f}s")
        else:
            self.log(f"✗ Failed: {result['stderr'][:200]}")

        return result

    def test_resolution_threshold(self, prompt_specs_by_resolution: dict[str, list[str]]):
        """Test to find vocab error resolution threshold."""
        self.log("\n=== Testing Resolution Threshold ===")

        resolution_results = {}

        # Test resolutions in order
        test_resolutions = ["360p", "480p", "540p", "600p", "720p", "900p", "1080p", "1440p", "4k"]

        for res in test_resolutions:
            if res not in prompt_specs_by_resolution:
                self.log(f"Skipping {res}: no test specs available")
                continue

            # Test without preprocessing
            self.log(f"\nTesting {res} WITHOUT preprocessing...")
            specs = prompt_specs_by_resolution[res]
            if specs:
                test_spec = specs[0]  # Use first spec

                save_dir = self.output_dir / "resolution" / f"{res}_raw"
                result = self.run_upsample_command(
                    input_path=test_spec, save_dir=str(save_dir), preprocess_videos=False
                )

                resolution_results[f"{res}_raw"] = {
                    "resolution": res,
                    "preprocessed": False,
                    "success": result["success"],
                    "vocab_error": result["has_vocab_error"],
                    "duration": result["duration"],
                }

                if result["has_vocab_error"]:
                    self.log(f"  ✗ Vocab error at {res}")
                elif result["success"]:
                    self.log(f"  ✓ Success at {res}")
                else:
                    self.log(f"  ✗ Other error at {res}")

                # If failed, test WITH preprocessing
                if not result["success"]:
                    self.log(f"Testing {res} WITH preprocessing...")

                    save_dir = self.output_dir / "resolution" / f"{res}_preprocessed"
                    result = self.run_upsample_command(
                        input_path=test_spec,
                        save_dir=str(save_dir),
                        preprocess_videos=True,
                        max_resolution=480,
                    )

                    resolution_results[f"{res}_preprocessed"] = {
                        "resolution": res,
                        "preprocessed": True,
                        "success": result["success"],
                        "vocab_error": result["has_vocab_error"],
                        "duration": result["duration"],
                    }

                    if result["success"]:
                        self.log("  ✓ Success with preprocessing")

        # Save resolution test results
        with open(self.output_dir / "resolution_threshold.json", "w") as f:
            json.dump(resolution_results, f, indent=2)

        return resolution_results

    def test_batch_sizes(self, prompt_dir: str):
        """Test different batch sizes for optimization."""
        self.log("\n=== Testing Batch Sizes ===")

        batch_results = {}
        batch_sizes = [1, 5, 10, 20]

        # Get all prompt specs
        prompt_path = Path(prompt_dir)
        all_specs = list(prompt_path.glob("*_ps_*.json"))

        for batch_size in batch_sizes:
            if batch_size > len(all_specs):
                self.log(f"Skipping batch size {batch_size}: not enough specs")
                continue

            # Create test batch directory
            batch_dir = self.output_dir / "batch_test" / f"batch_{batch_size}"
            batch_dir.mkdir(parents=True, exist_ok=True)

            # Copy subset of specs
            for i, spec in enumerate(all_specs[:batch_size]):
                import shutil

                shutil.copy(spec, batch_dir / spec.name)

            # Run batch upsampling
            self.log(f"\nTesting batch size {batch_size}...")

            save_dir = self.output_dir / "batch_output" / f"batch_{batch_size}"
            result = self.run_upsample_command(input_path=str(batch_dir), save_dir=str(save_dir))

            if result["success"]:
                time_per_prompt = result["duration"] / batch_size
                self.log(
                    f"  ✓ Batch {batch_size}: {result['duration']:.2f}s total, {time_per_prompt:.2f}s per prompt"
                )
            else:
                self.log(f"  ✗ Batch {batch_size} failed")

            batch_results[f"batch_{batch_size}"] = {
                "batch_size": batch_size,
                "success": result["success"],
                "total_duration": result["duration"],
                "time_per_prompt": result["duration"] / batch_size if result["success"] else None,
            }

        # Save batch test results
        with open(self.output_dir / "batch_optimization.json", "w") as f:
            json.dump(batch_results, f, indent=2)

        return batch_results

    def test_frame_count_impact(self, test_spec: str):
        """Test impact of frame count on vocab error and performance."""
        self.log("\n=== Testing Frame Count Impact ===")

        frame_results = {}
        frame_counts = [1, 2, 4, 8]

        for frames in frame_counts:
            self.log(f"\nTesting with {frames} frames...")

            save_dir = self.output_dir / "frames" / f"frames_{frames}"
            result = self.run_upsample_command(
                input_path=test_spec,
                save_dir=str(save_dir),
                num_frames=frames,
                preprocess_videos=False,  # Test raw to see vocab errors
            )

            frame_results[f"frames_{frames}"] = {
                "frame_count": frames,
                "success": result["success"],
                "vocab_error": result["has_vocab_error"],
                "duration": result["duration"],
            }

            if result["success"]:
                self.log(f"  ✓ Success with {frames} frames in {result['duration']:.2f}s")
            elif result["has_vocab_error"]:
                self.log(f"  ✗ Vocab error with {frames} frames")
            else:
                self.log(f"  ✗ Other error with {frames} frames")

        # Save frame test results
        with open(self.output_dir / "frame_impact.json", "w") as f:
            json.dump(frame_results, f, indent=2)

        return frame_results

    def generate_report(self):
        """Generate comprehensive test report."""
        report = {
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tests": len(self.results),
            "successful_tests": sum(1 for r in self.results if r.get("success")),
            "failed_tests": sum(1 for r in self.results if not r.get("success")),
            "vocab_errors": sum(1 for r in self.results if r.get("has_vocab_error")),
            "results": self.results,
        }

        report_path = self.output_dir / "test_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        self.log("\n=== Test Report ===")
        self.log(f"Total tests: {report['total_tests']}")
        self.log(f"Successful: {report['successful_tests']}")
        self.log(f"Failed: {report['failed_tests']}")
        self.log(f"Vocab errors: {report['vocab_errors']}")
        self.log(f"\nFull report saved to: {report_path}")

        return report


def main():
    """Run comprehensive upsampling tests."""
    tester = UpsampleTester()

    # Check for test prompts
    prompt_manifest_path = Path("testing/prompt_manifest.json")
    if prompt_manifest_path.exists():
        with open(prompt_manifest_path) as f:
            manifest = json.load(f)

        specs_by_res = manifest.get("specs_by_resolution", {})

        # 1. Test single prompt (480p if available)
        if specs_by_res.get("480p"):
            tester.test_single_prompt(specs_by_res["480p"][0], "single_480p")
        elif specs_by_res.get("text_only"):
            tester.test_single_prompt(specs_by_res["text_only"][0], "single_text_only")

        # 2. Test resolution threshold
        if len(specs_by_res) > 1:
            tester.test_resolution_threshold(specs_by_res)

        # 3. Test batch sizes
        if "text_only" in specs_by_res:
            # Use text-only for batch testing (faster)
            tester.test_batch_sizes("inputs/prompts")

        # 4. Test frame count impact (if we have video specs)
        video_specs = [v for k, v in specs_by_res.items() if k != "text_only" and v]
        if video_specs:
            tester.test_frame_count_impact(video_specs[0][0])

    else:
        tester.log("No test prompts found. Run create_test_prompts.py first.")
        return

    # Generate final report
    tester.generate_report()


if __name__ == "__main__":
    main()
