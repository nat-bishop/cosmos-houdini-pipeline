#!/usr/bin/env python3
"""Batch token test - loads model once, tests all videos."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager()
remote_config = config_manager.get_remote_config()
ssh_options = config_manager.get_ssh_options()

print("[INFO] Batch Token Test - Model loads once!")
print("=" * 60)

with SSHManager(ssh_options) as ssh:
    # First, create all test videos
    print("\n[1/2] Creating test videos...")
    
    test_configs = [
        ("320x180_2f", 320, 180, 2),  # Known to work
        ("360x203_2f", 360, 203, 2),
        ("400x225_2f", 400, 225, 2),
        ("440x248_2f", 440, 248, 2),
        ("480x270_2f", 480, 270, 2),
        ("520x293_2f", 520, 293, 2),
        ("560x315_2f", 560, 315, 2),
        ("600x338_2f", 600, 338, 2),
        ("640x360_2f", 640, 360, 2),
        # Frame count tests
        ("320x180_1f", 320, 180, 1),
        ("320x180_3f", 320, 180, 3),
        ("320x180_4f", 320, 180, 4),
        ("320x180_5f", 320, 180, 5),
        # Prompt length test videos (all same size)
        ("320x180_prompt", 320, 180, 2),
    ]
    
    for name, width, height, frames in test_configs:
        cmd = f"""
        cd {remote_config.remote_dir}
        ffmpeg -y -i inputs/videos/city_scene_20250830_203504/color.mp4 \
            -vf "scale={width}:{height}:flags=lanczos" \
            -vframes {frames} \
            -c:v libx264 -preset ultrafast -pix_fmt yuv420p \
            inputs/videos/test_{name}.mp4 2>/dev/null
        """
        ssh.execute_command_success(cmd, timeout=10)
        print(f"  Created: test_{name}.mp4")
    
    # Create Python test script that runs all tests with one model load
    print("\n[2/2] Running all tests with single model load...")
    
    test_script = f"""
cd {remote_config.remote_dir}

cat > batch_test.py << 'EOF'
import os, sys, re, json
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

# Set environment
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1'),
             ('LOCAL_WORLD_SIZE', '1'), ('GROUP_RANK', '0'), ('ROLE_RANK', '0'),
             ('ROLE_NAME', 'default'), ('OMP_NUM_THREADS', '4'),
             ('MASTER_ADDR', '127.0.0.1'), ('MASTER_PORT', '29500')]:
    os.environ.setdefault(k, v)

print('[LOADING] Initializing model (this takes ~90 seconds)...')
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=False  # KEEP MODEL LOADED!
)
print('[READY] Model loaded! Running tests...')
print('=' * 60)

results = []

# Test 1: Resolution impact
print('\\nTEST 1: Resolution Impact (2 frames, short prompt)')
print('-' * 40)
for name in ['320x180_2f', '360x203_2f', '400x225_2f', '440x248_2f', 
             '480x270_2f', '520x293_2f', '560x315_2f', '600x338_2f', '640x360_2f']:
    video_path = f'/workspace/inputs/videos/test_{{name}}.mp4'
    try:
        result = upsampler._prompt_upsample('A sunset', video_path)
        print(f'  ✓ {{name}}: PASS (< 4096 tokens)')
        results.append({{'test': name, 'result': 'pass'}})
    except ValueError as e:
        if 'longer than' in str(e):
            match = re.search(r'Prompt length of (\\d+)', str(e))
            tokens = match.group(1) if match else '?'
            print(f'  ✗ {{name}}: FAIL ({{tokens}} tokens)')
            results.append({{'test': name, 'result': 'fail', 'tokens': int(tokens)}})
        else:
            print(f'  ? {{name}}: ERROR')
            results.append({{'test': name, 'result': 'error'}})

# Test 2: Frame count impact
print('\\nTEST 2: Frame Count Impact (320x180, short prompt)')
print('-' * 40)
for name in ['320x180_1f', '320x180_2f', '320x180_3f', '320x180_4f', '320x180_5f']:
    video_path = f'/workspace/inputs/videos/test_{{name}}.mp4'
    try:
        result = upsampler._prompt_upsample('A sunset', video_path)
        frames = name.split('_')[1].replace('f', '')
        print(f'  ✓ {{frames}} frame(s): PASS')
        results.append({{'test': name, 'result': 'pass'}})
    except ValueError as e:
        if 'longer than' in str(e):
            match = re.search(r'Prompt length of (\\d+)', str(e))
            tokens = match.group(1) if match else '?'
            frames = name.split('_')[1].replace('f', '')
            print(f'  ✗ {{frames}} frame(s): FAIL ({{tokens}} tokens)')
            results.append({{'test': name, 'result': 'fail', 'tokens': int(tokens)}})

# Test 3: Prompt length impact
print('\\nTEST 3: Prompt Length Impact (320x180, 2 frames)')
print('-' * 40)
prompts = [
    ("5 words", "A beautiful golden ocean sunset"),
    ("25 words", " ".join(["sunset"] * 25)),
    ("50 words", " ".join(["sunset"] * 50)),
    ("100 words", " ".join(["sunset"] * 100)),
    ("200 words", " ".join(["sunset"] * 200)),
]

video_path = '/workspace/inputs/videos/test_320x180_prompt.mp4'
for label, prompt in prompts:
    try:
        result = upsampler._prompt_upsample(prompt, video_path)
        print(f'  ✓ {{label}}: PASS')
        results.append({{'test': f'prompt_{{label}}', 'result': 'pass'}})
    except ValueError as e:
        if 'longer than' in str(e):
            match = re.search(r'Prompt length of (\\d+)', str(e))
            tokens = match.group(1) if match else '?'
            print(f'  ✗ {{label}}: FAIL ({{tokens}} tokens)')
            results.append({{'test': f'prompt_{{label}}', 'result': 'fail', 'tokens': int(tokens)}})

# Analysis
print('\\n' + '=' * 60)
print('ANALYSIS')
print('=' * 60)

# Find resolution threshold
resolution_tests = [r for r in results if '_2f' in r['test'] and 'prompt' not in r['test']]
last_pass_res = None
first_fail_res = None
for r in resolution_tests:
    if r['result'] == 'pass':
        last_pass_res = r['test']
    elif r['result'] == 'fail' and not first_fail_res:
        first_fail_res = r['test']
        fail_tokens = r.get('tokens', '?')

if last_pass_res and first_fail_res:
    print(f'\\nResolution threshold (2 frames):')
    print(f'  Last passing: {{last_pass_res}}')
    print(f'  First failing: {{first_fail_res}} ({{fail_tokens}} tokens)')
    
    # Calculate approximate tokens per pixel
    if isinstance(fail_tokens, int):
        dims = first_fail_res.split('_')[0].split('x')
        width, height = int(dims[0]), int(dims[1])
        pixels = width * height * 2  # 2 frames
        tokens_per_1k_pixels = (fail_tokens - 100) / (pixels / 1000)  # Subtract ~100 for prompt
        print(f'  Approx: ~{{tokens_per_1k_pixels:.1f}} tokens per 1K pixels')

# Frame count threshold
frame_tests = [r for r in results if '320x180_' in r['test'] and 'prompt' not in r['test']]
print(f'\\nFrame count threshold (320x180):')
for r in frame_tests:
    frames = r['test'].split('_')[1].replace('f', '')
    status = 'PASS' if r['result'] == 'pass' else f"FAIL ({{r.get('tokens', '?')}} tokens)"
    print(f'  {{frames}} frame(s): {{status}}')

# Save results
with open('/workspace/outputs/batch_token_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print('\\n[DONE] All tests complete!')
EOF

# Run the batch test
sudo docker run --rm --gpus all \
    -v {remote_config.remote_dir}:/workspace \
    -w /workspace \
    -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
    -e CUDA_VISIBLE_DEVICES=0 \
    {remote_config.docker_image} \
    python /workspace/batch_test.py
"""
    
    try:
        output = ssh.execute_command(test_script, timeout=300, stream_output=False)
        exit_code, stdout, stderr = output
        
        # Print the output
        if "[READY]" in stdout:
            # Extract everything after model loaded
            ready_idx = stdout.find("[READY]")
            test_output = stdout[ready_idx:]
            print(test_output)
        else:
            print("Full output:")
            print(stdout[-5000:] if len(stdout) > 5000 else stdout)
            
    except Exception as e:
        print(f"Error: {e}")

print("\n[COMPLETE] Check outputs/batch_token_results.json for detailed results")