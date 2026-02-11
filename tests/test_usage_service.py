from app.services.usage import UsageService
from app.db.session import async_session as async_session_factory
import asyncio
import sys
import os

# Setup path to find 'app'
sys.path.append(os.getcwd())

# --- FIX: Importing the correct variable name ---

# --- CONFIGURATION ---
# Your REAL User ID
TARGET_USER_ID = "d2d9686e-720b-4d79-ad5c-43e6ed15a2d7"
# ---------------------


async def test_logic():
    # usage: async_session() creates the session instance
    async with async_session_factory() as db:
        service = UsageService(db)
        print(f"🔍 Testing UsageService for User: {TARGET_USER_ID}")

        # 1. Check Initial State
        print("\n--- Step 1: Checking Initial Limits ---")
        try:
            initial_check = await service.check_limit(TARGET_USER_ID, "docs_generated")
            print(f"📊 Plan: {initial_check['plan']}")
            print(f"📊 Used: {initial_check['used']}")
            print(f"📊 Remaining: {initial_check['remaining']}")

            initial_used = initial_check['used']
        except Exception as e:
            print(f"❌ Failed to check limit: {e}")
            return

        # 2. Record New Usage
        print("\n--- Step 2: Recording Usage (+1) ---")
        try:
            # We record 1 'docs_generated'
            usage_record = await service.record_usage(
                user_id=TARGET_USER_ID,
                resource_type="docs_generated",
                amount=1,
                resource_id="test_script_verify"
            )
            print(f"✅ Usage Recorded! ID: {usage_record.id}")
        except Exception as e:
            print(f"❌ Failed to record usage: {e}")
            return

        # 3. Verify the Ledger Updated
        print("\n--- Step 3: Verifying Math ---")
        final_check = await service.check_limit(TARGET_USER_ID, "docs_generated")
        print(f"📊 New Used Count: {final_check['used']}")

        if final_check['used'] == initial_used + 1:
            print("\n🎉 SUCCESS: The Service is counting correctly!")
        else:
            print("\n⚠️ FAILURE: The count did not increase. Check your SQL query logic.")

if __name__ == "__main__":
    asyncio.run(test_logic())
