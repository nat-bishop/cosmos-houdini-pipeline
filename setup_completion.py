#!/usr/bin/env python3
"""Setup shell completion for Cosmos CLI.

This script sets up tab completion for the cosmos command.
Works on Windows (Git Bash, CMD, PowerShell) and Unix systems.
"""

import os
import platform
import sys
from pathlib import Path


def setup_bash_completion():
    """Setup completion for Bash/Git Bash."""
    bashrc = Path.home() / ".bashrc"

    completion_script = """
# Cosmos CLI completion
_cosmos_completion() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD \\
        _COSMOS_COMPLETE=bash_complete cosmos)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        elif [[ $type == 'file' ]]; then
            COMPREPLY+=( $(compgen -f -- "$value") )
        elif [[ $type == 'dir' ]]; then
            COMPREPLY+=( $(compgen -d -- "$value") )
        fi
    done

    return 0
}

_cosmos_completion_setup() {
    complete -o nosort -F _cosmos_completion cosmos
}

_cosmos_completion_setup
"""

    print(f"Setting up Bash completion in {bashrc}")

    # Check if completion already exists
    if bashrc.exists():
        content = bashrc.read_text()
        if "_cosmos_completion" in content:
            print("Completion already installed. Skipping.")
            return

    # Append completion script
    with open(bashrc, "a") as f:
        f.write("\n" + completion_script)

    print("Bash completion installed successfully!")
    print("Run 'source ~/.bashrc' or restart your terminal.")


def setup_windows_completion():
    """Setup completion for Windows CMD using doskey."""
    # Create a batch file for CMD completion
    batch_content = """@echo off
doskey cosmos=python "%~dp0cosmos" $*
"""

    batch_file = Path("cosmos_complete.bat")
    batch_file.write_text(batch_content)

    print(f"Created {batch_file}")
    print("To enable completion in CMD:")
    print("  1. Add this directory to your PATH")
    print(f"  2. Run: {batch_file}")
    print("\nFor permanent setup, add the doskey command to your CMD startup.")


def setup_powershell_completion():
    """Setup completion for PowerShell."""
    ps_script = """
Register-ArgumentCompleter -Native -CommandName cosmos -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $env:COMP_WORDS = $commandAst.ToString()
    $env:COMP_CWORD = $wordToComplete
    $env:_COSMOS_COMPLETE = 'powershell_complete'

    cosmos | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
"""

    # Get PowerShell profile path
    if platform.system() == "Windows":
        profile_path = (
            Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
        )
    else:
        profile_path = Path.home() / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"

    print("PowerShell completion script:")
    print(ps_script)
    print(f"\nAdd this to your PowerShell profile: {profile_path}")


def main():
    """Main setup function."""
    system = platform.system()

    print("Cosmos CLI Completion Setup")
    print("=" * 40)

    if len(sys.argv) > 1:
        shell = sys.argv[1].lower()
    else:
        # Auto-detect shell
        shell_env = os.environ.get("SHELL", "").lower()
        if "bash" in shell_env or "MINGW" in os.environ.get("MSYSTEM", ""):
            shell = "bash"
        elif system == "Windows":
            shell = "cmd"
        else:
            shell = "bash"

    if shell in ["bash", "gitbash"]:
        setup_bash_completion()
    elif shell == "cmd":
        setup_windows_completion()
    elif shell in ["powershell", "pwsh"]:
        setup_powershell_completion()
    else:
        print(f"Unsupported shell: {shell}")
        print("Supported shells: bash, gitbash, cmd, powershell")
        sys.exit(1)


if __name__ == "__main__":
    main()
