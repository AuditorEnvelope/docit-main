"""
Change Documentation Functions (ported from old codebase)
Handles change documentation, changelog, README updates, and migration guides
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.services.llm.rotator import get_rotator


def create_change_documentation(
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
        rotator = get_rotator()
        detailed_doc = rotator.generate_with_rotation(change_prompt)
        
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
    with open(change_file, "w", encoding="utf-8") as f:
        f.write(f"# {analysis['title']}\n\n")
        f.write(f"**Type:** {analysis['type']}  \n")
        f.write(f"**Significance:** {analysis['significance']}/10  \n")
        f.write(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
        f.write(f"**Commit:** {commit_sha}  \n")
        f.write(f"**Branch:** {ref}  \n\n")
        f.write(f"## Summary\n{analysis['summary']}\n\n")
        f.write(f"## Impact Scope\n{', '.join(analysis.get('impact_scope', []))}\n\n")
        f.write(f"## Affected Components\n{', '.join(analysis.get('affected_components', []))}\n\n")
        f.write(f"## Technical Details\n{analysis.get('technical_details', 'N/A')}\n")


def update_main_readme(repo_dir: Path, analysis: Dict[str, Any]) -> None:
    """Update main README with new features (like old codebase)"""
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

*Added on {datetime.utcnow().strftime('%Y-%m-%d')}*
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


def update_changelog(repo_dir: Path, analysis: Dict[str, Any], commit_sha: str) -> None:
    """Update CHANGELOG.md (like old codebase)"""
    changelog_path = Path(repo_dir) / "CHANGELOG.md"
    
    # Create changelog if it doesn't exist
    if not changelog_path.exists():
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n")
    
    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add new entry
        today = datetime.utcnow().strftime('%Y-%m-%d')
        entry = f"""
## [{today}] - {analysis['title']}

### {analysis['type'].title()}
- {analysis['summary']}

### Details
- **Significance:** {analysis['significance']}/10
- **Commit:** {commit_sha}
- **Impact:** {', '.join(analysis.get('impact_scope', []))}

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


def create_migration_guide(docs_dir: Path, analysis: Dict[str, Any]) -> None:
    """Create migration guide for breaking changes (like old codebase)"""
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
                f.write(f"*Updated: {datetime.utcnow().strftime('%Y-%m-%d')}*\n\n")
                f.write(migration_doc)
            
            print("📝 Created migration guide")
            
    except Exception as e:
        print(f"❌ Failed to create migration guide: {e}")


def update_summary_md(docs_dir: Path, analysis: Dict[str, Any], commit_sha: str) -> None:
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

