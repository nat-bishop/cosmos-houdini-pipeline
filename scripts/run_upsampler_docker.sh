#!/bin/bash
# Run the working prompt upsampler in Docker on remote GPU
# This script should be executed on the remote machine

# Configuration
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/NatsFS/cosmos-transfer1}"
DOCKER_IMAGE="${DOCKER_IMAGE:-nvcr.io/ubuntu/cosmos-transfer1:latest}"
CHECKPOINT_DIR="/workspace/checkpoints"

# Parse arguments
PROMPT=""
VIDEO=""
BATCH=""
OUTPUT_DIR="outputs/upsampled"
NO_OFFLOAD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)
            PROMPT="$2"
            shift 2
            ;;
        --video)
            VIDEO="$2"
            shift 2
            ;;
        --batch)
            BATCH="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --no-offload)
            NO_OFFLOAD="--no-offload"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build the Python command
if [ -n "$BATCH" ]; then
    PYTHON_CMD="python /workspace/scripts/working_prompt_upsampler.py --batch $BATCH --output-dir $OUTPUT_DIR --checkpoint-dir $CHECKPOINT_DIR $NO_OFFLOAD"
elif [ -n "$PROMPT" ] && [ -n "$VIDEO" ]; then
    PYTHON_CMD="python /workspace/scripts/working_prompt_upsampler.py --prompt \"$PROMPT\" --video $VIDEO --output-dir $OUTPUT_DIR --checkpoint-dir $CHECKPOINT_DIR $NO_OFFLOAD"
else
    echo "Error: Provide either --batch or both --prompt and --video"
    exit 1
fi

# Run Docker container with proper environment
echo "[INFO] Starting Docker container..."
echo "[INFO] Command: $PYTHON_CMD"

sudo docker run --rm --gpus all \
    -v "$REMOTE_DIR:/workspace" \
    -w /workspace \
    -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
    -e RANK=0 \
    -e LOCAL_RANK=0 \
    -e WORLD_SIZE=1 \
    -e LOCAL_WORLD_SIZE=1 \
    -e GROUP_RANK=0 \
    -e ROLE_RANK=0 \
    -e ROLE_NAME=default \
    -e OMP_NUM_THREADS=4 \
    -e MASTER_ADDR=127.0.0.1 \
    -e MASTER_PORT=29500 \
    -e TORCHELASTIC_USE_AGENT_STORE=False \
    -e TORCHELASTIC_MAX_RESTARTS=0 \
    -e TORCHELASTIC_RUN_ID=local \
    -e TORCH_NCCL_ASYNC_ERROR_HANDLING=1 \
    -e TORCHELASTIC_ERROR_FILE=/tmp/torch_error.log \
    $DOCKER_IMAGE \
    bash -c "$PYTHON_CMD"