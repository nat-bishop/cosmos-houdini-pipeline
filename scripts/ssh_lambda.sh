#!/usr/bin/env bash
# ssh_lambda.sh — quick SSH into remote
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/config.sh"
ssh ${SSH_OPTS} "${REMOTE}"
