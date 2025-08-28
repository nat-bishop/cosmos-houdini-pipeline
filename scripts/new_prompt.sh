#!/usr/bin/env bash
# new_prompt.sh <base_name> "<prompt text>" | new_prompt.sh --duplicate <existing_prompt.json>
# Creates a multimodal-ready JSON with standard paths under inputs/videos/<base_name>/
# Or duplicates an existing prompt with a new timestamp
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <base_name> \"<prompt text>\""
  echo "   OR: $0 --duplicate <existing_prompt.json>"
  exit 1
fi

if [ "$1" = "--duplicate" ]; then
  if [ $# -lt 2 ]; then
    echo "Usage: $0 --duplicate <existing_prompt.json>"
    exit 1
  fi
  
  EXISTING_PROMPT="$2"
  if [ ! -f "$EXISTING_PROMPT" ]; then
    echo "ERROR: Prompt file not found: $EXISTING_PROMPT"
    exit 1
  fi
  
  # Extract the base name from the existing prompt filename
  EXISTING_BN="$(basename "$EXISTING_PROMPT")"
  BASE_NAME="${EXISTING_BN%_*.json}"
  
  # Generate new timestamp
  DATE_TAG="$(date +%Y%m%d_%H%M%S)"
  PROMPT_NAME="${BASE_NAME}_${DATE_TAG}"
  PROMPT_JSON="${LOCAL_PROMPTS_DIR}/${PROMPT_NAME}.json"
  OUT_DIR="${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}"
  
  mkdir -p "${LOCAL_PROMPTS_DIR}" "${OUT_DIR}"
  
  # Copy the existing prompt content and update the timestamp in the filename
  cp "$EXISTING_PROMPT" "$PROMPT_JSON"
  
  echo "✅ Duplicated prompt: ${PROMPT_JSON}"
  echo "   Outputs will be saved under: ${OUT_DIR}"
  echo
  echo "Next:"
  echo "  1) Edit the prompt text if needed: ${PROMPT_JSON}"
  echo "  2) Run full cycle:"
  echo "       ./scripts/full_cycle.sh ${PROMPT_JSON}"
  
  exit 0
fi

if [ $# -lt 2 ]; then
  echo "Usage: $0 <base_name> \"<prompt text>\""
  echo "   OR: $0 --duplicate <existing_prompt.json>"
  exit 1
fi

BASE_NAME="$1"; shift
PROMPT_TEXT="$*"

DATE_TAG="$(date +%Y%m%d_%H%M%S)"
PROMPT_NAME="${BASE_NAME}_${DATE_TAG}"
PROMPT_JSON="${LOCAL_PROMPTS_DIR}/${PROMPT_NAME}.json"
OUT_DIR="${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}"

mkdir -p "${LOCAL_PROMPTS_DIR}" "${OUT_DIR}"

cat > "${PROMPT_JSON}" <<JSON
{
  "prompt": "${PROMPT_TEXT//\"/\\\"}",

  "input_video_path": "inputs/videos/${BASE_NAME}/color.mp4",

  "vis": {
    "control_weight": 0.25
  },

  "edge": {
    "control_weight": 0.25
  },

  "depth": {
    "control_weight": 0.25,
    "input_control": "inputs/videos/${BASE_NAME}/depth.mp4"
  },

  "seg": {
    "control_weight": 0.25,
    "input_control": "inputs/videos/${BASE_NAME}/segmentation.mp4"
  }
}
JSON

echo "✅ Created prompt: ${PROMPT_JSON}"
echo "   Outputs will be saved under: ${OUT_DIR}"
echo
echo "Next:"
echo "  1) If you don't have a modality (edge/depth/seg), delete its 'input_control' line or the whole block."
echo "  2) Adjust control_weight values as needed."
echo "  3) Run full cycle:"
echo "       ./scripts/full_cycle.sh ${PROMPT_JSON}"
