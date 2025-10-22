"""
Documentation Generation Endpoint
Handles on-demand documentation generation for repositories
Follows the same pattern as webhook-based generation - clones, generates, and pushes
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException

def run_cmd(cmd, cwd=None, capture_output=False):
    """Run shell command"""
    print(f"RUN: {cmd}")
    if capture_output:
        result = subprocess.run(cmd, shell=True, check=True, cwd=cwd, capture_output=True, text=True)
        return result.stdout
    else:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)

def clone_repo_via_token(repo_full_name, token, target_dir):
    """Clone repository using GitHub token"""
    url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    run_cmd(f"git clone {url} {target_dir}")

async def generate_repository_documentation(repo_name: str, github_token: str) -> dict:
    """
    Generate comprehensive documentation for a repository
    Clones repo, generates docs in docs/ folder, and pushes to GitHub
    
    Args:
        repo_name: Repository full name (owner/repo)
        github_token: GitHub access token
        
    Returns:
        Generated documentation dict
    """
    tmpdir = tempfile.mkdtemp(prefix="docai_gen_")
    
    try:
        print(f"🚀 Starting documentation generation for {repo_name}...")
        
        # Clone repository
        print(f"📥 Cloning repository {repo_name}...")
        clone_repo_via_token(repo_name, github_token, tmpdir)
        print(f"✅ Repository cloned")
        
        # Create docs directory
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir(exist_ok=True)
        print(f"📁 Created docs directory")
        
        # Generate documentation using LLM
        from llm_provider_v2 import get_rotator
        
        llm_rotator = get_rotator()
        
        # Read README if exists
        readme_path = Path(tmpdir) / "README.md"
        readme_content = readme_path.read_text() if readme_path.exists() else ""
        
        # Get repository structure
        try:
            tree_output = run_cmd(f"find {tmpdir} -type f -name '*.py' -o -name '*.js' -o -name '*.ts' | head -30", capture_output=True)
            tree_content = tree_output
        except:
            tree_content = ""
        
        # Generate SUMMARY.md
        summary_prompt = f"""Analyze this GitHub repository and create a comprehensive summary:

Repository: {repo_name}
README Content:
{readme_content[:2000]}

Repository Files:
{tree_content}

Generate a detailed summary covering:
1. Project purpose and goals
2. Key features
3. Technology stack
4. Getting started guide
5. Project structure overview

Format as markdown."""

        summary = llm_rotator.generate_with_rotation(summary_prompt)
        summary_file = docs_dir / "SUMMARY.md"
        summary_file.write_text(summary)
        print(f"✅ Generated SUMMARY.md ({len(summary)} chars)")
        
        # Generate ARCHITECTURE.md
        architecture_prompt = f"""Based on this repository, create architecture documentation:

Repository: {repo_name}
README: {readme_content[:1500]}
Files: {tree_content}

Generate detailed architecture documentation covering:
1. System architecture overview
2. Main components and modules
3. Data flow
4. Dependencies and relationships
5. Design patterns used

Format as markdown."""

        architecture = llm_rotator.generate_with_rotation(architecture_prompt)
        arch_file = docs_dir / "ARCHITECTURE.md"
        arch_file.write_text(architecture)
        print(f"✅ Generated ARCHITECTURE.md ({len(architecture)} chars)")
        
        # Generate API.md
        api_prompt = f"""Based on this repository, create API documentation:

Repository: {repo_name}
README: {readme_content[:1500]}
Files: {tree_content}

Generate API documentation covering:
1. Available endpoints/functions
2. Parameters and return types
3. Usage examples
4. Error handling
5. Authentication (if applicable)

Format as markdown."""

        api_docs = llm_rotator.generate_with_rotation(api_prompt)
        api_file = docs_dir / "API.md"
        api_file.write_text(api_docs)
        print(f"✅ Generated API.md ({len(api_docs)} chars)")
        
        # Commit and push changes
        print("\n" + "="*60)
        print("📤 Committing and pushing documentation to GitHub")
        print("="*60)
        
        # Configure git
        run_cmd("git config user.email 'docai@bots.local' && git config user.name 'docai-bot'", cwd=tmpdir)
        
        # Fetch latest
        run_cmd("git fetch origin", cwd=tmpdir)
        run_cmd("git reset --hard origin/main", cwd=tmpdir)
        
        # Add docs
        run_cmd("git add docs/ || true", cwd=tmpdir)
        
        # Check if there are changes
        status = run_cmd("git status --porcelain", cwd=tmpdir, capture_output=True).strip()
        if status:
            # Commit
            commit_msg = f"docs: Auto-generated documentation for {repo_name}"
            run_cmd(f"git commit -m '{commit_msg}'", cwd=tmpdir)
            
            # Push
            print("⬆️  Pushing to GitHub...")
            run_cmd(f"git push https://x-access-token:{github_token}@github.com/{repo_name}.git HEAD:main", cwd=tmpdir)
            print("✅ Documentation pushed to GitHub")
        else:
            print("ℹ️  No changes to commit")
        
        documentation = {
            "repo_name": repo_name,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "architecture": architecture,
            "api": api_docs,
            "status": "success",
            "message": f"Documentation generated and pushed to GitHub in docs/ folder"
        }
        
        print(f"\n✅ Documentation generation complete for {repo_name}")
        return documentation
        
    except Exception as e:
        print(f"❌ Error generating documentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate documentation: {str(e)}")
    finally:
        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)
