#!/usr/bin/env python3
"""Test script to debug app installation check"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_app_check():
    # Use the GitHub token from env
    github_token = os.getenv("GITHUB_TOKEN")
    org_id = "beta-org-for-pustak"
    
    if not github_token:
        print("❌ No GITHUB_TOKEN in .env")
        return
    
    print(f"🔐 Using token: {github_token[:20]}...")
    print(f"🏢 Checking org: {org_id}")
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Test endpoint
        async with session.get(
            "https://api.github.com/user/installations",
            headers=headers
        ) as resp:
            print(f"\n📊 Response status: {resp.status}")
            data = await resp.json()
            
            print(f"\n📦 Full response:")
            import json
            print(json.dumps(data, indent=2))
            
            installations = data.get('installations', [])
            print(f"\n📋 Found {len(installations)} installations:")
            for inst in installations:
                account = inst.get('account', {})
                login = account.get('login')
                app_name = inst.get('app_slug')
                print(f"   - {login} (app: {app_name})")
            
            # Check if our org is there
            app_installed = any(
                inst.get('account', {}).get('login') == org_id 
                for inst in installations
            )
            print(f"\n✅ App installed for {org_id}: {app_installed}")

if __name__ == "__main__":
    asyncio.run(test_app_check())
