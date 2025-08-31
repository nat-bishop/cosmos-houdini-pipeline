#!/usr/bin/env python3
"""
Test script to verify the upsampler approach works locally.
This simulates what would run inside the Docker container.
"""

import json
import os
import sys
from pathlib import Path

# CRITICAL: Set VLLM spawn method BEFORE imports
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

# Set torch elastic defaults
env_defaults = {
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

print("[TEST] Setting environment variables...")
for k, v in env_defaults.items():
    os.environ.setdefault(k, v)
    print(f"  {k}={v}")

print(f"\n[TEST] VLLM_WORKER_MULTIPROC_METHOD={os.environ.get('VLLM_WORKER_MULTIPROC_METHOD')}")

# Try to import the upsampler
print("\n[TEST] Attempting to import PixtralPromptUpsampler...")
try:
    # Add cosmos-transfer1 to path if needed
    cosmos_path = Path("F:/Art/cosmos-transfer1")
    if cosmos_path.exists() and str(cosmos_path) not in sys.path:
        sys.path.insert(0, str(cosmos_path))
        print(f"[TEST] Added to Python path: {cosmos_path}")
    
    from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
    print("[SUCCESS] Import successful!")
    
    # Try to check if the class has the expected methods
    print("\n[TEST] Checking class methods...")
    methods = [m for m in dir(PixtralPromptUpsampler) if not m.startswith('_')]
    print(f"  Public methods: {methods}")
    
    # Check for the key methods we need
    required_methods = ['_prompt_upsample', '_prompt_upsample_with_offload']
    for method in required_methods:
        if hasattr(PixtralPromptUpsampler, method):
            print(f"  ✓ Found method: {method}")
        else:
            print(f"  ✗ Missing method: {method}")
    
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    print("\nMake sure you have:")
    print("1. cosmos-transfer1 repository at F:/Art/cosmos-transfer1")
    print("2. All required dependencies installed")
    sys.exit(1)

print("\n[TEST] Test complete - approach should work!")
print("\nTo use on remote GPU:")
print("1. Upload scripts/working_prompt_upsampler.py to remote")
print("2. Run via Docker with the environment variables set")
print("3. Or run scripts/run_upsampler_docker.sh on the remote machine")