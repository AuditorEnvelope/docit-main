#!/usr/bin/env python3
"""
GitBook Configuration Helper
This script helps ensure your GitBook is properly configured to sync with your docs.
"""

import os
from pathlib import Path

def create_gitbook_config():
    """Create GitBook configuration files"""
    
    # Create .gitbook.yaml for GitBook configuration
    gitbook_config = """# GitBook Configuration
root: docs/
structure:
  readme: README.md
  summary: SUMMARY.md
"""
    
    with open(".gitbook.yaml", "w") as f:
        f.write(gitbook_config)
    
    print("✅ Created .gitbook.yaml configuration")
    
    # Create docs/README.md if it doesn't exist
    docs_readme = """# Documentation

This documentation is generated automatically by DocAI from repository changes.

## Navigation

Use the sidebar to navigate individual pages:

- **Changes**: Recent changes and updates
- **API**: API documentation and endpoints  
- **Architecture**: System architecture and design
- **Guides**: Setup and migration guides

## Recent Updates

Check the Changes section for the latest updates to the codebase.

*This documentation is automatically maintained by DocAI.*
"""
    
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    readme_path = docs_dir / "README.md"
    if not readme_path.exists():
        with open(readme_path, "w") as f:
            f.write(docs_readme)
        print("✅ Created docs/README.md")
    
    # Create initial SUMMARY.md
    summary_content = """# Table of Contents

* [Home](README.md)

## Changes
*Recent changes and updates will appear here*

## API Documentation
* [API Reference](api.md)

## Architecture
* [System Architecture](architecture.md)

## Guides
* [Setup Guide](SETUP_GUIDE.md)
* [Migration Guide](migration-guide.md)
"""
    
    summary_path = docs_dir / "SUMMARY.md"
    if not summary_path.exists():
        with open(summary_path, "w") as f:
            f.write(summary_content)
        print("✅ Created docs/SUMMARY.md")
    
    print("\n🎉 GitBook configuration complete!")
    print("\n📋 Next steps:")
    print("1. Commit these files to your repository")
    print("2. In GitBook, go to Settings > Integrations > GitHub")
    print("3. Make sure the 'Root folder' is set to 'docs'")
    print("4. Ensure 'Branch' is set to 'main'")
    print("5. Click 'Sync' to update your GitBook")

def check_gitbook_sync():
    """Check if GitBook sync is working"""
    print("🔍 Checking GitBook sync configuration...")
    
    # Check if docs folder exists
    if not Path("docs").exists():
        print("❌ docs/ folder not found")
        return False
    
    # Check if SUMMARY.md exists
    if not Path("docs/SUMMARY.md").exists():
        print("❌ docs/SUMMARY.md not found")
        return False
    
    # Check if changes folder exists
    if not Path("docs/changes").exists():
        print("⚠️  docs/changes/ folder not found (will be created on first change)")
    
    print("✅ GitBook configuration looks good!")
    return True

if __name__ == "__main__":
    print("🔧 GitBook Configuration Helper")
    print("=" * 40)
    
    if check_gitbook_sync():
        print("\n🎉 Your GitBook should sync properly now!")
    else:
        print("\n🛠️  Let's fix the configuration...")
        create_gitbook_config()
