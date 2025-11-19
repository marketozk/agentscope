import asyncio
from playwright.async_api import async_playwright
import httpx

async def main():
    print("Starting Playwright with remote-debugging-port=9222 ...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--remote-debugging-port=9222"],
        )
        print("Browser launched. Checking CDP /json/version ...")
        try:
            resp = httpx.get("http://127.0.0.1:9222/json/version", timeout=5)
            print("Status:", resp.status_code)
            print("Text (first 500 chars):\n", resp.text[:500])
        except Exception as e:
            print("Error requesting CDP version:", e)
        await browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
