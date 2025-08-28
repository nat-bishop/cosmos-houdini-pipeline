#!/usr/bin/env bash
# full_cycle.sh <prompt.json> [videos_subdir_override] [--no-upscale] [--upscale-weight <weight>]
# 1) upload prompt + videos  2) run remote inference (attached)  3) run 4K upscaling (optional)  4) download results  5) append to run_history.log
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <prompt.json> [videos_subdir_override] [--no-upscale] [--upscale-weight <weight>]"
  exit 1
fi

PROMPT="$1"
VIDEOS_SUBDIR="${2:-}"
NO_UPSCALE=false
UPSCALE_WEIGHT="0.5"

# Parse optional arguments - only shift if videos_subdir was provided
if [ $# -ge 2 ] && [[ "$2" != --* ]]; then
  # videos_subdir was provided, shift it
  shift 2
else
  # no videos_subdir, just shift the prompt
  shift 1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --no-upscale)
      NO_UPSCALE=true
      shift
      ;;
    --upscale-weight)
      if [ $# -lt 2 ]; then
        echo "Error: --upscale-weight requires a value"
        exit 1
      fi
      UPSCALE_WEIGHT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 <prompt.json> [videos_subdir_override] [--no-upscale] [--upscale-weight <weight>]"
      exit 1
      ;;
  esac
done

start_ts="$(date +%Y-%m-%dT%H:%M:%S)"
"${HERE}/upload_prompt.sh" "${PROMPT}" "${VIDEOS_SUBDIR}"
"${HERE}/run_inference_remote.sh" "${PROMPT}"

# Check if video generation succeeded before running upscaling
if [ $? -eq 0 ]; then
  # Run 4K upscaling if enabled (default)
  if [ "$NO_UPSCALE" = false ]; then
    echo ">>> Running 4K upscaling with control weight: ${UPSCALE_WEIGHT}"
    "${HERE}/run_upscale_remote.sh" "${PROMPT}" "${UPSCALE_WEIGHT}"
  else
    echo ">>> Skipping 4K upscaling (--no-upscale flag used)"
  fi
else
  echo ">>> Video generation failed, skipping upscaling"
  NO_UPSCALE=true  # Force this to true for logging
fi

"${HERE}/download_results.sh" "${PROMPT}"
end_ts="$(date +%Y-%m-%dT%H:%M:%S)"

mkdir -p "${LOCAL_NOTES_DIR}"
PROMPT_BN="$(basename "$PROMPT")"
PROMPT_NAME="${PROMPT_BN%.json}"

echo "${start_ts} -> ${end_ts} | prompt=${PROMPT_BN} | outputs=outputs/${PROMPT_NAME} | host=${REMOTE_HOST} | num_gpu=${NUM_GPU:-1} | upscaled=${NO_UPSCALE:-false} | upscale_weight=${UPSCALE_WEIGHT}" >> "${LOCAL_NOTES_DIR}/run_history.log"

echo ">>> Full cycle completed for ${PROMPT_NAME}. Logged to notes/run_history.log"

# Open the output video on Windows
OUTPUT_VIDEO="${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}/output.mp4"
if [ -f "${OUTPUT_VIDEO}" ]; then
  echo ">>> Opening output video: ${OUTPUT_VIDEO}"
  start "${OUTPUT_VIDEO}"
else
  echo ">>> Output video not found: ${OUTPUT_VIDEO}"
fi

# Also open the upscaled video if it exists
UPSCALED_VIDEO="${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}_upscaled/output.mp4"
if [ -f "${UPSCALED_VIDEO}" ]; then
  echo ">>> Opening upscaled video: ${UPSCALED_VIDEO}"
  start "${UPSCALED_VIDEO}"
else
  echo ">>> Upscaled video not found: ${UPSCALED_VIDEO}"
fi
