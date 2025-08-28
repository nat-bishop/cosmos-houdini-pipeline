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

# Create a multiline command for better readability
DOCKER_CMD="sudo docker run --rm --gpus all \\
  --ipc=host --shm-size=8g \\
  -v ${REMOTE_DIR}:/workspace \\
  -v \$HOME/.cache/huggingface:/root/.cache/huggingface \\
  -w /workspace \\
  ${DOCKER_IMAGE} \\
  bash -lc \"
    mkdir -p outputs/${PROMPT_NAME}
    
    # Export environment variables (NVIDIA style)
    export CUDA_VISIBLE_DEVICES=\\\"\\\${CUDA_VISIBLE_DEVICES:=0}\\\"
    export CHECKPOINT_DIR=\\\"\\\${CHECKPOINT_DIR:=./checkpoints}\\\"
    export NUM_GPU=\\\"\\\${NUM_GPU:=1}\\\"
    export PYTHONPATH=\\\$(pwd)
    
    # Save the full command and spec to spec_used.json
    cat > outputs/${PROMPT_NAME}/spec_used.json << 'SPEC_EOF'
{
  \\\"prompt_spec\\\": \\\$(cat inputs/prompts/${PROMPT_BN}),
  \\\"inference_command\\\": \\\"torchrun --nproc_per_node=\\\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \\\$CHECKPOINT_DIR --video_save_folder outputs/${PROMPT_NAME} --controlnet_specs inputs/prompts/${PROMPT_BN} --offload_text_encoder_model --upsample_prompt --offload_prompt_upsampler --offload_guardrail_models --num_gpus \\\$NUM_GPU\\\",
  \\\"environment\\\": {
    \\\"CUDA_VISIBLE_DEVICES\\\": \\\"\\\$CUDA_VISIBLE_DEVICES\\\",
    \\\"CHECKPOINT_DIR\\\": \\\"\\\$CHECKPOINT_DIR\\\",
    \\\"NUM_GPU\\\": \\\"\\\$NUM_GPU\\\"
  }
}
SPEC_EOF
    
    # Run inference with torchrun (both single and multi-GPU)
    torchrun --nproc_per_node=\\\$NUM_GPU --nnodes=1 --node_rank=0 \\
      cosmos_transfer1/diffusion/inference/transfer.py \\
      --checkpoint_dir \\\$CHECKPOINT_DIR \\
      --video_save_folder outputs/${PROMPT_NAME} \\
      --controlnet_specs inputs/prompts/${PROMPT_BN} \\
      --offload_text_encoder_model \\
      --upsample_prompt \\
      --offload_prompt_upsampler \\
      --offload_guardrail_models \\
      --num_gpus \\\$NUM_GPU \\
      2>&1 | tee outputs/${PROMPT_NAME}/run.log
  \""

ssh ${SSH_OPTS} "${REMOTE}" "set -euo pipefail; mkdir -p '${REMOTE_OUTPUT_DIR}'; cp '${REMOTE_PROMPT_SPEC}' '${REMOTE_OUTPUT_DIR}/prompt_spec.json'; ${DOCKER_CMD}"
