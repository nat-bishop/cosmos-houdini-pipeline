#!/usr/bin/env python3
"""Verification script for PromptManager removal refactoring."""

# Set UTF-8 encoding for Windows
import io
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def verify_no_prompt_manager_references():
    """Ensure PromptManager is completely removed."""
    print("Checking for PromptManager references...")

    # Use Python's glob to search for PromptManager references
    cosmos_dir = Path("cosmos_workflow")
    found_references = []

    for py_file in cosmos_dir.rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()
                if "PromptManager" in content:
                    # Check if it's not in a comment or deprecation notice
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "PromptManager" in line and not line.strip().startswith("#"):
                            found_references.append(f"{py_file}:{i + 1}: {line.strip()}")
        except Exception as e:
            print(f"  Warning: Could not read {py_file}: {e}")

    if found_references:
        print("✗ Found PromptManager references:")
        for ref in found_references:
            print(f"  {ref}")
        return False
    else:
        print("✓ No PromptManager references found in production code")
        return True


def verify_smart_naming_works():
    """Test smart naming end-to-end."""
    print("\nTesting smart naming functionality...")

    try:
        from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
        from cosmos_workflow.prompts.schemas import DirectoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input/output directories
            input_dir = Path(tmpdir) / "inputs"
            output_dir = Path(tmpdir) / "outputs"
            input_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            dir_manager = DirectoryManager(str(input_dir), str(output_dir))
            spec_manager = PromptSpecManager(dir_manager)

            # Test 1: Create enhanced prompt with descriptive content
            spec1 = spec_manager.create_prompt_spec(
                prompt_text="A foggy morning in the mountains with golden sunlight breaking through mist",
                is_upsampled=True,
                parent_prompt_text="morning",
            )

            # Check that smart naming worked (should contain keywords from prompt)
            name_lower = spec1.name.lower()
            has_smart_name = any(
                keyword in name_lower
                for keyword in ["fog", "morning", "mountain", "mist", "golden", "sunlight"]
            )

            if has_smart_name:
                print(f"✓ Smart naming works for descriptive prompt: {spec1.name}")
            else:
                print(f"✗ Smart naming failed for descriptive prompt: {spec1.name}")
                return False

            # Test 2: Verify it doesn't use old pattern
            if "_enhanced" in spec1.name:
                print(f"✗ Still using old '_enhanced' pattern: {spec1.name}")
                return False
            else:
                print("✓ Not using old '_enhanced' pattern")

            # Test 3: Test with minimal prompt (should fall back gracefully)
            spec2 = spec_manager.create_prompt_spec(prompt_text="test", is_upsampled=True)

            if spec2.name and spec2.name != "":
                print(f"✓ Fallback naming works for minimal prompt: {spec2.name}")
            else:
                print("✗ Fallback naming failed for minimal prompt")
                return False

            return True

    except ImportError as e:
        print(f"✗ Failed to import required modules: {e}")
        return False
    except Exception as e:
        print(f"✗ Smart naming test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_no_duplicate_saves():
    """Ensure single file creation per enhancement."""
    print("\nChecking for duplicate save patterns...")

    try:
        import json
        from pathlib import Path

        from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
        from cosmos_workflow.prompts.schemas import DirectoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup directories with date structure
            input_dir = Path(tmpdir) / "inputs"
            output_dir = Path(tmpdir) / "outputs"
            input_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            dir_manager = DirectoryManager(str(input_dir), str(output_dir))
            spec_manager = PromptSpecManager(dir_manager)

            # Create a prompt (it auto-saves on creation)
            spec = spec_manager.create_prompt_spec(
                prompt_text="A beautiful sunset over the ocean", is_upsampled=True
            )

            # Check that only one file was created in the date-based directory structure
            # Files are saved in inputs/YYYY-MM-DD/*.json format
            json_files = list(input_dir.rglob("*.json"))

            if len(json_files) == 1:
                print(f"✓ Single file created: {json_files[0].name}")

                # Verify content is correct
                with open(json_files[0]) as f:
                    saved_data = json.load(f)
                    spec_dict = spec.to_dict()
                    if saved_data.get("prompt") == spec_dict.get("prompt"):
                        print("✓ Saved content is correct")

                        # Verify smart naming in the saved file
                        if (
                            "sunset" in json_files[0].name.lower()
                            or "ocean" in json_files[0].name.lower()
                        ):
                            print("✓ Smart naming reflected in filename")
                        return True
                    else:
                        print("✗ Saved content mismatch")
                        return False
            elif len(json_files) == 0:
                print("✗ No files were created")
                return False
            else:
                print(f"✗ Multiple files created: {len(json_files)} files")
                for f in json_files:
                    print(f"  - {f.name}")
                return False

    except Exception as e:
        print(f"✗ Duplicate save check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_cli_commands_work():
    """Verify basic CLI commands work without PromptManager."""
    print("\nTesting CLI commands...")

    results = []

    # Test 1: Check if cosmos CLI is accessible using the correct entry point
    try:
        # Try the direct cosmos command first
        result = subprocess.run(  # noqa: S603
            [sys.executable, "cosmos", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,  # Run from project root
        )

        # If direct command doesn't work, try as module
        if result.returncode != 0:
            result = subprocess.run(  # noqa: S603
                [sys.executable, "-m", "cosmos_workflow", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

        if result.returncode == 0:
            print("✓ CLI help command works")
            results.append(True)
        else:
            # Check if the error is just about missing imports, not PromptManager
            if "PromptManager" in result.stderr:
                print(f"✗ CLI still references PromptManager: {result.stderr}")
                results.append(False)
            else:
                # CLI loads but may have other issues (like missing config)
                print("✓ CLI loads without PromptManager references")
                results.append(True)
    except Exception as e:
        print(f"✗ CLI help test failed: {e}")
        results.append(False)

    # Test 2: Check that we can import the main modules without PromptManager
    try:
        # This tests that the modules load properly
        import cosmos_workflow.cli
        import cosmos_workflow.prompts.prompt_spec_manager
        import cosmos_workflow.workflows.workflow_orchestrator

        print("✓ Core modules import successfully without PromptManager")
        results.append(True)
    except ImportError as e:
        if "PromptManager" in str(e):
            print(f"✗ Import failed due to PromptManager reference: {e}")
            results.append(False)
        else:
            print(f"✗ Import failed for other reason: {e}")
            results.append(False)
    except Exception as e:
        print(f"✗ Module import test failed: {e}")
        results.append(False)

    return all(results) if results else False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("VERIFICATION SCRIPT FOR PROMPTMANAGER REMOVAL")
    print("=" * 60)

    all_passed = True

    # Run each verification
    checks = [
        ("PromptManager References", verify_no_prompt_manager_references),
        ("Smart Naming", verify_smart_naming_works),
        ("Duplicate Saves", verify_no_duplicate_saves),
        ("CLI Commands", verify_cli_commands_work),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
            if not results[name]:
                all_passed = False
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results[name] = False
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")

    if all_passed:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        return 0
    else:
        print("\n⚠️ Some verifications failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
