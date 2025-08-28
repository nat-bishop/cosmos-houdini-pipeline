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
scp -r -P ${REMOTE_PORT} -i ${SSH_KEY} "${REMOTE}:${REMOTE_DIR}/outputs/${PROMPT_NAME}/" "${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}/"

# Also download upscaled results if they exist
UPSCALED_REMOTE_DIR="${REMOTE_DIR}/outputs/${PROMPT_NAME}_upscaled"
if ssh ${SSH_OPTS} "${REMOTE}" "[ -d '${UPSCALED_REMOTE_DIR}' ]"; then
  echo ">>> Downloading upscaled results for ${PROMPT_NAME}"
  mkdir -p "${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}_upscaled"
  scp -r -P ${REMOTE_PORT} -i ${SSH_KEY} "${REMOTE}:${UPSCALED_REMOTE_DIR}/" "${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}_upscaled/"
  echo "Saved upscaled results to ${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}_upscaled/"
else
  echo ">>> No upscaled results found for ${PROMPT_NAME}"
fi

echo "Saved to ${LOCAL_OUTPUTS_DIR}/${PROMPT_NAME}/"
