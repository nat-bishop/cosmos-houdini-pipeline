#!/usr/bin/env bash
# config.sh — central config for Lambda runs

# ===== Remote instance =====
REMOTE_USER="${REMOTE_USER:-ubuntu}"
REMOTE_HOST="${REMOTE_HOST:-192.222.52.59}"   # <-- change this when the IP changes
REMOTE_PORT="${REMOTE_PORT:-22}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/LambdaSSHkey.pem}"

# ===== Project paths =====
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/NatsFS/cosmos-transfer1}"
# ===== Local paths =====
LOCAL_PROMPTS_DIR="${LOCAL_PROMPTS_DIR:-./inputs/prompts}"
LOCAL_VIDEOS_DIR="${LOCAL_VIDEOS_DIR:-./inputs/videos}"
LOCAL_OUTPUTS_DIR="${LOCAL_OUTPUTS_DIR:-./outputs}"
LOCAL_NOTES_DIR="${LOCAL_NOTES_DIR:-./notes}"

# ===== Docker image on remote =====
DOCKER_IMAGE="${DOCKER_IMAGE:-nvcr.io/ubuntu/cosmos-transfer1:latest}"

# ===== Derived helpers (do not edit) =====
SSH_BASE_OPTS="-p ${REMOTE_PORT} -o StrictHostKeyChecking=accept-new"
if [ -n "${SSH_KEY}" ] && [ -f "${SSH_KEY}" ]; then
  SSH_OPTS="${SSH_BASE_OPTS} -i ${SSH_KEY}"
else
  SSH_OPTS="${SSH_BASE_OPTS}"
fi
RSYNC_SSH="ssh ${SSH_OPTS}"
REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
