#!/usr/bin/env python3
"""
GitHub OAuth Diagnostic Script
Run this to check if your GitHub OAuth app is properly configured
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings

def check_oauth_config():
    print("\n" + "="*60)
    print("🔍 GITHUB OAUTH CONFIGURATION CHECK")
    print("="*60 + "\n")
    
    issues = []
    
    # Check Client ID
    if not settings.GITHUB_CLIENT_ID or settings.GITHUB_CLIENT_ID == "your_github_oauth_client_id":
        print("❌ GITHUB_CLIENT_ID is not set or is using default value")
        issues.append("GITHUB_CLIENT_ID")
    else:
        print(f"✅ GITHUB_CLIENT_ID is set: {settings.GITHUB_CLIENT_ID[:10]}...")
    
    # Check Client Secret
    if not settings.GITHUB_CLIENT_SECRET or settings.GITHUB_CLIENT_SECRET == "your_github_oauth_client_secret":
        print("❌ GITHUB_CLIENT_SECRET is not set or is using default value")
        issues.append("GITHUB_CLIENT_SECRET")
    else:
        print(f"✅ GITHUB_CLIENT_SECRET is set: {settings.GITHUB_CLIENT_SECRET[:10]}...")
    
    # Check callback URL
    print(f"\n📍 Callback URL: {settings.GITHUB_OAUTH_CALLBACK_URL}")
    
    print("\n" + "="*60)
    
    if issues:
        print("\n⚠️  ISSUES FOUND:\n")
        print("Please set the following environment variables in your .env file:\n")
        for var in issues:
            print(f"  {var}=<your_value_here>")
        
        print("\n📖 To create a GitHub OAuth App:")
        print("  1. Go to: https://github.com/settings/developers")
        print("  2. Click 'New OAuth App'")
        print("  3. Set 'Authorization callback URL' to:")
        print(f"     {settings.GITHUB_OAUTH_CALLBACK_URL}")
        print("  4. Copy Client ID and Client Secret to your .env file")
        print("\n")
        return False
    else:
        print("\n✅ All OAuth credentials are configured!")
        print("\n💡 If you're still getting errors, check that:")
        print("  1. The OAuth app exists at: https://github.com/settings/developers")
        print(f"  2. The callback URL matches: {settings.GITHUB_OAUTH_CALLBACK_URL}")
        print("  3. The Client ID and Secret are correct")
        print("\n")
        return True

if __name__ == "__main__":
    success = check_oauth_config()
    sys.exit(0 if success else 1)
