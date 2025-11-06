# smart_processor.py - Enhanced smart documentation agent
import os, subprocess, tempfile, shutil, datetime, json
import asyncio
import time  # Added for retry delays
import re  # Added for regex pattern matching
from aiolimiter import AsyncLimiter
from webhooks.github_app import get_installation_token
from utilities.llm_provider_v2 import get_rotator
from utilities.github_dual_app_helper import get_github_dual_app_helper
from core.app_installation_service import AppInstallationService
from pathlib import Path
from processors.comprehensive_doc_generator import generate_comprehensive_documentation

# Rate limiters (global instances)
github_rate_limiter = AsyncLimiter(4000, 3600)  # 4000 requests per hour (safe margin)
llm_rate_limiter = AsyncLimiter(50, 60)  # 50 requests per minute (safe margin)


async def generate_hierarchical_docs(repo_dir, repo_full, commit_sha, changed_files):
    """
    Generate hierarchical documentation tree - DISABLED

    This function was causing excessive LLM calls and cache issues.
    The comprehensive documentation generation provides all the necessary documentation.
    """
    print("❌ Hierarchical documentation generation is disabled")
    return  # Completely disabled


def run_cmd(cmd, cwd=None, capture_output=False):
    print("RUN:", cmd)
    if capture_output:
        result = subprocess.run(cmd, shell=True, check=True, cwd=cwd, capture_output=True, text=True)
        return result.stdout
    else:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)

def clone_repo_via_token(repo_full_name, token, target_dir):
    url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    # Remove --depth 1 to get full history for commit checkout
    run_cmd(f"git clone {url} {target_dir}")

async def handle_push_event(payload, github_token=None, doc_persona="internal"):
    """Enhanced push event handler with smart analysis
    
    Args:
        payload: GitHub webhook payload
        github_token: GitHub token for authentication
        doc_persona: Documentation persona (internal|developer) - NEW!
    """
    # Use provided token or fall back to env var
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    
    repo = payload.get("repository", {})
    repo_full = repo.get("full_name")
    installation = payload.get("installation", {})
    installation_id = installation.get("id")
    
    # If no token provided but we have installation_id, try to get app token
    if not github_token and installation_id:
        try:
            dual_app = get_github_dual_app_helper()
            github_token = await dual_app.get_reader_token(installation_id)
            if github_token:
                print(f"✅ Using GitHub App installation token (Reader)")
        except Exception as e:
            print(f"⚠️  Failed to get app token: {e}")
            github_token = os.getenv("GITHUB_TOKEN")
    
    # Get changed files
    changed_files = set()
    removed_files = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        removed_files.update(commit.get("removed", []))

    if not changed_files:
        print("No changed files in push, skipping.")
        return

    print(f"📁 Changed files: {len(changed_files)} files")
    print(f"🗑️  Removed files: {len(removed_files)} files")

    # Skip DocAI's own commits
    commits = payload.get("commits", [])
    if commits:
        last_commit = commits[-1]
        author = last_commit.get("author", {}).get("name", "")
        if author == "docai-bot" or "docai@bots.local" in last_commit.get("author", {}).get("email", ""):
            print(f"⏭️  Skipping DocAI's own commit from {author}")
            return

    # Use provided token, or try app installation, or fallback to env
    token = github_token
    
    if not token:
        if installation_id:
            token = get_installation_token(installation_id)
            print(f"✨ Using GitHub App installation token")
        else:
            # Only use env token as last resort
            token = os.getenv("GITHUB_TOKEN")
            if token:
                print(f"⚠️  Using env GITHUB_TOKEN (no user token provided)")
    
    if not token:
        print("❌ No GitHub token available")
        return
    tmpdir = tempfile.mkdtemp(prefix="docai_smart_")
    
    try:
        clone_repo_via_token(repo_full, token, tmpdir)
        
        # Checkout the exact commit
        ref = payload.get("ref")
        after_sha = payload.get("after")
        if after_sha:
            try:
                run_cmd(f"git checkout --detach {after_sha}", cwd=tmpdir)
                print(f"✅ Checked out commit {after_sha[:8]}")
            except Exception as e:
                print(f"⚠️  Could not checkout commit {after_sha[:8]}: {e}")
                print("   Using current branch instead")
        
        # Smart analysis of the change
        analysis = smart_analyze_change(payload, tmpdir, changed_files, removed_files)
        
        if not analysis["is_significant"]:
            print(f"❌ Change not significant: {analysis['reason']}")
            return
        
        print(f"✅ Significant change detected: {analysis['title']}")
        
        # Generate comprehensive documentation (flat docs - backward compatible)
        generate_smart_documentation(tmpdir, analysis, after_sha, ref, doc_persona)
        
        # NEW: Generate hierarchical documentation tree (stored in database)
        # COMPLETELY REMOVED - causing too many LLM calls and cache issues
        # The comprehensive documentation generation is sufficient and works perfectly
        print("⏭️  Hierarchical documentation generation completely removed")
        
        # ⭐ NEW: Pass doc_persona to doc generator
        print(f"📚 Using doc_persona: {doc_persona}")
        
        # QUALITY VALIDATION: Check documentation quality before committing
        print("\n" + "="*60)
        print("🔍 RUNNING QUALITY VALIDATION")
        print("="*60)
        
        from processors.quality_integration import validate_documentation_quality
        quality_passed = await validate_documentation_quality(tmpdir, repo.get("name", "unknown"))
        
        if not quality_passed:
            print("\n⚠️  WARNING: Documentation quality below threshold (< 8.0/10)")
            print("   Proceeding with commit anyway (auto-regeneration coming soon)")
            print("   Check docs/QUALITY_REPORT.md for detailed feedback")
        
        # ⭐ V4: Push to docbook repo instead of source repo
        print(f"📚 V4 Mode - Publishing to docbook repo (staging branch)")

        dual_app = get_github_dual_app_helper()

        writer_installation_id = installation_id

        if dual_app.dual_app_mode and dual_app.writer_app_id:
            writer_installation_id = None
            org_id = payload.get("_org_id")
            if not org_id and repo_full and "/" in repo_full:
                org_id = repo_full.split("/", 1)[0]

            db_pool = payload.get("_db_pool")

            if org_id and db_pool:
                try:
                    service = AppInstallationService(db_pool)
                    writer_installation_id = await service.get_app_installation_id(
                        org_id,
                        int(dual_app.writer_app_id),
                    )
                    if writer_installation_id:
                        print(
                            f"✅ Resolved writer installation ID {writer_installation_id} for org {org_id}"
                        )
                except Exception as lookup_error:
                    print(f"⚠️  Could not resolve writer installation ID from DB: {lookup_error}")

            if not writer_installation_id:
                writer_installation_id = installation_id

        if not writer_installation_id:
            raise RuntimeError("Writer app installation ID missing for docbook publish")

        writer_token = await dual_app.get_writer_token(writer_installation_id)
        if not writer_token:
            raise RuntimeError("Writer token unavailable for docbook publish")

        print(f"✅ Using Writer token for docbook publish")

        await push_to_docbook_v4(
            tmpdir,
            repo,
            analysis,
            after_sha,
            writer_token,
            payload,
        )
    
    except Exception as e:
        print(f"❌ Error in handle_push_event: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up tmpdir AFTER publishing
        try:
            shutil.rmtree(tmpdir)
        except:
            pass

def smart_analyze_change(payload, repo_dir, changed_files, removed_files):
    """Comprehensive analysis of the entire change impact"""
    
    # Get git diff for context
    diff_context = get_git_diff_context(repo_dir, changed_files)
    
    # Get commit messages and context
    commits = payload.get("commits", [])
    commit_messages = [commit.get("message", "") for commit in commits]
    
    # Analyze file patterns to understand change type
    file_analysis = analyze_file_patterns(changed_files, removed_files)
    
    # Get codebase context for major changes
    codebase_context = ""
    if file_analysis["is_major_change"]:
        codebase_context = get_codebase_context(repo_dir, changed_files)
    
    # Create comprehensive analysis prompt
    analysis_prompt = f"""
You are DocAI, an expert code analysis AI. Analyze this code change comprehensively.

REPOSITORY CONTEXT:
- Repository: {payload.get("repository", {}).get("full_name", "unknown")}
- Branch: {payload.get("ref", "unknown")}
- Commit SHA: {payload.get("after", "unknown")}

COMMIT MESSAGES:
{chr(10).join(f"- {msg}" for msg in commit_messages)}

FILE CHANGES:
Changed files ({len(changed_files)}):
{chr(10).join(f"- {f}" for f in sorted(changed_files))}

Removed files ({len(removed_files)}):
{chr(10).join(f"- {f}" for f in sorted(removed_files))}

FILE PATTERN ANALYSIS:
{json.dumps(file_analysis, indent=2)}

GIT DIFF CONTEXT:
{diff_context}

CODEBASE CONTEXT (for major changes):
{codebase_context}

ANALYSIS REQUIREMENTS:
1. Determine the TYPE of change (feature, bug_fix, refactor, breaking_change, security, performance, etc.)
2. Assess SIGNIFICANCE (1-10 scale) - only document 7+ significant changes
3. Identify the MAIN PURPOSE and impact
4. Understand which parts of the system are affected
5. Determine what documentation needs updating

IMPORTANT: Respond with VALID JSON only. Do NOT use backslashes except for escaping quotes.
Use forward slashes (/) for paths. Keep strings simple and avoid special characters.

Respond in JSON format:
{{
    "type": "feature|bug_fix|refactor|breaking_change|security|performance|chore|docs",
    "significance": 8,
    "is_significant": true,
    "title": "Add OAuth2 Authentication System",
    "summary": "Implemented comprehensive OAuth2 authentication with JWT tokens, user management, and role-based access control",
    "impact_scope": ["authentication", "user_management", "api_security"],
    "affected_components": ["auth/", "api/middleware/", "database/schemas/"],
    "breaking_changes": false,
    "new_features": ["OAuth2 login", "JWT tokens", "Role-based access"],
    "technical_details": "Detailed technical implementation...",
    "documentation_needs": {{
        "update_readme": true,
        "create_changelog": true,
        "update_api_docs": true,
        "create_migration_guide": false
    }},
    "reason": "Major authentication feature affecting core system security"
}}
"""

    try:
        rotator = get_rotator()
        result = rotator.generate_with_rotation(analysis_prompt)
        
        if result:
            # Parse JSON response with sanitization
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                
                # Sanitize JSON: fix common escape issues
                # Replace invalid escape sequences
                json_str = json_str.replace('\\n', '\\\\n')  # Fix newlines
                json_str = json_str.replace('\\t', '\\\\t')  # Fix tabs
                json_str = json_str.replace('\\r', '\\\\r')  # Fix carriage returns
                
                # Remove any remaining single backslashes that aren't part of valid escapes
                # Valid escapes: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
                json_str = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_str)
                
                try:
                    analysis = json.loads(json_str)
                    return analysis
                except json.JSONDecodeError as json_err:
                    print(f"⚠️  JSON parsing failed: {json_err}")
                    print(f"   Attempting alternative parsing...")
                    
                    # Try to extract key fields manually as fallback
                    try:
                        # Use regex to extract key fields
                        type_match = re.search(r'"type"\s*:\s*"([^"]+)"', result)
                        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', result)
                        significance_match = re.search(r'"significance"\s*:\s*(\d+)', result)
                        
                        if type_match and title_match:
                            print(f"   ✅ Extracted key fields manually")
                            return {
                                "type": type_match.group(1),
                                "title": title_match.group(1),
                                "significance": int(significance_match.group(1)) if significance_match else 7,
                                "is_significant": True,
                                "summary": title_match.group(1),
                                "impact_scope": ["general"],
                                "affected_components": list(changed_files)[:5],
                                "breaking_changes": False,
                                "new_features": [],
                                "technical_details": f"Files changed: {', '.join(sorted(changed_files)[:5])}",
                                "documentation_needs": {
                                    "update_readme": True,
                                    "create_changelog": True,
                                    "update_api_docs": True,
                                    "create_migration_guide": False
                                },
                                "reason": "Partial analysis from malformed JSON"
                            }
                    except Exception as extract_err:
                        print(f"   ❌ Manual extraction failed: {extract_err}")
                        raise json_err
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        print(f"   LLM response preview: {result[:200] if 'result' in locals() else 'No response'}")
    
    # Fallback analysis
    return {
        "type": "unknown",
        "significance": 5,
        "is_significant": len(changed_files) > 10,  # Heuristic: many files = significant
        "title": f"Code changes in {len(changed_files)} files",
        "summary": f"Modified {len(changed_files)} files, removed {len(removed_files)} files",
        "impact_scope": ["general"],
        "affected_components": list(changed_files)[:5],
        "breaking_changes": False,
        "new_features": [],
        "technical_details": f"Files changed: {', '.join(sorted(changed_files))}",
        "documentation_needs": {
            "update_readme": False,
            "create_changelog": True,
            "update_api_docs": False,
            "create_migration_guide": False
        },
        "reason": "Fallback analysis due to LLM failure"
    }

def analyze_file_patterns(changed_files, removed_files):
    """Analyze file patterns to understand change type"""
    patterns = {
        "auth": ["auth", "login", "jwt", "oauth", "session", "user"],
        "api": ["api", "endpoint", "route", "controller"],
        "database": ["migration", "schema", "model", "db"],
        "frontend": ["component", "page", "view", "ui", "css", "jsx"],
        "config": ["config", "env", "docker", "yaml", "json"],
        "test": ["test", "spec", "mock"],
        "docs": ["readme", "docs", "changelog", "guide"]
    }
    
    detected_patterns = []
    for pattern, keywords in patterns.items():
        for file in changed_files:
            if any(keyword in file.lower() for keyword in keywords):
                detected_patterns.append(pattern)
                break
    
    # Determine if it's a major change
    major_indicators = [
        len(changed_files) > 20,
        "auth" in detected_patterns,
        "database" in detected_patterns,
        any("config" in f for f in changed_files),
        len(removed_files) > 5
    ]
    
    return {
        "detected_patterns": list(set(detected_patterns)),
        "is_major_change": any(major_indicators),
        "file_count": len(changed_files),
        "removed_count": len(removed_files)
    }

def get_git_diff_context(repo_dir, changed_files):
    """Get git diff for changed files"""
    try:
        # Get diff for changed files
        files_str = " ".join(f'"{f}"' for f in changed_files if not f.startswith("docs/"))
        if files_str:
            result = subprocess.run(
                f"git diff HEAD~1 -- {files_str}",
                shell=True, cwd=repo_dir, capture_output=True, text=True
            )
            return result.stdout[:5000]  # Limit size
    except Exception as e:
        print(f"Warning: Could not get git diff: {e}")
    return ""

def get_codebase_context(repo_dir, changed_files):
    """Get broader codebase context for major changes"""
    try:
        # Get project structure
        structure = subprocess.run(
            "find . -type f -name '*.py' -o -name '*.js' -o -name '*.ts' | head -20",
            shell=True, cwd=repo_dir, capture_output=True, text=True
        ).stdout
        
        # Get package.json or requirements.txt for context
        package_info = ""
        for file in ["package.json", "requirements.txt", "pyproject.toml"]:
            if os.path.exists(os.path.join(repo_dir, file)):
                with open(os.path.join(repo_dir, file), 'r') as f:
                    package_info += f"\n{file}:\n{f.read()[:1000]}\n"
        
        return f"Project structure:\n{structure}\n\nPackage info:\n{package_info}"
    except Exception as e:
        print(f"Warning: Could not get codebase context: {e}")
    return ""

def generate_smart_documentation(repo_dir, analysis, commit_sha, ref, doc_persona="internal"):
    """Generate comprehensive documentation based on analysis
    
    Args:
        doc_persona: Documentation persona (internal|developer)
    """
    
    # Create docs directory structure - everything goes in docs/
    docs_dir = Path(repo_dir) / "docs"
    changes_dir = docs_dir / "changes"  # Move changes inside docs
    docs_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)
    
    # NEW: Check documentation quality and generate comprehensive docs if needed
    print("🔍 Checking documentation quality...")
    changed_files = get_changed_files_from_analysis(analysis)
    generate_comprehensive_documentation(repo_dir, analysis, changed_files, doc_persona)
    
    # 1. Create detailed change documentation
    create_change_documentation(changes_dir, analysis, commit_sha, ref)
    
    # 2. Update main README if needed
    if analysis["documentation_needs"]["update_readme"]:
        update_main_readme(repo_dir, analysis)
    
    # 3. Update changelog
    if analysis["documentation_needs"]["create_changelog"]:
        update_changelog(repo_dir, analysis, commit_sha)
    
    # 4. Create API documentation if needed
    if analysis["documentation_needs"]["update_api_docs"]:
        create_api_documentation(docs_dir, analysis)
    
    # 5. Create migration guide for breaking changes
    if analysis["documentation_needs"]["create_migration_guide"]:
        create_migration_guide(docs_dir, analysis)
    
    # 6. Update SUMMARY.md for GitBook navigation
    update_summary_md(docs_dir, analysis, commit_sha)


def get_changed_files_from_analysis(analysis):
    """Extract changed files list from analysis"""
    return analysis.get("affected_components", [])

def create_change_documentation(changes_dir, analysis, commit_sha, ref):
    """Create detailed change documentation"""
    
    # Generate comprehensive change description
    change_prompt = f"""
Create comprehensive documentation for this code change:

CHANGE ANALYSIS:
{json.dumps(analysis, indent=2)}

Create a detailed markdown document that includes:
1. **Overview**: Clear summary of what changed and why
2. **Impact**: What parts of the system are affected
3. **New Features**: What new functionality was added
4. **Breaking Changes**: Any breaking changes and migration steps
5. **Technical Details**: Implementation specifics
6. **Usage Examples**: How to use new features
7. **Testing**: How to test the changes
8. **Migration Guide**: If applicable, steps to migrate

Make it professional, detailed, and useful for developers.
"""

    try:
        rotator = get_rotator()
        detailed_doc = rotator.generate_with_rotation(change_prompt)
        
        if detailed_doc:
            # Save detailed documentation
            change_file = changes_dir / f"{commit_sha}-{analysis['type']}.md"
            with open(change_file, "w", encoding="utf-8") as f:
                f.write(f"# {analysis['title']}\n\n")
                f.write(f"**Type:** {analysis['type']}  \n")
                f.write(f"**Significance:** {analysis['significance']}/10  \n")
                f.write(f"**Date:** {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
                f.write(f"**Commit:** {commit_sha}  \n")
                f.write(f"**Branch:** {ref}  \n\n")
                f.write(detailed_doc)
            
            print(f"📝 Created detailed change documentation: {change_file}")
        else:
            # Fallback documentation
            create_fallback_change_doc(changes_dir, analysis, commit_sha, ref)
            
    except Exception as e:
        print(f"❌ Failed to create detailed documentation: {e}")
        create_fallback_change_doc(changes_dir, analysis, commit_sha, ref)

def create_fallback_change_doc(changes_dir, analysis, commit_sha, ref):
    """Create fallback change documentation"""
    change_file = changes_dir / f"{commit_sha}-{analysis['type']}.md"
    with open(change_file, "w", encoding="utf-8") as f:
        f.write(f"# {analysis['title']}\n\n")
        f.write(f"**Type:** {analysis['type']}  \n")
        f.write(f"**Significance:** {analysis['significance']}/10  \n")
        f.write(f"**Date:** {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
        f.write(f"**Commit:** {commit_sha}  \n")
        f.write(f"**Branch:** {ref}  \n\n")
        f.write(f"## Summary\n{analysis['summary']}\n\n")
        f.write(f"## Impact Scope\n{', '.join(analysis['impact_scope'])}\n\n")
        f.write(f"## Affected Components\n{', '.join(analysis['affected_components'])}\n\n")
        f.write(f"## Technical Details\n{analysis['technical_details']}\n")

def update_main_readme(repo_dir, analysis):
    """Update main README with new features"""
    readme_path = Path(repo_dir) / "README.md"
    
    if not readme_path.exists():
        return
    
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add new features section if it's a major feature
        if analysis["type"] == "feature" and analysis["significance"] >= 8:
            new_section = f"""
## 🆕 Recent Updates

### {analysis['title']}
{analysis['summary']}

**New Features:**
{chr(10).join(f"- {feature}" for feature in analysis.get('new_features', []))}

*Added on {datetime.datetime.utcnow().strftime('%Y-%m-%d')}*
"""
            
            # Insert after the main title/description
            if "# " in content:
                lines = content.split('\n')
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.startswith("# ") and i > 0:
                        insert_index = i + 1
                        break
                lines.insert(insert_index, new_section)
                content = '\n'.join(lines)
            
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            print("📝 Updated main README with new features")
            
    except Exception as e:
        print(f"❌ Failed to update README: {e}")

def update_changelog(repo_dir, analysis, commit_sha):
    """Update CHANGELOG.md"""
    changelog_path = Path(repo_dir) / "CHANGELOG.md"
    
    # Create changelog if it doesn't exist
    if not changelog_path.exists():
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n")
    
    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add new entry
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        entry = f"""
## [{today}] - {analysis['title']}

### {analysis['type'].title()}
- {analysis['summary']}

### Details
- **Significance:** {analysis['significance']}/10
- **Commit:** {commit_sha}
- **Impact:** {', '.join(analysis['impact_scope'])}

"""
        
        # Insert after the header
        lines = content.split('\n')
        insert_index = 2  # After "# Changelog" and empty line
        lines.insert(insert_index, entry)
        
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        print("📝 Updated CHANGELOG.md")
        
    except Exception as e:
        print(f"❌ Failed to update CHANGELOG: {e}")

def create_api_documentation(docs_dir, analysis):
    """Create API documentation for new features"""
    if analysis["type"] not in ["feature", "api"]:
        return
    
    api_doc_path = docs_dir / "api.md"
    
    try:
        api_prompt = f"""
Create API documentation for this change:

{json.dumps(analysis, indent=2)}

Focus on:
1. New API endpoints
2. Request/response formats
3. Authentication requirements
4. Usage examples
5. Error handling

Create comprehensive API documentation.
"""
        
        rotator = get_rotator()
        api_doc = rotator.generate_with_rotation(api_prompt)
        
        if api_doc:
            with open(api_doc_path, "w", encoding="utf-8") as f:
                f.write(f"# API Documentation\n\n")
                f.write(f"*Updated: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}*\n\n")
                f.write(api_doc)
            
            print("📝 Created API documentation")
            
    except Exception as e:
        print(f"❌ Failed to create API documentation: {e}")

def create_migration_guide(docs_dir, analysis):
    """Create migration guide for breaking changes"""
    if not analysis.get("breaking_changes", False):
        return
    
    migration_path = docs_dir / "migration-guide.md"
    
    try:
        migration_prompt = f"""
Create a migration guide for this breaking change:

{json.dumps(analysis, indent=2)}

Include:
1. What changed and why
2. Step-by-step migration instructions
3. Code examples (before/after)
4. Common issues and solutions
5. Rollback instructions

Create a comprehensive migration guide.
"""
        
        rotator = get_rotator()
        migration_doc = rotator.generate_with_rotation(migration_prompt)
        
        if migration_doc:
            with open(migration_path, "w", encoding="utf-8") as f:
                f.write(f"# Migration Guide\n\n")
                f.write(f"*Updated: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}*\n\n")
                f.write(migration_doc)
            
            print("📝 Created migration guide")
            
    except Exception as e:
        print(f"❌ Failed to create migration guide: {e}")

def update_summary_md(docs_dir, analysis, commit_sha):
    """Update SUMMARY.md for GitBook navigation"""
    summary_path = docs_dir / "SUMMARY.md"
    
    try:
        # Read existing SUMMARY.md or create new one
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "# Table of Contents\n\n"
        
        # Add new change entry if it's significant
        if analysis["significance"] >= 7:
            change_entry = f"* [{analysis['title']}](changes/{commit_sha}-{analysis['type']}.md)\n"
            
            # Find the Changes section or create it
            if "## Changes" in content:
                # Insert after the Changes header
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == "## Changes":
                        lines.insert(i + 1, change_entry)
                        break
                content = '\n'.join(lines)
            else:
                # Add Changes section
                content += f"\n## Changes\n\n{change_entry}\n"
        
        # Write updated SUMMARY.md
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print("📝 Updated SUMMARY.md for GitBook navigation")
        
    except Exception as e:
        print(f"❌ Failed to update SUMMARY.md: {e}")

def commit_and_push_changes(repo_dir, analysis, commit_sha, token, repo_full):
    """Commit and push all documentation changes with conflict handling"""

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # Configure git
            run_cmd("git config user.email 'docai@bots.local' && git config user.name 'docai-bot'", cwd=repo_dir)

            # Fetch latest changes from remote
            print("🔄 Fetching latest changes from remote...")
            run_cmd("git fetch origin", cwd=repo_dir)

            # Get default branch name
            try:
                default_branch = run_cmd("git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'", cwd=repo_dir, capture_output=True).strip()
                if not default_branch:
                    default_branch = "main"  # Fallback to main
            except:
                default_branch = "main"  # Fallback to main
            
            print(f"🌿 Using default branch: {default_branch}")
            run_cmd(f"git reset --hard origin/{default_branch}", cwd=repo_dir)

            # Add all documentation files (changes is now inside docs/)
            run_cmd("git add docs/ README.md CHANGELOG.md || true", cwd=repo_dir)

            # Check if there are changes to commit
            status = run_cmd("git status --porcelain", cwd=repo_dir, capture_output=True).strip()
            if not status:
                print("ℹ️  No changes to commit")
                return

            # Create commit message
            commit_msg = f"docs: {analysis['type']} - {analysis['title']} [sha:{commit_sha}]"

            # Commit
            run_cmd(f"git commit -m '{commit_msg}' || echo 'no changes'", cwd=repo_dir)

            # Push with force if needed (for non-fast-forward updates)
            print("⬆️  Pushing changes to remote...")
            try:
                run_cmd(f"git push https://x-access-token:{token}@github.com/{repo_full}.git HEAD:{default_branch}", cwd=repo_dir)
                print("✅ Documentation changes committed and pushed")
                return

            except Exception as push_error:
                if "rejected" in str(push_error).lower() and attempt < max_retries - 1:
                    print(f"⚠️  Push rejected, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise push_error

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                print(f"   Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"❌ Failed to commit/push changes after {max_retries} attempts: {e}")
                print("   Continuing without pushing (docs saved locally)")
                return

    print("❌ All retry attempts exhausted")
    return

# Backward compatibility
def has_already_processed_push(repo_dir, sha, changed_files):
    """Check if push already processed"""
    try:
        run_cmd("git log -n 20 --pretty=format:%s > .gitlog.tmp", cwd=repo_dir)
        with open(Path(repo_dir)/".gitlog.tmp", "r", encoding="utf-8", errors="ignore") as fh:
            subjects = fh.read()
        return f"[sha:{sha}]" in subjects
    except Exception as e:
        print(f"Warning: could not check if push already processed: {e}")
    return False

# ============================================================================
# V4: PUSH TO DOCBOOK REPO (NEW!)
# ============================================================================

async def push_to_docbook_v4(tmpdir, repo, analysis, commit_sha, token, payload):
    """
    V4 Flow: Auto-publish generated docs to docbook repo (staging branch)
    Called from handle_push_event BEFORE tmpdir is deleted
    """
    try:
        from services.docbook_publisher import DocbookPublisher
        from pathlib import Path
        
        # Get user_id and org_id from payload
        user_id = payload.get('_user_id')
        org_id = payload.get('_org_id')
        
        if not user_id or not org_id:
            print(f"⚠️  No user_id/org_id in payload, skipping docbook publish")
            return
        
        repo_full = repo.get("full_name")
        if '/' not in repo_full:
            print(f"❌ Invalid repo name: {repo_full}")
            return
        
        org_id_from_repo, source_repo = repo_full.split('/', 1)
        
        # Check if docs exist
        docs_dir = Path(tmpdir) / "docs"
        if not docs_dir.exists():
            print(f"⚠️  No docs directory found, skipping docbook publish")
            return
        
        # Get database pool from payload (passed by event_consumer)
        db_pool = payload.get('_db_pool')
        if not db_pool:
            print(f"⚠️  No database pool in payload, skipping docbook publish")
            print(f"   (This is normal for webhook mode - use event_consumer for auto-publish)")
            return

        # Get writer token using dual app helper
        try:
            print("🔑 Getting writer token using dual app helper...")
            dual_app = get_github_dual_app_helper()
            if not dual_app:
                print("❌ Failed to initialize GitHubDualAppHelper")
                return
            
            # Get installation ID for writer app
            publisher = DocbookPublisher(db_pool)
            installation_id = await publisher.get_docbook_installation_id(org_id)
            if not installation_id:
                print("❌ Failed to get installation ID for writer app")
                return
                
            # Get writer token with installation ID
            try:
                writer_token = await dual_app.get_writer_token(installation_id)
                if not writer_token:
                    print("❌ Failed to get writer token: No token returned from dual app helper")
                    return False
                    
                print("✅ Successfully obtained writer token")
                
                # Publish to docbook with the obtained token
                print(f"📚 AUTO-PUBLISHING to docbook/staging...")
                # Extract user_id and org_id from the payload
                user_id = payload.get('_user_id', '')
                org_id = payload.get('_org_id', '')
                result = await publisher.publish_to_docbook(
                    user_id=user_id,
                    org_id=org_id,
                    source_repo_name=repo_full.split('/')[-1],  # Get just the repo name
                    docs_dir=Path(str(docs_dir)),
                    writer_token=writer_token,
                    commit_message=f"docs: Auto-generated documentation for {commit_sha}"
                )
                
                if result:
                    print("✅ Successfully published to docbook")
                    return True
                else:
                    print("❌ Failed to publish to docbook")
                    return False
                
            except Exception as e:
                print(f"❌ Error in docbook publishing: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            print(f"❌ Failed to get writer token: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"⚠️  Auto-publish error: {e}")
        import traceback
        traceback.print_exc()
        return False
