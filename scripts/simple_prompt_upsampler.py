#!/usr/bin/env python3
"""Simple prompt upsampler for Cosmos-Transfer1 without distributed training complexity.

This script:
- Loads the Pixtral model once
- Processes multiple prompts from a JSON file
- Saves upsampled results
- Doesn't require distributed training environment variables
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add cosmos_transfer1 to path if needed
sys.path.append('/workspace')

from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
from cosmos_transfer1.utils.misc import extract_video_frames


def load_prompts_batch(batch_file: str) -> List[Dict[str, Any]]:
    """Load prompts from a batch JSON file."""
    with open(batch_file, 'r') as f:
        return json.load(f)


def save_results(results: List[Dict[str, Any]], output_file: str):
    """Save upsampled results to JSON file."""
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Simple batch prompt upsampler")
    parser.add_argument("--batch-file", type=str, required=True,
                        help="JSON file with prompts to upsample")
    parser.add_argument("--output-file", type=str, required=True,
                        help="Output JSON file for upsampled prompts")
    parser.add_argument("--checkpoint-dir", type=str, default="/workspace/checkpoints",
                        help="Directory containing model checkpoints")
    parser.add_argument("--default-video", type=str, 
                        default="/workspace/inputs/videos/color.mp4",
                        help="Default video to use if not specified in batch")
    parser.add_argument("--offload-model", action="store_true",
                        help="Offload model after each prompt (saves memory but slower)")
    parser.add_argument("--num-frames", type=int, default=2,
                        help="Number of frames to extract from video")
    
    args = parser.parse_args()
    
    print(f"Loading prompts from: {args.batch_file}")
    prompts_batch = load_prompts_batch(args.batch_file)
    
    print(f"Initializing Pixtral upsampler model...")
    print(f"Checkpoint dir: {args.checkpoint_dir}")
    
    # Initialize model (loads once unless offloading is enabled)
    upsampler = PixtralPromptUpsampler(
        checkpoint_dir=args.checkpoint_dir,
        offload_prompt_upsampler=args.offload_model
    )
    
    results = []
    
    for i, item in enumerate(prompts_batch):
        print(f"\nProcessing prompt {i+1}/{len(prompts_batch)}: {item.get('name', 'unnamed')}")
        
        prompt_text = item.get('prompt', '')
        video_path = item.get('video_path', args.default_video)
        
        # Skip if no prompt
        if not prompt_text:
            print(f"  Skipping: No prompt text provided")
            results.append({
                'name': item.get('name', 'unnamed'),
                'original_prompt': prompt_text,
                'upsampled_prompt': '',
                'error': 'No prompt text provided'
            })
            continue
        
        try:
            # Extract frames from video
            if os.path.exists(video_path):
                print(f"  Using video: {video_path}")
                # The upsampler will handle frame extraction internally
            else:
                print(f"  Warning: Video not found: {video_path}")
                print(f"  Using default: {args.default_video}")
                video_path = args.default_video
            
            # Upsample the prompt
            print(f"  Upsampling prompt...")
            if args.offload_model:
                # Use the offload method that handles loading/unloading
                upsampled = upsampler._prompt_upsample_with_offload(prompt_text, video_path)
            else:
                # Direct upsampling (model stays loaded)
                upsampled = upsampler._prompt_upsample(prompt_text, video_path)
            
            print(f"  ✓ Upsampled successfully")
            
            # Store result
            results.append({
                'name': item.get('name', 'unnamed'),
                'spec_id': item.get('spec_id', ''),
                'original_prompt': prompt_text,
                'upsampled_prompt': upsampled,
                'video_path': video_path
            })
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({
                'name': item.get('name', 'unnamed'),
                'original_prompt': prompt_text,
                'upsampled_prompt': '',
                'error': str(e)
            })
    
    # Save all results
    save_results(results, args.output_file)
    
    print(f"\nCompleted {len(results)} prompts")
    successful = sum(1 for r in results if r.get('upsampled_prompt'))
    print(f"Successful: {successful}/{len(results)}")


if __name__ == "__main__":
    # No distributed training setup needed!
    main()