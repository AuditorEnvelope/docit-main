#!/usr/bin/env python3
"""
Pustak Integration Script
This script integrates DocAI with the Pustak documentation platform.
"""

import requests
import json
import os
from pathlib import Path
from typing import Dict, Any

class PustakIntegration:
    """Integration between DocAI and Pustak platform"""
    
    def __init__(self, pustak_url: str = None):
        self.pustak_url = pustak_url or os.getenv("PUSTAK_URL", "http://localhost:3000")
        self.api_url = f"{self.pustak_url}/api"
        
    def sync_documentation(self, repo_name: str, doc_type: str, content: str, metadata: Dict[str, Any] = None):
        """Sync documentation with Pustak platform"""
        
        payload = {
            "repoName": repo_name,
            "docType": doc_type,
            "content": content,
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/sync",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully synced {repo_name}/{doc_type} to Pustak")
                return True
            else:
                print(f"❌ Failed to sync {repo_name}/{doc_type}: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error syncing to Pustak: {e}")
            return False
    
    def notify_doc_generated(self, repo_name: str, doc_type: str, file_path: str, commit_sha: str):
        """Notify Pustak that new documentation has been generated"""
        
        # Read the generated documentation
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
        
        metadata = {
            "filePath": file_path,
            "commitSha": commit_sha,
            "generatedAt": str(Path(file_path).stat().st_mtime),
            "source": "DocAI"
        }
        
        return self.sync_documentation(repo_name, doc_type, content, metadata)

def update_smart_processor_with_pustak():
    """Update the smart processor to integrate with Pustak"""
    
    smart_processor_path = Path("smart_processor.py")
    
    if not smart_processor_path.exists():
        print("❌ smart_processor.py not found")
        return False
    
    # Read the current smart processor
    with open(smart_processor_path, 'r') as f:
        content = f.read()
    
    # Check if Pustak integration is already added
    if "PustakIntegration" in content:
        print("✅ Pustak integration already exists in smart_processor.py")
        return True
    
    # Add Pustak integration
    integration_code = '''
# Pustak Integration
from pustak_integration import PustakIntegration

def notify_pustak(repo_name: str, doc_type: str, file_path: str, commit_sha: str):
    """Notify Pustak platform of new documentation"""
    try:
        pustak = PustakIntegration()
        success = pustak.notify_doc_generated(repo_name, doc_type, file_path, commit_sha)
        if success:
            print(f"📚 Notified Pustak of {repo_name}/{doc_type}")
        else:
            print(f"⚠️  Failed to notify Pustak of {repo_name}/{docType}")
    except Exception as e:
        print(f"❌ Pustak notification error: {e}")
'''
    
    # Insert the integration code before the commit_and_push_changes function
    insertion_point = "def commit_and_push_changes(repo_dir, analysis, commit_sha, token, repo_full):"
    
    if insertion_point in content:
        # Split content and insert integration code
        parts = content.split(insertion_point)
        new_content = parts[0] + integration_code + "\n\n" + insertion_point + parts[1]
        
        # Write the updated content
        with open(smart_processor_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Added Pustak integration to smart_processor.py")
        
        # Now update the create_change_documentation function to call Pustak
        with open(smart_processor_path, 'r') as f:
            content = f.read()
        
        # Find the create_change_documentation function and add Pustak notification
        if 'print(f"📝 Created detailed change documentation: {change_file}")' in content:
            content = content.replace(
                'print(f"📝 Created detailed change documentation: {change_file}")',
                '''print(f"📝 Created detailed change documentation: {change_file}")
        
        # Notify Pustak
        notify_pustak(repo_full.split("/")[-1], analysis['type'], str(change_file), commit_sha)'''
            )
            
            with open(smart_processor_path, 'w') as f:
                f.write(content)
            
            print("✅ Added Pustak notification to change documentation")
        
        return True
    else:
        print("❌ Could not find insertion point in smart_processor.py")
        return False

def create_pustak_config():
    """Create Pustak configuration file"""
    
    config_content = '''# Pustak Configuration
# This file configures the integration between DocAI and Pustak

PUSTAK_URL = "http://localhost:3000"  # Change to your Pustak URL
PUSTAK_API_URL = "http://localhost:3000/api"

# Optional: Authentication token if required
# PUSTAK_API_TOKEN = "your-api-token"

# Sync settings
AUTO_SYNC_TO_PUSTAK = True
SYNC_TIMEOUT = 30  # seconds
'''
    
    with open("pustak_config.py", "w") as f:
        f.write(config_content)
    
    print("✅ Created pustak_config.py")

def main():
    """Main integration setup"""
    print("🚀 Setting up Pustak integration for DocAI")
    print("=" * 50)
    
    # Create Pustak integration file
    print("📁 Creating Pustak integration module...")
    
    # Create configuration
    create_pustak_config()
    
    # Update smart processor
    print("🔧 Updating smart_processor.py...")
    if update_smart_processor_with_pustak():
        print("✅ Integration setup complete!")
        
        print("\n📋 Next steps:")
        print("1. Update pustak_config.py with your Pustak URL")
        print("2. Deploy Pustak to Vercel or your preferred platform")
        print("3. Update PUSTAK_URL in your environment variables")
        print("4. Test the integration by pushing code changes")
        
        print("\n🎉 DocAI is now integrated with Pustak!")
        print("Your documentation will automatically sync to the Pustak platform.")
    else:
        print("❌ Integration setup failed")

if __name__ == "__main__":
    main()
