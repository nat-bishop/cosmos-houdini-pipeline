#!/usr/bin/env bash
# run_inference_remote.sh <prompt.json>
# Runs inference on remote Lambda inside Docker (attached; logs stream & are saved)
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

CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
CHECKPOINT_DIR_REMOTE="${CHECKPOINT_DIR_REMOTE:-${REMOTE_DIR}/checkpoints}"
NUM_GPU="${NUM_GPU:-1}"

REMOTE_OUTPUT_DIR="${REMOTE_DIR}/outputs/${PROMPT_NAME}"
REMOTE_PROMPT_SPEC="${REMOTE_DIR}/inputs/prompts/${PROMPT_BN}"

echo ">>> Executing remote inference for ${PROMPT_NAME} (logs will stream):"
ssh ${SSH_OPTS} "${REMOTE}" "set -euo pipefail;   mkdir -p '${REMOTE_OUTPUT_DIR}';   cp '${REMOTE_PROMPT_SPEC}' '${REMOTE_OUTPUT_DIR}/spec_used.json';   if [ '${NUM_GPU}' -gt 1 ]; then
    LAUNCH='CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES} CHECKPOINT_DIR=${CHECKPOINT_DIR_REMOTE} NUM_GPU=${NUM_GPU}       torchrun --nproc_per_node=${NUM_GPU} --nnodes=1 --node_rank=0       cosmos_transfer1/diffusion/inference/transfer.py         --checkpoint_dir ${CHECKPOINT_DIR_REMOTE}         --video_save_folder outputs/${PROMPT_NAME}         --controlnet_specs inputs/prompts/${PROMPT_BN}         --offload_text_encoder_model --offload_guardrail_models         --num_gpus ${NUM_GPU}'
  else
    LAUNCH='CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES} CHECKPOINT_DIR=${CHECKPOINT_DIR_REMOTE} NUM_GPU=${NUM_GPU}       python3 cosmos_transfer1/diffusion/inference/transfer.py         --checkpoint_dir ${CHECKPOINT_DIR_REMOTE}         --video_save_folder outputs/${PROMPT_NAME}         --controlnet_specs inputs/prompts/${PROMPT_BN}         --offload_text_encoder_model --offload_guardrail_models         --num_gpus ${NUM_GPU}'
  fi;   echo "[ENV] CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}  NUM_GPU=${NUM_GPU}  CHECKPOINT_DIR=${CHECKPOINT_DIR_REMOTE}" | tee '${REMOTE_OUTPUT_DIR}/run.log';   echo "[CMD] $LAUNCH" | tee -a '${REMOTE_OUTPUT_DIR}/run.log';   docker run --rm --gpus all     --ipc=host --shm-size=8g     -v ${REMOTE_DIR}:/workspace     -v $HOME/.cache/huggingface:/root/.cache/huggingface     -w /workspace     ${DOCKER_IMAGE}     bash -lc "$LAUNCH 2>&1 | tee -a '${REMOTE_OUTPUT_DIR}/run.log'" "
