#!/usr/bin/env bash
# convert_png_sequences.sh <input_directory> <output_name>
# Converts PNG sequences (color.####.png, depth.####.png, segmentation.####.png) to MP4 videos
# and places them in inputs/videos/<output_name>/ directory
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

# Function to show usage
show_usage() {
  echo "Usage: $0 <input_directory> <output_name> [frame_count]"
  echo
  echo "Converts PNG sequences to MP4 videos for Cosmos inference:"
  echo "  - color.####.png → color.mp4"
  echo "  - depth.####.png → depth.mp4"
  echo "  - segmentation.####.png → segmentation.mp4"
  echo
  echo "Arguments:"
  echo "  input_directory  Path to directory containing PNG sequences"
  echo "  output_name     Name of folder in inputs/videos/ to create"
  echo "  frame_count     Optional: Number of frames to convert (e.g., 50 for frames 1-50)"
  echo
  echo "Examples:"
  echo "  $0 ./art/houdini/renders/building_shot1 building_shot1"
  echo "  # Creates inputs/videos/building_shot1/{color.mp4,depth.mp4,segmentation.mp4}"
  echo "  $0 ./art/houdini/renders/building_shot1 building_shot1 50"
  echo "  # Creates videos with only frames 1-50"
  echo
  echo "Requirements:"
  echo "  - ffmpeg must be installed and available in PATH"
  echo "  - PNG sequences must be named: color.####.png, depth.####.png, segmentation.####.png"
  echo "  - All sequences must have the same frame count and frame rate"
}

# Check arguments
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
  show_usage
  exit 1
fi

INPUT_DIR="$1"
OUTPUT_NAME="$2"
FRAME_COUNT="${3:-}"

# Validate input directory
if [ ! -d "$INPUT_DIR" ]; then
  echo "ERROR: Input directory not found: $INPUT_DIR"
  exit 1
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
  echo "ERROR: ffmpeg is not installed or not in PATH"
  echo "Please install ffmpeg and try again"
  exit 1
fi

# Create output directory
OUTPUT_DIR="${LOCAL_VIDEOS_DIR}/${OUTPUT_NAME}"
mkdir -p "$OUTPUT_DIR"

echo "🔍 Scanning for PNG sequences in: $INPUT_DIR"

# Check for required PNG sequences
COLOR_SEQ=""
DEPTH_SEQ=""
SEG_SEQ=""

# Find PNG sequences (looking for patterns like color.####.png, depth.####.png, etc.)
for file in "$INPUT_DIR"/*.png; do
  if [[ -f "$file" ]]; then
    filename=$(basename "$file")
    if [[ "$filename" =~ ^(color|depth|segmentation)\.([0-9]+)\.png$ ]]; then
      type="${BASH_REMATCH[1]}"
      frame_num="${BASH_REMATCH[2]}"
      
      case "$type" in
        "color")
          COLOR_SEQ="$file"
          echo "  ✅ Found color sequence: $filename"
          ;;
        "depth")
          DEPTH_SEQ="$file"
          echo "  ✅ Found depth sequence: $filename"
          ;;
        "segmentation")
          SEG_SEQ="$file"
          echo "  ✅ Found segmentation sequence: $filename"
          ;;
      esac
    fi
  fi
done

# Check if we found any sequences
if [ -z "$COLOR_SEQ" ] && [ -z "$DEPTH_SEQ" ] && [ -z "$SEG_SEQ" ]; then
  echo "ERROR: No valid PNG sequences found in $INPUT_DIR"
  echo "Expected files: color.####.png, depth.####.png, segmentation.####.png"
  exit 1
fi

# Function to convert PNG sequence to MP4
convert_sequence() {
  local input_pattern="$1"
  local output_file="$2"
  local sequence_name="$3"
  
  if [ -n "$input_pattern" ]; then
    echo "🎬 Converting $sequence_name sequence to MP4..."
    
    # Extract the pattern for ffmpeg (e.g., color.%04d.png)
    pattern=$(echo "$input_pattern" | sed 's/[0-9]\+\.png$/%04d.png/')
    
    # Build ffmpeg command
    local ffmpeg_cmd="ffmpeg -framerate 24 -i \"$pattern\""
    
    # Add frame range if specified
    if [ -n "$FRAME_COUNT" ]; then
      ffmpeg_cmd="$ffmpeg_cmd -frames:v $FRAME_COUNT"
      echo "  📊 Converting frames 1-$FRAME_COUNT"
    fi
    
    # Complete ffmpeg command
    ffmpeg_cmd="$ffmpeg_cmd -c:v libx264 -pix_fmt yuv420p -crf 18 -y \"$output_file\""
    
    # Execute ffmpeg command
    eval $ffmpeg_cmd 2>/dev/null
    
    if [ $? -eq 0 ]; then
      echo "  ✅ Created: $output_file"
    else
      echo "  ❌ Failed to create: $output_file"
      return 1
    fi
  fi
}

# Convert each sequence
if [ -n "$COLOR_SEQ" ]; then
  convert_sequence "$COLOR_SEQ" "$OUTPUT_DIR/color.mp4" "color"
fi

if [ -n "$DEPTH_SEQ" ]; then
  convert_sequence "$DEPTH_SEQ" "$OUTPUT_DIR/depth.mp4" "depth"
fi

if [ -n "$SEG_SEQ" ]; then
  convert_sequence "$SEG_SEQ" "$OUTPUT_DIR/segmentation.mp4" "segmentation"
fi

echo
echo "🎉 Conversion complete!"
echo "Output directory: $OUTPUT_DIR"
echo
echo "Next steps:"
echo "  1) Create a prompt: ./scripts/new_prompt.sh $OUTPUT_NAME \"<your prompt text>\""
echo "  2) Run full cycle: ./scripts/full_cycle.sh inputs/prompts/${OUTPUT_NAME}_<timestamp>.json"
