import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Starting Playwright...")
    async with async_playwright() as p:
        print("Launching Browser...")
        try:
            # Try launching with arguments similar to what browser-use might use
            browser = await p.chromium.launch(
                headless=False,
                args=['--remote-debugging-port=9222']
            )
            print("Browser launched successfully!")
            
            page = await browser.new_page()
            await page.goto('https://google.com')
            print(f"Page title: {await page.title()}")
            
            await asyncio.sleep(2)
            await browser.close()
            print("Browser closed.")
        except Exception as e:
            print(f"Error launching browser: {e}")

if __name__ == "__main__":
    asyncio.run(main())
