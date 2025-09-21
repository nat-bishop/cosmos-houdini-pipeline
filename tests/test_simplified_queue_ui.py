"""Playwright tests for SimplifiedQueueService UI integration."""

import time
from pathlib import Path

# Test data
TEST_PROMPT_DESC = "Test prompt for SimplifiedQueueService"
TEST_VIDEO_DIR = "F:/Art/cosmos-transfer1/inputs/base_video_v9/first20/originals"


def test_queue_processing_with_timer(page, app_url):
    """Test that the SimplifiedQueueService processes jobs via Gradio timer."""

    # Navigate to the app
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Go to Prompts tab
    prompts_tab = page.locator("button", has_text="Prompts")
    prompts_tab.click()
    time.sleep(2)

    # Create a test prompt
    desc_input = page.locator("textarea[placeholder*='Enter prompt description']")
    desc_input.fill(TEST_PROMPT_DESC)

    video_dir_input = page.locator("input[placeholder*='Full path to video directory']")
    video_dir_input.fill(TEST_VIDEO_DIR)

    create_btn = page.locator("button", has_text="Create Prompt")
    create_btn.click()

    # Wait for success message
    time.sleep(3)
    success_msg = page.locator("text=/Created prompt ps_/")
    assert success_msg.is_visible(), "Prompt creation failed"

    # Extract prompt ID from success message
    success_text = success_msg.inner_text()
    prompt_id = success_text.split("Created prompt ")[1].split(" ")[0]
    print(f"Created prompt: {prompt_id}")

    # Go to Jobs tab to check queue
    jobs_tab = page.locator("button", has_text="Jobs")
    jobs_tab.click()
    time.sleep(2)

    # Check initial queue status
    queue_status = page.locator("div[id*='queue-status']")
    initial_status = queue_status.inner_text()
    print(f"Initial queue status: {initial_status}")

    # Now queue an enhancement job (simpler than inference)
    prompts_tab.click()
    time.sleep(2)

    # Select the created prompt
    select_btn = page.locator(f"button[id*='select-{prompt_id}']").first
    select_btn.click()
    time.sleep(1)

    # Click Enhance button
    enhance_btn = page.locator("button", has_text="Enhance")
    enhance_btn.click()
    time.sleep(1)

    # Confirm enhancement
    confirm_btn = page.locator("button", has_text="Enhance 1 Prompt(s)")
    confirm_btn.click()

    # Wait for job to be added to queue
    time.sleep(2)

    # Go back to Jobs tab
    jobs_tab.click()
    time.sleep(2)

    # Check that job appears in queue
    queue_content = queue_status.inner_text()
    assert "enhancement" in queue_content.lower() or "queued" in queue_content.lower(), (
        f"Job not in queue. Status: {queue_content}"
    )
    print(f"Job queued successfully: {queue_content}")

    # Wait for automatic processing (timer runs every 2 seconds)
    # Give it up to 10 seconds to process
    processed = False
    for _ in range(5):
        time.sleep(2)
        queue_content = queue_status.inner_text()
        if "running" in queue_content.lower():
            print(f"Job is running: {queue_content}")
            processed = True
            break
        elif "completed" in queue_content.lower() or "No jobs" in queue_content:
            print(f"Job completed: {queue_content}")
            processed = True
            break

    assert processed, f"Job was not processed automatically. Final status: {queue_content}"

    print("[SUCCESS] SimplifiedQueueService is processing jobs via Gradio timer!")


def test_no_race_conditions(page, app_url):
    """Test that multiple rapid job submissions don't cause race conditions."""

    # Navigate to the app
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Go to Prompts tab
    prompts_tab = page.locator("button", has_text="Prompts")
    prompts_tab.click()
    time.sleep(2)

    # Create multiple test prompts quickly
    prompt_ids = []
    for i in range(3):
        desc_input = page.locator("textarea[placeholder*='Enter prompt description']")
        desc_input.fill(f"Test prompt {i} for race condition test")

        video_dir_input = page.locator("input[placeholder*='Full path to video directory']")
        video_dir_input.fill(TEST_VIDEO_DIR)

        create_btn = page.locator("button", has_text="Create Prompt")
        create_btn.click()
        time.sleep(2)

        # Extract prompt ID
        success_msg = page.locator("text=/Created prompt ps_/")
        success_text = success_msg.inner_text()
        prompt_id = success_text.split("Created prompt ")[1].split(" ")[0]
        prompt_ids.append(prompt_id)
        print(f"Created prompt {i}: {prompt_id}")

    # Now rapidly queue enhancement jobs for all prompts
    for prompt_id in prompt_ids:
        select_btn = page.locator(f"button[id*='select-{prompt_id}']").first
        select_btn.click()
        time.sleep(0.5)

        enhance_btn = page.locator("button", has_text="Enhance")
        enhance_btn.click()
        time.sleep(0.5)

        confirm_btn = page.locator("button", has_text="Enhance 1 Prompt(s)")
        confirm_btn.click()
        time.sleep(0.5)

        print(f"Queued enhancement for {prompt_id}")

    # Go to Jobs tab
    jobs_tab = page.locator("button", has_text="Jobs")
    jobs_tab.click()
    time.sleep(2)

    # Check queue status
    queue_status = page.locator("div[id*='queue-status']")
    queue_content = queue_status.inner_text()
    print(f"Queue after rapid submission: {queue_content}")

    # Wait for processing to complete (or timeout)
    max_wait = 30  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        queue_content = queue_status.inner_text()
        if "No jobs" in queue_content:
            break
        print(f"Queue status: {queue_content}")
        time.sleep(2)

    print(f"Final queue status after {time.time() - start_time:.1f}s: {queue_content}")

    # Check that no errors occurred (would show in status)
    assert "error" not in queue_content.lower(), f"Errors detected: {queue_content}"
    assert "failed" not in queue_content.lower(), f"Failed jobs detected: {queue_content}"

    print("[SUCCESS] No race conditions detected with SimplifiedQueueService!")


if __name__ == "__main__":
    # For manual testing
    import subprocess
    import sys

    print("Starting Gradio app for testing...")
    app_process = subprocess.Popen(
        [sys.executable, "-m", "cosmos_workflow.ui.app"], cwd=Path(__file__).parent.parent
    )

    try:
        time.sleep(5)  # Wait for app to start

        # Run tests manually
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            app_url = "http://localhost:7860"

            print("\nRunning test_queue_processing_with_timer...")
            test_queue_processing_with_timer(page, app_url)

            print("\nRunning test_no_race_conditions...")
            test_no_race_conditions(page, app_url)

            browser.close()

    finally:
        app_process.terminate()
        print("\nAll tests completed!")
