#!/usr/bin/env python3
"""Import JSON prompts from 2025-09-03 into the database using cosmos create prompt."""

import json
import subprocess
from pathlib import Path

# Directory containing JSON prompts
prompts_dir = Path("inputs/prompts/2025-09-03")

# Get all JSON files
json_files = sorted(prompts_dir.glob("*.json"))

print(f"Found {len(json_files)} JSON files to import")

successful = 0
failed = 0

for json_file in json_files:
    try:
        # Read the JSON file
        with open(json_file) as f:
            data = json.load(f)

        # Extract fields
        name = data.get("name", json_file.stem)
        prompt_text = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")

        # Fix Windows paths to Unix style
        input_video = data.get("input_video_path", "").replace("\\", "/")
        control_inputs = data.get("control_inputs", {})
        depth_video = (
            control_inputs.get("depth", "").replace("\\", "/") if "depth" in control_inputs else ""
        )
        seg_video = (
            control_inputs.get("seg", "").replace("\\", "/") if "seg" in control_inputs else ""
        )

        # Extract just the video directory name
        if input_video:
            # Extract the directory name from the path
            video_dir = Path(input_video).parent

            # Build the cosmos create prompt command
            cmd = ["cosmos", "create", "prompt", prompt_text, str(video_dir)]

            # Add optional parameters
            if negative_prompt:
                cmd.extend(["--negative", negative_prompt])
            if name:
                cmd.extend(["--name", name])

            print(f"\nImporting: {name}")
            print(f"  Video dir: {video_dir}")

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Extract prompt ID from output
                output = result.stdout.strip()
                if "Created prompt:" in output:
                    prompt_id = output.split("Created prompt:")[1].strip().split()[0]
                    print(f"  Success! Created prompt: {prompt_id}")
                    successful += 1
                else:
                    print(f"  Success! Output: {output}")
                    successful += 1
            else:
                print(f"  Failed: {result.stderr}")
                failed += 1
        else:
            print(f"\nSkipping {name}: No input video path")
            failed += 1

    except Exception as e:
        print(f"\nError processing {json_file.name}: {e}")
        failed += 1

print(f"\n{'=' * 50}")
print("Import complete!")
print(f"  Successful: {successful}")
print(f"  Failed: {failed}")
print(f"  Total: {len(json_files)}")
