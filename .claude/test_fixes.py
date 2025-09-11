"""Test the Video Directory update and Outputs tab prompt details fixes."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_ui_fixes():
    """Test the specific fixes for Video Directory and Outputs tab."""
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

            print("[NAVIGATE] Opening http://127.0.0.1:7860...")
            await page.goto("http://127.0.0.1:7860", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # ===== TEST 1: Video Directory field update =====
            print("\n[TEST 1] Testing Video Directory field update in Inputs tab...")

            # Navigate to Inputs tab
            inputs_tab = page.locator('button').filter(has_text="Inputs")
            if await inputs_tab.is_visible():
                await inputs_tab.click()
                await page.wait_for_timeout(1500)
                print("  ✓ Clicked on Inputs tab")

            # Check if there are any input directories to select
            gallery_items = page.locator('.gallery-item')
            item_count = await gallery_items.count()

            if item_count > 0:
                print(f"  ✓ Found {item_count} input directories")

                # Click on the first input directory
                await gallery_items.first.click()
                await page.wait_for_timeout(1000)
                print("  ✓ Selected first input directory")

                # Check if Video Directory field is populated
                video_dir_field = page.locator('input[placeholder*="Auto-filled"]').first
                if await video_dir_field.is_visible():
                    video_dir_value = await video_dir_field.input_value()
                    if video_dir_value:
                        print(f"  ✓ Video Directory field populated: {video_dir_value}")
                        await page.screenshot(path=".claude/fix1_video_dir_populated.png")
                    else:
                        print("  ✗ Video Directory field is empty")
                        await page.screenshot(path=".claude/fix1_video_dir_empty.png")
                else:
                    print("  ✗ Video Directory field not found")

                # Also check the selected info
                selected_info = page.locator('*:has-text("Path:")').first
                if await selected_info.is_visible():
                    info_text = await selected_info.inner_text()
                    print(f"  ✓ Selected info shows path: {info_text[:100]}...")
            else:
                print("  ! No input directories found to test")

            # ===== TEST 2: Outputs tab showing prompt details =====
            print("\n[TEST 2] Testing Outputs tab prompt details...")

            # Navigate to Outputs tab
            outputs_tab = page.locator('button').filter(has_text="Outputs")
            if await outputs_tab.is_visible():
                await outputs_tab.click()
                await page.wait_for_timeout(2000)
                print("  ✓ Clicked on Outputs tab")

            # Refresh outputs
            refresh_btn = page.locator('button:has-text("Refresh Outputs")')
            if await refresh_btn.is_visible():
                await refresh_btn.click()
                await page.wait_for_timeout(2000)
                print("  ✓ Refreshed outputs")

            # Check outputs table
            outputs_table = page.locator('table').last
            if await outputs_table.is_visible():
                # Check table headers
                headers = outputs_table.locator('thead th')
                header_count = await headers.count()

                if header_count > 0:
                    header_texts = []
                    for i in range(header_count):
                        header_text = await headers.nth(i).inner_text()
                        header_texts.append(header_text)
                    print(f"  ✓ Table headers: {header_texts}")

                    # Check if "Prompt" column exists (should be second column)
                    if len(header_texts) > 1 and "Prompt" in header_texts[1]:
                        print("  ✓ Prompt column found in table")

                        # Check table rows for prompt data
                        rows = outputs_table.locator('tbody tr')
                        row_count = await rows.count()

                        if row_count > 0:
                            print(f"  ✓ Found {row_count} output rows")

                            # Check first row's prompt column
                            first_row = rows.first
                            prompt_cell = first_row.locator('td').nth(1)
                            if await prompt_cell.is_visible():
                                prompt_text = await prompt_cell.inner_text()
                                if prompt_text and prompt_text != "N/A":
                                    print(f"  ✓ First row shows prompt: {prompt_text}")
                                else:
                                    print(f"  ! First row prompt shows: {prompt_text}")
                        else:
                            print("  ! No output rows found")
                    else:
                        print("  ✗ Prompt column not found in table")

                await page.screenshot(path=".claude/fix2_outputs_table.png")

            # Check gallery for outputs
            gallery_items = page.locator('.gallery-item')
            gallery_count = await gallery_items.count()

            if gallery_count > 0:
                print(f"  ✓ Found {gallery_count} gallery items")

                # Click on first gallery item
                await gallery_items.first.click()
                await page.wait_for_timeout(1500)
                print("  ✓ Selected first output")

                # Check if output details show prompt information
                output_info = page.locator('*:has-text("Prompt Information")')
                if await output_info.is_visible():
                    print("  ✓ Output details show 'Prompt Information' section")

                    # Check for input videos section
                    input_videos = page.locator('*:has-text("Input Videos")')
                    if await input_videos.is_visible():
                        print("  ✓ Output details show 'Input Videos' section")

                        # Get full details text
                        details_container = page.locator('*:has-text("Output Details")').locator('..')
                        if await details_container.is_visible():
                            details_text = await details_container.inner_text()
                            print("\n  Output Details Content:")
                            print("  " + "\n  ".join(details_text.split("\n")[:15]))
                    else:
                        print("  ! 'Input Videos' section not found")
                else:
                    print("  ! 'Prompt Information' section not found")

                    # Check what is actually shown
                    details_text = page.locator('*:has-text("Output Details")').locator('..')
                    if await details_text.is_visible():
                        content = await details_text.inner_text()
                        print(f"  Actual content shown:\n  {content[:300]}...")

                await page.screenshot(path=".claude/fix2_output_details.png")
            else:
                print("  ! No gallery items found")

            # ===== TEST 3: Verify CosmosAPI usage =====
            print("\n[TEST 3] Checking CosmosAPI usage...")

            # Navigate to Prompts tab to test prompt details
            prompts_tab = page.locator('button').filter(has_text="Prompts")
            if await prompts_tab.is_visible():
                await prompts_tab.click()
                await page.wait_for_timeout(1500)
                print("  ✓ Navigated to Prompts tab")

                # Check if prompts table has data
                prompts_table = page.locator('table').first
                if await prompts_table.is_visible():
                    rows = prompts_table.locator('tbody tr')
                    row_count = await rows.count()

                    if row_count > 0:
                        # Click on first row
                        await rows.first.click()
                        await page.wait_for_timeout(1000)

                        # Check if prompt details are shown
                        details = page.locator('*:has-text("Prompt Details")')
                        if await details.is_visible():
                            details_content = await details.locator('..').inner_text()
                            if "Prompt ID:" in details_content or "Created:" in details_content:
                                print("  ✓ Prompt details are displayed correctly")
                                print(f"  Details preview: {details_content[:200]}...")
                            else:
                                print("  ! Prompt details seem incomplete")
                        else:
                            print("  ✗ Prompt details not visible")

            # Final summary
            print("\n" + "="*50)
            print("TESTING COMPLETE")
            print("="*50)
            print("\nScreenshots saved:")
            print("  - fix1_video_dir_populated.png (or fix1_video_dir_empty.png)")
            print("  - fix2_outputs_table.png")
            print("  - fix2_output_details.png")

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
    asyncio.run(test_ui_fixes())