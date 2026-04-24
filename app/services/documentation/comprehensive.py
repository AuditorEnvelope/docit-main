"""
ComprehensiveDocBuilder - orchestrates the two-call LLM-first documentation pipeline.

The key change from the old system:
  OLD: Python code decides sections → LLM fills in templates
  NEW: LLM decides sections (planning call) → LLM writes them (generation call)

Everything else (file writing, SUMMARY.md, versioning) is unchanged.
"""

import json
import logging
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# The new aggregate_prompt replaces the old one completely
from app.services.documentation.aggregate_prompt import generate_all_docs_in_single_call
from app.services.documentation.planner import get_planner, DocumentationPlan
from app.services.documentation.tree_builder import build_document_tree, debug_tree_structure
from app.services.documentation.tree_models import DocumentTree
from app.services.extraction import build_semantic_snapshot

logger = logging.getLogger(__name__)


# ============================================================================
# SUMMARY NAVIGATION (unchanged)
# ============================================================================

def update_summary_navigation(docs_dir: Path) -> None:
    """Update SUMMARY.md with navigation links to all documentation sections."""
    print(f"📚 Updating SUMMARY.md navigation for: {docs_dir}")
    summary = ["# Summary", ""]

    if (docs_dir / "README.md").exists():
        summary.append("* [Project Overview](README.md)")

    skip_folders = {"changes", ".git", "__pycache__"}

    section_folders = []
    for item in sorted(docs_dir.iterdir()):
        if item.is_dir() and item.name not in skip_folders:
            if (item / "current.md").exists():
                section_folders.append(item.name)

    for section_name in section_folders:
        section_dir = docs_dir / section_name
        readable_title = section_name.replace(
            "-", " ").replace("_", " ").title()
        summary.append(f"\n## {readable_title}")
        summary.append(f"* [Current](/{section_name}/current.md)")
        version_files = sorted(
            section_dir.glob(f"v*-{section_name}.md"), reverse=True
        )[:5]
        for path in version_files:
            summary.append(
                f"* [{path.stem.upper()}]({section_name}/{path.name})")

    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary.append("\n## Recent Changes")
            for cf in change_files[:10]:
                title = cf.stem.split("-", 1)[-1].replace("-", " ").title()
                summary.append(f"* [{title}](changes/{cf.name})")

    persona = docs_dir.name
    if persona:
        summary.append(f"\n## Documentation Info")
        summary.append(f"* Persona: **{persona}**")
        summary.append(
            f"* Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    (docs_dir / "SUMMARY.md").write_text("\n".join(summary))
    print(f"✅ Updated SUMMARY.md for {docs_dir.name}")


def get_current_version(docs_dir: Path, doc_type: str) -> str:
    """Return the next semantic version string (e.g. '1.0', '1.1')."""
    version_dir = docs_dir / doc_type
    if not version_dir.exists():
        return "1.0"

    version_files = list(version_dir.glob("v*-*.md"))
    if not version_files:
        return "1.0"

    versions = []
    for vf in version_files:
        try:
            version_str = vf.stem.split("-")[0][1:]
            if "." in version_str:
                major, minor = version_str.split(".")
                versions.append((int(major), int(minor)))
            else:
                versions.append((int(version_str), 0))
        except Exception:
            continue

    if not versions:
        return "1.0"

    max_major, max_minor = max(versions)
    if max_minor >= 9:
        return f"{max_major + 1}.0"
    return f"{max_major}.{max_minor + 1}"


# ============================================================================
# SUPPORTED EXTENSIONS & IGNORED DIRECTORIES (unchanged)
# ============================================================================

SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx",
    ".js": "javascript", ".jsx": "jsx", ".go": "go",
    ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".swift": "swift", ".rb": "ruby", ".php": "php",
    ".cs": "csharp", ".cpp": "cpp", ".h": "c", ".c": "c",
}

IGNORED_DIRECTORIES = {
    ".git", "node_modules", "dist", "build", "__pycache__",
    "vendor", "env", "venv", "docbook", "docs", "coverage", "tmp",
}


# ============================================================================
# COMPREHENSIVE DOC BUILDER
# ============================================================================

@dataclass
class DocumentedFile:
    path: Path
    content: str


class ComprehensiveDocBuilder:
    """
    High-fidelity documentation generator.

    NEW PIPELINE:
      1. Analyse codebase (unchanged)
      2. Build semantic snapshot (unchanged)
      3. Two-call LLM-first generation (replaces old template fill)
      4. Write files (unchanged)
    """

    def __init__(
        self,
        repository_root: Path,
        doc_persona: str = "internal",
        repo_name: str = None,
    ) -> None:
        self.repository_root = repository_root
        self.doc_persona = doc_persona
        self.repo_name = repo_name or repository_root.name

    async def build(self) -> Dict[str, str]:
        print("=" * 80)
        print(
            f"📦 Starting comprehensive documentation build for {self.repo_name}")
        print(f"👤 Persona: {self.doc_persona}")
        print("=" * 80)

        # ── Codebase analysis ────────────────────────────────────────────────
        analysis = analyze_full_codebase(self.repository_root)

        if self.repo_name and not self.repo_name.startswith("docai"):
            clean_name = self.repo_name.split(
                "/")[-1] if "/" in self.repo_name else self.repo_name
            if not analysis.get("package_name"):
                analysis["project_name"] = clean_name

        print(f"📊 Codebase analysis complete:")
        print(f"   Languages: {analysis.get('languages', [])}")
        print(f"   Frameworks: {analysis.get('frameworks', [])}")
        print(f"   File count: {analysis.get('file_count', 0)}")

        recent_changes = {"generated_at": datetime.utcnow().isoformat()}
        docs_dir = self.repository_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # ── Semantic snapshot ────────────────────────────────────────────────
        print("🔎 Running semantic extractors...")
        semantic_snapshot = build_semantic_snapshot(
            repo_path=self.repository_root,
            repo_analysis=analysis,
        )
        print(f"📸 Semantic snapshot result:")
        print(f"   Primary framework: {semantic_snapshot.primary_framework}")
        print(f"   Primary language: {semantic_snapshot.primary_language}")
        print(f"   Signals: {len(semantic_snapshot.signals)}")

        # ── LLM-first two-call generation ────────────────────────────────────
        # The planner is still used for the plan object (needed by tree_builder)
        # but it no longer drives section names.
        planner = get_planner()
        plan = planner.create_dynamic_plan(
            analysis,
            semantic_snapshot=semantic_snapshot.to_dict(),
            persona=self.doc_persona,
        )

        docs, token_data = await generate_all_docs_in_single_call(
            self.repository_root,
            analysis,
            recent_changes,
            self.doc_persona,
            plan=plan,
            repo_name=self.repo_name,
        )

        # Attach semantic snapshot for internal use
        docs["_semantic_snapshot"] = semantic_snapshot.to_dict()

        # The plan returned from generate_all_docs_in_single_call is the LLM-planned one;
        # keep it but add metadata from the structural planner.
        if "plan" not in docs or not docs["plan"].get("sections"):
            docs["plan"] = {
                "repo_type": plan.repo_type,
                "complexity_score": plan.complexity_score,
                "sections": [
                    {"id": s.id, "title": s.title, "type": s.type,
                        "required": s.required, "priority": s.priority}
                    for s in plan.sections
                ],
            }
        else:
            docs["plan"]["repo_type"] = plan.repo_type
            docs["plan"]["complexity_score"] = plan.complexity_score

        docs["token_data"] = token_data
        print(
            f"📊 Token Usage: {token_data['input_tokens']} in / {token_data['output_tokens']} out | Model: {token_data['model_name']}")

        # ── Document tree (Phase 2 – non-breaking) ───────────────────────────
        doc_tree = build_document_tree(
            flat_docs=docs,
            repo_id=self.repo_name,
            persona=self.doc_persona,
            plan=plan,
            commit_sha=recent_changes.get("generated_at"),
            model_name=token_data.get("model_name"),
            token_usage={
                "input_tokens": token_data.get("input_tokens", 0),
                "output_tokens": token_data.get("output_tokens", 0),
            },
        )
        if doc_tree:
            print("\n" + "=" * 60)
            print(debug_tree_structure(doc_tree))
            print("=" * 60 + "\n")
            docs["_document_tree"] = doc_tree

        # ── Write documentation files ─────────────────────────────────────────
        print(
            f"📝 Writing sections: {[k for k in docs.keys() if not k.startswith('_') and k not in ('plan', 'token_data')]}")

        # Write SUMMARY / overview
        summary_content = docs.get("overview") or docs.get("summary", "")
        if summary_content:
            (docs_dir / "SUMMARY.md").write_text(summary_content)

        # Write planned sections using their LLM-chosen IDs
        planned_sections = docs.get("plan", {}).get("sections", [])
        written_sections: List[str] = []

        for section_info in planned_sections:
            section_id = section_info.get("id", "")
            section_title = section_info.get("title", section_id)
            content = docs.get(section_id, "")

            if content:
                section_dir = docs_dir / section_id
                section_dir.mkdir(exist_ok=True)
                (section_dir / "current.md").write_text(content)
                version = get_current_version(docs_dir, section_id)
                (section_dir /
                 f"v{version}-{section_id}.md").write_text(content)
                print(f"   📄 {section_title}: v{version}")
                written_sections.append(section_id)
            else:
                print(f"   ⚠️  {section_title}: no content generated")

        # Fallback: write any remaining well-known section keys not already written
        fallback_keys = ["architecture", "workflow", "api",
                         "components", "dependencies", "deployment"]
        for key in fallback_keys:
            if key not in written_sections:
                content = docs.get(key, "")
                if content:
                    section_dir = docs_dir / key
                    section_dir.mkdir(exist_ok=True)
                    (section_dir / "current.md").write_text(content)
                    version = get_current_version(docs_dir, key)
                    (section_dir / f"v{version}-{key}.md").write_text(content)
                    print(f"   📄 {key}: v{version} [fallback]")
                    written_sections.append(key)

        # Changes folder
        (docs_dir / "changes").mkdir(exist_ok=True)

        # Root SUMMARY
        update_summary_navigation(docs_dir)

        # Root README / CHANGELOG
        if summary_content:
            (self.repository_root / "README.md").write_text(summary_content)

        changelog = (
            "# Changelog\n\n"
            "## [1.0.0] - Auto-generated documentation\n\n"
            "### Added\n"
            "- Comprehensive documentation set generated by Pustak AI\n"
            "- Repository-specific sections based on actual codebase analysis\n"
            "- Updated README summary\n"
        )
        (self.repository_root / "CHANGELOG.md").write_text(changelog)

        print("✅ Comprehensive documentation build complete!")
        return docs

    # ------------------------------------------------------------------
    # Helpers (unchanged)
    # ------------------------------------------------------------------

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
                if any(p.name in IGNORED_DIRECTORIES for p in path.parents):
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


# ============================================================================
# ALL CODEBASE ANALYSIS FUNCTIONS (unchanged from original)
# ============================================================================

def check_documentation_quality(repo_dir: Path, doc_persona: str = "internal") -> Dict[str, object]:
    docs_dir = Path(repo_dir) / "docs" / doc_persona
    quality_report = {
        "summary_exists": False, "summary_quality": 0,
        "architecture_exists": False, "architecture_quality": 0,
        "workflow_exists": False, "workflow_quality": 0,
        "api_exists": False, "api_quality": 0,
        "needs_generation": [],
    }

    for summary_file in [docs_dir / "SUMMARY.md", docs_dir / "README.md", Path(repo_dir) / "README.md"]:
        if summary_file.exists():
            quality_report["summary_exists"] = True
            quality_report["summary_quality"] = assess_content_quality(
                summary_file.read_text(), "summary")
            break

    for arch_file in [docs_dir / "architecture.md", docs_dir / "architecture" / "current.md"]:
        if arch_file.exists():
            quality_report["architecture_exists"] = True
            quality_report["architecture_quality"] = assess_content_quality(
                arch_file.read_text(), "architecture")
            break

    for wf_file in [docs_dir / "workflow.md", docs_dir / "workflow" / "current.md"]:
        if wf_file.exists():
            quality_report["workflow_exists"] = True
            quality_report["workflow_quality"] = assess_content_quality(
                wf_file.read_text(), "workflow")
            break

    for api_file in [docs_dir / "api.md", docs_dir / "api" / "README.md"]:
        if api_file.exists():
            quality_report["api_exists"] = True
            quality_report["api_quality"] = assess_content_quality(
                api_file.read_text(), "api")
            break

    for key in ["summary", "architecture", "workflow", "api"]:
        if not quality_report[f"{key}_exists"] or quality_report[f"{key}_quality"] < 8:
            quality_report["needs_generation"].append(key)

    return quality_report


def assess_content_quality(content: str, doc_type: str) -> float:
    if len(content.strip()) < 100:
        return 2.0
    score = 5.0
    if "##" in content or "# " in content:
        score += 1.0
    if "```" in content:
        score += 1.0
    if "- " in content or "* " in content or "1. " in content:
        score += 1.0
    if len(content) > 1000:
        score += 1.0
    if len(content) > 3000:
        score += 1.0
    return score


def detect_repo_structure(repo_dir: Path) -> Dict[str, Any]:
    """Adaptively detect repository structure."""
    result = {"type": "single", "subprojects": [],
              "root_config": None, "detected_structure": ""}

    skip_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
        ".idea", ".vscode", "dist", "build", "target", "coverage",
        ".next", ".nuxt", "out", "docs", ".cache", "tmp", "temp",
        "vendor", "bower_components", ".gradle", ".mvn",
    }

    for config_file in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml"]:
        if (repo_dir / config_file).exists():
            result["root_config"] = repo_dir / config_file
            break

    discovered_projects = []
    for item in repo_dir.iterdir():
        if not item.is_dir() or item.name.startswith(".") or item.name.lower() in skip_dirs:
            continue
        project_info = _analyze_directory_type(item)
        if project_info["is_project"]:
            discovered_projects.append({
                "name": item.name, "path": item,
                "type": project_info["type"], "tech_stack": project_info["tech_stack"],
                "confidence": project_info["confidence"],
            })
            tech_str = ", ".join(project_info["tech_stack"].get(
                "frameworks", [])) or project_info["type"]
            print(
                f"   📂 Found {item.name}/ → {project_info['type']} ({tech_str})")

    root_analysis = _analyze_directory_type(repo_dir)

    if len(discovered_projects) >= 2:
        result["type"] = "monorepo"
        result["subprojects"] = discovered_projects
        types = [p["type"] for p in discovered_projects]
        has_backend = any(t in ["backend", "api", "service"] for t in types)
        has_frontend = any(t in ["frontend", "web", "ui", "app"]
                           for t in types)
        result["detected_structure"] = "fullstack" if (
            has_backend and has_frontend) else "multi-project"
        print(
            f"   📦 Detected: MULTI-PROJECT REPO with {len(discovered_projects)} subprojects")
    elif len(discovered_projects) == 1 and root_analysis["is_project"]:
        result["type"] = "monorepo"
        result["subprojects"] = discovered_projects
        result["detected_structure"] = "hybrid"
    else:
        result["type"] = "single"
        result["detected_structure"] = "single"
        print(f"   📦 Detected: SINGLE PROJECT")

    return result


def _analyze_directory_type(folder: Path) -> Dict[str, Any]:
    result = {
        "is_project": False, "type": "unknown",
        "tech_stack": {"languages": [], "frameworks": [], "databases": [], "tools": []},
        "confidence": 0.0,
    }
    signals = {"frontend": 0, "backend": 0, "library": 0,
               "mobile": 0, "devops": 0, "data": 0}

    project_indicators = [
        "package.json", "pyproject.toml", "requirements.txt", "setup.py",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Gemfile",
        "composer.json", "mix.exs", "pubspec.yaml",
    ]
    has_project_file = any((folder / ind).exists()
                           for ind in project_indicators)
    if not has_project_file:
        source_extensions = {".py", ".ts", ".tsx",
                             ".js", ".jsx", ".go", ".rs", ".java", ".rb"}
        source_count = sum(1 for _ in folder.rglob(
            "*") if _.suffix in source_extensions)
        if source_count < 3:
            return result

    pkg_json = folder / "package.json"
    if pkg_json.exists():
        try:
            import json as _json
            pkg_data = _json.loads(pkg_json.read_text())
            deps = {**pkg_data.get("dependencies", {}),
                    **pkg_data.get("devDependencies", {})}
            dep_names = set(deps.keys())

            frontend_frameworks = {
                "react": "React", "react-dom": "React", "vue": "Vue", "next": "Next.js",
                "svelte": "Svelte", "@sveltejs/kit": "SvelteKit", "gatsby": "Gatsby",
                "@angular/core": "Angular", "solid-js": "Solid",
            }
            backend_frameworks = {
                "express": "Express", "fastify": "Fastify", "koa": "Koa",
                "@nestjs/core": "NestJS", "hapi": "Hapi",
            }
            mobile_frameworks = {
                "react-native": "React Native", "expo": "Expo"}

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

            if "typescript" in dep_names or (folder / "tsconfig.json").exists():
                result["tech_stack"]["languages"].append("TypeScript")
            else:
                result["tech_stack"]["languages"].append("JavaScript")
        except Exception:
            pass

    if (folder / "pyproject.toml").exists() or (folder / "requirements.txt").exists():
        result["tech_stack"]["languages"].append("Python")
        py_content = ""
        try:
            py_content = (folder / "requirements.txt").read_text() if (folder /
                                                                       "requirements.txt").exists() else ""
            py_content += (folder / "pyproject.toml").read_text() if (folder /
                                                                      "pyproject.toml").exists() else ""
        except Exception:
            pass
        python_backend = {"fastapi": "FastAPI", "django": "Django",
                          "flask": "Flask", "aiohttp": "aiohttp"}
        for dep, name in python_backend.items():
            if dep in py_content.lower():
                signals["backend"] += 5
                result["tech_stack"]["frameworks"].append(name)

    if (folder / "go.mod").exists():
        result["tech_stack"]["languages"].append("Go")
        signals["backend"] += 3

    dir_signals = {
        "components": ("frontend", 3), "pages": ("frontend", 3), "views": ("frontend", 2),
        "routes": ("backend", 3), "controllers": ("backend", 3), "handlers": ("backend", 3),
        "api": ("backend", 2), "services": ("backend", 2), "models": ("backend", 2),
        "terraform": ("devops", 5), "k8s": ("devops", 5), "kubernetes": ("devops", 5),
    }
    for subdir in folder.iterdir():
        if subdir.is_dir() and subdir.name.lower() in dir_signals:
            category, score = dir_signals[subdir.name.lower()]
            signals[category] += score

    file_signals = {
        "Dockerfile": ("devops", 2), "docker-compose.yml": ("devops", 3),
        "main.py": ("backend", 2), "server.py": ("backend", 3), "server.ts": ("backend", 3),
        "index.html": ("frontend", 2), "App.tsx": ("frontend", 3), "App.jsx": ("frontend", 3),
    }
    for filename, (category, score) in file_signals.items():
        if (folder / filename).exists():
            signals[category] += score

    max_signal = max(signals.values())
    if max_signal < 3:
        return result

    result["is_project"] = True
    result["confidence"] = min(1.0, max_signal / 15)

    type_mapping = {
        "frontend": "frontend", "backend": "backend", "mobile": "mobile",
        "devops": "devops", "data": "data", "library": "library",
    }
    dominant = max(signals, key=signals.get)
    result["type"] = type_mapping.get(dominant, "unknown")
    result["tech_stack"]["frameworks"] = list(
        set(result["tech_stack"]["frameworks"]))
    result["tech_stack"]["languages"] = list(
        set(result["tech_stack"]["languages"]))
    return result


def analyze_subproject(subproject_path: Path, subproject_name: str, subproject_type: str) -> Dict[str, object]:
    print(f"   📂 Analyzing subproject: {subproject_name} ({subproject_type})")
    analysis = {"subproject_name": subproject_name,
                "subproject_type": subproject_type, "subproject_path": str(subproject_path)}
    sub_analysis = _analyze_single_project(subproject_path)
    analysis.update(sub_analysis)
    return analysis


def _analyze_single_project(repo_dir: Path) -> Dict[str, object]:
    analysis: Dict[str, object] = {
        "project_name": Path(repo_dir).name,
        "file_count": 0, "languages": [], "main_directories": [],
        "dependencies": {}, "imports": {}, "frameworks": [],
        "database_tech": [], "deployment_tech": [],
    }
    try:
        analysis["file_count"] = int(
            subprocess.run("find . -type f | wc -l", shell=True,
                           cwd=repo_dir, capture_output=True, text=True).stdout.strip()
        )
        for ext in [".py", ".ts", ".js", ".go", ".java", ".rs", ".cpp", ".c", ".php", ".rb"]:
            count = int(
                subprocess.run(f"find . -name '*{ext}' | wc -l", shell=True,
                               cwd=repo_dir, capture_output=True, text=True).stdout.strip()
            )
            if count:
                analysis["languages"].append(ext[1:])

        dirs = subprocess.run(
            "find . -maxdepth 2 -type d | head -20", shell=True, cwd=repo_dir, capture_output=True, text=True
        ).stdout.strip()
        analysis["main_directories"] = dirs.split("\n")

        if "py" in analysis["languages"]:
            _analyze_python_dependencies(repo_dir, analysis)
        if "js" in analysis["languages"] or "ts" in analysis["languages"]:
            _analyze_js_dependencies(repo_dir, analysis)
            _analyze_js_source_files(repo_dir, analysis)

        _detect_technologies(repo_dir, analysis)
    except Exception as exc:
        logger.warning("Single project scan failed: %s", exc)
    return analysis


def analyze_full_codebase(repo_dir: Path) -> Dict[str, object]:
    print(f"📊 Starting codebase analysis for: {repo_dir}")
    repo_structure = detect_repo_structure(repo_dir)

    if repo_structure["type"] == "monorepo" and repo_structure["subprojects"]:
        print(
            f"   📦 Monorepo detected with {len(repo_structure['subprojects'])} subprojects")
        analysis = _analyze_single_project(repo_dir)
        analysis["repo_structure"] = "monorepo"
        analysis["subprojects"] = {}

        for subproject in repo_structure["subprojects"]:
            sub_name = subproject["name"]
            sub_analysis = analyze_subproject(
                subproject["path"], sub_name, subproject["type"])
            analysis["subprojects"][sub_name] = sub_analysis

            for lang in sub_analysis.get("languages", []):
                if lang not in analysis["languages"]:
                    analysis["languages"].append(lang)
            for fw in sub_analysis.get("frameworks", []):
                if fw not in analysis["frameworks"]:
                    analysis["frameworks"].append(fw)
            for dep, ver in sub_analysis.get("dependencies", {}).items():
                analysis["dependencies"][f"{sub_name}/{dep}"] = ver
            if "source_files" not in analysis:
                analysis["source_files"] = []
            for sf in sub_analysis.get("source_files", []):
                analysis["source_files"].append(f"{sub_name}/{sf}")

        # Detected structure for the plan
        detected = repo_structure.get("detected_structure", "")
        sub_types = {s["type"] for s in repo_structure["subprojects"]}
        has_fe = any(t in ["frontend", "web", "ui", "app"] for t in sub_types)
        has_be = any(t in ["backend", "api", "service"] for t in sub_types)
        if has_fe and has_be:
            print(f"   🎯 Detected FULLSTACK from subprojects: {sub_types}")

        return analysis
    else:
        print(f"   📦 Single project detected")
        analysis = _analyze_single_project(repo_dir)
        analysis["repo_structure"] = "single"
        return analysis


def _analyze_js_source_files(repo_dir: Path, analysis: Dict[str, object]) -> None:
    print(f"   _analyze_js_source_files called with repo_dir: {repo_dir}")
    try:
        source_files, component_files, page_files, hook_files, util_files, api_files = [
        ], [], [], [], [], []

        possible_src_dirs = ["src", "app", "pages",
                             "components", "lib", "utils", "hooks", "api"]
        search_dirs = []
        for d in possible_src_dirs:
            dp = repo_dir / d
            if dp.exists() and dp.is_dir():
                search_dirs.append(dp)

        if not search_dirs:
            print("   No standard source directories found, searching root...")
        search_dirs.insert(0, repo_dir)

        all_items = list(repo_dir.iterdir())
        print(f"   Items in root: {[i.name for i in all_items[:20]]}")

        for item in all_items:
            if item.is_dir() and not item.name.startswith(".") and item.name not in ["node_modules", "docs"]:
                sub_items = list(item.iterdir())[:5]
                print(
                    f"   Found directory: {item.name}/  Contents: {[i.name for i in sub_items]}")

        for search_dir in search_dirs:
            for ext in ["*.tsx", "*.ts", "*.jsx", "*.js"]:
                for file_path in search_dir.rglob(ext):
                    if "node_modules" in str(file_path) or file_path.name.startswith("."):
                        continue
                    if file_path.name.endswith(".d.ts"):
                        continue
                    if "/docs/" in str(file_path):
                        continue
                    rel = str(file_path.relative_to(repo_dir))
                    if rel in source_files:
                        continue
                    source_files.append(rel)
                    lp, ln = rel.lower(), file_path.stem.lower()
                    if file_path.stem in ["next.config", "tailwind.config", "tsconfig", "vite.config"]:
                        pass
                    elif "component" in lp:
                        component_files.append(file_path.stem)
                    elif "page" in ln or "layout" in ln or "pages/" in lp:
                        page_files.append(rel)
                    elif "hook" in lp or ln.startswith("use"):
                        hook_files.append(file_path.stem)
                    elif "util" in lp or "lib" in lp:
                        util_files.append(file_path.stem)
                    elif "/api/" in lp:
                        api_files.append(rel)

        analysis.update({
            "source_files": source_files[:50],
            "component_files": component_files[:20],
            "page_files": page_files[:20],
            "hook_files": hook_files[:10],
            "util_files": util_files[:10],
            "api_files": api_files[:10],
            "total_components": len(component_files),
            "total_pages": len(page_files),
            "total_hooks": len(hook_files),
            "total_source_files": len(source_files),
            "root_directories": [i.name for i in repo_dir.iterdir() if i.is_dir() and not i.name.startswith(".") and i.name not in ["node_modules", "docs"]],
        })

        print(f"   📁 Source files found: {len(source_files)}")
        if source_files:
            print(f"   📄 Sample source files: {source_files[:5]}")
    except Exception as e:
        logger.warning("JS source file analysis failed: %s", e)


def _analyze_js_dependencies(repo_dir: Path, analysis: Dict[str, object]) -> None:
    import json as _json
    try:
        pkg = repo_dir / "package.json"
        if not pkg.exists():
            return
        data = _json.loads(pkg.read_text())
        deps = {**data.get("dependencies", {}), **
                data.get("devDependencies", {})}
        analysis["dependencies"] = deps
        analysis["scripts"] = data.get("scripts", {})

        framework_indicators = {
            "React": ["react", "react-dom"], "Next.js": ["next"], "Vue": ["vue"],
            "Angular": ["@angular/core"], "Svelte": ["svelte"], "Express": ["express"],
            "Fastify": ["fastify"], "NestJS": ["@nestjs/core"], "Redux": ["redux", "@reduxjs/toolkit"],
            "Zustand": ["zustand"], "Tailwind CSS": ["tailwindcss"],
            "TypeScript": ["typescript"], "Vite": ["vite"],
        }
        detected = []
        for fw, indicators in framework_indicators.items():
            if any(i in deps for i in indicators):
                detected.append(fw)
        analysis["frameworks"] = detected

        state_libs = []
        for lib, indicators in {"Redux": ["redux", "@reduxjs/toolkit"], "Zustand": ["zustand"], "MobX": ["mobx"]}.items():
            if any(i in deps for i in indicators):
                state_libs.append(lib)
        analysis["state_management"] = state_libs
        analysis["package_name"] = data.get("name", "")
        analysis["package_version"] = data.get("version", "")
        analysis["package_description"] = data.get("description", "")
    except Exception as e:
        logger.warning("JS dep analysis failed: %s", e)


def _analyze_python_dependencies(repo_dir: Path, analysis: Dict[str, object]) -> None:
    imports: Dict[str, int] = {}
    frameworks: List[str] = []
    try:
        for py_file in repo_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith(("import ", "from ")):
                        module = line.split(" ")[1].split(".")[0]
                        if module not in {"os", "sys", "json", "time", "datetime", "typing", "pathlib", "logging"}:
                            imports[module] = imports.get(module, 0) + 1
            except Exception:
                continue

        framework_indicators = {
            "FastAPI": ["fastapi"], "Django": ["django"], "Flask": ["flask"],
            "SQLAlchemy": ["sqlalchemy"], "Pydantic": ["pydantic"],
        }
        for fw, indicators in framework_indicators.items():
            if any(i in str(imports) for i in indicators):
                frameworks.append(fw)

        analysis["imports"] = dict(
            sorted(imports.items(), key=lambda x: x[1], reverse=True)[:10])
        analysis["frameworks"] = frameworks
    except Exception as e:
        logger.warning("Python analysis failed: %s", e)


def _detect_technologies(repo_dir: Path, analysis: Dict[str, object]) -> None:
    content = ""
    for file_path in repo_dir.rglob("*"):
        try:
            if file_path.is_file() and file_path.suffix in {".py", ".js", ".ts", ".yaml", ".yml", ".json", ".md"}:
                content += file_path.read_text().lower()
        except Exception:
            continue

    db_indicators = {
        "PostgreSQL": ["postgresql", "postgres", "psycopg"],
        "MySQL": ["mysql", "pymysql"], "SQLite": ["sqlite"],
        "MongoDB": ["mongodb", "pymongo"], "Redis": ["redis"],
    }
    for db, indicators in db_indicators.items():
        if any(i in content for i in indicators):
            analysis["database_tech"].append(db)

    deploy_indicators = {
        "Docker": ["docker", "dockerfile"], "Kubernetes": ["kubernetes", "k8s"],
        "AWS": ["aws", "boto3"], "Vercel": ["vercel"], "Netlify": ["netlify"],
    }
    for deploy, indicators in deploy_indicators.items():
        if any(i in content for i in indicators):
            analysis["deployment_tech"].append(deploy)


# ── Keep all the rest of the helper functions unchanged ────────────────────
# (analyze_components, detect_design_patterns, analyze_architecture,
#  analyze_architectural_impact, generate_comprehensive_documentation,
#  analyze_workflows, analyze_api_structure, generate_smart_documentation,
#  get_changed_files_from_analysis)
# They are not involved in the generation pipeline but are imported elsewhere.

def analyze_components(repo_dir: Path) -> Dict[str, object]:
    components = {"detected": [], "services": [],
                  "utilities": [], "models": [], "handlers": []}
    try:
        search_dirs = [repo_dir / "src", repo_dir / "app"]
        search_dirs = [d for d in search_dirs if d.exists()] or [repo_dir]
        for search_dir in search_dirs:
            for py_file in search_dir.rglob("*.py"):
                try:
                    filename = py_file.stem.lower()
                    content = py_file.read_text()
                    if "service" in filename:
                        components["services"].append(
                            {"name": py_file.stem, "path": str(py_file.relative_to(repo_dir))})
                    elif "handler" in filename:
                        components["handlers"].append(
                            {"name": py_file.stem, "path": str(py_file.relative_to(repo_dir))})
                    elif ("model" in filename or "schema" in filename) and "class" in content:
                        components["models"].append(
                            {"name": py_file.stem, "path": str(py_file.relative_to(repo_dir))})
                except Exception:
                    continue
        if not components["detected"]:
            components["detected"] = ["core", "api", "database"]
    except Exception as e:
        logger.warning("Component analysis failed: %s", e)
    return components


def detect_design_patterns(repo_dir: Path) -> List[str]:
    patterns: List[str] = []
    try:
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
    except Exception as e:
        logger.warning("Design pattern detection failed: %s", e)
    return patterns or ["Object-Oriented Design"]


def analyze_architecture(repo_dir: Path) -> Dict[str, object]:
    return {
        "components": analyze_components(repo_dir),
        "structure": analyze_full_codebase(repo_dir),
        "patterns": detect_design_patterns(repo_dir),
    }


def analyze_architectural_impact(repo_dir: Path, changed_files: List[str], analysis: Dict[str, object]) -> Dict[str, object]:
    return {
        "needs_new_architecture_version": False,
        "needs_new_workflow_version": False,
        "architecture_change_reason": "",
        "workflow_change_reason": "",
    }


async def generate_comprehensive_documentation(repo_dir, analysis, changed_files, doc_persona="internal"):
    pass


def analyze_workflows(repo_dir: Path) -> Dict[str, object]:
    workflows = {"has_ci_cd": False, "ci_files": [], "scripts": []}
    for ci_file in [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile"]:
        if (Path(repo_dir) / ci_file).exists():
            workflows["has_ci_cd"] = True
            workflows["ci_files"].append(ci_file)
    return workflows


def analyze_api_structure(repo_dir: Path) -> Dict[str, object]:
    return {"has_api": False, "api_files": [], "framework": None}


async def generate_smart_documentation(repo_dir, analysis, commit_sha, ref, doc_persona="internal"):
    pass


def get_changed_files_from_analysis(analysis: Dict[str, Any]) -> List[str]:
    return analysis.get("affected_components", [])
