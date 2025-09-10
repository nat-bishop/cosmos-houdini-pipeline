# Python Package Development Best Practices with Claude Code

## The Multi-Branch Challenge

When developing Python packages across multiple branches with AI assistants like Claude Code, you face several challenges:

1. **Single Installation Point**: `pip install` creates one installation per environment
2. **Branch Switching**: Different branches may have incompatible code
3. **AI Assistant Context**: Claude Code runs commands in isolated sessions
4. **Testing Requirements**: Need to test actual code from current branch

## Best Practice Recommendations

### 1. **For Active Development: Use Module Execution (RECOMMENDED)**

The simplest and most reliable approach for multi-branch development:

```bash
# Instead of installed commands:
cosmos ui  # ❌ Depends on pip install

# Use Python module execution:
python -m cosmos_workflow.ui.app  # ✅ Always uses current directory code
```

**Advantages:**
- No installation required
- Always uses code from current directory
- Branch-independent
- Claude Code can run these reliably
- No environment conflicts

**Implementation:**
```python
# Create a dev runner script (run.py) in project root:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Now import and run your code
from cosmos_workflow.ui.app import create_ui
create_ui().launch()
```

### 2. **For CLI Testing: Temporary Editable Install**

When you need to test CLI commands as they'll be used in production:

```bash
# Install from current branch
pip install -e .

# Test your commands
cosmos ui
cosmos create prompt "test" inputs/videos/dir

# When switching branches
cd /other/branch
pip install -e .  # Overwrites previous installation
```

**Advantages:**
- Tests actual CLI interface
- Matches production usage
- Simple mental model

**Disadvantages:**
- Must reinstall when switching branches
- Only one branch active at a time

### 3. **For Simultaneous Multi-Branch: Virtual Environments**

When working on multiple branches simultaneously:

```bash
# Branch 1
cd /project/branch1
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -e .

# Branch 2 (different terminal)
cd /project/branch2
python -m venv .venv
source .venv/Scripts/activate
pip install -e .
```

**Advantages:**
- Complete isolation
- Multiple branches active simultaneously
- No conflicts

**Disadvantages:**
- More setup overhead
- Must remember to activate venv
- Claude Code needs venv-aware commands

### 4. **For Claude Code Integration: Direct Module Pattern**

The pattern that works best with AI assistants:

```python
# Commands Claude Code can always run:
python -m cosmos_workflow.ui.app
python -m cosmos_workflow.api

# Or with a runner script:
python run_cosmos.py ui
python run_cosmos.py api-test
```

This approach ensures:
- Commands work without installation
- Branch code is always used
- No environment conflicts
- Consistent behavior

## Recommended Project Structure

```
cosmos-workflow/
├── run_cosmos.py          # Development runner (no install needed)
├── setup.py               # Package definition
├── cosmos_workflow/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py   # CLI entry point
│   │   └── ...
│   ├── ui/
│   │   ├── app.py        # Can be run with python -m
│   │   └── ...
│   └── api/
│       ├── __init__.py   # API module
│       └── ...
└── scripts/
    ├── dev.sh            # Development shortcuts
    └── test.sh           # Test runners
```

## Decision Matrix

| Scenario | Recommended Approach | Why |
|----------|---------------------|-----|
| Active development on one branch | `python -m` commands | No install needed, always current |
| Testing CLI interface | `pip install -e .` | Tests actual CLI behavior |
| Multiple branches simultaneously | Virtual environments | Complete isolation |
| Claude Code automation | Direct module execution | Reliable, branch-independent |
| Production deployment | `pip install` | Standard Python packaging |
| Quick experiments | `python run_cosmos.py` | Simple, flexible |

## Anti-Patterns to Avoid

1. **Global pip install of development packages**
   ```bash
   # Don't do this for dev packages:
   pip install /path/to/dev/package  # ❌
   ```

2. **Hardcoding paths in imports**
   ```python
   # Don't do this:
   sys.path.append('/specific/path/to/project')  # ❌
   ```

3. **Assuming installation in AI sessions**
   ```bash
   # Claude Code shouldn't assume:
   cosmos ui  # ❌ May not be installed

   # Better:
   python -m cosmos_workflow.ui.app  # ✅
   ```

## The Golden Rule

**For development: Run from source**
**For production: Install the package**

This keeps development flexible while ensuring production deployment follows Python standards.

## Quick Start for This Project

```bash
# For immediate use without any setup:
python -m cosmos_workflow.ui.app

# For testing CLI commands:
pip install -e . && cosmos ui

# For Claude Code to run commands:
python run_cosmos.py ui
```