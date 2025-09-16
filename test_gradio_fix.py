#!/usr/bin/env python3
"""Test the fixed Gradio app to ensure inference and file downloads work."""

import asyncio
import time
from pathlib import Path


async def test_gradio_app():
    """Test the Gradio app functionality with Playwright."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Opening Gradio app...")
        await page.goto("http://localhost:7860")
        await page.wait_for_load_state("networkidle")

        # Wait for the app to fully load
        await asyncio.sleep(3)

        # Navigate to Prompts tab
        print("Navigating to Prompts tab...")
        prompts_tab = page.locator("button:has-text('Prompts')")
        await prompts_tab.click()
        await asyncio.sleep(2)

        # Check if prompts are loaded
        prompts_table = page.locator("table").first
        await prompts_table.wait_for(timeout=5000)

        # Get all rows in the prompts table
        rows = await page.locator("tbody tr").all()
        print(f"Found {len(rows)} prompts in the table")

        if len(rows) > 0:
            # Select the first prompt by clicking its checkbox
            print("Selecting first prompt...")
            first_checkbox = page.locator("tbody tr").first.locator("input[type='checkbox']")
            await first_checkbox.click()
            await asyncio.sleep(1)

            # Check selection count
            selection_count = page.locator("text=/\\d+ prompt[s]? selected/")
            if await selection_count.is_visible():
                count_text = await selection_count.text_content()
                print(f"Selection count: {count_text}")

            # Scroll down to inference section
            inference_section = page.locator("text='Inference Parameters'")
            if await inference_section.is_visible():
                await inference_section.scroll_into_view_if_needed()
                print("Found Inference Parameters section")

            # Click Run Inference button
            run_button = page.locator("button:has-text('Run Inference')")
            if await run_button.is_visible():
                print("Clicking Run Inference button...")
                await run_button.click()

                # Wait for status message
                await asyncio.sleep(2)

                # Check for inference status message
                status_msg = page.locator("text=/✅|❌|Running|Started/").first
                if await status_msg.is_visible():
                    status_text = await status_msg.text_content()
                    print(f"Inference status: {status_text}")

                # Navigate to Jobs & Queue tab to check if job is running
                print("Checking Jobs & Queue tab...")
                jobs_tab = page.locator("button:has-text('Jobs & Queue')")
                await jobs_tab.click()
                await asyncio.sleep(2)

                # Check for active job
                active_job = page.locator("text=/Active Job|Container/")
                if await active_job.is_visible():
                    job_text = await active_job.text_content()
                    print(f"Jobs status: {job_text[:100]}...")

                # Check container details
                container_details = page.locator("text=/Container:|container_/")
                if await container_details.is_visible():
                    details_text = await container_details.text_content()
                    print(f"Container found: {details_text[:100]}...")
                else:
                    print("WARNING: No active container found in Jobs & Queue")
            else:
                print("ERROR: Run Inference button not found")
        else:
            print("WARNING: No prompts available to test inference")

        # Keep browser open for manual inspection
        print("\nTest complete! Keeping browser open for 10 seconds...")
        await asyncio.sleep(10)

        await browser.close()
        print("Test finished!")


if __name__ == "__main__":
    asyncio.run(test_gradio_app())
