#!/usr/bin/env python3
"""Working prompt upsampler for NVIDIA Cosmos-Transfer1.
Based on user's previous working approach - sets VLLM spawn method BEFORE imports.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add cosmos-transfer1 to Python path if running in Docker
if os.path.exists("/workspace"):
    sys.path.insert(0, "/workspace")

# CRITICAL: Set VLLM to use spawn BEFORE any imports!
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

# Set all TorchElastic environment defaults BEFORE imports
# These prevent KeyErrors when the upsampler tries to clean up environment
_defaults = {
    "RANK": "0",
    "LOCAL_RANK": "0",
    "WORLD_SIZE": "1",
    "LOCAL_WORLD_SIZE": "1",
    "GROUP_RANK": "0",
    "ROLE_RANK": "0",
    "ROLE_NAME": "default",
    "OMP_NUM_THREADS": "4",
    "MASTER_ADDR": "127.0.0.1",
    "MASTER_PORT": "29500",
    "TORCHELASTIC_USE_AGENT_STORE": "False",
    "TORCHELASTIC_MAX_RESTARTS": "0",
    "TORCHELASTIC_RUN_ID": "local",
    "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1",
    "TORCHELASTIC_ERROR_FILE": "/tmp/torch_error.log",
}
for k, v in _defaults.items():
    os.environ.setdefault(k, v)

# NOW we can import the upsampler after environment is prepared
try:
    from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
except ImportError as e:
    print(f"[ERROR] Failed to import PixtralPromptUpsampler: {e}", file=sys.stderr)
    print(
        "Make sure you're in the cosmos-transfer1 directory or have it in PYTHONPATH",
        file=sys.stderr,
    )
    sys.exit(1)


def upsample_prompt(
    prompt: str,
    video_path: str,
    checkpoint_dir: str = "/workspace/checkpoints",
    offload: bool = True,
) -> str:
    """Upsample a single prompt using the Pixtral model.

    Args:
        prompt: Text prompt to upsample
        video_path: Path to video file for visual context
        checkpoint_dir: Path to model checkpoints
        offload: Whether to offload model after use (saves memory)

    Returns:
        Upsampled prompt text
    """
    print("[INFO] Initializing Pixtral upsampler...", flush=True)
    print(f"[INFO] Checkpoint dir: {checkpoint_dir}", flush=True)
    print(f"[INFO] Offload mode: {offload}", flush=True)

    # Initialize the upsampler
    upsampler = PixtralPromptUpsampler(
        checkpoint_dir=checkpoint_dir, offload_prompt_upsampler=offload
    )

    # Run upsampling
    print(f"[INFO] Upsampling prompt with video: {video_path}", flush=True)

    if offload:
        # Use the offload version which loads/unloads model
        upsampled = upsampler._prompt_upsample_with_offload(prompt, video_path)
    else:
        # Keep model in memory (faster for multiple prompts)
        upsampled = upsampler._prompt_upsample(prompt, video_path)

    return upsampled


def process_batch(
    input_file: str,
    output_dir: str,
    checkpoint_dir: str = "/workspace/checkpoints",
    offload: bool = True,
) -> None:
    """Process a batch of prompts from a JSON file.

    Expected input format:
    [
        {
            "name": "prompt_name",
            "prompt": "text prompt",
            "video_path": "path/to/video.mp4"
        },
        ...
    ]
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load input data
    with open(input_path) as f:
        batch_data = json.load(f)

    print(f"[INFO] Processing {len(batch_data)} prompts", flush=True)

    # Initialize upsampler once if not offloading
    upsampler = None
    if not offload:
        print("[INFO] Loading Pixtral model (keeping in memory)...", flush=True)
        upsampler = PixtralPromptUpsampler(
            checkpoint_dir=checkpoint_dir, offload_prompt_upsampler=False
        )

    # Process each prompt
    results = []
    for i, item in enumerate(batch_data, 1):
        name = item.get("name", f"prompt_{i}")
        prompt = item["prompt"]
        video_path = item["video_path"]

        print(f"\n[{i}/{len(batch_data)}] Processing: {name}", flush=True)

        try:
            if offload:
                # Create new upsampler for each prompt (memory efficient)
                upsampled = upsample_prompt(prompt, video_path, checkpoint_dir, offload=True)
            else:
                # Use persistent upsampler (faster)
                upsampled = upsampler._prompt_upsample(prompt, video_path)

            result = {
                "name": name,
                "original_prompt": prompt,
                "upsampled_prompt": upsampled,
                "video_path": video_path,
                "success": True,
            }

            # Save individual result
            result_file = output_path / f"{name}_upsampled.json"
            with open(result_file, "w") as f:
                json.dump(result, f, indent=2)

            print(f"[SUCCESS] Saved to: {result_file}", flush=True)

        except Exception as e:
            print(f"[ERROR] Failed to process {name}: {e}", file=sys.stderr)
            result = {
                "name": name,
                "original_prompt": prompt,
                "video_path": video_path,
                "success": False,
                "error": str(e),
            }

        results.append(result)

    # Save batch results
    batch_results_file = output_path / "batch_results.json"
    with open(batch_results_file, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n[DONE] Processed {successful}/{len(batch_data)} prompts successfully")
    print(f"[INFO] Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Upsample prompts using Pixtral model")
    parser.add_argument("--prompt", help="Text prompt to upsample (for single prompt mode)")
    parser.add_argument("--video", help="Video path for visual context (for single prompt mode)")
    parser.add_argument("--batch", help="JSON file with batch of prompts to process")
    parser.add_argument(
        "--output-dir", default="outputs/upsampled", help="Output directory for results"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="/workspace/checkpoints",
        help="Path to model checkpoints directory",
    )
    parser.add_argument(
        "--no-offload",
        action="store_true",
        help="Keep model in memory (faster for batches, uses more VRAM)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.batch:
        # Batch mode
        if not Path(args.batch).exists():
            print(f"[ERROR] Batch file not found: {args.batch}", file=sys.stderr)
            sys.exit(1)

        process_batch(args.batch, args.output_dir, args.checkpoint_dir, offload=not args.no_offload)

    elif args.prompt and args.video:
        # Single prompt mode
        if not Path(args.video).exists():
            print(f"[ERROR] Video file not found: {args.video}", file=sys.stderr)
            sys.exit(1)

        upsampled = upsample_prompt(
            args.prompt, args.video, args.checkpoint_dir, offload=not args.no_offload
        )

        # Save result
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        result = {
            "original_prompt": args.prompt,
            "upsampled_prompt": upsampled,
            "video_path": args.video,
        }

        result_file = output_path / "upsampled_prompt.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\n[SUCCESS] Upsampled prompt saved to: {result_file}")
        print(f"\n[ORIGINAL]: {args.prompt}")
        print(f"\n[UPSAMPLED]: {upsampled}")

    else:
        print(
            "[ERROR] Provide either --batch for batch processing or --prompt and --video for single prompt",
            file=sys.stderr,
        )
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
