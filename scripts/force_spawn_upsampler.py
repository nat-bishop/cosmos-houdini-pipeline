#!/usr/bin/env python3
"""Force Python to use spawn for multiprocessing before any imports."""

# CRITICAL: Set multiprocessing to spawn BEFORE any torch/cuda imports
import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

import argparse
import json
import os
import sys
from pathlib import Path

def setup_environment_for_single_gpu():
    """Set up environment variables as torchrun would for single GPU."""
    env_defaults = {
        "RANK": "0",
        "LOCAL_RANK": "0",
        "WORLD_SIZE": "1",
        "LOCAL_WORLD_SIZE": "1",
        "GROUP_RANK": "0",
        "ROLE_RANK": "0",
        "ROLE_NAME": "default",
        "OMP_NUM_THREADS": "1",
        "MASTER_ADDR": "127.0.0.1",
        "MASTER_PORT": "29500",
        "TORCHELASTIC_USE_AGENT_STORE": "False",
        "TORCHELASTIC_MAX_RESTARTS": "0",
        "TORCHELASTIC_RUN_ID": "none",
        "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1",
        "TORCHELASTIC_ERROR_FILE": "/tmp/torch_error.log"
    }
    
    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value
    
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    print("Environment variables set for single-GPU inference")


def main():
    parser = argparse.ArgumentParser(description="Upsampler with forced spawn method")
    parser.add_argument("--prompt", type=str, required=True,
                        help="Prompt to upsample")
    parser.add_argument("--input-video", type=str, required=True,
                        help="Path to input video file")
    parser.add_argument("--checkpoint-dir", type=str, default="/workspace/checkpoints",
                        help="Directory containing model checkpoints")
    parser.add_argument("--output-file", type=str, default="/workspace/outputs/upsampled.json",
                        help="Output file for result")
    
    args = parser.parse_args()
    
    print("Python multiprocessing start method:", multiprocessing.get_start_method())
    print("Setting up environment...")
    setup_environment_for_single_gpu()
    
    # Add workspace to path
    sys.path.append('/workspace')
    
    # Now import torch and the upsampler
    print("Importing modules...")
    import torch
    torch.enable_grad(False)
    
    from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
    
    print(f"Initializing upsampler...")
    print(f"  Checkpoint: {args.checkpoint_dir}")
    print(f"  Video: {args.input_video}")
    
    try:
        # Initialize with offloading to minimize memory usage
        upsampler = PixtralPromptUpsampler(
            checkpoint_dir=args.checkpoint_dir,
            offload_prompt_upsampler=True
        )
        
        print(f"\nUpsampling prompt...")
        print(f"  Original: {args.prompt[:80]}...")
        
        # Use the offload method
        upsampled = upsampler._prompt_upsample_with_offload(
            prompt=args.prompt,
            video_path=args.input_video
        )
        
        print(f"  Upsampled: {upsampled[:80]}...")
        
        # Save result
        result = {
            'original_prompt': args.prompt,
            'upsampled_prompt': upsampled,
            'video_path': args.input_video
        }
        
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nSaved to: {args.output_file}")
        print("\n=== UPSAMPLED ===")
        print(upsampled)
        print("=================")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()