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
    """
    Update SUMMARY.md with navigation links to all documentation sections.

    DYNAMIC: Discovers all section folders instead of hardcoding names.
    This supports meaningful folder names like 'component-hierarchy', 'state-management'.
    """
    print(f"📚 Updating SUMMARY.md navigation for: {docs_dir}")
    summary = ["# Summary", ""]

    # Add overview link - prefer README.md for content
    if (docs_dir / "README.md").exists():
        summary.append("* [Project Overview](README.md)")
        print("   Added: Project Overview link (README.md)")

    # ============================================================
    # DYNAMIC SECTION DISCOVERY
    # Finds ALL folders with current.md and adds them to navigation
    # ============================================================

    # Folders to skip in navigation
    skip_folders = {"changes", ".git", "__pycache__"}

    # Discover all section folders dynamically
    section_folders = []
    for item in sorted(docs_dir.iterdir()):
        if item.is_dir() and item.name not in skip_folders:
            if (item / "current.md").exists():
                section_folders.append(item.name)

    # Add each discovered section
    for section_name in section_folders:
        section_dir = docs_dir / section_name

        # Convert folder name to readable title
        # e.g., "component-hierarchy" -> "Component Hierarchy"
        readable_title = section_name.replace(
            "-", " ").replace("_", " ").title()

        summary.append(f"\n## {readable_title}")
        summary.append(f"* [Current](/{section_name}/current.md)")
        print(f"   Added: {readable_title} section")

        # Add version history (newest first, max 5)
        version_files = sorted(section_dir.glob(
            f"v*-{section_name}.md"), reverse=True)[:5]
        for path in version_files:
            summary.append(
                f"* [{path.stem.upper()}]({section_name}/{path.name})")

    # Add changes (show only last 10 changes to avoid clutter)
    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary.append("\n## Recent Changes")
            for change_file in change_files[:10]:  # Latest 10 only
                title = change_file.stem.split(
                    "-", 1)[-1].replace("-", " ").title()
                summary.append(f"* [{title}](changes/{change_file.name})")

    # Add persona information if available
    persona = ""
    if "internal" in str(docs_dir) or "dev" in str(docs_dir):
        persona = docs_dir.name
    if persona:
        summary.append(f"\n## Documentation Info")
        summary.append(f"* Persona: **{persona}**")
        summary.append(
            f"* Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    (docs_dir / "SUMMARY.md").write_text("\n".join(summary))
    print(f"✅ Updated SUMMARY.md for {docs_dir.name}")


@dataclass
class DocumentedFile:
    path: Path
    content: str


class ComprehensiveDocBuilder:
    """High-fidelity documentation generator (legacy comprehensive flow)."""

    def __init__(self, repository_root: Path, doc_persona: str = "internal", repo_name: str = None) -> None:
        self.repository_root = repository_root
        self.doc_persona = doc_persona
        # Use provided repo_name or fall back to directory name
        self.repo_name = repo_name or repository_root.name

    async def build(self) -> Dict[str, str]:
        """
        Build comprehensive documentation.

        Phase 1 Enhancement: Uses DocumentationPlanner for structured guidance.
        Phase 6 Enhancement: Captures token usage and stores in 'token_data' key.
        """
        print("================================================================================")
        print(
            f"📦 Starting comprehensive documentation build for {self.repo_name}")
        print(f"👤 Persona: {self.doc_persona}")
        print("================================================================================")

        analysis = analyze_full_codebase(self.repository_root)
        
        # Override project_name with actual repo name (not temp directory)
        # Priority: package_name from package.json > repo_name > directory name
        if self.repo_name and not self.repo_name.startswith("docai"):
            clean_name = self.repo_name.split("/")[-1] if "/" in self.repo_name else self.repo_name
            if not analysis.get("package_name"):
                analysis["project_name"] = clean_name
        
        print(f"📊 Codebase analysis complete:")
        print(f"   Languages: {analysis.get('languages', [])}")
        print(f"   Frameworks: {analysis.get('frameworks', [])}")
        print(f"   File count: {analysis.get('file_count', 0)}")
        print(f"   Analysis keys: {list(analysis.keys())}")
        recent_changes = {"generated_at": datetime.utcnow().isoformat()}

        docs_dir = self.repository_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Phase 3: Build semantic snapshot for enhanced planning
        print("🔎 Running semantic extractors...")
        semantic_snapshot = build_semantic_snapshot(
            repo_path=self.repository_root,
            repo_analysis=analysis,
        )
        print(f"📸 Semantic snapshot result:")
        print(f"   Primary framework: {semantic_snapshot.primary_framework}")
        print(f"   Primary language: {semantic_snapshot.primary_language}")
        print(f"   Detected routes: {len(semantic_snapshot.detected_routes)}")
        print(f"   Signals: {len(semantic_snapshot.signals)}")
        print(f"   Extraction errors: {semantic_snapshot.extraction_errors}")

        # Phase 1: Create documentation plan for structured guidance
        # Phase 3: Pass semantic snapshot for enhanced planning
        # NEW: Use persona-aware dynamic planning
        planner = get_planner()
        plan = planner.create_dynamic_plan(
            analysis,
            semantic_snapshot=semantic_snapshot.to_dict(),
            persona=self.doc_persona
        )
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
            plan=plan,  # Phase 1: Pass plan to guide generation
            repo_name=self.repo_name  # Pass actual repo name
        )

        # Attach semantic snapshot to docs for internal use (must be after docs is created)
        docs["_semantic_snapshot"] = semantic_snapshot.to_dict()

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
            repo_id=self.repo_name,  # Use actual repo name, not temp directory
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
        # WRITE DOCUMENTS TO FILES (Dynamic Sections)
        # -----------------------------
        # Debug: Log all keys in docs
        print(f"📝 Generated sections: {list(docs.keys())}")

        # Write README/summary (always in root)
        summary_content = docs.get("overview") or docs.get("summary", "")
        if summary_content:
            (docs_dir / "SUMMARY.md").write_text(summary_content)
            print(f"   Summary: {len(summary_content)} chars")

        # Write each section from the plan using meaningful folder names
        # The plan now has meaningful section IDs (slugified titles)
        written_sections = []
        for section in plan.sections:
            section_id = section.id  # e.g., "component-hierarchy" or "state-management"
            section_content = docs.get(section_id, "")

            # Try alternate keys if the meaningful key doesn't match
            if not section_content:
                # Try original section type as fallback
                section_content = docs.get(section.type, "")

            if section_content:
                section_dir = docs_dir / section_id
                section_dir.mkdir(exist_ok=True)
                (section_dir / "current.md").write_text(section_content)
                version = get_current_version(docs_dir, section_id)
                (section_dir /
                 f"v{version}-{section_id}.md").write_text(section_content)
                print(
                    f"   ✅ Written: {section_id}/current.md ({len(section_content)} chars)")
                written_sections.append(section_id)

        # Fallback: Write any remaining sections not in the plan (backward compatibility)
        fallback_sections = ["architecture", "workflow",
                             "api", "components", "dependencies", "deployment"]
        for fallback_key in fallback_sections:
            if fallback_key not in written_sections:
                content = docs.get(fallback_key, "")
                if content:
                    section_dir = docs_dir / fallback_key
                    section_dir.mkdir(exist_ok=True)
                    (section_dir / "current.md").write_text(content)
                    version = get_current_version(docs_dir, fallback_key)
                    (section_dir /
                     f"v{version}-{fallback_key}.md").write_text(content)
                    print(
                        f"   ✅ Written: {fallback_key}/current.md ({len(content)} chars) [fallback]")
                    written_sections.append(fallback_key)

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


# ============================================================================
# ADAPTIVE REPO STRUCTURE DETECTION
# No hardcoded patterns - analyzes ANY repo structure intelligently
# ============================================================================

def detect_repo_structure(repo_dir: Path) -> Dict[str, Any]:
    """
    Adaptively detect repository structure - works with ANY folder organization.

    Instead of hardcoded patterns (backend/, frontend/, apps/), this function:
    1. Scans ALL top-level directories
    2. Analyzes each directory's contents to determine its purpose
    3. Scores directories based on file types, dependencies, and code patterns
    4. Automatically detects multi-project repos regardless of folder names

    Returns:
        {
            "type": "monorepo" | "single",
            "subprojects": [{"name": str, "path": Path, "type": str, "tech_stack": dict}],
            "root_config": Path | None,
            "detected_structure": str  # Description of what was found
        }
    """
    print(f"🔍 Detecting repository structure for: {repo_dir}")

    result = {
        "type": "single",
        "subprojects": [],
        "root_config": None,
        "detected_structure": "",
    }

    # Directories to skip during analysis
    skip_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
        ".idea", ".vscode", "dist", "build", "target", "coverage",
        ".next", ".nuxt", "out", "docs", ".cache", "tmp", "temp",
        "vendor", "bower_components", ".gradle", ".mvn"
    }

    # Find root config file
    for config_file in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"]:
        if (repo_dir / config_file).exists():
            result["root_config"] = repo_dir / config_file
            break

    # Scan ALL top-level directories and analyze each one
    discovered_projects = []

    for item in repo_dir.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        if item.name.lower() in skip_dirs:
            continue

        # Analyze this directory
        project_info = _analyze_directory_type(item)

        if project_info["is_project"]:
            discovered_projects.append({
                "name": item.name,
                "path": item,
                "type": project_info["type"],
                "tech_stack": project_info["tech_stack"],
                "confidence": project_info["confidence"],
            })
            tech_str = ", ".join(project_info["tech_stack"].get(
                "frameworks", [])) or project_info["type"]
            print(
                f"   📂 Found {item.name}/ → {project_info['type']} ({tech_str})")

    # Also check if root itself is a project (single project repo)
    root_analysis = _analyze_directory_type(repo_dir)

    # Determine repo structure
    if len(discovered_projects) >= 2:
        # Multiple subprojects = multi-project repo
        result["type"] = "monorepo"
        result["subprojects"] = discovered_projects

        # Describe what we found
        types = [p["type"] for p in discovered_projects]
        has_backend = any(t in ["backend", "api", "service"] for t in types)
        has_frontend = any(t in ["frontend", "web", "ui", "app"]
                           for t in types)

        if has_backend and has_frontend:
            result["detected_structure"] = "fullstack"
        else:
            result["detected_structure"] = "multi-project"

        print(
            f"   📦 Detected: MULTI-PROJECT REPO with {len(discovered_projects)} subprojects")

    elif len(discovered_projects) == 1 and root_analysis["is_project"]:
        # One subproject + root is also a project
        result["type"] = "monorepo"
        result["subprojects"] = discovered_projects
        # Also add root as implicit project if it has different tech
        if root_analysis["type"] != discovered_projects[0]["type"]:
            result["subprojects"].insert(0, {
                "name": "root",
                "path": repo_dir,
                "type": root_analysis["type"],
                "tech_stack": root_analysis["tech_stack"],
                "confidence": root_analysis["confidence"],
            })
        result["detected_structure"] = "hybrid"
        print(f"   📦 Detected: HYBRID REPO")

    else:
        result["type"] = "single"
        result["detected_structure"] = "single"
        print(f"   📦 Detected: SINGLE PROJECT")

    return result


def _analyze_directory_type(folder: Path) -> Dict[str, Any]:
    """
    Analyze a directory to determine what kind of project it contains.

    Returns detailed analysis including:
    - is_project: bool (is this a standalone project?)
    - type: str (backend, frontend, library, service, tool, etc.)
    - tech_stack: dict (languages, frameworks, databases, etc.)
    - confidence: float (0-1 how confident we are)
    """
    result = {
        "is_project": False,
        "type": "unknown",
        "tech_stack": {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": [],
        },
        "confidence": 0.0,
    }

    # Signals we'll collect
    signals = {
        "frontend": 0,
        "backend": 0,
        "library": 0,
        "mobile": 0,
        "devops": 0,
        "data": 0,
    }

    # Check for project indicator files (any of these = likely a project)
    project_indicators = [
        "package.json", "pyproject.toml", "requirements.txt", "setup.py",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Gemfile",
        "composer.json", "mix.exs", "pubspec.yaml", "CMakeLists.txt"
    ]

    has_project_file = False
    for indicator in project_indicators:
        if (folder / indicator).exists():
            has_project_file = True
            break

    if not has_project_file:
        # Check if there are significant source files even without config
        source_extensions = {".py", ".ts", ".tsx",
                             ".js", ".jsx", ".go", ".rs", ".java", ".rb"}
        source_count = sum(1 for _ in folder.rglob(
            "*") if _.suffix in source_extensions)
        if source_count < 3:
            return result  # Not enough to be a project

    # Analyze package.json for JS/TS projects
    pkg_json = folder / "package.json"
    if pkg_json.exists():
        try:
            import json
            with open(pkg_json) as f:
                pkg_data = json.load(f)

            deps = {**pkg_data.get("dependencies", {}),
                    **pkg_data.get("devDependencies", {})}
            dep_names = set(deps.keys())

            # Frontend frameworks
            frontend_frameworks = {
                "react": "React", "react-dom": "React", "@types/react": "React",
                "vue": "Vue", "nuxt": "Nuxt", "@vue/cli": "Vue",
                "angular": "Angular", "@angular/core": "Angular",
                "svelte": "Svelte", "@sveltejs/kit": "SvelteKit",
                "next": "Next.js", "gatsby": "Gatsby",
                "solid-js": "Solid", "preact": "Preact",
            }

            # Backend frameworks
            backend_frameworks = {
                "express": "Express", "fastify": "Fastify", "koa": "Koa",
                "@nestjs/core": "NestJS", "nest": "NestJS", "hapi": "Hapi",
                "restify": "Restify", "strapi": "Strapi", "adonis": "AdonisJS",
            }

            # Mobile frameworks
            mobile_frameworks = {
                "react-native": "React Native", "expo": "Expo",
                "@capacitor/core": "Capacitor", "cordova": "Cordova",
            }

            for dep, name in frontend_frameworks.items():
                if dep in dep_names:
                    signals["frontend"] += 5
                    result["tech_stack"]["frameworks"].append(name)

            for dep, name in backend_frameworks.items():
                if dep in dep_names:
                    signals["backend"] += 5
                    result["tech_stack"]["frameworks"].append(name)

            for dep, name in mobile_frameworks.items():
                if dep in dep_names:
                    signals["mobile"] += 5
                    result["tech_stack"]["frameworks"].append(name)

            # Check for TypeScript
            if "typescript" in dep_names or (folder / "tsconfig.json").exists():
                result["tech_stack"]["languages"].append("TypeScript")
            else:
                result["tech_stack"]["languages"].append("JavaScript")

        except Exception:
            pass

    # Analyze Python projects
    pyproject = folder / "pyproject.toml"
    requirements = folder / "requirements.txt"

    if pyproject.exists() or requirements.exists():
        result["tech_stack"]["languages"].append("Python")

        # Read dependencies
        py_deps = set()
        if requirements.exists():
            try:
                content = requirements.read_text()
                for line in content.split("\n"):
                    line = line.strip().split("==")[0].split(">=")[
                        0].split("<=")[0]
                    if line and not line.startswith("#"):
                        py_deps.add(line.lower())
            except:
                pass

        if pyproject.exists():
            try:
                content = pyproject.read_text()
                # Simple extraction of dependencies
                if "fastapi" in content.lower():
                    py_deps.add("fastapi")
                if "django" in content.lower():
                    py_deps.add("django")
                if "flask" in content.lower():
                    py_deps.add("flask")
            except:
                pass

        # Python frameworks
        python_backend = {
            "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
            "starlette": "Starlette", "tornado": "Tornado", "aiohttp": "aiohttp",
            "sanic": "Sanic", "falcon": "Falcon",
        }
        python_data = {
            "pandas": "Pandas", "numpy": "NumPy", "scipy": "SciPy",
            "tensorflow": "TensorFlow", "torch": "PyTorch", "keras": "Keras",
            "scikit-learn": "scikit-learn",
        }

        for dep, name in python_backend.items():
            if dep in py_deps:
                signals["backend"] += 5
                result["tech_stack"]["frameworks"].append(name)

        for dep, name in python_data.items():
            if dep in py_deps:
                signals["data"] += 5
                result["tech_stack"]["frameworks"].append(name)

    # Analyze Go projects
    if (folder / "go.mod").exists():
        result["tech_stack"]["languages"].append("Go")
        signals["backend"] += 3

        try:
            content = (folder / "go.mod").read_text()
            if "gin-gonic" in content:
                result["tech_stack"]["frameworks"].append("Gin")
                signals["backend"] += 3
            if "echo" in content:
                result["tech_stack"]["frameworks"].append("Echo")
                signals["backend"] += 3
            if "fiber" in content:
                result["tech_stack"]["frameworks"].append("Fiber")
                signals["backend"] += 3
        except:
            pass

    # Analyze Rust projects
    if (folder / "Cargo.toml").exists():
        result["tech_stack"]["languages"].append("Rust")
        signals["backend"] += 2

        try:
            content = (folder / "Cargo.toml").read_text()
            if "actix" in content:
                result["tech_stack"]["frameworks"].append("Actix")
                signals["backend"] += 3
            if "rocket" in content:
                result["tech_stack"]["frameworks"].append("Rocket")
                signals["backend"] += 3
            if "axum" in content:
                result["tech_stack"]["frameworks"].append("Axum")
                signals["backend"] += 3
        except:
            pass

    # Directory-based signals (adaptive)
    dir_signals = {
        # Frontend signals
        "components": ("frontend", 3),
        "pages": ("frontend", 3),
        "views": ("frontend", 2),
        "styles": ("frontend", 2),
        "css": ("frontend", 2),
        "assets": ("frontend", 1),
        "public": ("frontend", 1),
        # Backend signals
        "routes": ("backend", 3),
        "controllers": ("backend", 3),
        "handlers": ("backend", 3),
        "api": ("backend", 2),
        "services": ("backend", 2),
        "models": ("backend", 2),
        "middleware": ("backend", 2),
        "migrations": ("backend", 2),
        # DevOps signals
        "terraform": ("devops", 5),
        "k8s": ("devops", 5),
        "kubernetes": ("devops", 5),
        "helm": ("devops", 4),
        "ansible": ("devops", 4),
        "docker": ("devops", 2),
        # Data signals
        "notebooks": ("data", 4),
        "data": ("data", 2),
        "models": ("data", 1),  # Can also be backend
    }

    for subdir in folder.iterdir():
        if subdir.is_dir() and subdir.name.lower() in dir_signals:
            category, score = dir_signals[subdir.name.lower()]
            signals[category] += score

    # File-based signals
    file_signals = {
        "Dockerfile": ("devops", 2),
        "docker-compose.yml": ("devops", 3),
        "docker-compose.yaml": ("devops", 3),
        ".dockerignore": ("devops", 1),
        "Makefile": ("backend", 1),
        "main.py": ("backend", 2),
        "app.py": ("backend", 2),
        "server.py": ("backend", 3),
        "server.ts": ("backend", 3),
        "server.js": ("backend", 3),
        "index.html": ("frontend", 2),
        "App.tsx": ("frontend", 3),
        "App.jsx": ("frontend", 3),
        "App.vue": ("frontend", 3),
    }

    for filename, (category, score) in file_signals.items():
        if (folder / filename).exists():
            signals[category] += score

    # Determine the dominant type
    max_signal = max(signals.values())
    if max_signal < 3:
        return result  # Not confident enough

    result["is_project"] = True
    result["confidence"] = min(1.0, max_signal / 15)

    # Map signals to types
    type_mapping = {
        "frontend": ["frontend", "web", "ui"],
        "backend": ["backend", "api", "service"],
        "mobile": ["mobile", "app"],
        "devops": ["devops", "infrastructure"],
        "data": ["data", "ml", "analytics"],
        "library": ["library", "package"],
    }

    dominant_category = max(signals, key=signals.get)
    result["type"] = type_mapping.get(dominant_category, ["unknown"])[0]

    # Deduplicate frameworks
    result["tech_stack"]["frameworks"] = list(
        set(result["tech_stack"]["frameworks"]))
    result["tech_stack"]["languages"] = list(
        set(result["tech_stack"]["languages"]))

    return result


def analyze_subproject(subproject_path: Path, subproject_name: str, subproject_type: str) -> Dict[str, object]:
    """
    Analyze a single subproject within a monorepo.

    Returns analysis specific to that subproject.
    """
    print(f"   📂 Analyzing subproject: {subproject_name} ({subproject_type})")

    # Run full analysis on the subproject directory
    analysis = {
        "subproject_name": subproject_name,
        "subproject_type": subproject_type,
        "subproject_path": str(subproject_path),
    }

    # Merge with full codebase analysis of that directory
    sub_analysis = _analyze_single_project(subproject_path)
    analysis.update(sub_analysis)

    return analysis


def _analyze_single_project(repo_dir: Path) -> Dict[str, object]:
    """
    Analyze a single project directory (used for both root and subprojects).
    This is the core analysis logic extracted for reuse.
    """
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

        # Analyze Python dependencies and imports
        if "py" in analysis["languages"]:
            _analyze_python_dependencies(repo_dir, analysis)

        # Analyze JavaScript/TypeScript dependencies
        if "js" in analysis["languages"] or "ts" in analysis["languages"]:
            _analyze_js_dependencies(repo_dir, analysis)
            _analyze_js_source_files(repo_dir, analysis)

        # Detect technologies
        _detect_technologies(repo_dir, analysis)

    except Exception as exc:
        logger.warning("Single project scan failed: %s", exc)

    return analysis


def analyze_full_codebase(repo_dir: Path) -> Dict[str, object]:
    """
    Analyze the entire codebase structure with detailed insights.

    Supports both single projects and monorepos:
    - For single projects: Standard analysis
    - For monorepos: Analyzes each subproject and merges results
    """
    print(f"📊 Starting codebase analysis for: {repo_dir}")

    # Detect repo structure first
    repo_structure = detect_repo_structure(repo_dir)

    if repo_structure["type"] == "monorepo" and repo_structure["subprojects"]:
        # MONOREPO: Analyze each subproject
        print(
            f"   📦 Monorepo detected with {len(repo_structure['subprojects'])} subprojects")

        # Start with root-level analysis
        analysis = _analyze_single_project(repo_dir)
        analysis["repo_structure"] = "monorepo"
        analysis["subprojects"] = {}

        # Analyze each subproject
        for subproject in repo_structure["subprojects"]:
            sub_name = subproject["name"]
            sub_path = subproject["path"]
            sub_type = subproject["type"]

            sub_analysis = analyze_subproject(sub_path, sub_name, sub_type)
            analysis["subprojects"][sub_name] = sub_analysis

            # Merge key data into root analysis
            # Languages
            for lang in sub_analysis.get("languages", []):
                if lang not in analysis["languages"]:
                    analysis["languages"].append(lang)

            # Frameworks
            for fw in sub_analysis.get("frameworks", []):
                if fw not in analysis["frameworks"]:
                    analysis["frameworks"].append(fw)

            # Dependencies (prefix with subproject name)
            for dep, version in sub_analysis.get("dependencies", {}).items():
                analysis["dependencies"][f"{sub_name}/{dep}"] = version

            # Source files (prefix with subproject name)
            for sf in sub_analysis.get("source_files", []):
                prefixed_file = f"{sub_name}/{sf}"
                if "source_files" not in analysis:
                    analysis["source_files"] = []
                analysis["source_files"].append(prefixed_file)

        print(
            f"   ✅ Monorepo analysis complete: {len(analysis['subprojects'])} subprojects")
        return analysis
    else:
        # SINGLE PROJECT: Standard analysis
        print(f"   📦 Single project detected")
        analysis = _analyze_single_project(repo_dir)
        analysis["repo_structure"] = "single"
        return analysis


def _analyze_js_source_files(repo_dir: Path, analysis: Dict[str, object]) -> None:
    """Analyze actual source files in JS/TS projects for concrete documentation."""
    print(f"   _analyze_js_source_files called with repo_dir: {repo_dir}")
    try:
        source_files = []
        component_files = []
        page_files = []
        hook_files = []
        util_files = []
        api_files = []
        style_files = []
        config_files = []

        # Find source directories - check multiple common patterns
        possible_src_dirs = ["src", "app", "pages",
                             "components", "lib", "utils", "hooks", "api"]
        search_dirs = []

        print(f"   Checking for source directories in {repo_dir}...")
        for dir_name in possible_src_dirs:
            dir_path = repo_dir / dir_name
            print(
                f"   Checking {dir_name}/: exists={dir_path.exists()}, is_dir={dir_path.is_dir() if dir_path.exists() else 'N/A'}")
            if dir_path.exists() and dir_path.is_dir():
                search_dirs.append(dir_path)
                print(f"   Found source directory: {dir_name}/")

        # Also search root directory for immediate files
        if not search_dirs:
            print("   No standard source directories found, searching root...")

        # Always include root for config files and flat structures
        search_dirs.insert(0, repo_dir)

        # First, let's see what's actually in the repo
        print(f"   Listing all files in repo root...")
        all_items = list(repo_dir.iterdir())
        print(f"   Items in root: {[item.name for item in all_items[:20]]}")

        # Check for nested directories
        for item in all_items:
            if item.is_dir() and not item.name.startswith(".") and item.name not in ["node_modules", "docs"]:
                print(f"   Found directory: {item.name}/")
                # Check what's inside
                sub_items = list(item.iterdir())[:5]
                print(f"      Contents: {[i.name for i in sub_items]}")

        # Collect files by type
        for search_dir in search_dirs:
            for ext in ["*.tsx", "*.ts", "*.jsx", "*.js"]:
                for file_path in search_dir.rglob(ext):
                    # Skip node_modules and hidden files
                    if "node_modules" in str(file_path) or file_path.name.startswith("."):
                        continue
                    if file_path.name.endswith(".d.ts"):
                        continue
                    # Skip files in docs directory
                    if "/docs/" in str(file_path) or "\\docs\\" in str(file_path):
                        continue

                    relative_path = str(file_path.relative_to(repo_dir))
                    file_name = file_path.stem

                    # Avoid duplicates
                    if relative_path in source_files:
                        continue

                    source_files.append(relative_path)

                    # Categorize by location/name
                    lower_path = relative_path.lower()
                    lower_name = file_name.lower()

                    # Config files
                    if file_name in ["next.config", "tailwind.config", "tsconfig", "vite.config", "webpack.config"]:
                        config_files.append(file_name + file_path.suffix)
                    # Components
                    elif "component" in lower_path or "components" in lower_path:
                        component_files.append(file_name)
                    # Pages/App routes
                    elif "page" in lower_name or "layout" in lower_name or "pages/" in lower_path:
                        page_files.append(relative_path)
                    # Hooks
                    elif "hook" in lower_path or lower_name.startswith("use"):
                        hook_files.append(file_name)
                    # Utils/Libs
                    elif "util" in lower_path or "utils" in lower_path or "lib" in lower_path:
                        util_files.append(file_name)
                    # API routes
                    elif "/api/" in lower_path:
                        api_files.append(relative_path)

        # Also find style files
        for search_dir in search_dirs:
            for ext in ["*.css", "*.scss", "*.sass"]:
                for file_path in search_dir.rglob(ext):
                    if "node_modules" in str(file_path):
                        continue
                    relative_path = str(file_path.relative_to(repo_dir))
                    style_files.append(relative_path)

        # Store in analysis
        analysis["source_files"] = source_files[:50]  # Limit to 50 files
        analysis["component_files"] = component_files[:20]  # Limit to 20
        analysis["page_files"] = page_files[:20]
        analysis["hook_files"] = hook_files[:10]
        analysis["util_files"] = util_files[:10]
        analysis["api_files"] = api_files[:10]
        analysis["style_files"] = style_files[:10]
        analysis["config_files"] = config_files[:10]

        # Count totals
        analysis["total_components"] = len(component_files)
        analysis["total_pages"] = len(page_files)
        analysis["total_hooks"] = len(hook_files)
        analysis["total_source_files"] = len(source_files)

        # Log what was found
        print(f"   📁 Source files found: {len(source_files)}")
        print(f"   📦 Components: {len(component_files)}")
        print(f"   📄 Pages: {len(page_files)}")
        print(f"   🪝 Hooks: {len(hook_files)}")

        # Analyze directory structure
        dir_structure = []
        for item in repo_dir.iterdir():
            if item.is_dir() and not item.name.startswith(".") and item.name not in ["node_modules", "docs"]:
                dir_structure.append(item.name)
        analysis["root_directories"] = dir_structure
        print(f"   📂 Root directories: {dir_structure}")

        # Also print what files ARE being found
        if source_files:
            print(f"   📄 Sample source files: {source_files[:5]}")

    except Exception as e:
        logger.warning("JS source file analysis failed: %s", e)
        import traceback
        traceback.print_exc()


def _analyze_js_dependencies(repo_dir: Path, analysis: Dict[str, object]) -> None:
    """Analyze JavaScript/TypeScript dependencies from package.json"""
    import json

    try:
        package_json_path = repo_dir / "package.json"
        if not package_json_path.exists():
            return

        content = package_json_path.read_text()
        package_data = json.loads(content)

        dependencies = package_data.get("dependencies", {})
        dev_dependencies = package_data.get("devDependencies", {})
        scripts = package_data.get("scripts", {})

        # Combine all dependencies
        all_deps = {**dependencies, **dev_dependencies}
        analysis["dependencies"] = all_deps
        analysis["scripts"] = scripts

        # Detect frameworks based on dependencies
        framework_indicators = {
            "React": ["react", "react-dom"],
            "Next.js": ["next"],
            "Vue": ["vue"],
            "Angular": ["@angular/core"],
            "Svelte": ["svelte"],
            "Express": ["express"],
            "Fastify": ["fastify"],
            "NestJS": ["@nestjs/core"],
            "Redux": ["redux", "@reduxjs/toolkit"],
            "Zustand": ["zustand"],
            "MobX": ["mobx"],
            "React Router": ["react-router", "react-router-dom"],
            "Tailwind CSS": ["tailwindcss"],
            "Material-UI": ["@mui/material", "@material-ui/core"],
            "Chakra UI": ["@chakra-ui/react"],
            "Ant Design": ["antd"],
            "Styled Components": ["styled-components"],
            "TypeScript": ["typescript"],
            "Jest": ["jest"],
            "Vitest": ["vitest"],
            "Cypress": ["cypress"],
            "Playwright": ["@playwright/test"],
            "Vite": ["vite"],
            "Webpack": ["webpack"],
            "ESLint": ["eslint"],
            "Prettier": ["prettier"],
        }

        detected_frameworks = []
        for framework, indicators in framework_indicators.items():
            if any(indicator in all_deps for indicator in indicators):
                detected_frameworks.append(framework)

        analysis["frameworks"] = detected_frameworks

        # Detect state management
        state_libs = []
        if "redux" in all_deps or "@reduxjs/toolkit" in all_deps:
            state_libs.append("Redux")
        if "zustand" in all_deps:
            state_libs.append("Zustand")
        if "mobx" in all_deps:
            state_libs.append("MobX")
        if "recoil" in all_deps:
            state_libs.append("Recoil")
        if "jotai" in all_deps:
            state_libs.append("Jotai")
        analysis["state_management"] = state_libs

        # Store package.json metadata
        analysis["package_name"] = package_data.get("name", "")
        analysis["package_version"] = package_data.get("version", "")
        analysis["package_description"] = package_data.get("description", "")

    except Exception as e:
        logger.warning("JavaScript dependency analysis failed: %s", e)


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
