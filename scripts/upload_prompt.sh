#!/usr/bin/env bash
# upload_prompt.sh <prompt.json> [videos_subdir_override]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <prompt.json> [videos_subdir_override]"
  exit 1
fi

PROMPT_PATH="$1"
PROMPT_BN="$(basename "$PROMPT_PATH")"
PROMPT_NAME="${PROMPT_BN%.json}"

VIDEOS_SUBDIR_OVERRIDE="${2:-}"

derive_base_root() {
  # Takes BASENAME (without .json) and removes the trailing _YYYYMMDD_HHMMSS if present.
  local name="$1"
  if [[ "$name" =~ ^(.+)_([0-9]{8}_[0-9]{6})$ ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    # Fallback: strip after last underscore
    echo "${name%_*}"
  fi
}


if [ -n "$VIDEOS_SUBDIR_OVERRIDE" ]; then
  VIDEOS_SUBDIR="$VIDEOS_SUBDIR_OVERRIDE"
else
  VIDEOS_SUBDIR="$(derive_base_root "$PROMPT_NAME")"
fi

LOCAL_VIDEOS_PATH="${LOCAL_VIDEOS_DIR}/${VIDEOS_SUBDIR}/"

if [ ! -d "${LOCAL_VIDEOS_PATH}" ]; then
  echo "ERROR: Local videos directory not found: ${LOCAL_VIDEOS_PATH}"
  echo "Provide it explicitly: $0 $PROMPT_PATH <videos_subdir>"
  exit 2
fi

echo ">>> Creating remote directories..."
ssh ${SSH_OPTS} "${REMOTE}" "mkdir -p '${REMOTE_DIR}/inputs/prompts' '${REMOTE_DIR}/inputs/videos/${VIDEOS_SUBDIR}'"

echo ">>> Uploading prompt JSON -> remote"
rsync -avz -e "${RSYNC_SSH}" "${PROMPT_PATH}" "${REMOTE}:${REMOTE_DIR}/inputs/prompts/${PROMPT_BN}"

echo ">>> Uploading videos dir -> remote"
rsync -avz -e "${RSYNC_SSH}" "${LOCAL_VIDEOS_PATH}" "${REMOTE}:${REMOTE_DIR}/inputs/videos/${VIDEOS_SUBDIR}/"

echo "Done uploading. Prompt: $PROMPT_BN  Videos subdir: $VIDEOS_SUBDIR"
