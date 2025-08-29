#!/usr/bin/env bash
set -euo pipefail

PROMPT_NAME="$1"           # e.g., my_prompt
CONTROL_WEIGHT="${2:-0.5}"
NUM_GPU="${3:-1}"
CUDA_VISIBLE_DEVICES="${4:-0}"

mkdir -p "outputs/${PROMPT_NAME}_upscaled"

if [ ! -f "outputs/${PROMPT_NAME}/output.mp4" ]; then
  echo "ERROR: outputs/${PROMPT_NAME}/output.mp4 not found." >&2
  exit 1
fi

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES}"
export CHECKPOINT_DIR="${CHECKPOINT_DIR:-./checkpoints}"
export NUM_GPU="${NUM_GPU}"
export PYTHONPATH="$(pwd)"

# Log spec for reproducibility
cat > "outputs/${PROMPT_NAME}_upscaled/spec_used.json" <<JSON
{
  "upscale_spec": {
    "input_video_path": "outputs/${PROMPT_NAME}/output.mp4",
    "upscale": { "control_weight": ${CONTROL_WEIGHT} }
  },
  "upscale_command": "torchrun --nproc_per_node=\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \$CHECKPOINT_DIR --video_save_folder outputs/${PROMPT_NAME}_upscaled --controlnet_specs outputs/${PROMPT_NAME}/upscaler_spec.json --num_steps 10 --offload_text_encoder_model --num_gpus \$NUM_GPU",
  "environment": {
    "CUDA_VISIBLE_DEVICES": "\$CUDA_VISIBLE_DEVICES",
    "CHECKPOINT_DIR": "\$CHECKPOINT_DIR",
    "NUM_GPU": "\$NUM_GPU"
  }
}
JSON

torchrun --nproc_per_node="$NUM_GPU" --nnodes=1 --node_rank=0 \
  cosmos_transfer1/diffusion/inference/transfer.py \
  --checkpoint_dir "$CHECKPOINT_DIR" \
  --video_save_folder "outputs/${PROMPT_NAME}_upscaled" \
  --controlnet_specs "outputs/${PROMPT_NAME}/upscaler_spec.json" \
  --num_steps 10 \
  --offload_text_encoder_model \
  --num_gpus "$NUM_GPU" \
  2>&1 | tee "outputs/${PROMPT_NAME}_upscaled/upscale_run.log"
