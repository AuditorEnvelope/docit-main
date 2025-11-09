import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

from app.services.documentation.fallback_generation import create_fallback_doc
from app.services.llm.rotator import generate_doc_for_file

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".h": "c",
    ".c": "c",
}

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    "vendor",
    "env",
    "venv",
    "docbook",
    "docs",
    "coverage",
    "tmp",
}


@dataclass
class DocumentedFile:
    path: Path
    content: str


class ComprehensiveDocBuilder:
    """High-fidelity documentation generator (legacy comprehensive flow)."""

    def __init__(self, repository_root: Path, doc_persona: str = "internal") -> None:
        self.repository_root = repository_root
        self.doc_persona = doc_persona

    async def build(self) -> Dict[str, str]:
        print("================================================================================")
        print(f"📦 Starting comprehensive documentation build for {self.repository_root.name}")
        print(f"👤 Persona: {self.doc_persona}")
        print("================================================================================")

        quality = check_documentation_quality(self.repository_root)
        print(f"📋 Quality Report: {json.dumps(quality, indent=2)}")

        analysis = analyze_full_codebase(self.repository_root)
        recent_changes = {"generated_at": datetime.utcnow().isoformat()}

        docs: Dict[str, str] = {}
        if "summary" in quality["needs_generation"]:
            print("📝 Generating comprehensive SUMMARY/README...")
            docs["summary"] = await generate_comprehensive_summary(
                self.repository_root, analysis, recent_changes, self.doc_persona
            )
        else:
            docs["summary"] = self._try_read(self.repository_root / "docs" / "SUMMARY.md")

        if "architecture" in quality["needs_generation"]:
            print("🏗️  Generating architecture documentation...")
            docs["architecture"] = await generate_versioned_architecture(
                self.repository_root, analysis, recent_changes, self.doc_persona
            )
        else:
            docs["architecture"] = self._try_read(self.repository_root / "docs" / "architecture" / "current.md")

        if "workflow" in quality["needs_generation"]:
            print("🔄 Generating workflow documentation...")
            docs["workflow"] = await generate_versioned_workflow(
                self.repository_root, analysis, recent_changes, self.doc_persona
            )
        else:
            docs["workflow"] = self._try_read(self.repository_root / "docs" / "workflow" / "current.md")

        if "api" in quality["needs_generation"]:
            print("📡 Generating API documentation...")
            docs["api"] = await generate_api_documentation(
                self.repository_root, analysis, recent_changes, self.doc_persona
            )
        else:
            docs["api"] = self._try_read(self.repository_root / "docs" / "api.md")

        update_summary_navigation(self.repository_root / "docs")
        print("✅ Comprehensive documentation build complete!")
        return docs

    def _collect_listing(self, limit: int = 50) -> str:
        entries = []
        count = 0
        for path in self._iter_source_files():
            entries.append(str(path.relative_to(self.repository_root)))
            count += 1
            if count >= limit:
                break
        return "\n".join(entries)

    def _iter_source_files(self) -> Iterable[Path]:
        for path in self.repository_root.rglob("*"):
            if path.is_dir():
                if path.name in IGNORED_DIRECTORIES:
                    continue
                if any(parent.name in IGNORED_DIRECTORIES for parent in path.parents):
                    continue
                continue
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path

    def _try_read(self, path: Path, limit: int = 2000) -> str:
        if not path.exists():
            return ""
        try:
            return path.read_text(errors="ignore")[:limit]
        except Exception:
            return ""


def check_documentation_quality(repo_dir: Path) -> Dict[str, object]:
    docs_dir = Path(repo_dir) / "docs"
    report = {
        "summary_exists": False,
        "summary_quality": 0,
        "architecture_exists": False,
        "architecture_quality": 0,
        "workflow_exists": False,
        "workflow_quality": 0,
        "api_exists": False,
        "api_quality": 0,
        "needs_generation": [],
    }

    def _score(path: Path, doc_type: str) -> None:
        if path.exists():
            content = path.read_text(errors="ignore")
            report[f"{doc_type}_exists"] = True
            report[f"{doc_type}_quality"] = assess_content_quality(content, doc_type)
            if report[f"{doc_type}_quality"] < 8:
                report["needs_generation"].append(doc_type)
        else:
            report["needs_generation"].append(doc_type)

    _score(docs_dir / "SUMMARY.md", "summary")
    _score(docs_dir / "architecture" / "current.md", "architecture")
    _score(docs_dir / "workflow" / "current.md", "workflow")
    _score(docs_dir / "api.md", "api")
    return report


def assess_content_quality(content: str, doc_type: str) -> int:
    if len(content.strip()) < 100:
        return 2
    score = 5
    if "##" in content or "# " in content:
        score += 1
    if "```" in content:
        score += 1
    if any(marker in content for marker in ("- ", "* ", "1. ")):
        score += 1
    if len(content) > 1000:
        score += 1
    if len(content) > 3000:
        score += 1
    return min(score, 10)


async def generate_comprehensive_summary(
    repo_dir: Path, analysis: Dict[str, object], recent_changes: Dict[str, object], doc_persona: str
) -> str:
    prompt = (
        "You are DocAI, an expert technical writer analyzing THIS SPECIFIC REPOSITORY.\n\n"
        f"Persona: {doc_persona}\n"
        f"Repository: {Path(repo_dir).name}\n\n"
        f"ACTUAL CODEBASE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\n"
        f"RECENT CHANGES:\n{json.dumps(recent_changes, indent=2)}\n\n"
        "Generate a comprehensive README that includes overview, architecture, getting started, usage, project structure,"
        " API overview, development workflow, and key dependencies."
    )
    return generate_doc_for_file("SUMMARY.md", prompt)


async def generate_versioned_architecture(
    repo_dir: Path, analysis: Dict[str, object], recent_changes: Dict[str, object], doc_persona: str
) -> str:
    docs_dir = Path(repo_dir) / "docs"
    arch_dir = docs_dir / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    version = get_current_version(docs_dir, "architecture")

    prompt = (
        "You are DocAI, an expert system architect. Base all statements on ACTUAL code.\n\n"
        f"Persona: {doc_persona}\n"
        f"Repository: {Path(repo_dir).name}\n"
        f"VERSION: v{version}\n"
        f"CODE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n"
        f"RECENT CHANGES:\n{json.dumps(recent_changes, indent=2)}\n"
        "Document real services, handlers, models, utilities, technology stack, data flow, and design patterns."
    )
    content = generate_doc_for_file("architecture.md", prompt)
    (arch_dir / f"v{version}-architecture.md").write_text(content)
    (arch_dir / "current.md").write_text(content)
    return content


async def generate_versioned_workflow(
    repo_dir: Path, analysis: Dict[str, object], recent_changes: Dict[str, object], doc_persona: str
) -> str:
    docs_dir = Path(repo_dir) / "docs"
    workflow_dir = docs_dir / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    version = get_current_version(docs_dir, "workflow")

    prompt = (
        "You are DocAI, an expert process analyst documenting ACTUAL workflows.\n\n"
        f"Persona: {doc_persona}\n"
        f"Repository: {Path(repo_dir).name}\n"
        f"VERSION: v{version}\n"
        f"CODE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n"
        f"RECENT CHANGES:\n{json.dumps(recent_changes, indent=2)}\n"
        "Cover development workflow, CI/CD, deployments, release process, and monitoring."
    )
    content = generate_doc_for_file("workflow.md", prompt)
    (workflow_dir / f"v{version}-workflow.md").write_text(content)
    (workflow_dir / "current.md").write_text(content)
    return content


async def generate_api_documentation(
    repo_dir: Path, analysis: Dict[str, object], recent_changes: Dict[str, object], doc_persona: str
) -> str:
    docs_dir = Path(repo_dir) / "docs"
    prompt = (
        "You are DocAI, an expert API writer documenting REAL endpoints from this repository.\n\n"
        f"Persona: {doc_persona}\n"
        f"Repository: {Path(repo_dir).name}\n"
        f"CODE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n"
        f"RECENT CHANGES:\n{json.dumps(recent_changes, indent=2)}\n"
        "Provide endpoint summaries, request/response examples, authentication, rate limits, and SDK guidance."
    )
    content = generate_doc_for_file("api.md", prompt)
    (docs_dir / "api.md").write_text(content)
    return content


def get_current_version(docs_dir: Path, doc_type: str) -> str:
    version_dir = docs_dir / doc_type
    if not version_dir.exists():
        return "1.0"
    versions = []
    for path in version_dir.glob("v*-*.md"):
        try:
            major_minor = path.stem.split("-")[0][1:]
            major, minor = major_minor.split(".")
            versions.append((int(major), int(minor)))
        except Exception:
            continue
    if not versions:
        return "1.0"
    major, minor = max(versions)
    if minor >= 9:
        return f"{major + 1}.0"
    return f"{major}.{minor + 1}"


def analyze_full_codebase(repo_dir: Path) -> Dict[str, object]:
    analysis: Dict[str, object] = {
        "project_name": Path(repo_dir).name,
        "file_count": 0,
        "languages": [],
        "main_directories": [],
        "dependencies": {},
        "imports": {},
        "frameworks": [],
        "database_tech": [],
        "deployment_tech": [],
    }
    try:
        analysis["file_count"] = int(
            subprocess.run("find . -type f | wc -l", shell=True, cwd=repo_dir, capture_output=True, text=True).stdout.strip()
        )
        for ext in [".py", ".ts", ".js", ".go", ".java", ".rs", ".cpp", ".c", ".php", ".rb"]:
            count = int(
                subprocess.run(
                    f"find . -name '*{ext}' | wc -l",
                    shell=True,
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
            if count:
                analysis["languages"].append(ext[1:])
        dirs = subprocess.run(
            "find . -maxdepth 2 -type d | head -20",
            shell=True,
            cwd=repo_dir,
            capture_output=True,
            text=True,
        ).stdout.strip()
        analysis["main_directories"] = dirs.split("\n")
    except Exception as exc:
        logger.warning("Codebase scan failed: %s", exc)
    return analysis


def update_summary_navigation(docs_dir: Path) -> None:
    summary = ["# Summary", ""]
    if (docs_dir / "SUMMARY.md").exists():
        summary.append("* [Home](SUMMARY.md)")
    arch_dir = docs_dir / "architecture"
    if arch_dir.exists():
        summary.append("\n## Architecture")
        for path in sorted(arch_dir.glob("v*-architecture.md"), reverse=True)[:5]:
            summary.append(f"* [{path.stem.upper()}](architecture/{path.name})")
    workflow_dir = docs_dir / "workflow"
    if workflow_dir.exists():
        summary.append("\n## Workflow")
        for path in sorted(workflow_dir.glob("v*-workflow.md"), reverse=True)[:5]:
            summary.append(f"* [{path.stem.upper()}](workflow/{path.name})")
    if (docs_dir / "api.md").exists():
        summary.append("\n## API")
        summary.append("* [API Documentation](api.md)")
    (docs_dir / "SUMMARY.md").write_text("\n".join(summary))
