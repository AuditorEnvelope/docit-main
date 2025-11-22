"""
Change Documentation Functions (ported from old codebase)
Handles change documentation, changelog, README updates, and migration guides
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.services.llm.rotator import get_rotator


async def create_change_documentation(
    changes_dir: Path,
    analysis: Dict[str, Any],
    commit_sha: str,
    ref: str
) -> None:
    """Create detailed change documentation (like old codebase)"""
    
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
        rotator = await get_rotator()
        detailed_doc = await rotator.generate_with_rotation(change_prompt)
        
        if detailed_doc:
            # Save detailed documentation
            change_file = changes_dir / f"{commit_sha}-{analysis['type']}.md"
            with open(change_file, "w", encoding="utf-8") as f:
                f.write(f"# {analysis['title']}\n\n")
                f.write(f"**Type:** {analysis['type']}  \n")
                f.write(f"**Significance:** {analysis['significance']}/10  \n")
                f.write(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
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


def create_fallback_change_doc(
    changes_dir: Path,
    analysis: Dict[str, Any],
    commit_sha: str,
    ref: str
) -> None:
    """Create fallback change documentation (like old codebase)"""
    change_file = changes_dir / f"{commit_sha}-{analysis['type']}.md"
    
    try:
        with open(change_file, "w", encoding="utf-8") as f:
            f.write(f"# {analysis.get('title', 'Untitled Change')}\n\n")
            f.write(f"**Type:** {analysis.get('type', 'unknown')}  \n")
            f.write(f"**Significance:** {analysis.get('significance', 0)}/10  \n")
            f.write(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
            f.write(f"**Commit:** {commit_sha}  \n")
            f.write(f"**Branch:** {ref}  \n\n")
            f.write(f"## Summary\n{analysis.get('summary', 'No summary available')}\n\n")
            
            impact_scope = analysis.get('impact_scope', [])
            if impact_scope:
                f.write(f"## Impact Scope\n{', '.join(impact_scope)}\n\n")
            
            affected_components = analysis.get('affected_components', [])
            if affected_components:
                f.write(f"## Affected Components\n{', '.join(affected_components)}\n\n")
            
            f.write(f"## Technical Details\n{analysis.get('technical_details', 'N/A')}\n")
        
        print(f"📝 Created fallback change documentation: {change_file}")
        
    except Exception as e:
        print(f"❌ Failed to create fallback documentation: {e}")


async def update_main_readme(repo_dir: Path, analysis: Dict[str, Any]) -> None:
    """Update main README with new features (like old codebase)"""
    readme_path = repo_dir / "README.md"
    
    if not readme_path.exists():
        print("ℹ️ README.md not found, skipping update")
        return
    
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add new features section if it's a major feature
        if analysis.get("type") == "feature" and analysis.get("significance", 0) >= 8:
            new_features = analysis.get('new_features', [])
            if not new_features:
                print("ℹ️ No new features to add to README")
                return
            
            new_section = f"""
## 🆕 Recent Updates

### {analysis.get('title', 'Untitled Update')}
{analysis.get('summary', 'No summary available')}

**New Features:**
{chr(10).join(f"- {feature}" for feature in new_features)}

*Added on {datetime.utcnow().strftime('%Y-%m-%d')}*

---

"""
            
            # Insert after the first header and its description
            lines = content.split('\n')
            insert_index = 0
            
            # Find the end of the main title section
            found_title = False
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    found_title = True
                elif found_title and (line.startswith("## ") or (i > 0 and lines[i-1].strip() == "" and line.strip() != "")):
                    insert_index = i
                    break
            
            # If no good insertion point found, insert after first few lines
            if insert_index == 0:
                insert_index = min(3, len(lines))
            
            lines.insert(insert_index, new_section)
            content = '\n'.join(lines)
            
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            print("📝 Updated main README with new features")
        else:
            print(f"ℹ️ Change significance ({analysis.get('significance', 0)}) or type ({analysis.get('type')}) doesn't warrant README update")
            
    except Exception as e:
        print(f"❌ Failed to update README: {e}")


async def update_changelog(repo_dir: Path, analysis: Dict[str, Any], commit_sha: str) -> None:
    """Update CHANGELOG.md (like old codebase)"""
    changelog_path = repo_dir / "CHANGELOG.md"
    
    # Create changelog if it doesn't exist
    if not changelog_path.exists():
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\n")
            f.write("All notable changes to this project will be documented in this file.\n\n")
    
    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add new entry
        today = datetime.utcnow().strftime('%Y-%m-%d')
        change_type = analysis.get('type', 'unknown').title()
        
        entry = f"""## [{today}] - {analysis.get('title', 'Untitled Change')}

### {change_type}
- {analysis.get('summary', 'No summary available')}

### Details
- **Significance:** {analysis.get('significance', 0)}/10
- **Commit:** {commit_sha}
- **Impact:** {', '.join(analysis.get('impact_scope', ['N/A']))}

"""
        
        # Insert after the header section
        lines = content.split('\n')
        insert_index = 0
        
        # Find the first line after the main header and description
        for i, line in enumerate(lines):
            if i > 0 and (line.startswith("## ") or (lines[i-1].strip() == "" and i > 2)):
                insert_index = i
                break
        
        # If no good insertion point found, insert after header (line 3)
        if insert_index == 0:
            insert_index = min(3, len(lines))
        
        lines.insert(insert_index, entry)
        
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        print("📝 Updated CHANGELOG.md")
        
    except Exception as e:
        print(f"❌ Failed to update CHANGELOG: {e}")


async def create_migration_guide(docs_dir: Path, analysis: Dict[str, Any]) -> None:
    """Create migration guide for breaking changes (like old codebase)"""
    if not analysis.get("breaking_changes", False):
        print("ℹ️ No breaking changes, skipping migration guide")
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

Create a comprehensive migration guide in markdown format.
"""
        
        rotator = await get_rotator()
        migration_doc = await rotator.generate_with_rotation(migration_prompt)
        
        if migration_doc:
            with open(migration_path, "w", encoding="utf-8") as f:
                f.write(f"# Migration Guide\n\n")
                f.write(f"*Updated: {datetime.utcnow().strftime('%Y-%m-%d')}*\n\n")
                f.write(migration_doc)
            
            print(f"📝 Created migration guide: {migration_path}")
        else:
            # Create fallback migration guide
            with open(migration_path, "w", encoding="utf-8") as f:
                f.write(f"# Migration Guide\n\n")
                f.write(f"*Updated: {datetime.utcnow().strftime('%Y-%m-%d')}*\n\n")
                f.write(f"## Breaking Change: {analysis.get('title', 'Untitled')}\n\n")
                f.write(f"{analysis.get('summary', 'No summary available')}\n\n")
                f.write(f"### Affected Components\n")
                for component in analysis.get('affected_components', []):
                    f.write(f"- {component}\n")
                f.write(f"\n### Migration Steps\n")
                f.write(f"Please review the changes and update your code accordingly.\n")
            
            print(f"📝 Created fallback migration guide: {migration_path}")
            
    except Exception as e:
        print(f"❌ Failed to create migration guide: {e}")


async def update_summary_md(docs_dir: Path, analysis: Dict[str, Any], commit_sha: str) -> None:
    """Update SUMMARY.md for GitBook navigation (like old codebase)"""
    summary_path = docs_dir / "SUMMARY.md"
    
    try:
        # Read existing SUMMARY.md or create new one
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "# Table of Contents\n\n"
        
        # Add new change entry if it's significant
        if analysis.get("significance", 0) >= 7:
            change_type = analysis.get('type', 'unknown')
            change_title = analysis.get('title', 'Untitled Change')
            change_entry = f"* [{change_title}](changes/{commit_sha}-{change_type}.md)\n"
            
            # Find the Changes section or create it
            if "## Changes" in content:
                # Insert after the Changes header
                lines = content.split('\n')
                inserted = False
                for i, line in enumerate(lines):
                    if line.strip() == "## Changes":
                        # Check if this entry already exists
                        if change_entry.strip() not in content:
                            lines.insert(i + 1, change_entry)
                            inserted = True
                        break
                
                if inserted:
                    content = '\n'.join(lines)
                    print("📝 Added change to existing Changes section in SUMMARY.md")
                else:
                    print("ℹ️ Change entry already exists or couldn't insert")
            else:
                # Add Changes section at the end
                if not content.endswith('\n\n'):
                    content += '\n\n'
                content += f"## Changes\n\n{change_entry}"
                print("📝 Created new Changes section in SUMMARY.md")
        else:
            print(f"ℹ️ Change significance ({analysis.get('significance', 0)}) doesn't warrant SUMMARY.md update")
            return
        
        # Write updated SUMMARY.md
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print("📝 Updated SUMMARY.md for GitBook navigation")
        
    except Exception as e:
        print(f"❌ Failed to update SUMMARY.md: {e}")