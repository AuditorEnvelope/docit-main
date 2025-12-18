"""
Quality Integration Module
Integrates quality checking into the documentation generation workflow
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from core.quality_checker import DocumentationQualityChecker, DocumentationQuality

class QualityValidationWrapper:
    """
    Wraps documentation generation with quality validation
    Ensures all docs meet minimum quality standards before committing
    """
    
    def __init__(self, threshold: float = 8.0, max_regenerations: int = 2):
        self.checker = DocumentationQualityChecker()
        self.threshold = threshold
        self.max_regenerations = max_regenerations
    
    async def validate_and_improve(
        self,
        repo_dir: str,
        repo_name: str,
        docs: Dict[str, str],
        regeneration_callback=None
    ) -> tuple[bool, DocumentationQuality]:
        """
        Validate documentation quality and regenerate if needed
        
        Args:
            repo_dir: Path to repository
            repo_name: Repository name
            docs: Dictionary of doc_type -> content
            regeneration_callback: Function to call for regeneration
            
        Returns:
            (passed, quality_assessment)
        """
        
        # Calculate codebase size
        codebase_size = self._calculate_codebase_size(repo_dir)
        
        # Initial quality check
        print(f"\n{'='*60}")
        print(f"🔍 QUALITY VALIDATION: {repo_name}")
        print(f"{'='*60}")
        
        for attempt in range(self.max_regenerations + 1):
            quality = await self.checker.evaluate_documentation(
                repo_name=repo_name,
                codebase_size=codebase_size,
                docs=docs
            )
            
            if attempt == 0:
                print(f"\n📊 Initial Quality Assessment:")
            else:
                print(f"\n📊 Quality Assessment (Attempt {attempt + 1}):")
            
            self._print_quality_summary(quality)
            
            # Check if quality meets threshold
            if quality.overall_score >= self.threshold:
                print(f"\n✅ QUALITY CHECK PASSED (Score: {quality.overall_score:.1f}/10)")
                print(f"{'='*60}\n")
                return True, quality
            
            # Check if we should regenerate
            if attempt < self.max_regenerations:
                low_quality_docs = quality.get_low_quality_docs(self.threshold)
                print(f"\n⚠️  QUALITY CHECK FAILED (Score: {quality.overall_score:.1f}/10)")
                print(f"📝 Low-quality documents: {', '.join(low_quality_docs)}")
                print(f"🔄 Regenerating with feedback (Attempt {attempt + 1}/{self.max_regenerations})...")
                
                if regeneration_callback:
                    # Regenerate with specific feedback
                    docs = await regeneration_callback(low_quality_docs, quality)
                else:
                    print("⚠️  No regeneration callback provided, cannot improve")
                    break
            else:
                print(f"\n❌ QUALITY CHECK FAILED after {self.max_regenerations} regenerations")
                print(f"   Final Score: {quality.overall_score:.1f}/10 (Threshold: {self.threshold})")
                print(f"{'='*60}\n")
                return False, quality
        
        return False, quality
    
    def _calculate_codebase_size(self, repo_dir: str) -> Dict[str, int]:
        """Calculate lines of code per language"""
        
        language_extensions = {
            "Python": [".py"],
            "TypeScript": [".ts", ".tsx"],
            "JavaScript": [".js", ".jsx"],
            "Go": [".go"],
            "Rust": [".rs"],
            "Java": [".java"],
            "C++": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
            "C#": [".cs"],
            "Ruby": [".rb"],
            "PHP": [".php"],
            "Swift": [".swift"],
            "Kotlin": [".kt"],
            "Scala": [".scala"],
        }
        
        codebase_size = {}
        repo_path = Path(repo_dir)
        
        # Skip common non-code directories
        skip_dirs = {".git", "node_modules", "venv", "__pycache__", "dist", "build", ".next"}
        
        for lang, extensions in language_extensions.items():
            total_lines = 0
            for ext in extensions:
                for file_path in repo_path.rglob(f"*{ext}"):
                    # Skip if in excluded directory
                    if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            total_lines += lines
                    except Exception:
                        continue
            
            if total_lines > 0:
                codebase_size[lang] = total_lines
        
        return codebase_size
    
    def _print_quality_summary(self, quality: DocumentationQuality):
        """Print formatted quality summary"""
        
        print(f"\n   Overall Score: {quality.overall_score:.1f}/10")
        
        if quality.architecture_score:
            status = "✅" if quality.architecture_score.score >= self.threshold else "❌"
            print(f"   {status} Architecture: {quality.architecture_score.score:.1f}/10")
            if quality.architecture_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.architecture_score.weaknesses[:2])}")
        
        if quality.workflow_score:
            status = "✅" if quality.workflow_score.score >= self.threshold else "❌"
            print(f"   {status} Workflow: {quality.workflow_score.score:.1f}/10")
            if quality.workflow_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.workflow_score.weaknesses[:2])}")
        
        if quality.readme_score:
            status = "✅" if quality.readme_score.score >= self.threshold else "❌"
            print(f"   {status} README: {quality.readme_score.score:.1f}/10")
            if quality.readme_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.readme_score.weaknesses[:2])}")
        
        if quality.api_score:
            status = "✅" if quality.api_score.score >= self.threshold else "❌"
            print(f"   {status} API: {quality.api_score.score:.1f}/10")
            if quality.api_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.api_score.weaknesses[:2])}")
    
    def save_quality_report(self, repo_dir: str, quality: DocumentationQuality):
        """Save quality report to repository"""
        
        report = self.checker.generate_quality_report(quality)
        report_path = Path(repo_dir) / "docs" / "QUALITY_REPORT.md"
        
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 Quality report saved to {report_path}")
        except Exception as e:
            print(f"⚠️  Failed to save quality report: {e}")


async def validate_documentation_quality(repo_dir: str, repo_name: str) -> bool:
    """
    Async quality validation - no event loop conflicts!
    Returns True if quality check passes
    """
    
    # Read generated documentation
    docs = {}
    docs_path = Path(repo_dir) / "docs"
    
    # Read architecture
    arch_current = docs_path / "architecture" / "current.md"
    if arch_current.exists():
        with open(arch_current, 'r', encoding='utf-8') as f:
            docs["architecture"] = f.read()
    
    # Read workflow
    workflow_current = docs_path / "workflow" / "current.md"
    if workflow_current.exists():
        with open(workflow_current, 'r', encoding='utf-8') as f:
            docs["workflow"] = f.read()
    
    # Read README
    readme_path = Path(repo_dir) / "README.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            docs["readme"] = f.read()
    
    # Read API
    api_path = docs_path / "api.md"
    if api_path.exists():
        with open(api_path, 'r', encoding='utf-8') as f:
            docs["api"] = f.read()
    
    if not docs:
        print("⚠️  No documentation found to validate")
        return True  # Pass by default if no docs
    
    # Run validation
    wrapper = QualityValidationWrapper(threshold=8.0, max_regenerations=0)
    
    # Directly await async function (no event loop creation needed!)
    passed, quality = await wrapper.validate_and_improve(repo_dir, repo_name, docs)
    
    # Save quality report
    wrapper.save_quality_report(repo_dir, quality)
    
    return passed

"""
Quality Integration Module
Integrates quality checking into the documentation generation workflow
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from core.quality_checker import DocumentationQualityChecker, DocumentationQuality

class QualityValidationWrapper:
    """
    Wraps documentation generation with quality validation
    Ensures all docs meet minimum quality standards before committing
    """
    
    def __init__(self, threshold: float = 8.0, max_regenerations: int = 2):
        self.checker = DocumentationQualityChecker()
        self.threshold = threshold
        self.max_regenerations = max_regenerations
    
    async def validate_and_improve(
        self,
        repo_dir: str,
        repo_name: str,
        docs: Dict[str, str],
        regeneration_callback=None
    ) -> tuple[bool, DocumentationQuality]:
        """
        Validate documentation quality and regenerate if needed
        
        Args:
            repo_dir: Path to repository
            repo_name: Repository name
            docs: Dictionary of doc_type -> content
            regeneration_callback: Function to call for regeneration
            
        Returns:
            (passed, quality_assessment)
        """
        
        # Calculate codebase size
        codebase_size = self._calculate_codebase_size(repo_dir)
        
        # Initial quality check
        print(f"\n{'='*60}")
        print(f"🔍 QUALITY VALIDATION: {repo_name}")
        print(f"{'='*60}")
        
        for attempt in range(self.max_regenerations + 1):
            quality = await self.checker.evaluate_documentation(
                repo_name=repo_name,
                codebase_size=codebase_size,
                docs=docs
            )
            
            if attempt == 0:
                print(f"\n📊 Initial Quality Assessment:")
            else:
                print(f"\n📊 Quality Assessment (Attempt {attempt + 1}):")
            
            self._print_quality_summary(quality)
            
            # Check if quality meets threshold
            if quality.overall_score >= self.threshold:
                print(f"\n✅ QUALITY CHECK PASSED (Score: {quality.overall_score:.1f}/10)")
                print(f"{'='*60}\n")
                return True, quality
            
            # Check if we should regenerate
            if attempt < self.max_regenerations:
                low_quality_docs = quality.get_low_quality_docs(self.threshold)
                print(f"\n⚠️  QUALITY CHECK FAILED (Score: {quality.overall_score:.1f}/10)")
                print(f"📝 Low-quality documents: {', '.join(low_quality_docs)}")
                print(f"🔄 Regenerating with feedback (Attempt {attempt + 1}/{self.max_regenerations})...")
                
                if regeneration_callback:
                    # Regenerate with specific feedback
                    docs = await regeneration_callback(low_quality_docs, quality)
                else:
                    print("⚠️  No regeneration callback provided, cannot improve")
                    break
            else:
                print(f"\n❌ QUALITY CHECK FAILED after {self.max_regenerations} regenerations")
                print(f"   Final Score: {quality.overall_score:.1f}/10 (Threshold: {self.threshold})")
                print(f"{'='*60}\n")
                return False, quality
        
        return False, quality
    
    def _calculate_codebase_size(self, repo_dir: str) -> Dict[str, int]:
        """Calculate lines of code per language"""
        
        language_extensions = {
            "Python": [".py"],
            "TypeScript": [".ts", ".tsx"],
            "JavaScript": [".js", ".jsx"],
            "Go": [".go"],
            "Rust": [".rs"],
            "Java": [".java"],
            "C++": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
            "C#": [".cs"],
            "Ruby": [".rb"],
            "PHP": [".php"],
            "Swift": [".swift"],
            "Kotlin": [".kt"],
            "Scala": [".scala"],
        }
        
        codebase_size = {}
        repo_path = Path(repo_dir)
        
        # Skip common non-code directories
        skip_dirs = {".git", "node_modules", "venv", "__pycache__", "dist", "build", ".next"}
        
        for lang, extensions in language_extensions.items():
            total_lines = 0
            for ext in extensions:
                for file_path in repo_path.rglob(f"*{ext}"):
                    # Skip if in excluded directory
                    if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            total_lines += lines
                    except Exception:
                        continue
            
            if total_lines > 0:
                codebase_size[lang] = total_lines
        
        return codebase_size
    
    def _print_quality_summary(self, quality: DocumentationQuality):
        """Print formatted quality summary"""
        
        print(f"\n   Overall Score: {quality.overall_score:.1f}/10")
        
        if quality.architecture_score:
            status = "✅" if quality.architecture_score.score >= self.threshold else "❌"
            print(f"   {status} Architecture: {quality.architecture_score.score:.1f}/10")
            if quality.architecture_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.architecture_score.weaknesses[:2])}")
        
        if quality.workflow_score:
            status = "✅" if quality.workflow_score.score >= self.threshold else "❌"
            print(f"   {status} Workflow: {quality.workflow_score.score:.1f}/10")
            if quality.workflow_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.workflow_score.weaknesses[:2])}")
        
        if quality.readme_score:
            status = "✅" if quality.readme_score.score >= self.threshold else "❌"
            print(f"   {status} README: {quality.readme_score.score:.1f}/10")
            if quality.readme_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.readme_score.weaknesses[:2])}")
        
        if quality.api_score:
            status = "✅" if quality.api_score.score >= self.threshold else "❌"
            print(f"   {status} API: {quality.api_score.score:.1f}/10")
            if quality.api_score.score < self.threshold:
                print(f"      Issues: {', '.join(quality.api_score.weaknesses[:2])}")
    
    def save_quality_report(self, repo_dir: str, quality: DocumentationQuality):
        """Save quality report to repository"""
        
        report = self.checker.generate_quality_report(quality)
        report_path = Path(repo_dir) / "docs" / "QUALITY_REPORT.md"
        
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 Quality report saved to {report_path}")
        except Exception as e:
            print(f"⚠️  Failed to save quality report: {e}")


async def validate_documentation_quality(repo_dir: str, repo_name: str) -> bool:
    """
    Async quality validation - no event loop conflicts!
    Returns True if quality check passes
    """
    
    # Read generated documentation
    docs = {}
    docs_path = Path(repo_dir) / "docs"
    
    # Read architecture
    arch_current = docs_path / "architecture" / "current.md"
    if arch_current.exists():
        with open(arch_current, 'r', encoding='utf-8') as f:
            docs["architecture"] = f.read()
    
    # Read workflow
    workflow_current = docs_path / "workflow" / "current.md"
    if workflow_current.exists():
        with open(workflow_current, 'r', encoding='utf-8') as f:
            docs["workflow"] = f.read()
    
    # Read README
    readme_path = Path(repo_dir) / "README.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            docs["readme"] = f.read()
    
    # Read API
    api_path = docs_path / "api.md"
    if api_path.exists():
        with open(api_path, 'r', encoding='utf-8') as f:
            docs["api"] = f.read()
    
    if not docs:
        print("⚠️  No documentation found to validate")
        return True  # Pass by default if no docs
    
    # Run validation
    wrapper = QualityValidationWrapper(threshold=8.0, max_regenerations=0)
    
    # Directly await async function (no event loop creation needed!)
    passed, quality = await wrapper.validate_and_improve(repo_dir, repo_name, docs)
    
    # Save quality report
    wrapper.save_quality_report(repo_dir, quality)
    
    return passed
