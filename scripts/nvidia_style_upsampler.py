#!/usr/bin/env python3
"""NVIDIA-style prompt upsampler following the patterns from transfer.py and world_generation_pipeline.py"""

import argparse
import json
import os
import sys
from pathlib import Path

# Set this before importing torch/transformers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add cosmos_transfer1 to path
sys.path.append("/workspace")

import torch

torch.enable_grad(False)  # Disable gradients for inference

from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler


def save_and_clear_dist_env():
    """Save and clear distributed training environment variables.

    This follows NVIDIA's pattern from world_generation_pipeline.py
    """
    dist_keys = [
        "RANK",
        "LOCAL_RANK",
        "WORLD_SIZE",
        "LOCAL_WORLD_SIZE",
        "GROUP_RANK",
        "ROLE_RANK",
        "ROLE_NAME",
        "OMP_NUM_THREADS",
        "MASTER_ADDR",
        "MASTER_PORT",
        "TORCHELASTIC_USE_AGENT_STORE",
        "TORCHELASTIC_MAX_RESTARTS",
        "TORCHELASTIC_RUN_ID",
        "TORCH_NCCL_ASYNC_ERROR_HANDLING",
        "TORCHELASTIC_ERROR_FILE",
    ]

    saved_env = {}
    for key in dist_keys:
        if key in os.environ:
            saved_env[key] = os.environ[key]
            del os.environ[key]

    return saved_env


def restore_dist_env(saved_env):
    """Restore distributed training environment variables."""
    for key, value in saved_env.items():
        os.environ[key] = value


def main():
    parser = argparse.ArgumentParser(description="NVIDIA-style prompt upsampler")
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt to upsample")
    parser.add_argument("--input_video", type=str, required=True, help="Path to input video file")
    parser.add_argument(
        "--checkpoint_dir",
        type=str,
        default="/workspace/checkpoints",
        help="Directory containing model checkpoints",
    )
    parser.add_argument(
        "--offload_prompt_upsampler",
        action="store_true",
        help="Offload prompt upsampler model after inference",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="/workspace/outputs/upsampled_prompt.txt",
        help="Output file for upsampled prompt",
    )

    args = parser.parse_args()

    # Check if we're in distributed mode
    is_distributed = "RANK" in os.environ
    rank = int(os.environ.get("RANK", 0))

    # Only run on rank 0 (following NVIDIA's pattern)
    if rank != 0:
        print(f"Rank {rank}: Skipping prompt upsampling (only runs on rank 0)")
        return

    print("Initializing prompt upsampler...")
    print(f"Checkpoint dir: {args.checkpoint_dir}")
    print(f"Input video: {args.input_video}")

    # Save and clear distributed environment (NVIDIA's workaround)
    saved_env = {}
    if is_distributed:
        print("Saving and clearing distributed training environment...")
        saved_env = save_and_clear_dist_env()

    try:
        # Initialize the upsampler
        upsampler = PixtralPromptUpsampler(
            checkpoint_dir=args.checkpoint_dir,
            offload_prompt_upsampler=args.offload_prompt_upsampler,
        )

        print("Upsampling prompt...")
        print(f"Original: {args.prompt[:100]}...")

        # Upsample the prompt
        if args.offload_prompt_upsampler:
            upsampled = upsampler._prompt_upsample_with_offload(
                prompt=args.prompt, video_path=args.input_video
            )
        else:
            upsampled = upsampler._prompt_upsample(prompt=args.prompt, video_path=args.input_video)

        print(f"Upsampled: {upsampled[:100]}...")

        # Save result
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = {
            "original_prompt": args.prompt,
            "upsampled_prompt": upsampled,
            "input_video": args.input_video,
        }

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        print(f"Result saved to: {args.output_file}")

        # Also print just the upsampled text for easy capture
        print("\n=== UPSAMPLED PROMPT ===")
        print(upsampled)
        print("========================\n")

    finally:
        # Restore distributed environment
        if saved_env:
            print("Restoring distributed training environment...")
            restore_dist_env(saved_env)


if __name__ == "__main__":
    main()
