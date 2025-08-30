#!/usr/bin/env python3
"""
Batch prompt upsampling script for Cosmos Transfer.
Processes multiple prompts without running full inference.
Handles video preprocessing to avoid vocab out of range errors.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

# Add cosmos_transfer1 to path
sys.path.append("/home/ubuntu/NatsFS/cosmos-transfer1")

import cv2
import torch
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler


def preprocess_video_for_upsampling(
    video_path: str,
    max_resolution: int = 480,
    num_frames: int = 2,
    output_dir: Optional[str] = None
) -> str:
    """
    Preprocess video to avoid vocab out of range errors.
    
    Args:
        video_path: Path to input video
        max_resolution: Maximum height/width (will maintain aspect ratio)
        num_frames: Number of frames to extract
        output_dir: Directory for preprocessed video (uses temp if None)
    
    Returns:
        Path to preprocessed video
    """
    if not os.path.exists(video_path):
        print(f"Warning: Video not found at {video_path}, skipping preprocessing")
        return video_path
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Warning: Could not open video {video_path}, using original")
        return video_path
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate new dimensions
    if width > max_resolution or height > max_resolution:
        if width > height:
            new_width = max_resolution
            new_height = int(height * (max_resolution / width))
        else:
            new_height = max_resolution
            new_width = int(width * (max_resolution / height))
        print(f"Resizing video from {width}x{height} to {new_width}x{new_height}")
    else:
        new_width, new_height = width, height
    
    # Create output path
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"preprocessed_{os.path.basename(video_path)}")
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
    
    # Process frames
    frame_interval = max(1, total_frames // num_frames) if num_frames < total_frames else 1
    frames_written = 0
    frame_idx = 0
    
    while cap.isOpened() and frames_written < num_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % frame_interval == 0:
            # Resize frame
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            out.write(resized_frame)
            frames_written += 1
        
        frame_idx += 1
    
    cap.release()
    out.release()
    
    print(f"Preprocessed video saved to {output_path} ({frames_written} frames)")
    return output_path


def process_prompt_batch(
    prompts: List[Dict],
    checkpoint_dir: str,
    preprocess_videos: bool = True,
    max_resolution: int = 480,
    num_frames: int = 2,
    output_file: str = "upsampled_prompts.json"
) -> List[Dict]:
    """
    Process a batch of prompts with upsampling.
    
    Args:
        prompts: List of prompt dictionaries with 'prompt' and 'video_path' keys
        checkpoint_dir: Path to model checkpoints
        preprocess_videos: Whether to preprocess videos to avoid vocab errors
        max_resolution: Max resolution for preprocessing
        num_frames: Number of frames to extract
        output_file: Path to save upsampled prompts
    
    Returns:
        List of dictionaries with original and upsampled prompts
    """
    print(f"Initializing prompt upsampler with checkpoint dir: {checkpoint_dir}")
    
    # Initialize upsampler (keep model loaded for batch processing)
    upsampler = PixtralPromptUpsampler(
        checkpoint_dir=checkpoint_dir,
        offload_prompt_upsampler=False  # Keep model loaded
    )
    
    results = []
    temp_videos = []
    
    try:
        for i, prompt_data in enumerate(prompts):
            print(f"\n[{i+1}/{len(prompts)}] Processing prompt: {prompt_data.get('name', 'unnamed')}")
            
            original_prompt = prompt_data.get('prompt', '')
            video_path = prompt_data.get('video_path', '')
            
            # Preprocess video if needed
            if preprocess_videos and video_path:
                print(f"Preprocessing video: {video_path}")
                processed_video = preprocess_video_for_upsampling(
                    video_path, 
                    max_resolution=max_resolution,
                    num_frames=num_frames
                )
                temp_videos.append(processed_video)
            else:
                processed_video = video_path
            
            # Upsample prompt
            try:
                print(f"Original prompt: {original_prompt[:100]}...")
                upsampled = upsampler._prompt_upsample(
                    prompt=original_prompt,
                    video_path=processed_video if processed_video else None
                )
                print(f"Upsampled prompt: {upsampled[:100]}...")
                
                result = {
                    'name': prompt_data.get('name', f'prompt_{i}'),
                    'original_prompt': original_prompt,
                    'upsampled_prompt': upsampled,
                    'video_path': video_path,
                    'preprocessed_video': processed_video if preprocess_videos else None
                }
                results.append(result)
                
            except Exception as e:
                print(f"Error upsampling prompt: {e}")
                results.append({
                    'name': prompt_data.get('name', f'prompt_{i}'),
                    'original_prompt': original_prompt,
                    'upsampled_prompt': original_prompt,  # Fallback to original
                    'error': str(e)
                })
        
        # Save results
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")
        
    finally:
        # Cleanup temporary videos
        for temp_video in temp_videos:
            if temp_video and os.path.exists(temp_video) and 'preprocessed_' in temp_video:
                try:
                    os.remove(temp_video)
                except:
                    pass
        
        # Offload model to free memory
        if hasattr(upsampler, '_offload_upsampler_model'):
            upsampler._offload_upsampler_model()
        
        # Clear GPU cache
        torch.cuda.empty_cache()
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Batch prompt upsampling for Cosmos Transfer")
    parser.add_argument(
        "--prompts-file", 
        type=str, 
        required=True,
        help="JSON file containing prompts to upsample"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="/home/ubuntu/NatsFS/cosmos-transfer1/checkpoints",
        help="Base directory containing model checkpoints"
    )
    parser.add_argument(
        "--preprocess-videos",
        action="store_true",
        default=True,
        help="Preprocess videos to avoid vocab errors"
    )
    parser.add_argument(
        "--max-resolution",
        type=int,
        default=480,
        help="Maximum resolution for video preprocessing"
    )
    parser.add_argument(
        "--num-frames",
        type=int,
        default=2,
        help="Number of frames to extract from videos"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="upsampled_prompts.json",
        help="Output file for upsampled prompts"
    )
    
    args = parser.parse_args()
    
    # Load prompts
    with open(args.prompts_file, 'r') as f:
        prompts = json.load(f)
    
    if not isinstance(prompts, list):
        # If it's a single prompt spec, wrap in list
        prompts = [prompts]
    
    print(f"Loaded {len(prompts)} prompts from {args.prompts_file}")
    
    # Process batch
    results = process_prompt_batch(
        prompts=prompts,
        checkpoint_dir=args.checkpoint_dir,
        preprocess_videos=args.preprocess_videos,
        max_resolution=args.max_resolution,
        num_frames=args.num_frames,
        output_file=args.output_file
    )
    
    print(f"\nSuccessfully upsampled {len(results)} prompts")
    

if __name__ == "__main__":
    # Check if running with torchrun
    if "RANK" in os.environ:
        # Remove torchrun environment variables for vLLM
        rank = int(os.environ["RANK"])
        
        dist_keys = [
            "RANK", "LOCAL_RANK", "WORLD_SIZE", "LOCAL_WORLD_SIZE",
            "GROUP_RANK", "ROLE_RANK", "ROLE_NAME", "OMP_NUM_THREADS",
            "MASTER_ADDR", "MASTER_PORT", "TORCHELASTIC_USE_AGENT_STORE",
            "TORCHELASTIC_MAX_RESTARTS", "TORCHELASTIC_RUN_ID",
            "TORCH_NCCL_ASYNC_ERROR_HANDLING", "TORCHELASTIC_ERROR_FILE"
        ]
        
        for key in dist_keys:
            if key in os.environ:
                del os.environ[key]
        
        if rank == 0:
            main()
    else:
        main()