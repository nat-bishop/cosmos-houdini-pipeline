#!/usr/bin/env python3
"""Verify the NVIDIA JSON format we generate from database entries."""

from cosmos_workflow.utils import nvidia_format

# Create sample data like what's in the database
prompt_dict = {
    "id": "ps_fc66154c0f4898557578",
    "prompt_text": "test database prompt",
    "negative_prompt": "",  # Not stored in our parameters, would need to extract
    "inputs": {
        "video": "inputs/videos/city_scene_20250830_203504/color.mp4",
        "depth": "inputs/videos/city_scene_20250830_203504/depth.mp4",
        "seg": "inputs/videos/city_scene_20250830_203504/segmentation.mp4",
    },
    "parameters": {
        "negative_prompt": "The video captures a game playing, with bad crappy graphics...",
        "name": "database_prompt_test",
    },
}

run_dict = {
    "id": "rs_3b2a92ee789c47db8df6ea95e594de01",
    "prompt_id": "ps_fc66154c0f4898557578",
    "execution_config": {
        "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
        "num_steps": 35,
        "guidance": 7.0,
        "sigma_max": 70.0,
        "blur_strength": "medium",
        "canny_threshold": "medium",
        "fps": 24,
        "seed": 1,
    },
}

# Convert to NVIDIA format
nvidia_json = nvidia_format.to_cosmos_inference_json(prompt_dict, run_dict)

# Print the result

# Also test upscale format
upscale_json = nvidia_format.to_cosmos_upscale_json(prompt_dict, run_dict, upscale_weight=0.5)
