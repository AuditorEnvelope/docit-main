#!/usr/bin/env python
"""
Simple test script for dual persona documentation structure.
This script verifies the directory structure for dual persona documentation.
"""

import os
import tempfile
from pathlib import Path
import shutil

def test_dual_persona_structure():
    """Test dual persona documentation structure."""
    print("\n" + "=" * 80)
    print("TESTING DUAL PERSONA DOCUMENTATION STRUCTURE")
    print("=" * 80)

    # Create a temporary directory to simulate a repository
    with tempfile.TemporaryDirectory(prefix="docai_test_") as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create some sample files to simulate a repository
        (repo_path / "README.md").write_text("# Test Repository\n\nThis is a test repository.")
        (repo_path / "main.py").write_text("print('Hello, world!')")
        
        # Create a src directory with some Python files
        src_dir = repo_path / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.py").write_text("def main():\n    print('App running')")
        (src_dir / "utils.py").write_text("def helper():\n    return 'Helper function'")
        
        print(f"\n📂 Created test repository at {repo_path}")
        
        # Create documentation structure for both personas
        personas = ["internal", "dev"]
        for persona in personas:
            print(f"\n{'=' * 80}")
            print(f"📚 Creating {persona} documentation structure")
            print(f"{'=' * 80}")
            
            # Create persona-specific docs directory
            persona_docs_dir = repo_path / "docs" / persona
            persona_docs_dir.mkdir(parents=True, exist_ok=True)
            
            # Create SUMMARY.md
            (persona_docs_dir / "SUMMARY.md").write_text(f"# Summary for {persona}\n\n* [Home](README.md)\n\n## Documentation Info\n* Persona: **{persona}**")
            
            # Create README.md
            (persona_docs_dir / "README.md").write_text(f"# {persona.capitalize()} Documentation\n\nThis is the {persona} documentation.")
            
            # Create architecture directory with version files
            arch_dir = persona_docs_dir / "architecture"
            arch_dir.mkdir(parents=True, exist_ok=True)
            (arch_dir / "v1.0-architecture.md").write_text(f"# Architecture v1.0 ({persona})")
            (arch_dir / "current.md").write_text(f"# Current Architecture ({persona})")
            
            # Create workflow directory with version files
            workflow_dir = persona_docs_dir / "workflow"
            workflow_dir.mkdir(parents=True, exist_ok=True)
            (workflow_dir / "v1.0-workflow.md").write_text(f"# Workflow v1.0 ({persona})")
            (workflow_dir / "current.md").write_text(f"# Current Workflow ({persona})")
            
            # Create API documentation
            (persona_docs_dir / "api.md").write_text(f"# API Documentation ({persona})")
            
            # Create changes directory with some change files
            changes_dir = persona_docs_dir / "changes"
            changes_dir.mkdir(parents=True, exist_ok=True)
            (changes_dir / "20230101-initial-commit.md").write_text(f"# Initial Commit ({persona})")
            (changes_dir / "20230102-feature-update.md").write_text(f"# Feature Update ({persona})")
        
        # Check documentation structure
        print("\n" + "=" * 80)
        print("CHECKING DOCUMENTATION STRUCTURE")
        print("=" * 80)
        
        for persona in personas:
            persona_docs_dir = repo_path / "docs" / persona
            if not persona_docs_dir.exists():
                print(f"❌ {persona} docs directory not found!")
                continue
                
            print(f"\n📂 {persona} docs directory structure:")
            for item in persona_docs_dir.glob("**/*"):
                if item.is_file():
                    print(f"  - {item.relative_to(persona_docs_dir)}")
        
        # Test publishing to docbook
        print("\n" + "=" * 80)
        print("TESTING DOCBOOK PUBLISHING STRUCTURE")
        print("=" * 80)
        
        # Create a temporary directory to simulate a docbook repository
        with tempfile.TemporaryDirectory(prefix="docai_docbook_") as docbook_tmpdir:
            docbook_path = Path(docbook_tmpdir)
            
            # Simulate publishing
            print("\n📤 Simulating publishing to docbook...")
            
            # Copy docs directory to docbook repository
            source_repo_name = "test-repo"
            target_dir = docbook_path / source_repo_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create docs directory inside target repo directory
            target_docs_dir = target_dir / "docs"
            target_docs_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy persona folders directly
            shutil.copytree(repo_path / "docs", target_docs_dir, dirs_exist_ok=True)
            
            print("\n📂 Docbook repository structure after publishing:")
            for item in docbook_path.glob("**/*"):
                if item.is_file():
                    print(f"  - {item.relative_to(docbook_path)}")
            
            # Check if persona directories exist in the docbook repository
            for persona in personas:
                persona_dir = target_docs_dir / persona
                if persona_dir.exists():
                    print(f"\n✅ {persona} directory exists in docbook repository")
                    # Check if SUMMARY.md exists
                    summary_path = persona_dir / "SUMMARY.md"
                    if summary_path.exists():
                        print(f"✅ SUMMARY.md exists for {persona}")
                        print(f"📄 SUMMARY.md content:")
                        print(summary_path.read_text())
                    else:
                        print(f"❌ SUMMARY.md not found for {persona}")
                else:
                    print(f"\n❌ {persona} directory not found in docbook repository")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    test_dual_persona_structure()
