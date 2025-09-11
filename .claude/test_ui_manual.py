"""Comprehensive manual testing with Playwright to verify UI changes."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def comprehensive_ui_test():
    """Thoroughly test the unified Prompts interface."""
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
                viewport={'width': 1920, 'height': 1080},
                record_video_dir=".claude/videos"
            )
            page = await context.new_page()

            # Track console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            print("[NAVIGATE] Opening http://127.0.0.1:7860...")
            await page.goto("http://127.0.0.1:7860", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Take initial screenshot
            await page.screenshot(path=".claude/01_initial_load.png")
            print("[SCREENSHOT] Initial load captured")

            # ===== TEST 1: Check main title and tabs =====
            print("\n[TEST 1] Checking main UI structure...")

            # Check title
            title = page.locator("h1").first
            if await title.is_visible():
                title_text = await title.inner_text()
                print(f"  ✓ Title found: {title_text}")
            else:
                print("  ✗ Title not found")

            # Check tabs exist
            tabs = page.locator(".tab-nav button")
            tab_count = await tabs.count()
            print(f"  ✓ Found {tab_count} tabs")

            for i in range(tab_count):
                tab_text = await tabs.nth(i).inner_text()
                print(f"    - Tab {i+1}: {tab_text}")

            # ===== TEST 2: Navigate to unified Prompts tab =====
            print("\n[TEST 2] Testing unified Prompts tab...")

            prompts_tab = page.locator('button:has-text("🚀 Prompts")')
            if await prompts_tab.is_visible():
                await prompts_tab.click()
                await page.wait_for_timeout(1500)
                print("  ✓ Clicked on Prompts tab")
                await page.screenshot(path=".claude/02_prompts_tab.png")
            else:
                # Try alternative selector
                prompts_tab = page.locator('button').filter(has_text="Prompts")
                if await prompts_tab.is_visible():
                    await prompts_tab.click()
                    await page.wait_for_timeout(1500)
                    print("  ✓ Clicked on Prompts tab (alt selector)")
                else:
                    print("  ✗ Could not find Prompts tab")

            # ===== TEST 3: Verify split-view layout =====
            print("\n[TEST 3] Verifying split-view layout...")

            # Check for split view structure
            split_view = page.locator('.split-view').first
            if await split_view.is_visible():
                print("  ✓ Split view layout detected")
            else:
                print("  ! Split view class not found, checking columns...")

            # Check left panel (prompts table)
            left_panel = page.locator('.split-left').first
            if not await left_panel.is_visible():
                left_panel = page.locator('[class*="col"]').first

            if await left_panel.is_visible():
                print("  ✓ Left panel (table) found")

                # Look for table
                table = page.locator('table').first
                if await table.is_visible():
                    print("  ✓ Prompts table visible")

                    # Check table headers
                    headers = page.locator('thead th')
                    header_count = await headers.count()
                    print(f"  ✓ Table has {header_count} columns")

                    for i in range(min(header_count, 6)):
                        header_text = await headers.nth(i).inner_text()
                        print(f"    - Column {i+1}: {header_text}")

            # Check right panel (details/operations)
            right_panel = page.locator('.split-right').first
            if not await right_panel.is_visible():
                right_panel = page.locator('[class*="col"]').nth(1)

            if await right_panel.is_visible():
                print("  ✓ Right panel (details/operations) found")

                # Check for detail cards
                detail_cards = page.locator('.detail-card')
                card_count = await detail_cards.count()
                print(f"  ✓ Found {card_count} detail cards")

            # ===== TEST 4: Test selection controls =====
            print("\n[TEST 4] Testing selection controls...")

            # Find Select All button
            select_all = page.locator('button:has-text("Select All")')
            if not await select_all.is_visible():
                select_all = page.locator('button').filter(has_text="Select")

            if await select_all.is_visible():
                await select_all.click()
                await page.wait_for_timeout(500)
                print("  ✓ Clicked Select All button")

                # Check selection count
                count_text = page.locator('.selection-counter').first
                if not await count_text.is_visible():
                    count_text = page.locator('*:has-text("selected")')

                if await count_text.is_visible():
                    count = await count_text.inner_text()
                    print(f"  ✓ Selection count: {count}")

            # Find Clear button
            clear_btn = page.locator('button:has-text("Clear")')
            if await clear_btn.is_visible():
                await clear_btn.click()
                await page.wait_for_timeout(500)
                print("  ✓ Clicked Clear button")

            await page.screenshot(path=".claude/03_selection_controls.png")

            # ===== TEST 5: Test operation tabs =====
            print("\n[TEST 5] Testing operation controls...")

            # Check for Inference tab
            inference_tab = page.locator('button:has-text("Inference")')
            if await inference_tab.is_visible():
                await inference_tab.click()
                await page.wait_for_timeout(500)
                print("  ✓ Inference tab found and clicked")

                # Check for weight sliders
                sliders = page.locator('input[type="range"]')
                slider_count = await sliders.count()
                print(f"  ✓ Found {slider_count} weight sliders")

                # Check Run Inference button
                run_btn = page.locator('button:has-text("Run Inference")')
                if await run_btn.is_visible():
                    print("  ✓ Run Inference button visible")

            # Check for Enhance tab
            enhance_tab = page.locator('button:has-text("Enhance")')
            if await enhance_tab.is_visible():
                await enhance_tab.click()
                await page.wait_for_timeout(500)
                print("  ✓ Enhance tab found and clicked")

                enhance_btn = page.locator('button:has-text("Enhance Prompts")')
                if await enhance_btn.is_visible():
                    print("  ✓ Enhance Prompts button visible")

            await page.screenshot(path=".claude/04_operations.png")

            # ===== TEST 6: Test CSS animations =====
            print("\n[TEST 6] Testing CSS animations and hover effects...")

            # Test table row hover
            table_rows = page.locator('tbody tr')
            if await table_rows.count() > 0:
                first_row = table_rows.first
                await first_row.hover()
                await page.wait_for_timeout(300)
                print("  ✓ Tested table row hover animation")

            # Test button hover
            buttons = page.locator('button').filter(has_text="Refresh")
            if await buttons.count() > 0:
                await buttons.first.hover()
                await page.wait_for_timeout(300)
                print("  ✓ Tested button hover animation")

            # ===== TEST 7: Check other tabs =====
            print("\n[TEST 7] Checking other tabs...")

            # Check Inputs tab
            inputs_tab = page.locator('button').filter(has_text="Inputs")
            if await inputs_tab.is_visible():
                await inputs_tab.click()
                await page.wait_for_timeout(1000)
                print("  ✓ Inputs tab working")

                # Check for Create Prompt section
                create_section = page.locator('*:has-text("Create New Prompt")')
                if await create_section.is_visible():
                    print("  ✓ Create Prompt section found in Inputs tab")

            # Check Outputs tab
            outputs_tab = page.locator('button').filter(has_text="Outputs")
            if await outputs_tab.is_visible():
                await outputs_tab.click()
                await page.wait_for_timeout(1000)
                print("  ✓ Outputs tab working")

            await page.screenshot(path=".claude/05_other_tabs.png")

            # ===== FINAL: Console error check =====
            print("\n[FINAL] Console error check...")
            if console_errors:
                print(f"  ⚠ Found {len(console_errors)} console errors:")
                for err in console_errors[:5]:
                    print(f"    - {err[:100]}")
            else:
                print("  ✓ No console errors detected")

            # Take final full-page screenshot
            await page.screenshot(path=".claude/06_final_fullpage.png", full_page=True)
            print("\n[SCREENSHOT] Full page screenshot saved")

            # Summary
            print("\n" + "="*50)
            print("TESTING COMPLETE")
            print("="*50)
            print("\nScreenshots saved in .claude/")
            print("  - 01_initial_load.png")
            print("  - 02_prompts_tab.png")
            print("  - 03_selection_controls.png")
            print("  - 04_operations.png")
            print("  - 05_other_tabs.png")
            print("  - 06_final_fullpage.png")

            if await context.videos:
                print("\nVideo recording saved in .claude/videos/")

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
    Path(".claude/videos").mkdir(exist_ok=True)

    # Run the test
    asyncio.run(comprehensive_ui_test())