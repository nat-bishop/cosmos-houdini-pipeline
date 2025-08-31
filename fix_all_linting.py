#!/usr/bin/env python3
"""Script to fix all remaining linting issues systematically."""

import re
import subprocess
from pathlib import Path


def fix_logging_fstrings():
    """Fix all G004 logging f-string issues."""
    print("\n[1/6] Fixing logging f-strings...")
    
    # Find all Python files
    for py_file in Path("cosmos_workflow").rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            original = content
        except Exception as e:
            print(f"  Skipping {py_file}: {e}")
            continue
        
        # Fix logger.info/warning/error/debug with f-strings
        patterns = [
            (r'logger\.info\(f"([^"]+)"\)', r'logger.info("\1")'),
            (r'logger\.warning\(f"([^"]+)"\)', r'logger.warning("\1")'),
            (r'logger\.error\(f"([^"]+)"\)', r'logger.error("\1")'),
            (r'logger\.debug\(f"([^"]+)"\)', r'logger.debug("\1")'),
        ]
        
        for pattern, replacement in patterns:
            # Find f-strings with single variable
            content = re.sub(
                r'logger\.(info|warning|error|debug)\(f"([^{]*)\{([^}]+)\}([^"]*)"\)',
                r'logger.\1("\2%s\4", \3)',
                content
            )
            # Find f-strings with multiple variables (basic case)
            content = re.sub(
                r'logger\.(info|warning|error|debug)\(f"([^{]*)\{([^}]+)\}([^{]*)\{([^}]+)\}([^"]*)"\)',
                r'logger.\1("\2%s\4%s\6", \3, \5)',
                content
            )
        
        if content != original:
            py_file.write_text(content, encoding='utf-8')
            print(f"  Fixed: {py_file}")


def fix_datetime_timezone():
    """Fix datetime.now() without timezone."""
    print("\n[2/6] Fixing datetime timezone issues...")
    
    files_to_fix = [
        "cosmos_workflow/cli.py",
        "cosmos_workflow/prompts/schemas.py",
        "cosmos_workflow/workflows/workflow_orchestrator.py",
        "cosmos_workflow/local_ai/video_metadata.py",
        "cosmos_workflow/local_ai/cosmos_sequence.py",
    ]
    
    for file_path in files_to_fix:
        py_file = Path(file_path)
        if not py_file.exists():
            continue
            
        content = py_file.read_text(encoding='utf-8')
        original = content
        
        # Add timezone import if needed
        if "datetime.now()" in content and "from datetime import" in content:
            if "timezone" not in content:
                content = re.sub(
                    r'from datetime import ([^;]+)',
                    r'from datetime import \1, timezone',
                    content,
                    count=1
                )
            
            # Replace datetime.now() with datetime.now(timezone.utc)
            content = re.sub(
                r'datetime\.now\(\)',
                r'datetime.now(timezone.utc)',
                content
            )
        
        if content != original:
            py_file.write_text(content, encoding='utf-8')
            print(f"  Fixed: {py_file}")


def fix_docstring_formatting():
    """Fix D205 docstring formatting issues."""
    print("\n[3/6] Fixing docstring formatting...")
    
    files_to_fix = [
        "cosmos_workflow/__main__.py",
        "cosmos_workflow/cli.py",
        "cosmos_workflow/workflows/workflow_orchestrator.py",
    ]
    
    for file_path in files_to_fix:
        py_file = Path(file_path)
        if not py_file.exists():
            continue
            
        content = py_file.read_text(encoding='utf-8')
        original = content
        
        # Fix multiline docstrings without blank line after summary
        content = re.sub(
            r'("""[^"\n]+)\n(\s+[^"])',
            r'\1\n\n\2',
            content
        )
        
        if content != original:
            py_file.write_text(content, encoding='utf-8')
            print(f"  Fixed: {py_file}")


def move_imports_to_top():
    """Move function-level imports to module level."""
    print("\n[4/6] Moving imports to top-level...")
    
    # This is complex and needs manual review for each case
    # For now, we'll just report them
    result = subprocess.run(
        ["ruff", "check", "cosmos_workflow/", "--select", "PLC0415"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("  These imports need manual review (inside functions):")
        lines = result.stdout.split('\n')[:10]  # Show first 10
        for line in lines:
            if "PLC0415" in line:
                print(f"    {line}")


def fix_line_length():
    """Fix long lines."""
    print("\n[5/6] Fixing long lines...")
    
    # Use ruff format with line length limit
    subprocess.run(
        ["ruff", "format", "cosmos_workflow/", "--line-length", "100"],
        capture_output=True
    )
    print("  Formatted with 100 char line limit")


def run_final_fixes():
    """Run final ruff fixes."""
    print("\n[6/6] Running final Ruff fixes...")
    
    # Run ruff with all safe fixes
    result = subprocess.run(
        ["ruff", "check", "cosmos_workflow/", "--fix"],
        capture_output=True,
        text=True
    )
    
    # Count remaining issues
    remaining = len([l for l in result.stdout.split('\n') if 'cosmos_workflow' in l])
    print(f"  Remaining issues: {remaining}")


def main():
    """Run all fixes."""
    print("Starting comprehensive linting fixes...")
    
    fix_logging_fstrings()
    fix_datetime_timezone()
    fix_docstring_formatting()
    move_imports_to_top()
    fix_line_length()
    run_final_fixes()
    
    print("\n" + "="*60)
    print("COMPLETE! Running final check...")
    
    # Final statistics
    result = subprocess.run(
        ["ruff", "check", "cosmos_workflow/", "--statistics"],
        capture_output=True,
        text=True
    )
    
    print("\nFinal issue count by type:")
    for line in result.stdout.split('\n')[:10]:
        if line.strip():
            print(f"  {line}")


if __name__ == "__main__":
    main()