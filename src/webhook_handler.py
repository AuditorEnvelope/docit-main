"""
GitHub Webhook Handler
Automatically generates documentation when code is pushed
"""

import os
import hmac
import hashlib
import json
from fastapi import Request, HTTPException
from doc_generation_endpoint import generate_repository_documentation

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

def verify_github_signature(request_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not GITHUB_WEBHOOK_SECRET:
        print("⚠️  GITHUB_WEBHOOK_SECRET not set - skipping signature verification")
        return True
    
    expected_signature = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

async def handle_push_webhook(payload: dict, github_token: str):
    """Handle GitHub push webhook"""
    repo_name = payload.get("repository", {}).get("full_name")
    
    if not repo_name:
        print("❌ No repository name in webhook")
        return
    
    # Skip if it's a DocAI bot commit
    commits = payload.get("commits", [])
    if commits:
        last_commit = commits[-1]
        author = last_commit.get("author", {}).get("name", "")
        if author == "docai-bot":
            print(f"⏭️  Skipping DocAI's own commit")
            return
    
    print(f"🚀 Webhook triggered for {repo_name}")
    
    try:
        # Generate documentation
        docs = await generate_repository_documentation(repo_name, github_token)
        print(f"✅ Documentation auto-generated for {repo_name}")
    except Exception as e:
        print(f"❌ Error in webhook: {str(e)}")
