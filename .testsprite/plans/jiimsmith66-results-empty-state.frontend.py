import asyncio
import os
import re

from playwright import async_api
from playwright.async_api import expect


BASE_URL = os.environ.get("TARGET_URL", "http://121.43.99.199:3000").rstrip("/")


async def run_test():
    pw = None
    browser = None
    context = None

    try:
        pw = await async_api.async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process",
            ],
        )
        context = await browser.new_context()
        context.set_default_timeout(20000)
        page = await context.new_page()

        await page.goto(BASE_URL)
        await page.wait_for_load_state("domcontentloaded")

        await page.get_by_role("button", name=re.compile(r"Campaigns", re.I)).click()
        await page.get_by_role("button", name=re.compile(r"Results", re.I)).click()

        await expect(page.get_by_text("No published posts yet", exact=False)).to_be_visible()
        await expect(page.get_by_text("approved assets will land here", exact=False)).to_be_visible()
        await expect(page.get_by_text(re.compile(r"Mock data", re.I))).to_be_visible()
        await expect(page.get_by_text(re.compile(r"analytics.*signup attribution", re.I))).to_be_visible()

        for label in [
            "Impressions",
            "Clicks",
            "Signups",
            "Activated",
            "Paid",
            "Modeled pipeline",
        ]:
            await expect(page.get_by_text(label, exact=False).first).to_be_visible()

        await expect(page.get_by_text(re.compile(r"\$0"))).to_be_visible()

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()


asyncio.run(run_test())
