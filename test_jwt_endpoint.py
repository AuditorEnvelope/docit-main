#!/usr/bin/env python3
"""
Test GitHub App JWT authentication directly
"""
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, '/Users/harshsrivastava/Desktop/doc_ai/src')

from utilities.github_app_helper import get_github_app_helper

async def test_jwt():
    print("🔐 Testing GitHub App JWT Authentication\n")
    
    github_app = get_github_app_helper()
    
    # Test 1: Generate JWT
    print("1️⃣  Generating JWT...")
    jwt_token = github_app._generate_jwt()
    if jwt_token:
        print(f"   ✅ JWT generated: {jwt_token[:50]}...")
    else:
        print(f"   ❌ Failed to generate JWT")
        return False
    
    # Test 2: Get installations
    print("\n2️⃣  Getting app installations...")
    installations = await github_app.get_app_installations()
    if installations:
        print(f"   ✅ Got {len(installations)} installations:")
        for inst in installations:
            print(f"      - {inst.get('account', {}).get('login')}")
        return True
    else:
        print(f"   ❌ Failed to get installations")
        print(f"   This means the JWT is invalid or the app has no permissions")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_jwt())
    sys.exit(0 if result else 1)
