#!/usr/bin/env python3
"""Standalone prompt upsampler that sets proper environment variables before running.

This script sets all the required distributed training environment variables 
with sensible defaults for single-GPU inference, mimicking what torchrun would set.
"""

import argparse
import json
import os
import sys
from pathlib import Path

def setup_environment_for_single_gpu():
    """Set up environment variables as torchrun would for single GPU."""
    # These are the standard values torchrun sets for --nproc_per_node=1
    env_defaults = {
        "RANK": "0",                    # Global rank (0 for single process)
        "LOCAL_RANK": "0",               # Local rank on this node
        "WORLD_SIZE": "1",               # Total number of processes
        "LOCAL_WORLD_SIZE": "1",         # Number of processes on this node
        "GROUP_RANK": "0",               # Rank of this node
        "ROLE_RANK": "0",                # Rank within role
        "ROLE_NAME": "default",          # Role name
        "OMP_NUM_THREADS": "1",          # OpenMP threads
        "MASTER_ADDR": "127.0.0.1",      # Master address for coordination
        "MASTER_PORT": "29500",          # Master port for coordination
        "TORCHELASTIC_USE_AGENT_STORE": "False",  # Don't use agent store
        "TORCHELASTIC_MAX_RESTARTS": "0",         # No restarts
        "TORCHELASTIC_RUN_ID": "none",            # Run ID
        "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1",   # Enable async error handling
        "TORCHELASTIC_ERROR_FILE": "/tmp/torch_error.log"  # Error log file
    }
    
    # Only set if not already set (allow overrides)
    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"Set {key}={value}")
        else:
            print(f"Using existing {key}={os.environ[key]}")
    
    # Also set this to avoid tokenizer warnings
    os.environ["TOKENIZERS_PARALLELISM"] = "false"


def main():
    parser = argparse.ArgumentParser(description="Standalone prompt upsampler")
    parser.add_argument("--batch-file", type=str, 
                        help="JSON file with prompts to upsample")
    parser.add_argument("--prompt", type=str,
                        help="Single prompt to upsample (alternative to batch file)")
    parser.add_argument("--input-video", type=str, required=True,
                        help="Path to input video file")
    parser.add_argument("--checkpoint-dir", type=str, default="/workspace/checkpoints",
                        help="Directory containing model checkpoints")
    parser.add_argument("--output-file", type=str, default="/workspace/outputs/upsampled_result.json",
                        help="Output file for upsampled result")
    parser.add_argument("--offload", action="store_true",
                        help="Offload model after inference to save memory")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.prompt and not args.batch_file:
        print("ERROR: Must provide either --prompt or --batch-file")
        sys.exit(1)
    
    if args.prompt and args.batch_file:
        print("ERROR: Cannot provide both --prompt and --batch-file")
        sys.exit(1)
    
    print("Setting up environment for single-GPU inference...")
    setup_environment_for_single_gpu()
    
    # Now we can import the Cosmos modules (after env is set up)
    sys.path.append('/workspace')
    
    # Import after setting environment to avoid issues
    import torch
    torch.enable_grad(False)  # Disable gradients for inference
    
    # Import the upsampler AFTER setting up environment
    from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
    
    print(f"\nInitializing Pixtral prompt upsampler...")
    print(f"Checkpoint dir: {args.checkpoint_dir}")
    print(f"Offload model: {args.offload}")
    
    # Initialize the upsampler
    upsampler = PixtralPromptUpsampler(
        checkpoint_dir=args.checkpoint_dir,
        offload_prompt_upsampler=args.offload
    )
    
    # Process prompts
    results = []
    
    if args.batch_file:
        print(f"\nLoading batch file: {args.batch_file}")
        with open(args.batch_file, 'r') as f:
            batch_data = json.load(f)
        
        for item in batch_data:
            prompt = item.get('prompt', '')
            name = item.get('name', 'unnamed')
            video = item.get('video_path', args.input_video)
            
            print(f"\nProcessing: {name}")
            print(f"  Original: {prompt[:80]}...")
            
            if args.offload:
                upsampled = upsampler._prompt_upsample_with_offload(prompt, video)
            else:
                upsampled = upsampler._prompt_upsample(prompt, video)
            
            print(f"  Upsampled: {upsampled[:80]}...")
            
            results.append({
                'name': name,
                'original_prompt': prompt,
                'upsampled_prompt': upsampled,
                'video_path': video
            })
    else:
        # Single prompt
        print(f"\nProcessing single prompt")
        print(f"  Original: {args.prompt[:80]}...")
        
        if args.offload:
            upsampled = upsampler._prompt_upsample_with_offload(args.prompt, args.input_video)
        else:
            upsampled = upsampler._prompt_upsample(args.prompt, args.input_video)
        
        print(f"  Upsampled: {upsampled[:80]}...")
        
        results = [{
            'original_prompt': args.prompt,
            'upsampled_prompt': upsampled,
            'video_path': args.input_video
        }]
    
    # Save results
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {args.output_file}")
    
    # Print upsampled text for easy capture
    print("\n=== UPSAMPLED RESULTS ===")
    for r in results:
        if 'name' in r:
            print(f"\n{r['name']}:")
        print(r['upsampled_prompt'])
    print("========================\n")


if __name__ == "__main__":
    # IMPORTANT: Don't use the upsampler_pipeline.py __main__ logic
    # We handle environment setup ourselves
    main()