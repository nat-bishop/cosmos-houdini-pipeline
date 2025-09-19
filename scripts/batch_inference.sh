#!/usr/bin/env bash
set -euo pipefail

BATCH_NAME="$1"          # e.g., batch_20241206_123456
BATCH_JSONL="$2"         # e.g., batch_20241206_123456.jsonl
BASE_CONTROLNET_SPEC="$3" # e.g., base_controlnet_spec.json
NUM_GPU="${4:-1}"
CUDA_VISIBLE_DEVICES="${5:-0}"

mkdir -p "outputs/${BATCH_NAME}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES}"
export CHECKPOINT_DIR="${CHECKPOINT_DIR:-./checkpoints}"
export NUM_GPU="${NUM_GPU}"
export PYTHONPATH="$(pwd)"

# Log batch spec for reproducibility
cat > "outputs/${BATCH_NAME}/batch_spec.json" <<JSON
{
  "batch_input": "inputs/batches/${BATCH_JSONL}",
  "base_controlnet_spec": "inputs/batches/${BASE_CONTROLNET_SPEC}",
  "batch_size": $(wc -l < "inputs/batches/${BATCH_JSONL}"),
  "inference_command": "torchrun --nproc_per_node=\$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py --checkpoint_dir \$CHECKPOINT_DIR --video_save_folder outputs/${BATCH_NAME} --controlnet_specs inputs/batches/${BASE_CONTROLNET_SPEC} --batch_input_path inputs/batches/${BATCH_JSONL} --offload_text_encoder_model --num_gpus \$NUM_GPU",
  "environment": {
    "CUDA_VISIBLE_DEVICES": "\$CUDA_VISIBLE_DEVICES",
    "CHECKPOINT_DIR": "\$CHECKPOINT_DIR",
    "NUM_GPU": "\$NUM_GPU"
  }
}
JSON

# Run batch inference
torchrun --nproc_per_node="$NUM_GPU" --nnodes=1 --node_rank=0 \
  cosmos_transfer1/diffusion/inference/transfer.py \
  --checkpoint_dir "$CHECKPOINT_DIR" \
  --video_save_folder "outputs/${BATCH_NAME}" \
  --controlnet_specs "inputs/batches/${BASE_CONTROLNET_SPEC}" \
  --batch_input_path "inputs/batches/${BATCH_JSONL}" \
  --offload_text_encoder_model \
  --num_gpus "$NUM_GPU" \
  2>&1 | tee "outputs/${BATCH_NAME}/batch_run.log"

# Capture exit code and write completion marker
EXIT_CODE="${PIPESTATUS[0]}"
echo "[COSMOS_COMPLETE] exit_code=${EXIT_CODE}" >> "outputs/${BATCH_NAME}/batch_run.log"
exit ${EXIT_CODE}