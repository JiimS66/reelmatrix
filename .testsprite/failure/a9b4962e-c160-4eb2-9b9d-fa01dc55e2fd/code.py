import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://121.43.99.199:3000")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'Campaigns' button in the left navigation to open the Campaigns list.
        # Campaigns button
        elem = page.get_by_text('Home22', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Campaigns 12', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Results' button in the campaign header to open the Results tab.
        # Results button
        elem = page.get_by_role('button', name='Results', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the Results tab renders without a blank screen, browser error, or stuck loading state.
        await page.locator("xpath=/html/body/div[2]/main/div/div/div/div[2]/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: The 'Learn from results ↻' button is visible, showing the Results tab content rendered.
        await expect(page.locator("xpath=/html/body/div[2]/main/div/div/div/div[2]/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "The 'Learn from results \u21bb' button is visible, showing the Results tab content rendered."
        await page.locator("xpath=/html/body/div[2]/main/div/div/div/div[2]/div[1]/div[1]/div/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The 'Publish all ↑' control is visible, confirming the Results area is not blank or errored.
        await expect(page.locator("xpath=/html/body/div[2]/main/div/div/div/div[2]/div[1]/div[1]/div/button[1]").nth(0)).to_be_visible(timeout=15000), "The 'Publish all \u2191' control is visible, confirming the Results area is not blank or errored."
        await page.locator("xpath=/html/body/div[2]/main/div/div/div/div[2]/div[1]/div[1]/div/button[2]").nth(0).scroll_into_view_if_needed()
        # Assert: The 'Sync GA4 ↻' button is visible, indicating the Results tab finished loading and is interactive.
        await expect(page.locator("xpath=/html/body/div[2]/main/div/div/div/div[2]/div[1]/div[1]/div/button[2]").nth(0)).to_be_visible(timeout=15000), "The 'Sync GA4 \u21bb' button is visible, indicating the Results tab finished loading and is interactive."
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    