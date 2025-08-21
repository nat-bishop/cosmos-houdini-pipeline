#!/usr/bin/env bash
# new_prompt.sh <base_name> "<prompt text>"
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <base_name> <prompt text>"
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
  "prompt": "${PROMPT_TEXT//"/\"}",
  "input_video_path": "inputs/videos/${BASE_NAME}/visibility.mp4",
  "vis":   { "control_weight": 0.25 },
  "edge":  { "control_weight": 0.25 },
  "depth": { "control_weight": 0.25 },
  "seg":   { "control_weight": 0.25 }
}
JSON

echo "Created prompt: ${PROMPT_JSON}"
echo "Local outputs folder prepared: ${OUT_DIR}"
echo "Next: ./upload_prompt.sh ${PROMPT_JSON}"
