import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from app.services.documentation.aggregate_prompt import generate_all_docs_in_single_call
# Phase 1: Import planner
from app.services.documentation.planner import get_planner, DocumentationPlan
# Phase 2: Import tree builder
from app.services.documentation.tree_builder import build_document_tree, debug_tree_structure
from app.services.documentation.tree_models import DocumentTree
# Phase 3: Import semantic extraction
from app.services.extraction import build_semantic_snapshot

logger = logging.getLogger(__name__)


# ============================================================================
# QUALITY CHECKING SYSTEM (ported from old codebase)
# ============================================================================

def check_documentation_quality(repo_dir: Path, doc_persona: str = "internal") -> Dict[str, object]:
    """
    Check if existing documentation is comprehensive and worthy
    Returns dict with quality scores and what needs to be generated (like old codebase)

    Args:
        repo_dir: Path to repository
        doc_persona: Documentation persona (internal|developer)
    """
    # Check for persona-specific docs directory
    docs_dir = Path(repo_dir) / "docs" / doc_persona

    quality_report = {
        "summary_exists": False,
        "summary_quality": 0,  # 0-10 scale
        "architecture_exists": False,
        "architecture_quality": 0,
        "workflow_exists": False,
        "workflow_quality": 0,
        "api_exists": False,
        "api_quality": 0,
        "needs_generation": []
    }

    # Check SUMMARY.md or README.md
    summary_files = [
        docs_dir / "SUMMARY.md",
        docs_dir / "README.md",
        Path(repo_dir) / "README.md"
    ]

    for summary_file in summary_files:
        if summary_file.exists():
            content = summary_file.read_text()
            quality_report["summary_exists"] = True
            quality_report["summary_quality"] = assess_content_quality(
                content, "summary")
            break

    # Check architecture documentation
    arch_files = [
        docs_dir / "architecture.md",
        docs_dir / "ARCHITECTURE.md",
        docs_dir / "architecture" / "current.md"
    ]

    for arch_file in arch_files:
        if arch_file.exists():
            content = arch_file.read_text()
            quality_report["architecture_exists"] = True
            quality_report["architecture_quality"] = assess_content_quality(
                content, "architecture")
            break

    # Check workflow documentation
    workflow_files = [
        docs_dir / "workflow.md",
        docs_dir / "WORKFLOW.md",
        docs_dir / "workflow" / "current.md"
    ]

    for workflow_file in workflow_files:
        if workflow_file.exists():
            content = workflow_file.read_text()
            quality_report["workflow_exists"] = True
            quality_report["workflow_quality"] = assess_content_quality(
                content, "workflow")
            break

    # Check API documentation
    api_files = [
        docs_dir / "api.md",
        docs_dir / "API.md",
        docs_dir / "api" / "README.md"
    ]

    for api_file in api_files:
        if api_file.exists():
            content = api_file.read_text()
            quality_report["api_exists"] = True
            quality_report["api_quality"] = assess_content_quality(
                content, "api")
            break

    # Determine what needs generation (quality < 8 for regeneration)
    if not quality_report["summary_exists"] or quality_report["summary_quality"] < 8:
        quality_report["needs_generation"].append("summary")

    if not quality_report["architecture_exists"] or quality_report["architecture_quality"] < 8:
        quality_report["needs_generation"].append("architecture")

    if not quality_report["workflow_exists"] or quality_report["workflow_quality"] < 8:
        quality_report["needs_generation"].append("workflow")

    if not quality_report["api_exists"] or quality_report["api_quality"] < 8:
        quality_report["needs_generation"].append("api")

    return quality_report


def assess_content_quality(content: str, doc_type: str) -> float:
    """
    Use LLM to assess documentation quality (like old codebase)
    Returns score 0-10
    """
    if len(content.strip()) < 100:
        return 2.0  # Too short

    # Quick heuristic checks
    score = 5.0  # Base score

    # Check for headings
    if "##" in content or "# " in content:
        score += 1.0

    # Check for code blocks
    if "```" in content:
        score += 1.0

    # Check for lists
    if "- " in content or "* " in content or "1. " in content:
        score += 1.0

    # Check length (comprehensive docs are longer)
    if len(content) > 1000:
        score += 1.0
    if len(content) > 3000:
        score += 1.0
    return score


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


def update_summary_navigation(docs_dir: Path) -> None:
    summary = ["# Summary", ""]
    if (docs_dir / "SUMMARY.md").exists():
        summary.append("* [Home](SUMMARY.md)")
    arch_dir = docs_dir / "architecture"
    if arch_dir.exists():
        summary.append("\n## Architecture")
        for path in sorted(arch_dir.glob("v*-architecture.md"), reverse=True)[:5]:
            summary.append(
                f"* [{path.stem.upper()}](architecture/{path.name})")
    workflow_dir = docs_dir / "workflow"
    if workflow_dir.exists():
        summary.append("\n## Workflow")
        for path in sorted(workflow_dir.glob("v*-workflow.md"), reverse=True)[:5]:
            summary.append(f"* [{path.stem.upper()}](workflow/{path.name})")
    if (docs_dir / "api.md").exists():
        summary.append("\n## API")
        summary.append("* [API Documentation](api.md)")

    # Add changes (show only last 10 changes to avoid clutter)
    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary.append("\n## Recent Changes")
            for change_file in change_files[:10]:  # Latest 10 only
                # Extract title from filename (remove commit hash prefix)
                title = change_file.stem.split(
                    "-", 1)[-1].replace("-", " ").title()
                summary.append(f"* [{title}](changes/{change_file.name})")

    (docs_dir / "SUMMARY.md").write_text("\n".join(summary))
    print(f"✅ Updated SUMMARY.md (showing only recent versions)")


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
        """
        Build comprehensive documentation.

        Phase 1 Enhancement: Uses DocumentationPlanner for structured guidance.
        Phase 6 Enhancement: Captures token usage and stores in 'token_data' key.
        """
        print("================================================================================")
        print(
            f"📦 Starting comprehensive documentation build for {self.repository_root.name}")
        print(f"👤 Persona: {self.doc_persona}")
        print("================================================================================")

        analysis = analyze_full_codebase(self.repository_root)
        recent_changes = {"generated_at": datetime.utcnow().isoformat()}

        docs_dir = self.repository_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Phase 3: Build semantic snapshot for enhanced planning
        print("🔎 Running semantic extractors...")
        semantic_snapshot = build_semantic_snapshot(
            repo_path=self.repository_root,
            repo_analysis=analysis,
        )
        # Attach to docs for internal use
        docs["_semantic_snapshot"] = semantic_snapshot.to_dict()

        # Phase 1: Create documentation plan for structured guidance
        # Phase 3: Pass semantic snapshot for enhanced planning
        planner = get_planner()
        plan = planner.create_plan(
            analysis, semantic_snapshot=semantic_snapshot.to_dict())
        print(
            f"📋 Documentation Plan: {plan.repo_type} (complexity: {plan.complexity_score}/10)")
        print(f"   Sections: {len(plan.sections)} total")
        for s in plan.sections:
            status = "required" if s.required else "conditional"
            print(f"   - {s.title} ({s.type}, {status})")

        # 🔥 ONE LLM CALL FOR ALL DOCUMENTS (Phase 6: Now captures token usage)
        # Phase 1: Pass plan for structured prompting
        docs, token_data = await generate_all_docs_in_single_call(
            self.repository_root,
            analysis,
            recent_changes,
            self.doc_persona,
            plan=plan  # Phase 1: Pass plan to guide generation
        )

        # Phase 1: Store plan in returned dict for upstream inspection
        docs["plan"] = {
            "repo_type": plan.repo_type,
            "complexity_score": plan.complexity_score,
            "sections": [
                {
                    "id": s.id,
                    "title": s.title,
                    "type": s.type,
                    "required": s.required,
                    "priority": s.priority,
                }
                for s in plan.sections
            ]
        }

        # Store token data in the returned dict for upstream usage tracking
        docs["token_data"] = token_data
        print(
            f"📊 Token Usage: {token_data['input_tokens']} in / {token_data['output_tokens']} out | Model: {token_data['model_name']}")

        # -------------------------------
        # PHASE 2: BUILD DOCUMENT TREE
        # -------------------------------
        # Build internal structured representation (non-breaking)
        doc_tree = build_document_tree(
            flat_docs=docs,
            repo_id=str(self.repository_root.name),
            persona=self.doc_persona,
            plan=plan,
            # Using timestamp as identifier
            commit_sha=recent_changes.get("generated_at"),
            model_name=token_data.get("model_name"),
            token_usage={
                "input_tokens": token_data.get("input_tokens", 0),
                "output_tokens": token_data.get("output_tokens", 0),
            },
        )

        if doc_tree:
            # Log tree structure for debugging (Phase 2 only)
            print("\n" + "="*60)
            print(debug_tree_structure(doc_tree))
            print("="*60 + "\n")

            # Store tree reference in docs dict for upstream access
            # This is INTERNAL ONLY - external consumers can ignore it
            docs["_document_tree"] = doc_tree
        else:
            print("⚠️ Document tree build skipped (non-fatal)")

        # -----------------------------
        # WRITE DOCUMENTS TO FILES
        # -----------------------------
        # SUMMARY
        (docs_dir / "SUMMARY.md").write_text(docs["summary"])

        # ARCHITECTURE
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir(exist_ok=True)
        (arch_dir / "current.md").write_text(docs["architecture"])
        version = get_current_version(docs_dir, "architecture")
        (arch_dir /
         f"v{version}-architecture.md").write_text(docs["architecture"])

        # WORKFLOW
        workflow_dir = docs_dir / "workflow"
        workflow_dir.mkdir(exist_ok=True)
        (workflow_dir / "current.md").write_text(docs["workflow"])
        version = get_current_version(docs_dir, "workflow")
        (workflow_dir / f"v{version}-workflow.md").write_text(docs["workflow"])

        # API
        (docs_dir / "api.md").write_text(docs["api"])

        # Update GitBook SUMMARY
        update_summary_navigation(docs_dir)

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


def get_current_version(docs_dir: Path, doc_type: str) -> str:
    """
    Get the current version number using semantic versioning (v1.0, v1.1, v2.0)
    Returns the next version number to create (like old codebase)

    This prevents excessive versioning by using proper semantic versioning
    """
    version_dir = docs_dir / doc_type

    if not version_dir.exists():
        return "1.0"  # Start with v1.0

    # Find existing version files
    version_files = list(version_dir.glob("v*-*.md"))

    if not version_files:
        return "1.0"

    # Extract version numbers and find the highest
    versions = []
    for vf in version_files:
        try:
            # Extract version from v1.0-architecture.md format
            version_str = vf.stem.split("-")[0][1:]  # Remove 'v' prefix
            if "." in version_str:
                # Semantic version (1.0, 1.1, 2.0)
                major, minor = version_str.split(".")
                versions.append((int(major), int(minor)))
            else:
                # Legacy version (1, 2, 3) - treat as major version
                versions.append((int(version_str), 0))
        except Exception:
            continue

    if not versions:
        return "1.0"

    # Get the highest version
    max_major, max_minor = max(versions)

    # Return next minor version (v1.0 → v1.1, v1.9 → v2.0)
    if max_minor >= 9:
        return f"{max_major + 1}.0"
    else:
        return f"{max_major}.{max_minor + 1}"


def analyze_full_codebase(repo_dir: Path) -> Dict[str, object]:
    """Analyze the entire codebase structure with detailed insights (like old codebase)"""
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
            subprocess.run("find . -type f | wc -l", shell=True,
                           cwd=repo_dir, capture_output=True, text=True).stdout.strip()
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

        # Analyze Python dependencies and imports (like old codebase)
        if "py" in analysis["languages"]:
            _analyze_python_dependencies(repo_dir, analysis)

        # Detect technologies (like old codebase)
        _detect_technologies(repo_dir, analysis)

    except Exception as exc:
        logger.warning("Codebase scan failed: %s", exc)
    return analysis


def _analyze_python_dependencies(repo_dir: Path, analysis: Dict[str, object]) -> None:
    """Analyze Python imports and dependencies (like old codebase)"""
    imports: Dict[str, int] = {}
    frameworks: List[str] = []

    try:
        for py_file in repo_dir.rglob("*.py"):
            try:
                content = py_file.read_text()

                # Extract import statements
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')):
                        # Extract main module
                        if line.startswith('import '):
                            module = line.split(' ')[1].split('.')[0]
                        elif line.startswith('from '):
                            module = line.split(' ')[1].split('.')[0]
                        else:
                            continue

                        if module not in ['os', 'sys', 'json', 'time', 'datetime', 'typing', 'pathlib', 'logging']:
                            imports[module] = imports.get(module, 0) + 1
            except Exception:
                continue

        # Detect frameworks
        framework_indicators = {
            "FastAPI": ["fastapi", "FastAPI"],
            "Django": ["django", "DJANGO"],
            "Flask": ["flask", "Flask"],
            "SQLAlchemy": ["sqlalchemy", "SQLAlchemy"],
            "AsyncPG": ["asyncpg", "AsyncPG"],
            "Pydantic": ["pydantic", "Pydantic"],
            "Click": ["click", "Click"],
            "Typer": ["typer", "Typer"]
        }

        for framework, indicators in framework_indicators.items():
            if any(indicator in str(imports) for indicator in indicators):
                frameworks.append(framework)

        analysis["imports"] = dict(
            sorted(imports.items(), key=lambda x: x[1], reverse=True)[:10])
        analysis["frameworks"] = frameworks

    except Exception as e:
        logger.warning("Python analysis failed: %s", e)


def _detect_technologies(repo_dir: Path, analysis: Dict[str, object]) -> None:
    """Detect technologies and deployment methods (like old codebase)"""
    content = ""
    for file_path in repo_dir.rglob("*"):
        try:
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.yaml', '.yml', '.json', '.md']:
                content += file_path.read_text().lower()
        except Exception:
            continue

    # Database technologies
    db_indicators = {
        "PostgreSQL": ["postgresql", "postgres", "psycopg"],
        "MySQL": ["mysql", "pymysql"],
        "SQLite": ["sqlite", "sqlite3"],
        "MongoDB": ["mongodb", "pymongo", "mongo"],
        "Redis": ["redis", "aredis"],
        "Milvus": ["milvus", "pymilvus"]
    }

    for db, indicators in db_indicators.items():
        if any(indicator in content for indicator in indicators):
            analysis["database_tech"].append(db)

    # Deployment technologies
    deploy_indicators = {
        "Docker": ["docker", "dockerfile", "docker-compose"],
        "Kubernetes": ["kubernetes", "k8s", "kubectl"],
        "AWS": ["aws", "boto3", "s3", "ec2"],
        "GCP": ["google", "gcp", "firebase"],
        "Azure": ["azure", "microsoft"],
        "Heroku": ["heroku", "gunicorn"],
        "Vercel": ["vercel", "now"],
        "Netlify": ["netlify"]
    }

    for deploy, indicators in deploy_indicators.items():
        if any(indicator in content for indicator in indicators):
            analysis["deployment_tech"].append(deploy)


def analyze_components(repo_dir: Path) -> Dict[str, object]:
    """Analyze system components based on actual codebase structure (like old codebase)"""
    components = {
        "detected": [],
        "services": [],
        "utilities": [],
        "models": [],
        "handlers": []
    }

    try:
        # Look for actual component structure
        src_dir = repo_dir / "src"
        app_dir = repo_dir / "app"
        search_dirs = [src_dir, app_dir] if app_dir.exists(
        ) else [src_dir] if src_dir.exists() else [repo_dir]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            # Detect services
            for py_file in search_dir.rglob("*.py"):
                try:
                    filename = py_file.stem.lower()
                    content = py_file.read_text()

                    if any(pattern in filename for pattern in ["service", "_service"]):
                        components["services"].append({
                            "name": py_file.stem,
                            "path": str(py_file.relative_to(repo_dir)),
                            "description": f"Service module handling {filename.replace('_', ' ')} functionality"
                        })

                    elif any(pattern in filename for pattern in ["handler", "_handler"]):
                        components["handlers"].append({
                            "name": py_file.stem,
                            "path": str(py_file.relative_to(repo_dir)),
                            "description": f"Handler for {filename.replace('_', ' ')} operations"
                        })

                    elif any(pattern in filename for pattern in ["model", "_model", "schema"]) and "class" in content:
                        components["models"].append({
                            "name": py_file.stem,
                            "path": str(py_file.relative_to(repo_dir)),
                            "description": f"Data model/schema for {filename.replace('_', ' ')}"
                        })

                    elif any(pattern in filename for pattern in ["util", "helper", "utils"]) or ("def " in content and len(content.split("def ")) > 3):
                        components["utilities"].append({
                            "name": py_file.stem,
                            "path": str(py_file.relative_to(repo_dir)),
                            "description": f"Utility functions for {filename.replace('_', ' ')}"
                        })
                except Exception:
                    continue

        # Detect main application structure
        main_patterns = {
            "api": ["fastapi", "flask", "app.py", "main.py"],
            "database": ["database", "db", "postgres", "sqlite", "model"],
            "frontend": ["static", "templates", "public", "web", "ui"],
            "core": ["core", "engine", "manager", "processor"]
        }

        for component_type, patterns in main_patterns.items():
            for pattern in patterns:
                if any(pattern in str(f) for f in repo_dir.rglob("*") if f.is_file()):
                    if component_type not in components["detected"]:
                        components["detected"].append(component_type)

        # If no specific components found, fall back to basic detection
        if not components["detected"]:
            components["detected"] = ["core", "api", "database"]

        return components

    except Exception as e:
        logger.warning("Component analysis failed: %s", e)
        return {"detected": ["core", "api", "database"], "services": [], "utilities": [], "models": [], "handlers": []}


def detect_design_patterns(repo_dir: Path) -> List[str]:
    """Detect actual design patterns in the codebase (like old codebase)"""
    patterns: List[str] = []

    try:
        # Look for actual patterns in the code
        pattern_indicators = {
            "Factory Pattern": ["factory", "create", "builder"],
            "Observer Pattern": ["observer", "listener", "event", "callback", "subscribe"],
            "Singleton Pattern": ["singleton", "instance", "_instance", "getinstance"],
            "Repository Pattern": ["repository", "repo", "dao", "data access"],
            "MVC Pattern": ["model", "view", "controller", "mvc"],
            "Dependency Injection": ["inject", "container", "di", "provider"],
            "Strategy Pattern": ["strategy", "algorithm", "policy"],
            "Decorator Pattern": ["decorator", "wrapper", "wrap"],
            "Command Pattern": ["command", "execute", "undo"],
            "Adapter Pattern": ["adapter", "bridge", "interface"],
            "Facade Pattern": ["facade", "simplify", "interface"],
            "Proxy Pattern": ["proxy", "delegate", "surrogate"],
            "Chain of Responsibility": ["chain", "handler", "next"],
            "Template Method": ["template", "hook", "abstract"],
            "State Pattern": ["state", "context", "transition"],
            "Composite Pattern": ["composite", "component", "leaf", "container"],
            "Iterator Pattern": ["iterator", "next", "hasnext", "iterable"],
            "Mediator Pattern": ["mediator", "communicate", "central"],
            "Memento Pattern": ["memento", "snapshot", "state"],
            "Flyweight Pattern": ["flyweight", "cache", "pool", "reuse"]
        }

        # Search through Python files for pattern indicators
        for py_file in repo_dir.rglob("*.py"):
            try:
                content = py_file.read_text().lower()

                for pattern_name, indicators in pattern_indicators.items():
                    if any(indicator in content for indicator in indicators):
                        # Check for actual implementation, not just mentions
                        if pattern_name.lower() in content or any(f"class.*{ind}" in content for ind in indicators):
                            if pattern_name not in patterns:
                                patterns.append(pattern_name)
            except Exception:
                continue

        # If no patterns found, return basic ones that are commonly used
        if not patterns:
            # Check for common patterns in our specific codebase
            content = ""
            for py_file in repo_dir.rglob("*.py"):
                try:
                    content += py_file.read_text()
                except Exception:
                    continue

            if "class" in content and "def" in content:
                patterns.append("Object-Oriented Design")

            if "async" in content or "await" in content:
                patterns.append("Async/Await Pattern")

            if "try:" in content and "except" in content:
                patterns.append("Error Handling Pattern")

        return patterns if patterns else ["Object-Oriented Design", "Error Handling"]

    except Exception as e:
        logger.warning("Design pattern detection failed: %s", e)
        return ["Object-Oriented Design", "Async/Await Pattern"]


def analyze_architecture(repo_dir: Path) -> Dict[str, object]:
    """Analyze system architecture (like old codebase)"""
    return {
        "components": analyze_components(repo_dir),
        "structure": analyze_full_codebase(repo_dir),
        "patterns": detect_design_patterns(repo_dir)
    }


def update_summary_navigation(docs_dir: Path) -> None:
    """Update SUMMARY.md navigation with links to all documentation files.

    Args:
        docs_dir: Path to the documentation directory (persona-specific)
    """
    summary = ["# Summary", ""]

    # Get persona from path if available
    persona = ""
    if "internal" in str(docs_dir) or "dev" in str(docs_dir):
        persona = docs_dir.name
        print(f"📚 Updating SUMMARY.md for persona: {persona}")

    # Add home link
    if (docs_dir / "SUMMARY.md").exists():
        summary.append("* [Home](SUMMARY.md)")
    elif (docs_dir / "README.md").exists():
        summary.append("* [Home](README.md)")

    # Add architecture links
    arch_dir = docs_dir / "architecture"
    if arch_dir.exists():
        summary.append("\n## Architecture")
        for path in sorted(arch_dir.glob("v*-architecture.md"), reverse=True)[:5]:
            summary.append(
                f"* [{path.stem.upper()}](architecture/{path.name})")

    # Add workflow links
    workflow_dir = docs_dir / "workflow"
    if workflow_dir.exists():
        summary.append("\n## Workflow")
        for path in sorted(workflow_dir.glob("v*-workflow.md"), reverse=True)[:5]:
            summary.append(f"* [{path.stem.upper()}](workflow/{path.name})")

    # Add API link
    if (docs_dir / "api.md").exists():
        summary.append("\n## API")
        summary.append("* [API Documentation](api.md)")

    # Add changes (show only last 10 changes to avoid clutter)
    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary.append("\n## Recent Changes")
            for change_file in change_files[:10]:  # Latest 10 only
                # Extract title from filename (remove commit hash prefix)
                title = change_file.stem.split(
                    "-", 1)[-1].replace("-", " ").title()
                summary.append(f"* [{title}](changes/{change_file.name})")

    # Add persona information if applicable
    if persona:
        summary.append(f"\n## Documentation Info")
        summary.append(f"* Persona: **{persona}**")
        summary.append(
            f"* Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    # Write the SUMMARY.md file
    (docs_dir / "SUMMARY.md").write_text("\n".join(summary))
    print(
        f"✅ Updated SUMMARY.md for {docs_dir.name} (showing only recent versions)")


# ============================================================================
# VERSIONING LOGIC (ported from old codebase)
# ============================================================================

def analyze_architectural_impact(repo_dir: Path, changed_files: List[str], analysis: Dict[str, object]) -> Dict[str, object]:
    """
    Determine if changes warrant a new architecture/workflow version (like old codebase)
    Uses semantic versioning (v1.0, v1.1, v2.0) instead of incremental numbers

    Only create new versions for TRULY significant architectural changes:
    - Major feature additions that change system architecture
    - Breaking changes that affect core components
    - Major refactoring of system structure
    - NOT for: bug fixes, minor features, documentation updates
    """
    versioning_decision = {
        "needs_new_architecture_version": False,
        "needs_new_workflow_version": False,
        "architecture_change_reason": "",
        "workflow_change_reason": ""
    }

    # STRICT criteria for architectural changes (only truly major changes)
    major_arch_indicators = [
        # Major system restructuring
        len(changed_files) > 50,  # Only very large changes
        # Core infrastructure changes
        any("migrate" in f.lower() for f in changed_files),
        any("refactor" in f.lower() for f in changed_files),
        any("restructure" in f.lower() for f in changed_files),
        # Major new features that change architecture
        analysis.get("type") == "breaking_change" and analysis.get(
            "significance", 0) >= 9,
        # Database schema changes (but not migrations)
        any("schema" in f.lower() and "migration" not in f.lower()
            for f in changed_files),
        # Major technology stack changes
        any("docker" in f.lower() and "compose" in f.lower()
            for f in changed_files),
        any("kubernetes" in f.lower() for f in changed_files),
        any("terraform" in f.lower() for f in changed_files),
    ]

    # STRICT criteria for workflow changes (only major process changes)
    major_workflow_indicators = [
        # CI/CD pipeline changes
        any("github" in f.lower() and "workflow" in f.lower()
            for f in changed_files),
        any("gitlab" in f.lower() and "ci" in f.lower()
            for f in changed_files),
        any("jenkins" in f.lower() for f in changed_files),
        # Deployment process changes
        any("deploy" in f.lower() and ("script" in f.lower()
            or "config" in f.lower()) for f in changed_files),
        # Major development process changes
        analysis.get("type") == "breaking_change" and "deployment" in analysis.get(
            "impact_scope", []),
        len(changed_files) > 40,  # Large changes to development files
    ]

    # Only create new version for TRULY major changes
    if any(major_arch_indicators) and analysis.get("significance", 0) >= 8:
        versioning_decision["needs_new_architecture_version"] = True
        versioning_decision["architecture_change_reason"] = (
            f"Major architectural evolution: {analysis.get('title', 'Unknown')}"
        )

    if any(major_workflow_indicators) and analysis.get("significance", 0) >= 8:
        versioning_decision["needs_new_workflow_version"] = True
        versioning_decision["workflow_change_reason"] = (
            f"Major workflow change: {analysis.get('title', 'Unknown')}"
        )

    return versioning_decision


# ============================================================================
# MAIN ORCHESTRATOR (ported from old codebase)
# ============================================================================

async def generate_comprehensive_documentation(
    repo_dir: Path,
    analysis: Dict[str, object],
    changed_files: List[str],
    doc_persona: str = "internal"
) -> None:
    """
    Generate comprehensive documentation for the repository (like old codebase)
    This is the main orchestrator function

    Args:
        repo_dir: Path to repository
        analysis: Change analysis dict
        changed_files: List of changed files
        doc_persona: Documentation persona (internal|developer)
    """
    # Create base docs directory
    base_docs_dir = Path(repo_dir) / "docs"
    base_docs_dir.mkdir(parents=True, exist_ok=True)

    # Create persona-specific docs directory
    docs_dir = base_docs_dir / doc_persona
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 Checking documentation quality...")
    changed_files = changed_files or []  # safety

    quality_report = check_documentation_quality(repo_dir)
    # ⭐ NEW: Log doc_persona being used
    print(f"📚 Generating docs with persona: {doc_persona}")

    quality_report = check_documentation_quality(repo_dir, doc_persona)

    print(f"📋 Quality Report: {json.dumps(quality_report, indent=2)}")

    # NEW: Check if architecture/workflow need new versions
    impact = analyze_architectural_impact(repo_dir, changed_files, analysis)
    print("🔎 Architectural Impact:", json.dumps(impact, indent=2))

    # Decide whether to generate docs
    if quality_report["needs_generation"] or impact["needs_new_architecture_version"] or impact["needs_new_workflow_version"]:
        # Phase 1: Create plan for structured guidance
        planner = get_planner()
        plan = planner.create_plan(analysis)
        print(
            f"📋 Documentation Plan: {plan.repo_type} (complexity: {plan.complexity_score}/10)")

        docs_result = await generate_all_docs_in_single_call(
            repo_dir,
            analysis,
            {"generated_at": datetime.utcnow().isoformat()},
            doc_persona,
            plan=plan  # Phase 1: Pass plan for structured prompting
        )
        # Handle both old (dict) and new (tuple) return formats
        if isinstance(docs_result, tuple):
            docs, token_data = docs_result
        else:
            docs = docs_result
            token_data = {}

        # Phase 2: Build document tree (non-breaking)
        doc_tree = build_document_tree(
            flat_docs=docs,
            repo_id=str(repo_dir.name),
            persona=doc_persona,
            plan=plan,
            model_name=token_data.get("model_name"),
            token_usage={
                "input_tokens": token_data.get("input_tokens", 0),
                "output_tokens": token_data.get("output_tokens", 0),
            },
        )
        if doc_tree:
            print(
                f"📄 Document tree created with {len(doc_tree.sections)} sections")
            docs["_document_tree"] = doc_tree
    else:
        print("Docs look good. Skipping generation.")
        return

    # Write SUMMARY.md
    (docs_dir / "SUMMARY.md").write_text(docs["summary"])

    # --- ARCHITECTURE ---
    arch_dir = docs_dir / "architecture"
    arch_dir.mkdir(exist_ok=True)
    (arch_dir / "current.md").write_text(docs["architecture"])

    if impact["needs_new_architecture_version"]:
        version = get_current_version(docs_dir, "architecture")
        (arch_dir /
         f"v{version}-architecture.md").write_text(docs["architecture"])
        print(f"📐 NEW architecture version: v{version}")
    else:
        print("📐 No major architecture change. No new version created.")

    # --- WORKFLOW ---
    workflow_dir = docs_dir / "workflow"
    workflow_dir.mkdir(exist_ok=True)
    (workflow_dir / "current.md").write_text(docs["workflow"])

    if impact["needs_new_workflow_version"]:
        version = get_current_version(docs_dir, "workflow")
        (workflow_dir / f"v{version}-workflow.md").write_text(docs["workflow"])
        print(f"🔁 NEW workflow version: v{version}")
    else:
        print("🔁 No major workflow change. No new version created.")

    # API
    (docs_dir / "api.md").write_text(docs["api"])

    update_summary_navigation(docs_dir)
    print("✅ Comprehensive documentation generation complete!")

# ============================================================================
# WORKFLOW AND API ANALYSIS (ported from old codebase)
# ============================================================================


def analyze_workflows(repo_dir: Path) -> Dict[str, object]:
    """Analyze development workflows (like old codebase)"""
    workflows = {
        "has_ci_cd": False,
        "ci_files": [],
        "scripts": []
    }

    # Check for CI/CD files
    ci_files = [".github/workflows",
                ".gitlab-ci.yml", "Jenkinsfile", ".circleci"]
    for ci_file in ci_files:
        if (Path(repo_dir) / ci_file).exists():
            workflows["has_ci_cd"] = True
            workflows["ci_files"].append(ci_file)

    # Check for scripts
    scripts_dir = Path(repo_dir) / "scripts"
    if scripts_dir.exists():
        workflows["scripts"] = [
            f.name for f in scripts_dir.iterdir() if f.is_file()]

    return workflows


def analyze_api_structure(repo_dir: Path) -> Dict[str, object]:
    """Analyze API structure (like old codebase)"""
    api_info = {
        "has_api": False,
        "api_files": [],
        "framework": None
    }

    # Detect API framework
    frameworks = {
        "FastAPI": ["from fastapi", "FastAPI()"],
        "Flask": ["from flask", "Flask(__name__)"],
        "Express": ["express()", "require('express')"],
        "Django": ["django", "urls.py"]
    }

    try:
        for framework, patterns in frameworks.items():
            for pattern in patterns:
                result = subprocess.run(
                    f"grep -r '{pattern}' . --include='*.py' --include='*.js' | head -1",
                    shell=True,
                    cwd=repo_dir,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    api_info["has_api"] = True
                    api_info["framework"] = framework
                    break
            if api_info["framework"]:
                break
    except Exception as e:
        logger.warning(f"API analysis error: {e}")

    return api_info


# ============================================================================
# SMART DOCUMENTATION GENERATOR (ported from old codebase)
# ============================================================================

async def generate_smart_documentation(
    repo_dir: Path,
    analysis: Dict[str, Any],
    commit_sha: str,
    ref: str,
    doc_persona: str = "internal"
) -> None:
    """
    Generate comprehensive documentation based on analysis (like old codebase)
    This is the main entry point that orchestrates everything

    Args:
        repo_dir: Path to repository
        analysis: Change analysis dict
        commit_sha: Commit SHA
        ref: Git ref (branch)
        doc_persona: Documentation persona (internal|developer)
    """
    from app.services.documentation.change_docs import (
        create_change_documentation,
        update_main_readme,
        update_changelog,
        create_migration_guide,
        update_summary_md,
    )

    # Create base docs directory
    base_docs_dir = Path(repo_dir) / "docs"
    base_docs_dir.mkdir(parents=True, exist_ok=True)

    # Create persona-specific docs directory
    docs_dir = base_docs_dir / doc_persona
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Changes directory is persona-specific
    changes_dir = docs_dir / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)

    # Check documentation quality and generate comprehensive docs if needed
    print(f"🔍 Checking documentation quality for persona: {doc_persona}...")
    changed_files = get_changed_files_from_analysis(analysis)
    await generate_comprehensive_documentation(repo_dir, analysis, changed_files, doc_persona)

    # 1. Create detailed change documentation
    create_change_documentation(changes_dir, analysis, commit_sha, ref)

    # 2. Update main README if needed
    if analysis.get("documentation_needs", {}).get("update_readme", False):
        update_main_readme(repo_dir, analysis)

    # 3. Update changelog
    if analysis.get("documentation_needs", {}).get("create_changelog", False):
        update_changelog(repo_dir, analysis, commit_sha)

    # 4. Create API documentation if needed
    if analysis.get("documentation_needs", {}).get("update_api_docs", False):
        # This is handled by generate_comprehensive_documentation, but we can add additional API docs here if needed
        pass

    # 5. Create migration guide for breaking changes
    if analysis.get("documentation_needs", {}).get("create_migration_guide", False):
        create_migration_guide(docs_dir, analysis)

    # 6. Update SUMMARY.md for GitBook navigation
    update_summary_md(docs_dir, analysis, commit_sha)


def get_changed_files_from_analysis(analysis: Dict[str, Any]) -> List[str]:
    """Extract changed files list from analysis (like old codebase)"""
    return analysis.get("affected_components", [])
