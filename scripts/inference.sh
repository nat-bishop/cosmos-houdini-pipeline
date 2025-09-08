#!/usr/bin/env bash
set -euo pipefail

PROMPT_NAME="$1"           # e.g., my_prompt
NUM_GPU="${2:-1}"
CUDA_VISIBLE_DEVICES="${3:-0}"
RUN_ID="${4:-$PROMPT_NAME}"  # Use run_id if provided, otherwise fallback to prompt_name

# Use run_id for output directory
OUTPUT_DIR="outputs/run_${RUN_ID}"
mkdir -p "${OUTPUT_DIR}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES}"
export CHECKPOINT_DIR="${CHECKPOINT_DIR:-./checkpoints}"
export NUM_GPU="${NUM_GPU}"
export PYTHONPATH="$(pwd)"

# Log spec for reproducibility
cat > "${OUTPUT_DIR}/spec_used.json" <<JSON
{
  "prompt_spec": $(cat "inputs/prompts/${PROMPT_NAME}.json"),
  "inference_command": "torchrun --nproc_per_node=\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \$CHECKPOINT_DIR --video_save_folder ${OUTPUT_DIR} --controlnet_specs inputs/prompts/${PROMPT_NAME}.json --offload_text_encoder_model --upsample_prompt --offload_prompt_upsampler --offload_guardrail_models --num_gpus \$NUM_GPU",
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
  --video_save_folder "${OUTPUT_DIR}" \
  --controlnet_specs "inputs/prompts/${PROMPT_NAME}.json" \
  --offload_text_encoder_model \
  --offload_guardrail_models \
  --num_gpus "$NUM_GPU" \
  2>&1 | tee "${OUTPUT_DIR}/run.log"
