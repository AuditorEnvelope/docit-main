#!/usr/bin/env python3
"""
Quick test script for comprehensive documentation generation
"""

import sys
from pathlib import Path
from comprehensive_doc_generator import (
    check_documentation_quality,
    generate_comprehensive_documentation
)

def test_quality_check():
    """Test documentation quality checking"""
    print("=" * 60)
    print("Testing Documentation Quality Check")
    print("=" * 60)
    
    repo_dir = Path.cwd()
    quality_report = check_documentation_quality(repo_dir)
    
    print("\n📊 Quality Report:")
    print(f"  Summary exists: {quality_report['summary_exists']}")
    print(f"  Summary quality: {quality_report['summary_quality']}/10")
    print(f"  Architecture exists: {quality_report['architecture_exists']}")
    print(f"  Architecture quality: {quality_report['architecture_quality']}/10")
    print(f"  Workflow exists: {quality_report['workflow_exists']}")
    print(f"  Workflow quality: {quality_report['workflow_quality']}/10")
    print(f"  API exists: {quality_report['api_exists']}")
    print(f"  API quality: {quality_report['api_quality']}/10")
    print(f"\n  Needs generation: {quality_report['needs_generation']}")
    
    return quality_report

def test_generation(quality_report):
    """Test documentation generation"""
    if not quality_report['needs_generation']:
        print("\n✅ All documentation is high quality! No generation needed.")
        return
    
    print("\n" + "=" * 60)
    print("Testing Documentation Generation")
    print("=" * 60)
    
    # Mock analysis for testing
    mock_analysis = {
        "type": "feature",
        "significance": 8,
        "title": "Test Documentation Generation",
        "summary": "Testing comprehensive documentation generation system",
        "impact_scope": ["documentation"],
        "affected_components": ["docs/"],
        "documentation_needs": {
            "update_readme": True,
            "create_changelog": False,
            "update_api_docs": True,
            "create_migration_guide": False
        }
    }
    
    repo_dir = Path.cwd()
    changed_files = ["test.py"]
    
    try:
        generate_comprehensive_documentation(repo_dir, mock_analysis, changed_files)
        print("\n✅ Documentation generation completed!")
    except Exception as e:
        print(f"\n❌ Documentation generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🧪 Comprehensive Documentation System Test\n")
    
    # Test quality check
    quality_report = test_quality_check()
    
    # Ask user if they want to test generation
    if quality_report['needs_generation']:
        print("\n" + "=" * 60)
        response = input("\n🤔 Generate missing documentation? (y/n): ")
        if response.lower() == 'y':
            test_generation(quality_report)
        else:
            print("\n⏭️  Skipping generation test")
    
    print("\n✅ Test complete!\n")
