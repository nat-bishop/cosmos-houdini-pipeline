#!/usr/bin/env bash
set -eu

RUN_ID="$1"                # e.g., rs_xxxxx (run ID for upscaling)
CONTROL_WEIGHT="${2:-0.5}"
NUM_GPU="${3:-1}"
CUDA_VISIBLE_DEVICES="${4:-0}"
PARENT_RUN_ID="${5:-$RUN_ID}"  # Parent run to upscale from

# Use run_id for output directory
OUTPUT_DIR="outputs/run_${RUN_ID}"
mkdir -p "${OUTPUT_DIR}"

# Check for input video in parent run directory
INPUT_VIDEO="runs/${PARENT_RUN_ID}/outputs/output.mp4"
if [ ! -f "${INPUT_VIDEO}" ]; then
  echo "ERROR: ${INPUT_VIDEO} not found." >&2
  exit 1
fi

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES}"
export CHECKPOINT_DIR="${CHECKPOINT_DIR:-./checkpoints}"
export NUM_GPU="${NUM_GPU}"
export PYTHONPATH="$(pwd)"

# Log spec for reproducibility
cat > "${OUTPUT_DIR}/spec_used.json" <<JSON
{
  "upscale_spec": {
    "input_video_path": "${INPUT_VIDEO}",
    "upscale": { "control_weight": ${CONTROL_WEIGHT} }
  },
  "upscale_command": "torchrun --nproc_per_node=\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \$CHECKPOINT_DIR --video_save_folder ${OUTPUT_DIR} --controlnet_specs outputs/run_${PARENT_RUN_ID}/upscaler_spec.json --num_steps 10 --offload_text_encoder_model --num_gpus \$NUM_GPU",
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
  --num_steps 10 \
  --offload_text_encoder_model \
  --num_gpus "$NUM_GPU" \
  2>&1 | tee "${OUTPUT_DIR}/run.log"
