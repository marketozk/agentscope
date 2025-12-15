"""Quick smoke test: verify BrowserStep retries on ActionNotConfirmed during Airtable signup.

Runs only the registration step with an intentionally invalid email, so the step should fail and retry.
"""

import asyncio
import sys
from pathlib import Path

# The `autonomous_airtable` folder is not a Python package (no __init__.py),
# so we import modules via an explicit sys.path entry.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from autonomous_registration_loop import AutonomousRegistration  # noqa: E402
from fingerprint_generator import FingerprintGenerator  # noqa: E402


async def main() -> None:
    system = AutonomousRegistration()

    # Minimal browser init (no warmup / no temp-mail)
    profile = system.profile_manager.create_profile()
    profile_path = Path(profile["profile_path"])

    fingerprint = FingerprintGenerator().generate_complete_fingerprint()
    await system.init_browser(fingerprint, profile_path)

    try:
        airtable_page = await system.context.new_page()

        # Intentionally invalid email to trigger UI validation.
        ok = await system.register_step(
            airtable_page,
            email="invalid@@",
            full_name="Test User",
            password="Passw0rd!Passw0rd!",
            context={"iteration": 0, "email": "invalid@@", "purpose": "debug_register_retry"},
        )
        print(f"REGISTER_STEP_RESULT={ok}")
    finally:
        try:
            await system.agent.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
