#!/usr/bin/env bash
# full_cycle.sh <prompt.json> [videos_subdir_override]
# 1) upload prompt + videos  2) run remote inference (attached)  3) download results  4) append to run_history.log
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <prompt.json> [videos_subdir_override]"
  exit 1
fi

PROMPT="$1"
VIDEOS_SUBDIR="${2:-}"

start_ts="$(date +%Y-%m-%dT%H:%M:%S)"
"${HERE}/upload_prompt.sh" "${PROMPT}" "${VIDEOS_SUBDIR}"
"${HERE}/run_inference_remote.sh" "${PROMPT}"
"${HERE}/download_results.sh" "${PROMPT}"
end_ts="$(date +%Y-%m-%dT%H:%M:%S)"

mkdir -p "${LOCAL_NOTES_DIR}"
PROMPT_BN="$(basename "$PROMPT")"
PROMPT_NAME="${PROMPT_BN%.json}"

echo "${start_ts} -> ${end_ts} | prompt=${PROMPT_BN} | outputs=outputs/${PROMPT_NAME} | host=${REMOTE_HOST} | num_gpu=${NUM_GPU:-1}" >> "${LOCAL_NOTES_DIR}/run_history.log"

echo ">>> Full cycle completed for ${PROMPT_NAME}. Logged to notes/run_history.log"
