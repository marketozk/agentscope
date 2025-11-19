
import asyncio
import shutil
from pathlib import Path
from browser_use import Agent, BrowserSession, BrowserProfile
from dotenv import load_dotenv
import os

load_dotenv()

async def main():
    print("Testing browser connection with FRESH profile...")
    
    # Create a temporary directory for the profile
    temp_profile_path = Path("./temp_browser_profile")
    if temp_profile_path.exists():
        try:
            shutil.rmtree(temp_profile_path)
        except Exception as e:
            print(f"Warning: Could not delete temp profile: {e}")
    
    # Ensure it exists
    temp_profile_path.mkdir(exist_ok=True)
    
    print(f"Using temporary profile at: {temp_profile_path.absolute()}")

    from config import get_llm
    try:
        llm = get_llm()
    except Exception as e:
        print(f"LLM init failed: {e}")
        return

    # Configure browser profile
    profile = BrowserProfile(
        headless=False,
        disable_security=True
        # user_data_dir=str(temp_profile_path.absolute()) # Try without custom profile first
    )
    
    # Create session
    session = BrowserSession(browser_profile=profile)

    agent = Agent(
        task="Go to google.com and print the title",
        llm=llm,
        browser_session=session
    )
    
    print("Running agent...")
    try:
        result = await agent.run()
        print("Result:", result)
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        pass

if __name__ == "__main__":
    asyncio.run(main())
