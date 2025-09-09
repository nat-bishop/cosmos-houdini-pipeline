#!/usr/bin/env bash
set -eu

RUN_ID="$1"                # e.g., rs_xxxxx (run ID)
NUM_GPU="${2:-1}"
CUDA_VISIBLE_DEVICES="${3:-0}"
PROMPT_NAME="${4:-$RUN_ID}"  # For backwards compatibility

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
  "prompt_spec": $(cat "runs/${RUN_ID}/inputs/spec.json"),
  "inference_command": "torchrun --nproc_per_node=\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \$CHECKPOINT_DIR --video_save_folder ${OUTPUT_DIR} --controlnet_specs runs/${RUN_ID}/inputs/spec.json --offload_text_encoder_model --offload_guardrail_models --num_gpus \$NUM_GPU",
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
  --controlnet_specs "runs/${RUN_ID}/inputs/spec.json" \
  --offload_text_encoder_model \
  --offload_guardrail_models \
  --num_gpus "$NUM_GPU" \
  2>&1 | tee "${OUTPUT_DIR}/run.log"
