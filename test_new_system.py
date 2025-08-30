#!/usr/bin/env python3
"""
Test script for the new prompt system.
"""

import sys
from pathlib import Path

# Add the cosmos_workflow package to the path
sys.path.insert(0, str(Path(__file__).parent))

from cosmos_workflow.prompts.schemas import (
    PromptSpec, RunSpec, SchemaUtils, DirectoryManager,
    ExecutionStatus, BlurStrength, CannyThreshold
)
from cosmos_workflow.prompts.prompt_manager import PromptManager

def test_new_system():
    """Test the new prompt system."""
    print("🚀 Testing New Prompt System\n")
    
    try:
        # Create a PromptManager
        prompt_manager = PromptManager()
        print("✅ PromptManager created successfully")
        
        # Create a PromptSpec
        prompt_spec = prompt_manager.create_prompt_spec(
            name="test_cyberpunk_city",
            prompt_text="Cyberpunk city at night with neon lights and glowing streets",
            negative_prompt="bad quality, blurry, low resolution",
            control_inputs={
                "depth": "inputs/videos/test_cyberpunk_city/depth.mp4",
                "seg": "inputs/videos/test_cyberpunk_city/segmentation.mp4"
            }
        )
        print(f"✅ Created PromptSpec: {prompt_spec.id}")
        
        # Create a RunSpec
        run_spec = prompt_manager.create_run_spec(
            prompt_spec=prompt_spec,
            control_weights={
                "vis": 0.30,
                "edge": 0.40,
                "depth": 0.20,
                "seg": 0.10
            },
            parameters={
                "num_steps": 50,
                "guidance": 8.5,
                "sigma_max": 75.0,
                "blur_strength": "high",
                "canny_threshold": "medium",
                "fps": 30,
                "seed": 42
            }
        )
        print(f"✅ Created RunSpec: {run_spec.id}")
        
        print("\n🎉 New prompt system test completed successfully!")
        print(f"PromptSpec ID: {prompt_spec.id}")
        print(f"RunSpec ID: {run_spec.id}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_system()
