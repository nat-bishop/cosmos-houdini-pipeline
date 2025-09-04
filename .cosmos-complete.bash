#!/bin/bash
# Lazy-loaded bash completion for cosmos CLI
# Source this file in your .bashrc instead of using eval

_cosmos_completion_loader() {
    # Remove the loader
    complete -r cosmos

    # Generate and eval the actual completion
    eval "$(_COSMOS_COMPLETE=bash_source cosmos)"

    # Invoke the actual completion function
    return 124  # Retry completion with newly loaded function
}

# Install lazy loader - only loads completions when tab is pressed
complete -D -F _cosmos_completion_loader cosmos 2>/dev/null || \
complete -F _cosmos_completion_loader cosmos