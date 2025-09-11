"""Test the Output Details display in the Outputs tab."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_output_details():
    """Test that Output Details shows input videos and prompt info."""
    from playwright.async_api import async_playwright

    # Start the Gradio app
    print("[START] Launching Gradio app...")
    process = subprocess.Popen(
        [sys.executable, "-m", "cosmos_workflow.ui.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Capture stdout to see logging
    def read_output():
        for line in process.stdout:
            if "Found" in line or "Returning" in line or "Checking for output" in line or "Selected output video:" in line or "Extracted run_id:" in line or "Got run data:" in line or "Run has prompt_id:" in line or "Got prompt data:" in line or "Prompt has inputs:" in line or "Returning run_info" in line or "CosmosAPI" in line:
                print(f"[LOG] {line.strip()}")

    import threading
    log_thread = threading.Thread(target=read_output)
    log_thread.daemon = True
    log_thread.start()

    # Wait for app startup
    print("[WAIT] Waiting for app to initialize...")
    time.sleep(8)

    try:
        async with async_playwright() as p:
            print("[BROWSER] Launching browser...")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            print("[NAVIGATE] Opening http://127.0.0.1:7860...")
            await page.goto("http://127.0.0.1:7860", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Navigate to Outputs tab
            print("\n[TEST] Testing Outputs tab...")
            outputs_tab = page.locator('button[role="tab"]').filter(has_text="Outputs")
            if await outputs_tab.is_visible():
                await outputs_tab.click()
                await page.wait_for_timeout(2000)
                print("  Clicked on Outputs tab")

            # Refresh outputs
            refresh_btn = page.locator('button:has-text("Refresh Outputs")')
            if await refresh_btn.is_visible():
                await refresh_btn.click()
                await page.wait_for_timeout(2000)
                print("  Refreshed outputs")

            # Check gallery for outputs
            gallery_items = page.locator('.gallery-item')
            gallery_count = await gallery_items.count()

            if gallery_count > 0:
                print(f"  Found {gallery_count} gallery items")

                # Click on first gallery item
                await gallery_items.first.click()
                await page.wait_for_timeout(2000)
                print("  Selected first output")

                # Check if output details are visible
                output_details = page.locator('*:has-text("Output Details")')
                if await output_details.is_visible():
                    print("  Output Details section is visible")

                    # Get the entire details content
                    details_container = output_details.locator('..')
                    if await details_container.is_visible():
                        details_text = await details_container.inner_text()
                        print("\n  Output Details Content:")
                        print("  " + "=" * 50)
                        for line in details_text.split("\n"):
                            print(f"  {line}")
                        print("  " + "=" * 50)

                        # Check for specific sections
                        if "Prompt Information" in details_text:
                            print("  [OK] 'Prompt Information' section found")
                        else:
                            print("  [FAIL] 'Prompt Information' section NOT found")

                        if "Input Videos" in details_text:
                            print("  [OK] 'Input Videos' section found")
                        else:
                            print("  [FAIL] 'Input Videos' section NOT found")

                        if "Run Details" in details_text:
                            print("  [OK] 'Run Details' section found")
                        else:
                            print("  [FAIL] 'Run Details' section NOT found")
                else:
                    print("  [FAIL] Output Details section not visible")

                await page.screenshot(path=".claude/output_details_test.png")
                print("\n[SCREENSHOT] Saved to output_details_test.png")
            else:
                print("  ! No gallery items found")

            # Wait a bit to see console output
            await page.wait_for_timeout(3000)

            await browser.close()

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[CLEANUP] Stopping Gradio app...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("[DONE] App terminated")


if __name__ == "__main__":
    # Create output directory
    Path(".claude").mkdir(exist_ok=True)

    # Run the test
    asyncio.run(test_output_details())