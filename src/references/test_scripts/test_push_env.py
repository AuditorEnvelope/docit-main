import os
import aiohttp
import asyncio
from pathlib import Path
from datetime import datetime

# Configuration
REPO_OWNER = "jai-mahakal-poc"
REPO_NAME = "pustak-docbook-jai-mahakal-poc"
APP_ID = "2229202"  # Your writer app ID
INSTALLATION_ID = "93180288"  # Installation ID for jai-mahakal-poc

def get_private_key_from_env() -> str:
    """Get private key from environment variables"""
    private_key = os.getenv("WRITER_PRIVATE_KEY")
    if not private_key:
        raise ValueError("WRITER_PRIVATE_KEY not found in environment variables")
    
    # Handle escaped newlines if present
    private_key = private_key.replace('\\n', '\n')
    return private_key

async def get_installation_token():
    """Get installation access token using JWT"""
    import jwt
    import time
    
    # Get private key from environment
    private_key = get_private_key_from_env()
    
    # Generate JWT
    payload = {
        'iat': int(time.time()) - 60,
        'exp': int(time.time()) + 600,
        'iss': APP_ID
    }
    jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
    
    # Get installation token
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    url = f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as resp:
            if resp.status == 201:
                data = await resp.json()
                return data["token"]
            else:
                error = await resp.text()
                raise Exception(f"Failed to get token: {resp.status} - {error}")

async def update_readme(token: str):
    """Update README.md with a small change"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/README.md"
    
    async with aiohttp.ClientSession() as session:
        # Get current README
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                error = await resp.text()
                print(f"❌ Failed to get README: {error}")
                return
            
            readme_data = await resp.json()
            current_content = readme_data["content"]
            current_sha = readme_data["sha"]
            
            # Decode base64 content
            import base64
            content = base64.b64decode(current_content).decode('utf-8')
            
            # Add a small change
            new_content = content.rstrip() + "\n\n<!-- Updated via env test at " + datetime.now().isoformat() + " -->\n"
            
            # Encode back to base64
            new_content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            
            # Update README
            update_data = {
                "message": "test: Update README via env test",
                "content": new_content_b64,
                "sha": current_sha
            }
            
            async with session.put(url, headers=headers, json=update_data) as update_resp:
                if update_resp.status == 200:
                    print("✅ Successfully updated README using env key!")
                    result = await update_resp.json()
                    print(f"Commit SHA: {result.get('commit', {}).get('sha')}")
                else:
                    error = await update_resp.text()
                    print(f"❌ Failed to update README: {error}")

async def main():
    try:
        print("🔑 Getting installation token using env key...")
        token = await get_installation_token()
        print("✅ Got installation token")
        
        print("\n📝 Updating README...")
        await update_readme(token)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())