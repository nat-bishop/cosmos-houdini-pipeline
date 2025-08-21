#!/usr/bin/env bash
# download_results.sh <prompt.json>
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <prompt.json>"
  exit 1
fi

PROMPT_PATH="$1"
PROMPT_BN="$(basename "$PROMPT_PATH")"
PROMPT_NAME="${PROMPT_BN%.json}"

mkdir -p "${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}"

echo ">>> Downloading results for ${PROMPT_NAME}"
rsync -avz -e "${RSYNC_SSH}"   "${REMOTE}:${REMOTE_DIR}/outputs/${PROMPT_NAME}/"   "${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}/"

echo "Saved to ${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}/"
