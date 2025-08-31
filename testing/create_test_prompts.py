#!/usr/bin/env python3
"""Create test prompt specs from predefined atmospheric lighting prompts."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# User's atmospheric lighting prompts
TEST_PROMPTS = [
    {
        "id": "pre_dawn_blue_hour_calm",
        "text": "Cool slate-blue ambient light before sunrise; low overall luminance; faint tungsten or LED warmth from existing interior sources; colors slightly desaturated; air crisp and clear; metal and glass respond with subtle, cold reflections; deep, quiet shadows with soft edges."
    },
    {
        "id": "golden_hour_warmth",
        "text": "Warm low-angle sunlight grazing facades; gentle rim light on metal trims and window mullions; long soft shadows; color separation between warm sunlit areas and cooler skylit normals; moderate contrast without clipping; textures read with pleasant micro-contrast."
    },
    {
        "id": "overcast_noon_softness",
        "text": "Uniform cloud cover acting as a giant softbox; minimal shadowing; lowered contrast and saturation; materials appear matte and evenly lit; fine details remain visible without specular hotspots; neutral, balanced palette."
    },
    {
        "id": "just_after_rain_sheen",
        "text": "Surfaces darkened by recent rainfall; shallow puddling along natural low spots and seams; anisotropic specular glints on asphalt and stone; reflections tight and legible; slightly clearer air; palette deepened but natural; no visible rainfall, only wet response."
    },
    {
        "id": "steady_light_drizzle",
        "text": "Fine rain streaks at mid-distance; softened local contrast; wet ground with gentle specular break-up; colors subtly muted; highlights show controlled bloom on glossy materials; distant planes slightly desaturated."
    },
    {
        "id": "morning_condensation_on_glass",
        "text": "Cool morning humidity produces faint condensation and edge diffusion on windows; interior light appears soft and milky through glass; exterior materials remain dry; overall grade cool-neutral with delicate highlight roll-off."
    },
    {
        "id": "foggy_early_morning",
        "text": "Low-lying mist with gradual falloff; aerial perspective increasing with distance; far edges soften and desaturate; nearby materials retain clear texture; luminance uniform; speculars subdued by moisture in the air."
    },
    {
        "id": "light_snow_flurries_thin_settling",
        "text": "Sparse snowflakes drifting; ultra-thin accumulation only on flat, upward-facing ledges and rails; white balance slightly cooler; reflections dampened; atmosphere clean and quiet; underlying surfaces remain readable."
    },
    {
        "id": "hot_dry_midday_heat_shimmer",
        "text": "High sun and sun-bleached palette; subtle near-ground shimmer; lifted black point; metals and glass with crisp, hard highlights; shadows short and defined; textures appear sun-baked without exaggerated haze."
    },
    {
        "id": "cleaned_glass_polished_reflections",
        "text": "Recently cleaned glazing increases clarity and mirror-like reflections within plausible intensity; interiors visible where backlit; specular highlights well controlled; adjacent materials unchanged; overall look crisp and high-acuity."
    },
    {
        "id": "rain_darkened_stone_concrete",
        "text": "Stone tiles and concrete deepen in color; grout lines darken; micro-puddling in hairline depressions; specular response tighter and more directional; slight saturation increase from wetness while staying realistic."
    },
    {
        "id": "subtle_metal_patina",
        "text": "Existing metal elements gain a light oxidized sheen—matte microtexture with gentle green-brown hints in creases; softened highlights; surrounding materials untouched; overall feel gently weathered, not distressed."
    },
    {
        "id": "urban_haze_at_dusk",
        "text": "Warm–cool split near twilight with thin particulate haze; distant planes desaturate and warm slightly; practical lights halo subtly; midtones compress for a smooth cinematic roll-off; nearby textures remain clear."
    },
    {
        "id": "night_active_practicals",
        "text": "Deep, clean shadows punctuated by existing luminaires and interior lighting; high dynamic range; tight speculars on glossy materials; warm practicals balanced by cool ambient; shadow noise low and natural."
    },
    {
        "id": "night_after_rain_reflective_pavements",
        "text": "Dark, glossy ground planes carry crisp reflections of existing light sources; saturated color blooms are controlled and local; textures beneath remain readable; contrast deep yet stable; slight atmospheric humidity supports halation."
    },
    {
        "id": "dry_to_wet_progression",
        "text": "Gradual increase in surface wetness over time: matte to semi-gloss on stone and asphalt; micro-puddles forming along edges; specular intensity and reflection clarity slowly rising; atmosphere consistent and believable throughout."
    }
]


def create_prompt_specs_cli(prompts, video_path=None, output_dir="inputs/prompts"):
    """Create prompt specs using the CLI for each prompt.
    
    Args:
        prompts: List of prompt dictionaries with 'id' and 'text'
        video_path: Optional path to video file to use for all prompts
        output_dir: Output directory for prompt specs
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    created_specs = []
    
    for prompt in prompts:
        name = prompt["id"]
        text = prompt["text"]
        
        # Build command
        cmd = [
            "python", "-m", "cosmos_workflow.cli",
            "create-spec",
            name,
            text
        ]
        
        # Add video path if provided
        if video_path:
            cmd.extend(["--video-path", str(video_path)])
        
        print(f"Creating prompt spec: {name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse output to find created file path
            for line in result.stdout.split('\n'):
                if "Saved to:" in line:
                    spec_path = line.split("Saved to:")[-1].strip()
                    created_specs.append(spec_path)
                    print(f"  ✓ Created: {spec_path}")
                    break
        else:
            print(f"  ✗ Failed: {result.stderr}")
    
    return created_specs


def create_prompt_spec_batch(prompts, video_paths=None, resolutions=None):
    """Create prompt specs with different video resolutions for testing.
    
    Args:
        prompts: List of prompt dictionaries
        video_paths: Optional dict of resolution -> video path
        resolutions: List of resolutions to test
    """
    if not video_paths:
        # Default test videos
        video_dir = Path("testing/test_videos")
        if not video_dir.exists():
            print(f"Warning: Test videos directory not found: {video_dir}")
            print("Run create_test_videos.py first to generate test videos")
            video_paths = {}
        else:
            video_paths = {
                "480p": video_dir / "test_480p.mp4",
                "720p": video_dir / "test_720p.mp4", 
                "1080p": video_dir / "test_1080p.mp4"
            }
    
    if not resolutions:
        resolutions = ["480p", "720p", "1080p"]
    
    all_specs = {}
    
    # Create specs without video (text-only)
    print("\n=== Creating text-only prompt specs ===")
    text_only_specs = create_prompt_specs_cli(prompts, video_path=None)
    all_specs["text_only"] = text_only_specs
    
    # Create specs with videos at different resolutions
    for res in resolutions:
        if res in video_paths and video_paths[res].exists():
            print(f"\n=== Creating prompt specs with {res} video ===")
            res_specs = create_prompt_specs_cli(
                prompts, 
                video_path=video_paths[res],
                output_dir=f"inputs/prompts_{res}"
            )
            all_specs[res] = res_specs
        else:
            print(f"Skipping {res}: video not found")
    
    return all_specs


def save_batch_manifest(created_specs, output_file="testing/prompt_manifest.json"):
    """Save a manifest of all created prompt specs for batch processing."""
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_prompts": len(TEST_PROMPTS),
        "specs_by_resolution": created_specs,
        "prompt_ids": [p["id"] for p in TEST_PROMPTS]
    }
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest saved to: {output_path}")
    return output_path


def main():
    """Create all test prompt specs."""
    print("Creating test prompt specs for atmospheric lighting conditions...")
    print(f"Total prompts: {len(TEST_PROMPTS)}")
    
    # Check if we have test videos
    test_video_dir = Path("testing/test_videos")
    if not test_video_dir.exists():
        print("\n⚠️  Test videos not found. Creating basic prompt specs without videos.")
        print("   Run 'python testing/create_test_videos.py' to generate test videos.")
        
        # Create text-only specs
        specs = {"text_only": create_prompt_specs_cli(TEST_PROMPTS)}
    else:
        # Find available test videos
        available_videos = {}
        for res in ["360p", "480p", "720p", "1080p", "1440p", "4k"]:
            video_path = test_video_dir / f"test_{res}.mp4"
            if video_path.exists():
                available_videos[res] = video_path
        
        print(f"\nFound test videos: {list(available_videos.keys())}")
        
        # Create specs with different resolutions
        specs = create_prompt_spec_batch(
            TEST_PROMPTS,
            video_paths=available_videos,
            resolutions=list(available_videos.keys())
        )
    
    # Save manifest
    manifest_path = save_batch_manifest(specs)
    
    print("\n" + "="*60)
    print("✓ Test prompt creation complete!")
    print("\nNext steps:")
    print("1. Test single prompt upsampling:")
    print("   python -m cosmos_workflow.cli upsample inputs/prompts/[date]/[name]_ps_*.json --verbose")
    print("\n2. Test batch upsampling (text-only):")
    print("   python -m cosmos_workflow.cli upsample inputs/prompts/ --save-dir outputs/upsampled")
    print("\n3. Test with different resolutions:")
    print("   python -m cosmos_workflow.cli upsample inputs/prompts_720p/ --save-dir outputs/upsampled_720p")
    print("\n4. Test vocab error threshold:")
    print("   python -m cosmos_workflow.cli upsample inputs/prompts_1080p/ --preprocess-videos false")


if __name__ == "__main__":
    main()