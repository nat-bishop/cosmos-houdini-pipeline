# Shell Completion Setup

Enable tab completion for `cosmos` commands.

## Git Bash (Windows)
```bash
# Add to ~/.bashrc
eval "$(_COSMOS_COMPLETE=bash_source python /path/to/cosmos)"
source ~/.bashrc
```

## PowerShell
```powershell
# Add to $PROFILE (edit with: notepad $PROFILE)
Register-ArgumentCompleter -Native -CommandName cosmos -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $env:_COSMOS_COMPLETE = 'powershell_complete'
    python C:\path\to\cosmos | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
```

## Linux/Mac Bash
```bash
eval "$(_COSMOS_COMPLETE=bash_source cosmos)"
```

## Zsh
```bash
eval "$(_COSMOS_COMPLETE=zsh_source cosmos)"
```
