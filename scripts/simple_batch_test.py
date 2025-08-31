#!/usr/bin/env python3
"""Simple batch token test - loads model once, tests multiple videos."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager()
remote_config = config_manager.get_remote_config()
ssh_options = config_manager.get_ssh_options()

print("[INFO] Simple Batch Token Test")
print("=" * 60)

with SSHManager(ssh_options) as ssh:
    # Create a Python script that does everything
    batch_script = """#!/usr/bin/env python3
import os, sys, re, json, subprocess
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

# Set environment
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1'),
             ('LOCAL_WORLD_SIZE', '1'), ('GROUP_RANK', '0'), ('ROLE_RANK', '0'),
             ('ROLE_NAME', 'default'), ('OMP_NUM_THREADS', '4'),
             ('MASTER_ADDR', '127.0.0.1'), ('MASTER_PORT', '29500')]:
    os.environ.setdefault(k, v)

# Test configurations
tests = [
    # Resolution tests (2 frames)
    ("320x180", 320, 180, 2),
    ("400x225", 400, 225, 2),
    ("480x270", 480, 270, 2),
    ("560x315", 560, 315, 2),
    ("640x360", 640, 360, 2),
    # Frame tests (320x180)
    ("320x180_1f", 320, 180, 1),
    ("320x180_3f", 320, 180, 3),
    ("320x180_4f", 320, 180, 4),
]

print('[PREP] Creating test videos...')
for name, width, height, frames in tests:
    video_file = f'/workspace/inputs/videos/test_{name}.mp4'
    cmd = [
        'ffmpeg', '-y', '-i', '/workspace/inputs/videos/city_scene_20250830_203504/color.mp4',
        '-vf', f'scale={width}:{height}',
        '-vframes', str(frames),
        '-c:v', 'libx264', '-preset', 'ultrafast',
        video_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'  Created: {name}')

print('\\n[LOADING] Initializing model (~90 seconds)...')
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=False  # Keep loaded!
)
print('[READY] Model loaded!')
print('=' * 60)

results = []
print('\\nRunning tests (fast since model is loaded):')
for name, width, height, frames in tests:
    video_path = f'/workspace/inputs/videos/test_{name}.mp4'
    try:
        result = upsampler._prompt_upsample('Sunset', video_path)
        print(f'  ✓ {name}: PASS')
        results.append({'test': name, 'w': width, 'h': height, 'f': frames, 'result': 'pass'})
    except ValueError as e:
        if 'longer than' in str(e):
            match = re.search(r'Prompt length of (\\\\d+)', str(e))
            tokens = int(match.group(1)) if match else 0
            print(f'  ✗ {name}: FAIL ({tokens} tokens)')
            results.append({'test': name, 'w': width, 'h': height, 'f': frames, 
                          'result': 'fail', 'tokens': tokens})
        else:
            print(f'  ? {name}: ERROR - {str(e)[:50]}')
            results.append({'test': name, 'w': width, 'h': height, 'f': frames, 'result': 'error'})

# Analysis
print('\\n' + '=' * 60)
print('FINDINGS:')

# Resolution threshold
res_tests = [r for r in results if r['f'] == 2]
last_pass = None
first_fail = None
for r in res_tests:
    if r['result'] == 'pass':
        last_pass = r
    elif r['result'] == 'fail' and not first_fail:
        first_fail = r

if last_pass and first_fail:
    print(f"\\nResolution threshold (2 frames):")
    print(f"  ✓ Passes at: {last_pass['w']}x{last_pass['h']}")
    print(f"  ✗ Fails at: {first_fail['w']}x{first_fail['h']} ({first_fail.get('tokens', '?')} tokens)")
    
    # Estimate tokens per pixel
    if first_fail.get('tokens'):
        pixels = first_fail['w'] * first_fail['h'] * 2
        # Subtract ~50 for prompt overhead
        video_tokens = first_fail['tokens'] - 50
        tokens_per_1k = video_tokens / (pixels / 1000)
        print(f"  → Approximately {tokens_per_1k:.1f} tokens per 1K pixels")

# Frame threshold
print(f"\\nFrame count impact (320x180):")
frame_tests = [r for r in results if r['w'] == 320 and r['h'] == 180]
for r in sorted(frame_tests, key=lambda x: x['f']):
    status = "✓ PASS" if r['result'] == 'pass' else f"✗ FAIL ({r.get('tokens', '?')} tokens)"
    print(f"  {r['f']} frame(s): {status}")

# Save results
with open('/workspace/outputs/token_test_results.json', 'w') as f:
    json.dump(results, f, indent=2)
    
print('\\n[DONE] Results saved to outputs/token_test_results.json')
"""
    
    # Save script on remote
    print("\nUploading test script...")
    with ssh.get_sftp() as sftp:
        script_path = f"{remote_config.remote_dir}/batch_token_test.py"
        import io
        sftp.putfo(io.BytesIO(batch_script.encode()), script_path)
    
    # Run the test
    print("Running batch test (model loads once, then all tests are fast)...")
    cmd = f"""
    cd {remote_config.remote_dir}
    sudo docker run --rm --gpus all \
        -v {remote_config.remote_dir}:/workspace \
        -w /workspace \
        -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
        -e CUDA_VISIBLE_DEVICES=0 \
        {remote_config.docker_image} \
        python /workspace/batch_token_test.py
    """
    
    try:
        output = ssh.execute_command(cmd, timeout=300, stream_output=False)
        exit_code, stdout, stderr = output
        
        # Show results
        if "[READY]" in stdout:
            ready_idx = stdout.find("[READY]")
            results_output = stdout[ready_idx:]
            print(results_output)
        else:
            # Show last part of output
            print(stdout[-3000:] if len(stdout) > 3000 else stdout)
            
        # Download results file
        print("\nDownloading results...")
        with ssh.get_sftp() as sftp:
            try:
                sftp.get(f"{remote_config.remote_dir}/outputs/token_test_results.json",
                        "outputs/token_test_results.json")
                print("Results saved to outputs/token_test_results.json")
            except:
                pass
                
    except Exception as e:
        print(f"Error: {e}")

print("\n[COMPLETE]")