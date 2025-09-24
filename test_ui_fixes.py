#!/usr/bin/env python3
"""Test the UI fixes for issues reported by the user."""

import time
from playwright.sync_api import sync_playwright, expect


def test_ui_fixes():
    """Test all three UI fixes."""
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the app
        page.goto("http://localhost:7860")
        page.wait_for_load_state("networkidle")

        print("✓ App loaded successfully")

        # Test 1: Cancel selected job in queue
        print("\nTest 1: Testing Cancel Selected Job...")

        # Navigate to Active Jobs tab
        page.click('button:has-text("🚀 Active Jobs")')
        time.sleep(1)

        # Check if queue table exists
        queue_table = page.locator('.dataframe')
        if queue_table.count() > 0:
            print("✓ Queue table found")

            # Try to select a job if any exist
            rows = page.locator('.dataframe tbody tr')
            if rows.count() > 0:
                # Click on first row to select it
                rows.first.click()
                time.sleep(0.5)

                # Check if cancel button becomes visible
                cancel_btn = page.locator('button:has-text("❌ Cancel Selected Job")')
                if cancel_btn.is_visible():
                    print("✓ Cancel button is visible for selected job")
                else:
                    print("! Cancel button not visible (might not have queued jobs)")
            else:
                print("! No jobs in queue to test")
        else:
            print("! Queue table not found")

        # Test 2: Kill Active Job confirmation dialog
        print("\nTest 2: Testing Kill Active Job confirmation...")

        # Look for Kill Active Job button
        kill_btn = page.locator('button:has-text("🛑 Kill Active Job")')
        if kill_btn.is_visible():
            print("✓ Kill Active Job button found")

            # Click it
            kill_btn.click()
            time.sleep(0.5)

            # Check if confirmation dialog appears
            confirm_dialog = page.locator('text="⚠️ Confirm Kill Active Job"')
            if confirm_dialog.is_visible():
                print("✓ Kill confirmation dialog appeared!")

                # Check for confirm and cancel buttons
                confirm_btn = page.locator('button:has-text("⚠️ Confirm Kill")')
                cancel_btn = page.locator('button:has-text("Cancel")')

                if confirm_btn.is_visible() and cancel_btn.is_visible():
                    print("✓ Confirm and Cancel buttons visible")

                    # Test cancel button
                    cancel_btn.click()
                    time.sleep(0.5)

                    if not confirm_dialog.is_visible():
                        print("✓ Cancel button hides the dialog")
                    else:
                        print("✗ Dialog still visible after cancel")
                else:
                    print("✗ Confirm/Cancel buttons not visible")
            else:
                print("✗ Confirmation dialog did not appear")
        else:
            print("! Kill Active Job button not found")

        # Test 3: Delete Selected Run
        print("\nTest 3: Testing Delete Selected Run...")

        # Navigate to Runs tab
        page.click('button:has-text("📊 Runs")')
        time.sleep(2)

        # Check if there are any runs
        runs_gallery = page.locator('.gradio-gallery, [data-testid="gallery"]').first
        if runs_gallery.is_visible():
            print("✓ Runs gallery found")

            # Try to select first run if available
            gallery_items = page.locator('.gradio-gallery img, [data-testid="gallery"] img')
            if gallery_items.count() > 0:
                gallery_items.first.click()
                time.sleep(1)
                print("✓ Selected first run")

                # Look for delete button
                delete_btn = page.locator('button:has-text("🗑️ Delete Selected Run")')
                if delete_btn.is_visible():
                    print("✓ Delete button found")

                    # Click delete button
                    delete_btn.click()
                    time.sleep(1)

                    # Check if delete dialog appears
                    delete_preview = page.locator('text=/Delete Run:/')
                    if delete_preview.is_visible():
                        print("✓ Delete confirmation dialog appeared!")

                        # Check for checkbox
                        delete_checkbox = page.locator('label:has-text("Delete output files")')
                        if delete_checkbox.is_visible():
                            print("✓ Delete outputs checkbox visible")
                        else:
                            print("✗ Delete outputs checkbox not found")

                        # Check for confirm/cancel buttons
                        confirm_delete = page.locator('button:has-text("⚠️ Confirm Delete")')
                        cancel_delete = page.locator('button:has-text("Cancel")')

                        if confirm_delete.is_visible() and cancel_delete.is_visible():
                            print("✓ Confirm and Cancel buttons visible")

                            # Test cancel
                            cancel_delete.click()
                            time.sleep(0.5)

                            if not delete_preview.is_visible():
                                print("✓ Cancel button hides delete dialog")
                            else:
                                print("✗ Delete dialog still visible after cancel")
                        else:
                            print("✗ Delete dialog buttons not found")
                    else:
                        print("✗ Delete confirmation dialog did not appear")
                else:
                    print("! Delete button not visible")
            else:
                print("! No runs found to test delete")
        else:
            print("! Runs gallery not found")

        print("\n" + "="*50)
        print("Testing complete!")
        print("="*50)

        # Keep browser open for manual inspection
        input("\nPress Enter to close the browser...")

        browser.close()


if __name__ == "__main__":
    test_ui_fixes()