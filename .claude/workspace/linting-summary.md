# Linting Configuration Summary

## What We Changed

### Before (Overengineered)
- **31 rule sets** enabled
- **1,410 errors** (mostly false positives)
- Pedantic style enforcement
- Blocked legitimate code patterns

### After (Pragmatic)
- **11 rule sets** focused on real issues
- **41 real problems** to fix
- Catches bugs and security issues
- Allows legitimate patterns (print in CLI, etc.)

## Current Real Issues (41 total)

### Performance (17)
- `logging-f-string` (17) - Using f-strings in logging prevents lazy evaluation

### Potential Bugs (10)
- `unused-variable` (3) - Dead code
- `unused-loop-control-variable` (2) - Loop variable not used
- `raise-without-from-inside-except` (2) - Loses exception context
- `mutable-class-default` (5) - Dangerous mutable defaults

### Timezone Issues (10)
- `call-datetime-now-without-tzinfo` (7) - Can cause timezone bugs
- `call-datetime-fromtimestamp` (2) - Missing timezone
- `call-datetime-strptime-without-zone` (1) - Missing timezone

### Security (2)
- `hashlib-insecure-hash-function` (1) - Using MD5/SHA1
- `subprocess-without-shell-equals-true` (1) - Shell injection risk

## What We're NOT Checking Anymore

- Docstring formatting (not critical)
- Print statements (legitimate for CLI)
- Complexity metrics (subjective)
- Line length (formatter handles this)
- Import order minutiae (beyond basic sorting)
- Commented code detection (sometimes useful)
- Magic numbers (context-dependent)

## Rule Categories We Keep

1. **F - PyFlakes**: Undefined names, unused imports
2. **E/W - PyCodeStyle**: Basic Python errors/warnings
3. **B - Bugbear**: Common bugs and design problems
4. **I - isort**: Import sorting (consistency)
5. **UP - PyUpgrade**: Outdated Python syntax
6. **G - Logging Format**: Performance issues
7. **S - Security**: Vulnerabilities
8. **DTZ - Datetime**: Timezone awareness
9. **RUF - Ruff**: Helpful Ruff-specific checks

## Philosophy

**"Catch mistakes, not opinions"**

This configuration is specifically tuned for a CLI orchestration tool that:
- Uses print for legitimate output
- Has remote SSH/Docker execution (security matters!)
- Uses logging extensively (performance matters!)
- Needs to be maintainable, not perfect
