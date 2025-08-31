#!/usr/bin/env python3
"""Check and download results from remote GPU tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def main():
    """Check remote test results."""
    config_manager = ConfigManager()
    remote_config = config_manager.get_remote_config()
    ssh_options = config_manager.get_ssh_options()

    print("Checking remote test results...")
    print(f"Remote host: {remote_config.host}")

    ssh_manager = SSHManager(ssh_options)
    ssh_manager.connect()

    try:
        # Check for result files
        remote_results = "/home/ubuntu/resolution_tests"

        # List all files
        list_cmd = f"ls -la {remote_results}/ 2>/dev/null"
        exit_code, stdout, stderr = ssh_manager.execute_command(list_cmd, stream_output=False)

        if stdout:
            print("\nFiles found on remote:")
            print(stdout)

            # Check for JSON results
            json_cmd = f"ls -t {remote_results}/*.json 2>/dev/null | head -5"
            exit_code, stdout, stderr = ssh_manager.execute_command(json_cmd, stream_output=False)

            if stdout:
                print("\nJSON result files:")
                for line in stdout.strip().split("\n"):
                    if line:
                        print(f"  - {line}")

            # Check if test is still running
            ps_cmd = "ps aux | grep remote_resolution_test.py | grep -v grep"
            exit_code, stdout, stderr = ssh_manager.execute_command(ps_cmd, stream_output=False)

            if stdout:
                print("\n[INFO] Test is still running:")
                print(stdout)
            else:
                print("\n[INFO] Test appears to have completed or stopped")

            # Try to get summary if exists
            summary_cmd = f"tail -20 {remote_results}/summary.txt 2>/dev/null"
            exit_code, stdout, stderr = ssh_manager.execute_command(
                summary_cmd, stream_output=False
            )

            if stdout:
                print("\nLatest summary (last 20 lines):")
                print("-" * 60)
                print(stdout)
                print("-" * 60)

            # Download any available results
            local_results_dir = Path("resolution_test_results")
            local_results_dir.mkdir(exist_ok=True)

            # Get latest partial results
            latest_cmd = f"ls -t {remote_results}/results_partial_*.json 2>/dev/null | head -1"
            exit_code, stdout, stderr = ssh_manager.execute_command(latest_cmd, stream_output=False)

            if stdout and stdout.strip():
                latest_file = stdout.strip()
                local_file = local_results_dir / Path(latest_file).name

                print(f"\nDownloading latest partial results: {Path(latest_file).name}")
                with ssh_manager.get_sftp() as sftp:
                    sftp.get(latest_file, str(local_file))
                print(f"  Saved to: {local_file}")

                # Show a preview of results
                import json

                with open(local_file) as f:
                    results = json.load(f)

                print(f"\nResults so far: {len(results)} tests completed")

                successful = [r for r in results if r.get("success")]
                failed = [r for r in results if not r.get("success")]

                print(f"  Successful: {len(successful)}")
                print(f"  Failed: {len(failed)}")

                if successful:
                    print("\n  Working resolutions:")
                    for r in successful:
                        print(
                            f"    - {r['resolution']} with max_model_len={r.get('max_model_len', 4096)}"
                        )

                if failed:
                    print("\n  Failed resolutions:")
                    for r in failed:
                        error_type = r.get("error_type", "unknown")
                        print(
                            f"    - {r['resolution']} with max_model_len={r.get('max_model_len', 4096)} ({error_type})"
                        )
        else:
            print("No results directory found on remote")

    finally:
        ssh_manager.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
