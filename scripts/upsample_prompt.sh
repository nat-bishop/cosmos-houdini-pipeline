#!/bin/bash
# Batch prompt upsampling script for Cosmos Transfer
# Runs inside Docker container on remote GPU

set -e

# Configuration
COSMOS_DIR="/home/ubuntu/NatsFS/cosmos-transfer1"
CHECKPOINT_DIR="${COSMOS_DIR}/checkpoints"
INPUT_DIR="${COSMOS_DIR}/inputs"
OUTPUT_DIR="${COSMOS_DIR}/outputs"

# Parse arguments
PROMPTS_FILE="${1:-${INPUT_DIR}/prompts_to_upsample.json}"
OUTPUT_FILE="${2:-${OUTPUT_DIR}/upsampled_prompts.json}"
PREPROCESS_VIDEOS="${3:-true}"
MAX_RESOLUTION="${4:-480}"
NUM_FRAMES="${5:-2}"
NUM_GPU="${6:-1}"

echo "========================================="
echo "Cosmos Transfer Prompt Upsampling"
echo "========================================="
echo "Prompts file: ${PROMPTS_FILE}"
echo "Output file: ${OUTPUT_FILE}"
echo "Preprocess videos: ${PREPROCESS_VIDEOS}"
echo "Max resolution: ${MAX_RESOLUTION}"
echo "Num frames: ${NUM_FRAMES}"
echo "Num GPUs: ${NUM_GPU}"
echo "========================================="

# Create output directory
mkdir -p "$(dirname ${OUTPUT_FILE})"

# Set CUDA devices
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

# Change to cosmos directory
cd ${COSMOS_DIR}

# Run upsampling based on number of GPUs
if [ "${NUM_GPU}" -eq 1 ]; then
    echo "Running single GPU upsampling..."
    python scripts/upsample_prompts.py \
        --prompts-file "${PROMPTS_FILE}" \
        --checkpoint-dir "${CHECKPOINT_DIR}" \
        $([ "${PREPROCESS_VIDEOS}" = "true" ] && echo "--preprocess-videos") \
        --max-resolution ${MAX_RESOLUTION} \
        --num-frames ${NUM_FRAMES} \
        --output-file "${OUTPUT_FILE}"
else
    echo "Running multi-GPU upsampling with torchrun..."
    torchrun --nproc_per_node=${NUM_GPU} \
        scripts/upsample_prompts.py \
        --prompts-file "${PROMPTS_FILE}" \
        --checkpoint-dir "${CHECKPOINT_DIR}" \
        $([ "${PREPROCESS_VIDEOS}" = "true" ] && echo "--preprocess-videos") \
        --max-resolution ${MAX_RESOLUTION} \
        --num-frames ${NUM_FRAMES} \
        --output-file "${OUTPUT_FILE}"
fi

echo "========================================="
echo "Upsampling complete!"
echo "Results saved to: ${OUTPUT_FILE}"
echo "========================================="