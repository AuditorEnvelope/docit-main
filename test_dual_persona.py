#!/usr/bin/env python
"""
Test script for dual persona documentation generation.
This script simulates the documentation generation process for both internal and dev personas.
"""

import asyncio
import os
import tempfile
from pathlib import Path
import shutil
import sys

# Add the app directory to the path so we can import from it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.documentation.comprehensive import generate_comprehensive_documentation
from app.services.docbook.publisher import DocbookPublisher


async def test_dual_persona_docs():
    """Test dual persona documentation generation."""
    print("\n" + "=" * 80)
    print("TESTING DUAL PERSONA DOCUMENTATION GENERATION")
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
        
        # Create a test directory with some test files
        test_dir = repo_path / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "test_app.py").write_text("def test_main():\n    assert True")
        
        print(f"\n📂 Created test repository at {repo_path}")
        
        # Generate documentation for both personas
        personas = ["internal", "dev"]
        for persona in personas:
            print(f"\n{'=' * 80}")
            print(f"📚 Generating {persona} documentation")
            print(f"{'=' * 80}")
            
            # Create persona-specific docs directory
            persona_docs_dir = repo_path / "docs" / persona
            persona_docs_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate documentation
            analysis = {
                "title": "Test Documentation",
                "is_significant": True,
                "type": "feature",
                "summary": "Test documentation generation",
                "affected_components": ["src/app.py", "src/utils.py"]
            }
            
            await generate_comprehensive_documentation(
                repo_dir=repo_path,
                analysis=analysis,
                changed_files=["src/app.py", "src/utils.py"],
                doc_persona=persona
            )
        
        # Check if documentation was generated correctly
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
        print("TESTING DOCBOOK PUBLISHING")
        print("=" * 80)
        
        # Create a temporary directory to simulate a docbook repository
        with tempfile.TemporaryDirectory(prefix="docai_docbook_") as docbook_tmpdir:
            docbook_path = Path(docbook_tmpdir)
            
            # Initialize git repository
            os.system(f"cd {docbook_path} && git init && git config user.name 'Test User' && git config user.email 'test@example.com'")
            (docbook_path / "README.md").write_text("# Docbook Repository")
            os.system(f"cd {docbook_path} && git add . && git commit -m 'Initial commit'")
            
            print(f"\n📂 Created test docbook repository at {docbook_path}")
            
            # Create publisher
            publisher = DocbookPublisher()
            
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
    asyncio.run(test_dual_persona_docs())
