#!/usr/bin/env bash
# run_upscale_remote.sh <prompt.json> [control_weight]
# Runs 4K upscaling on remote Lambda inside Docker (attached; logs stream & are saved)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <prompt.json> [control_weight]"
  exit 1
fi

PROMPT_PATH="$1"
PROMPT_BN="$(basename "$PROMPT_PATH")"
PROMPT_NAME="${PROMPT_BN%.json}"
CONTROL_WEIGHT="${2:-0.5}"

CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
CHECKPOINT_DIR_REMOTE="${CHECKPOINT_DIR_REMOTE:-${REMOTE_DIR}/checkpoints}"
NUM_GPU="${NUM_GPU:-1}"

REMOTE_OUTPUT_DIR="${REMOTE_DIR}/outputs/${PROMPT_NAME}"
REMOTE_UPSCALE_OUTPUT_DIR="${REMOTE_DIR}/outputs/${PROMPT_NAME}_upscaled"

echo ">>> Executing remote 4K upscaling for ${PROMPT_NAME} (logs will stream):"

# Create a multiline command for better readability
DOCKER_CMD="sudo docker run --rm --gpus all \\
  --ipc=host --shm-size=8g \\
  -v ${REMOTE_DIR}:/workspace \\
  -v \$HOME/.cache/huggingface:/root/.cache/huggingface \\
  -w /workspace \\
  ${DOCKER_IMAGE} \\
  bash -lc \"
    mkdir -p outputs/${PROMPT_NAME}_upscaled
    
    # Check if input video exists before proceeding
    if [ ! -f outputs/${PROMPT_NAME}/output.mp4 ]; then
      echo 'ERROR: Input video outputs/${PROMPT_NAME}/output.mp4 not found. Skipping upscaling.'
      exit 1
    fi
    
    # Export environment variables (NVIDIA style)
    export CUDA_VISIBLE_DEVICES=\\\"\\\${CUDA_VISIBLE_DEVICES:=0}\\\"
    export CHECKPOINT_DIR=\\\"\\\${CHECKPOINT_DIR:=./checkpoints}\\\"
    export NUM_GPU=\\\"\\\${NUM_GPU:=1}\\\"
    export PYTHONPATH=\\\$(pwd)
    
    # Create upscaler transfer spec
    cat > outputs/${PROMPT_NAME}/upscaler_spec.json << 'UPSCALER_SPEC'
{
    \\\"input_video_path\\\" : \\\"outputs/${PROMPT_NAME}/output.mp4\\\",
    \\\"upscale\\\": {
        \\\"control_weight\\\": ${CONTROL_WEIGHT}
    }
}
UPSCALER_SPEC
    
    # Save the full upscaling command and spec to spec_used.json
    cat > outputs/${PROMPT_NAME}_upscaled/spec_used.json << 'UPSCALE_SPEC_EOF'
{
  \\\"upscale_spec\\\": {
    \\\"input_video_path\\\" : \\\"outputs/${PROMPT_NAME}/output.mp4\\\",
    \\\"upscale\\\": {
        \\\"control_weight\\\": ${CONTROL_WEIGHT}
    }
  },
  \\\"upscale_command\\\": \\\"torchrun --nproc_per_node=\\\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \\\$CHECKPOINT_DIR --video_save_folder outputs/${PROMPT_NAME}_upscaled --controlnet_specs outputs/${PROMPT_NAME}/upscaler_spec.json --num_steps 10 --offload_text_encoder_model --num_gpus \\\$NUM_GPU\\\",
  \\\"environment\\\": {
    \\\"CUDA_VISIBLE_DEVICES\\\": \\\"\\\$CUDA_VISIBLE_DEVICES\\\",
    \\\"CHECKPOINT_DIR\\\": \\\"\\\$CHECKPOINT_DIR\\\",
    \\\"NUM_GPU\\\": \\\"\\\$NUM_GPU\\\"
  }
}
UPSCALE_SPEC_EOF
    
    # Run 4K upscaling with torchrun
    torchrun --nproc_per_node=\\\$NUM_GPU --nnodes=1 --node_rank=0 \\
      cosmos_transfer1/diffusion/inference/transfer.py \\
      --checkpoint_dir \\\$CHECKPOINT_DIR \\
      --video_save_folder outputs/${PROMPT_NAME}_upscaled \\
      --controlnet_specs outputs/${PROMPT_NAME}/upscaler_spec.json \\
      --num_steps 10 \\
      --offload_text_encoder_model \\
      --num_gpus \\\$NUM_GPU \\
      2>&1 | tee outputs/${PROMPT_NAME}_upscaled/upscale_run.log
  \""

ssh ${SSH_OPTS} "${REMOTE}" "set -euo pipefail; mkdir -p '${REMOTE_UPSCALE_OUTPUT_DIR}'; ${DOCKER_CMD}"
