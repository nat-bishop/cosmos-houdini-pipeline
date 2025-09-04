#!/bin/bash
# Claude Code status line script
# Shows: user@host current_directory [model_name]

# Read JSON input from stdin
input=$(cat)

# Extract information from JSON
model=$(echo "$input" | jq -r '.model.display_name // "Claude"')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // "."')
style=$(echo "$input" | jq -r '.output_style.name // "default"')

# Get current directory name
dir_name=$(basename "$cwd")

# Output formatted status line with colors (dimmed as specified)
printf "\033[2m%s@%s\033[0m \033[36m%s\033[0m \033[33m[%s]\033[0m" \
    "$(whoami)" \
    "$(hostname -s)" \
    "$dir_name" \
    "$model"