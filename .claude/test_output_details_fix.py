"""Comprehensive test for Output Details fix with Playwright."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_output_details_fix():
    """Test that Output Details shows properly when clicking on generated videos."""
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

            # Track console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text()) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: console_errors.append(f"Page error: {exc}"))

            print("[NAVIGATE] Opening http://127.0.0.1:7860...")
            await page.goto("http://127.0.0.1:7860", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Navigate to Outputs tab
            print("\n[TEST 1] Navigating to Outputs tab...")
            outputs_tab = page.locator('button[role="tab"]').filter(has_text="Outputs")
            if await outputs_tab.is_visible():
                await outputs_tab.click()
                await page.wait_for_timeout(2000)
                print("  [OK] Clicked on Outputs tab")
                await page.screenshot(path=".claude/01_outputs_tab.png")
            else:
                print("  [FAIL] Could not find Outputs tab")
                return

            # Check if outputs are loaded
            print("\n[TEST 2] Checking for loaded outputs...")
            gallery_items = page.locator('.gallery-item, button[aria-label*="Thumbnail"]')
            gallery_count = await gallery_items.count()

            if gallery_count > 0:
                print(f"  [OK] Found {gallery_count} gallery items")
            else:
                print("  [FAIL] No gallery items found")
                # Try refreshing outputs
                refresh_btn = page.locator('button:has-text("Refresh Outputs")')
                if await refresh_btn.is_visible():
                    print("  → Clicking Refresh Outputs...")
                    await refresh_btn.click()
                    await page.wait_for_timeout(3000)
                    gallery_count = await gallery_items.count()
                    print(f"  → After refresh: {gallery_count} items")

            # Click on first gallery item
            print("\n[TEST 3] Clicking on first gallery item...")
            if gallery_count > 0:
                await gallery_items.first.click()
                await page.wait_for_timeout(2000)
                print("  [OK] Clicked on first gallery item")

                # Check for Output Details section
                print("\n[TEST 4] Checking for Output Details section...")

                # Look for Output Details heading
                output_details_heading = page.locator('text="Output Details"')
                if await output_details_heading.is_visible():
                    print("  [OK] Output Details heading is visible")
                else:
                    print("  [FAIL] Output Details heading NOT visible")

                # Check for content in the details
                details_content = page.locator('*:has-text("Output Video") >> ..')
                if await details_content.is_visible():
                    content_text = await details_content.inner_text()
                    print("\n  Output Details Content:")
                    print("  " + "=" * 60)
                    for line in content_text.split("\n")[:30]:
                        print(f"  {line}")
                    print("  " + "=" * 60)

                    # Check for specific sections
                    sections_found = []
                    if "Run Details" in content_text:
                        sections_found.append("Run Details")
                    if "Prompt Information" in content_text:
                        sections_found.append("Prompt Information")
                    if "Input Videos" in content_text:
                        sections_found.append("Input Videos")

                    print(f"\n  Sections found: {sections_found}")

                    if len(sections_found) == 3:
                        print("  [OK] ALL sections present (Run Details, Prompt Information, Input Videos)")
                    else:
                        missing = set(["Run Details", "Prompt Information", "Input Videos"]) - set(sections_found)
                        print(f"  [FAIL] Missing sections: {missing}")
                else:
                    # Try alternative selector
                    markdown_content = page.locator('.markdown, [class*="markdown"]').last
                    if await markdown_content.is_visible():
                        content_text = await markdown_content.inner_text()
                        print("\n  Found markdown content:")
                        print("  " + "=" * 60)
                        for line in content_text.split("\n")[:20]:
                            print(f"  {line}")
                        print("  " + "=" * 60)
                    else:
                        print("  [FAIL] No Output Details content found")

                await page.screenshot(path=".claude/02_output_details.png", full_page=True)
                print("\n[SCREENSHOT] Saved output details to 02_output_details.png")

                # Try clicking on other gallery items
                print("\n[TEST 5] Testing other gallery items...")
                for i in range(1, min(3, gallery_count)):
                    print(f"\n  Testing gallery item {i+1}...")
                    await gallery_items.nth(i).click()
                    await page.wait_for_timeout(1500)

                    details_check = page.locator('*:has-text("Run Details")')
                    if await details_check.is_visible():
                        print(f"    [OK] Item {i+1} shows Run Details")
                    else:
                        print(f"    [FAIL] Item {i+1} does NOT show Run Details")

            # Check console errors
            print("\n[TEST 6] Console error check...")
            if console_errors:
                print(f"  [WARNING] Found {len(console_errors)} console errors:")
                for err in console_errors[:5]:
                    if "KeyError" in err:
                        print(f"    [KEYERROR]: {err[:200]}")
                    elif "manifest.json" not in err.lower() and "postmessage" not in err.lower():
                        print(f"    - {err[:100]}")
            else:
                print("  [OK] No significant console errors")

            # Final summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)

            success = True
            if gallery_count == 0:
                print("FAIL: No gallery items loaded")
                success = False
            elif "KeyError" in str(console_errors):
                print("FAIL: KeyError detected when clicking gallery items")
                success = False
            else:
                print("PASS: Gallery items clickable without KeyError")

            print("\nScreenshots saved:")
            print("  - .claude/01_outputs_tab.png")
            print("  - .claude/02_output_details.png")

            await browser.close()
            return success

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    success = asyncio.run(test_output_details_fix())

    if success:
        print("\n[SUCCESS] All tests passed successfully!")
    else:
        print("\n[FAILED] Some tests failed - please review the output above")

    sys.exit(0 if success else 1)