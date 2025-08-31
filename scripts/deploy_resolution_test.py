#!/usr/bin/env python3
"""Deploy and run resolution testing on remote GPU instance."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def main():
    """Deploy and run resolution test on remote."""
    # Initialize configuration
    config_manager = ConfigManager()
    remote_config = config_manager.get_remote_config()
    ssh_options = config_manager.get_ssh_options()

    print("=" * 80)
    print("DEPLOYING RESOLUTION TEST TO REMOTE GPU")
    print("=" * 80)
    print(f"Remote host: {remote_config.host}")
    print(f"Remote user: {remote_config.user}")

    # Create SSH manager
    ssh_manager = SSHManager(ssh_options)
    ssh_manager.connect()

    try:
        # Step 1: Upload test script
        local_script = Path("scripts/remote_resolution_test.py")
        remote_script = f"{remote_config.remote_dir}/remote_resolution_test.py"

        print("\n1. Uploading test script...")
        with ssh_manager.get_sftp() as sftp:
            sftp.put(str(local_script), remote_script)
        print(f"   [OK] Uploaded to {remote_script}")

        # Step 2: Create output directory
        print("\n2. Creating output directory...")
        stdout, stderr, exit_code = ssh_manager.execute_command(
            "mkdir -p /home/ubuntu/resolution_tests"
        )
        print("   [OK] Created /home/ubuntu/resolution_tests")

        # Step 3: Run the test script
        print("\n3. Running resolution tests on GPU...")
        print("   This will take several minutes...")
        print("-" * 60)

        # Run with proper Python path
        cmd = f"""
        cd {remote_config.remote_dir} && \
        export PYTHONPATH={remote_config.remote_dir}:$PYTHONPATH && \
        export CUDA_VISIBLE_DEVICES=0 && \
        python remote_resolution_test.py
        """

        # Execute and stream output
        stdout, stderr, exit_code = ssh_manager.execute_command(cmd)

        if stdout:
            print(stdout)
        if stderr:
            print("STDERR:", stderr)

        # Step 4: Download results
        print("\n4. Downloading results...")

        # Create local results directory
        local_results_dir = Path("resolution_test_results")
        local_results_dir.mkdir(exist_ok=True)

        # Download result files
        remote_results = "/home/ubuntu/resolution_tests"

        # List result files
        list_cmd = f"ls -la {remote_results}/*.json {remote_results}/*.txt 2>/dev/null | tail -5"
        stdout, stderr, exit_code = ssh_manager.execute_command(list_cmd)

        if stdout:
            print("   Found result files:")
            print(stdout)

            # Download specific files
            try:
                # Try to download the most recent results file
                get_latest_cmd = (
                    f"ls -t {remote_results}/resolution_test_results_*.json 2>/dev/null | head -1"
                )
                latest_file, _, _ = ssh_manager.execute_command(get_latest_cmd)

                if latest_file and latest_file.strip():
                    latest_file = latest_file.strip()
                    local_file = local_results_dir / Path(latest_file).name
                    with ssh_manager.get_sftp() as sftp:
                        sftp.get(latest_file, str(local_file))
                    print(f"   [OK] Downloaded {Path(latest_file).name}")

                # Download summary if exists
                summary_remote = f"{remote_results}/summary.txt"
                summary_local = local_results_dir / "summary.txt"
                try:
                    with ssh_manager.get_sftp() as sftp:
                        sftp.get(summary_remote, str(summary_local))
                    print("   [OK] Downloaded summary.txt")
                except:
                    print("   [WARNING] No summary.txt found")

            except Exception as e:
                print(f"   [WARNING] Error downloading files: {e}")

            print(f"   Results saved to {local_results_dir}")
        else:
            print("   [WARNING] No result files found")

        # Step 5: Show summary
        print("\n5. Reading summary...")
        summary_cmd = f"cat {remote_results}/summary.txt 2>/dev/null"
        stdout, stderr, exit_code = ssh_manager.execute_command(summary_cmd)

        if stdout:
            print("-" * 60)
            print(stdout)
            print("-" * 60)

    finally:
        ssh_manager.disconnect()

    print("\n[OK] Testing complete!")
    print(f"Results saved in: {local_results_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
