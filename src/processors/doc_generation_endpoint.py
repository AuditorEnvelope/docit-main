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
    Generate comprehensive documentation for a repository with proper versioning
    Creates:
    - /docs/SUMMARY.md
    - /docs/architecture/v1.0-architecture.md
    - /docs/workflow/v1.0-workflow.md
    - /docs/api.md
    - /docs/changes/ folder
    - /README.md at root
    - /CHANGELOG.md at root
    
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
        
        # Create docs directory structure
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir(exist_ok=True)
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir(exist_ok=True)
        workflow_dir = docs_dir / "workflow"
        workflow_dir.mkdir(exist_ok=True)
        changes_dir = docs_dir / "changes"
        changes_dir.mkdir(exist_ok=True)
        print(f"📁 Created docs directory structure")
        
        # Generate documentation using LLM
        from utilities.llm_provider_v2 import get_rotator
        
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
        
        # Generate versioned ARCHITECTURE.md (v1.0)
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
        arch_file = arch_dir / "v1.0-architecture.md"
        arch_file.write_text(architecture)
        current_arch = arch_dir / "current.md"
        current_arch.write_text(architecture)
        print(f"✅ Generated v1.0-architecture.md ({len(architecture)} chars)")
        
        # Generate versioned WORKFLOW.md (v1.0)
        workflow_prompt = f"""Based on this repository, create workflow/process documentation:

Repository: {repo_name}
README: {readme_content[:1500]}
Files: {tree_content}

Generate workflow documentation covering:
1. Development workflow
2. Build and deployment process
3. Testing procedures
4. CI/CD pipeline
5. Release process

Format as markdown."""

        workflow = llm_rotator.generate_with_rotation(workflow_prompt)
        workflow_file = workflow_dir / "v1.0-workflow.md"
        workflow_file.write_text(workflow)
        current_workflow = workflow_dir / "current.md"
        current_workflow.write_text(workflow)
        print(f"✅ Generated v1.0-workflow.md ({len(workflow)} chars)")
        
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
        api_file = docs_dir / "api.md"
        api_file.write_text(api_docs)
        print(f"✅ Generated api.md ({len(api_docs)} chars)")
        
        # Create/update README.md at root
        root_readme = Path(tmpdir) / "README.md"
        root_readme.write_text(summary)
        print(f"✅ Updated README.md at root")
        
        # Create CHANGELOG.md at root
        changelog_content = f"""# Changelog

## [1.0.0] - {datetime.now().strftime('%Y-%m-%d')}

### Added
- Initial documentation generation
- Architecture documentation (v1.0)
- Workflow documentation (v1.0)
- API documentation
- Summary and README

### Documentation
- See `/docs` folder for complete documentation
- Architecture: `/docs/architecture/v1.0-architecture.md`
- Workflow: `/docs/workflow/v1.0-workflow.md`
- API: `/docs/api.md`
"""
        changelog_file = Path(tmpdir) / "CHANGELOG.md"
        changelog_file.write_text(changelog_content)
        print(f"✅ Created CHANGELOG.md at root")
        
        # Commit and push changes
        print("\n" + "="*60)
        print("📤 Committing and pushing documentation to GitHub")
        print("="*60)
        
        # Configure git
        run_cmd("git config user.email 'docai@bots.local' && git config user.name 'docai-bot'", cwd=tmpdir)
        
        # Fetch latest
        run_cmd("git fetch origin", cwd=tmpdir)
        
        # Get default branch name
        try:
            default_branch = run_cmd("git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'", cwd=tmpdir, capture_output=True).strip()
            if not default_branch:
                default_branch = "main"  # Fallback to main
        except:
            default_branch = "main"  # Fallback to main
        
        print(f"🌿 Using default branch: {default_branch}")
        run_cmd(f"git reset --hard origin/{default_branch}", cwd=tmpdir)
        
        # Add docs, README, and CHANGELOG
        run_cmd("git add docs/ README.md CHANGELOG.md || true", cwd=tmpdir)
        
        # Check if there are changes
        status = run_cmd("git status --porcelain", cwd=tmpdir, capture_output=True).strip()
        if status:
            # Commit
            commit_msg = f"docs: Auto-generated documentation v1.0 for {repo_name}"
            run_cmd(f"git commit -m '{commit_msg}'", cwd=tmpdir)
            
            # Push
            print("⬆️  Pushing to GitHub...")
            try:
                run_cmd(f"git push https://x-access-token:{github_token}@github.com/{repo_name}.git HEAD:{default_branch}", cwd=tmpdir)
                print("✅ Documentation pushed to GitHub")
                push_status = "pushed"
            except Exception as push_error:
                error_msg = str(push_error)
                if "403" in error_msg or "Permission denied" in error_msg:
                    print(f"⚠️  Permission denied: User doesn't have push access to {repo_name}")
                    print(f"   Docs generated locally but not pushed. Admin needs to push manually.")
                    push_status = "generated_not_pushed"
                else:
                    raise push_error
        else:
            print("ℹ️  No changes to commit")
            push_status = "no_changes"
        
        documentation = {
            "repo_name": repo_name,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "architecture": architecture,
            "workflow": workflow,
            "api": api_docs,
            "status": "success",
            "push_status": push_status,
            "message": f"Documentation v1.0 generated (push_status: {push_status})",
            "structure": {
                "docs": {
                    "SUMMARY.md": "Project summary",
                    "architecture": "v1.0-architecture.md + current.md",
                    "workflow": "v1.0-workflow.md + current.md",
                    "api.md": "API documentation",
                    "changes": "Changes folder"
                },
                "root": {
                    "README.md": "Updated with summary",
                    "CHANGELOG.md": "Created with v1.0 entry"
                }
            }
        }
        
        print(f"\n✅ Documentation generation complete for {repo_name} (push_status: {push_status})")
        return documentation
        
    except Exception as e:
        print(f"❌ Error generating documentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate documentation: {str(e)}")
    finally:
        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)
