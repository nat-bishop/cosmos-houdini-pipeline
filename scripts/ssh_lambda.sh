#!/usr/bin/env bash
# ssh_lambda.sh — quick SSH into remote using config.toml
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${HERE}/.." && pwd)"
CONFIG_FILE="${PROJECT_ROOT}/cosmos_workflow/config/config.toml"

# Simple TOML parsing to extract user, host, and SSH key
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file not found: $CONFIG_FILE" >&2
    exit 1
fi

# Extract user, host, and SSH key from TOML using grep and sed, handling comments
USER=$(grep "^user = " "$CONFIG_FILE" | sed 's/^user = "\([^"]*\)".*/\1/')
HOST=$(grep "^host = " "$CONFIG_FILE" | sed 's/^host = "\([^"]*\)".*/\1/')
SSH_KEY=$(grep "^ssh_key = " "$CONFIG_FILE" | sed 's/^ssh_key = "\([^"]*\)".*/\1/')

# Validate extracted values
if [[ -z "$USER" || -z "$HOST" || -z "$SSH_KEY" ]]; then
    echo "Error: Could not extract user, host, or SSH key from config file" >&2
    exit 1
fi

# Expand the SSH key path (handle ~ expansion)
SSH_KEY=$(echo "$SSH_KEY" | sed 's|^~|'"$HOME"'|')

# Check if SSH key exists
if [[ ! -f "$SSH_KEY" ]]; then
    echo "Error: SSH key not found: $SSH_KEY" >&2
    exit 1
fi

SSH_CONNECTION="${USER}@${HOST}"

# SSH options for better connection experience
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -i $SSH_KEY"

# Connect to remote
echo "Connecting to $SSH_CONNECTION using key: $SSH_KEY..."
ssh -A ${SSH_OPTS} "${SSH_CONNECTION}"
