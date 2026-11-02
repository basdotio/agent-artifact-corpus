#!/usr/bin/env python3
"""
Run this ONCE to build a real browser session.
Launches a visible Chrome window — you may need to solve a CAPTCHA manually.
Saves session state for headless reuse.
"""
import asyncio
from playwright.async_api import async_playwright

SESSION_FILE = "/Users/agenticjace/.openclaw/skills/cre-scraper/session.json"

async def bootstrap():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = await context.new_page()
        
        print("Loading Crexi...")
        await page.goto("https://www.crexi.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        
        print("Browsing around to build session history...")
        await page.goto("https://www.crexi.com/properties", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        
        for i in range(3):
            await page.evaluate(f"window.scrollTo(0, {i * 300})")
            await page.wait_for_timeout(1500)
        
        await page.goto(
            "https://www.crexi.com/properties?types=rv-parks&states=FL&minPrice=1000000&maxPrice=10000000",
            wait_until="domcontentloaded",
            timeout=30000
        )
        await page.wait_for_timeout(8000)
        
        print("Saving session state...")
        await context.storage_state(path=SESSION_FILE)
        print(f"Session saved to {SESSION_FILE}")
        
        await browser.close()

asyncio.run(bootstrap())
