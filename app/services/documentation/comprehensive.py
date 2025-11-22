import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.services.llm.rotator import get_rotator

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
    """Builds a comprehensive set of documentation for a repository."""

    def __init__(self, repo_dir: Path, doc_persona: str = "internal") -> None:
        self.repo_dir = repo_dir
        self.repository_root = repo_dir  # FIX: Add missing instance variable
        self.doc_persona = doc_persona
        self.recent_changes: List[Dict[str, Any]] = []  # FIX: Add missing instance variable

    async def build(self, analysis: Dict[str, Any], docs_to_update: Dict[str, bool]) -> Dict[str, str]:
        print("=" * 80)
        print(f"📦 Starting comprehensive documentation build for {self.repo_dir.name}")
        print(f"👤 Persona: {self.doc_persona}")
        print(f"📋 Smart generation plan: {', '.join(k for k, v in docs_to_update.items() if v)}")
        print("=" * 80)

        docs_dir = self.repo_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        docs: Dict[str, str] = {}

        if docs_to_update.get("summary"):
            docs["summary"] = await self._generate_summary(analysis)
            (docs_dir / "SUMMARY.md").write_text(docs["summary"], encoding="utf-8")

        if docs_to_update.get("architecture"):
            docs["architecture"] = await self._generate_architecture(analysis)

        if docs_to_update.get("workflow"):
            docs["workflow"] = await self._generate_workflow(analysis)

        if docs_to_update.get("api"):
            docs["api"] = await self._generate_api_documentation(analysis)
            (docs_dir / "api.md").write_text(docs["api"], encoding="utf-8")
            
        if docs:
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

    async def _generate_summary(self, analysis: Dict[str, Any]) -> str:
        prompt = (
            "You are DocAI, an expert technical writer analyzing THIS SPECIFIC REPOSITORY.\n\n"
            f"Persona: {self.doc_persona}\n"
            f"Repository: {self.repo_dir.name}\n\n"
            f"ACTUAL CODEBASE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\n"
            f"RECENT CHANGES:\n{json.dumps(self.recent_changes, indent=2)}\n\n"
            "Generate a comprehensive README that includes overview, architecture, getting started, usage, project structure,"
            " API overview, development workflow, and key dependencies."
        )
        rotator = await get_rotator()
        return await rotator.generate_with_rotation(prompt) or ""

    async def _generate_architecture(self, analysis: Dict[str, Any]) -> str:
        """Generate versioned architecture documentation"""
        docs_dir = self.repo_dir / "docs"
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)
        version = get_current_version(docs_dir, "architecture")

        # Analyze architecture components
        arch_analysis = analyze_architecture(self.repo_dir)
        
        # Build detailed architecture prompt
        arch_prompt = f"""
You are DocAI, an expert system architect analyzing THIS SPECIFIC CODEBASE.

VERSION: v{version}
REASON FOR NEW VERSION: Initial documentation

ACTUAL CODEBASE ANALYSIS (USE THIS DATA ONLY):
{json.dumps(arch_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(self.recent_changes, indent=2)}

CRITICAL INSTRUCTIONS:
1. ONLY document what EXISTS in the codebase analysis above
2. DO NOT invent components that don't exist
3. DO NOT use generic examples (no "Frontend", "API Gateway" unless they actually exist)
4. USE the actual file names, classes, and functions from the analysis
5. If you see FastAPI in the analysis, document FastAPI (not Flask/Express)
6. If you see PostgreSQL, document PostgreSQL (not MySQL/MongoDB)
7. Reference actual imports like {', '.join(list(arch_analysis.get('structure', {}).get('imports', {}).keys())[:5]) if arch_analysis.get('structure', {}).get('imports') else 'N/A'}
8. Document actual frameworks found: {', '.join(arch_analysis.get('structure', {}).get('frameworks', [])) or 'None detected'}
9. Include actual database technologies: {', '.join(arch_analysis.get('structure', {}).get('database_tech', [])) or 'None detected'}
10. Mention deployment methods: {', '.join(arch_analysis.get('structure', {}).get('deployment_tech', [])) or 'None detected'}

Create documentation based ONLY on the actual codebase:

# Architecture v{version}

## System Overview
[Create ASCII diagram showing ACTUAL components from the analysis - use real file/service names]

## Actual Components Found
[Document the services, handlers, models, and utilities that actually exist in the codebase]

### Services
{chr(10).join(f"- {svc['name']}: {svc['description']} (Path: {svc['path']})" for svc in arch_analysis.get('components', {}).get('services', [])) if arch_analysis.get('components', {}).get('services') else "- No services detected"}

### Handlers
{chr(10).join(f"- {hdl['name']}: {hdl['description']} (Path: {hdl['path']})" for hdl in arch_analysis.get('components', {}).get('handlers', [])) if arch_analysis.get('components', {}).get('handlers') else "- No handlers detected"}

### Models/Schemas
{chr(10).join(f"- {mdl['name']}: {mdl['description']} (Path: {mdl['path']})" for mdl in arch_analysis.get('components', {}).get('models', [])) if arch_analysis.get('components', {}).get('models') else "- No models detected"}

### Utilities
{chr(10).join(f"- {util['name']}: {util['description']} (Path: {util['path']})" for util in arch_analysis.get('components', {}).get('utilities', [])) if arch_analysis.get('components', {}).get('utilities') else "- No utilities detected"}

## Actual Technology Stack
### Core Technologies
- Languages: {', '.join(arch_analysis.get('structure', {}).get('languages', [])) or 'Not detected'}
- Frameworks: {', '.join(arch_analysis.get('structure', {}).get('frameworks', [])) or 'None detected'}
- Database: {', '.join(arch_analysis.get('structure', {}).get('database_tech', [])) or 'None detected'}
- Deployment: {', '.join(arch_analysis.get('structure', {}).get('deployment_tech', [])) or 'None detected'}

### Key Dependencies
{chr(10).join(f"- {dep}: Used {count} times across the codebase" for dep, count in list(arch_analysis.get('structure', {}).get('imports', {}).items())[:8]) if arch_analysis.get('structure', {}).get('imports') else "- No key dependencies detected"}

## Design Patterns Detected
[Document the actual patterns found in the code analysis]
{chr(10).join(f"- {pattern}" for pattern in arch_analysis.get('patterns', [])) if arch_analysis.get('patterns') else "- No specific design patterns detected"}

## Current Architecture
[Describe how the ACTUAL system works based on the real code structure, imports, and dependencies]

## Data Flow
[Explain how data flows between the actual components found in the analysis]

## Recent Changes Impact
[Explain how the recent changes affect this specific architecture version based on the actual changes]

BE SPECIFIC. USE ONLY THE DATA FROM THE ANALYSIS. NO GENERIC TEMPLATES.
"""
        
        print(f"🔄 Generating architecture v{version} with LLM...")
        rotator = await get_rotator()
        arch_content = await rotator.generate_with_rotation(arch_prompt)

        if not arch_content or len(arch_content.strip()) < 100:
            print("❌ LLM returned insufficient content for architecture")
            arch_content = f"# Architecture v{version}\n\nArchitecture documentation generation failed. Please review the codebase manually."

        # Save versioned file
        arch_file = arch_dir / f"v{version}-architecture.md"
        arch_file.write_text(arch_content, encoding="utf-8")
        print(f"✅ Created {arch_file}")

        # Also create/update current.md
        current_file = arch_dir / "current.md"
        current_file.write_text(arch_content, encoding="utf-8")
        print(f"✅ Updated {current_file}")

        return arch_content

    async def _generate_workflow(self, analysis: Dict[str, Any]) -> str:
        docs_dir = self.repo_dir / "docs"
        workflow_dir = docs_dir / "workflow"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        version = get_current_version(docs_dir, "workflow")

        prompt = (
            "You are DocAI, an expert process analyst documenting ACTUAL workflows.\n\n"
            f"Persona: {self.doc_persona}\n"
            f"Repository: {self.repo_dir.name}\n"
            f"VERSION: v{version}\n"
            f"CODE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n"
            f"RECENT CHANGES:\n{json.dumps(self.recent_changes, indent=2)}\n"
            "Cover development workflow, CI/CD, deployments, release process, and monitoring."
        )
        rotator = await get_rotator()
        content = await rotator.generate_with_rotation(prompt)
        if content:
            (workflow_dir / f"v{version}-workflow.md").write_text(content, encoding="utf-8")
            (workflow_dir / "current.md").write_text(content, encoding="utf-8")
        return content or ""

    async def _generate_api_documentation(self, analysis: Dict[str, Any]) -> str:
        docs_dir = self.repo_dir / "docs"
        prompt = (
            "You are DocAI, an expert API writer documenting REAL endpoints from this repository.\n\n"
            f"Persona: {self.doc_persona}\n"
            f"Repository: {self.repo_dir.name}\n"
            f"CODE ANALYSIS:\n{json.dumps(analysis, indent=2)}\n"
            f"RECENT CHANGES:\n{json.dumps(self.recent_changes, indent=2)}\n"
            "Provide endpoint summaries, request/response examples, authentication, rate limits, and SDK guidance."
        )
        rotator = await get_rotator()
        content = await rotator.generate_with_rotation(prompt)
        if content:
            (docs_dir / "api.md").write_text(content, encoding="utf-8")
        return content or ""


def get_current_version(docs_dir: Path, doc_type: str) -> str:
    """
    Get the current version number using semantic versioning (v1.0, v1.1, v2.0)
    Returns the next version number to create
    """
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
    else:
        return f"{max_major}.{max_minor + 1}"


def analyze_full_codebase(repo_dir: Path) -> Dict[str, Any]:
    """Analyze the entire codebase structure with detailed insights"""
    analysis: Dict[str, Any] = {
        "project_name": repo_dir.name,
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
        file_count = 0
        lang_counts = {ext: 0 for ext in [".py", ".ts", ".js", ".go", ".java", ".rs", ".cpp", ".c", ".php", ".rb"]}
        main_dirs = set()

        for p in repo_dir.rglob("*"):
            if p.is_dir():
                if any(parent.name in IGNORED_DIRECTORIES for parent in p.parents) or p.name in IGNORED_DIRECTORIES:
                    continue
                if len(p.relative_to(repo_dir).parts) <= 2:
                    main_dirs.add(str(p.relative_to(repo_dir)))
            elif p.is_file():
                file_count += 1
                if p.suffix in lang_counts:
                    lang_counts[p.suffix] += 1

        analysis["file_count"] = file_count
        analysis["languages"] = [ext[1:] for ext, count in lang_counts.items() if count > 0]
        analysis["main_directories"] = sorted(list(main_dirs))[:20]
        
        # Analyze Python dependencies and imports
        if "py" in analysis["languages"]:
            _analyze_python_dependencies(repo_dir, analysis)
        
        # Detect technologies
        _detect_technologies(repo_dir, analysis)
        
    except Exception as exc:
        logger.warning("Codebase scan failed: %s", exc)
    
    return analysis


def _analyze_python_dependencies(repo_dir: Path, analysis: Dict[str, Any]) -> None:
    """Analyze Python imports and dependencies"""
    imports: Dict[str, int] = {}
    frameworks: List[str] = []
    
    try:
        for py_file in repo_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')):
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
        
        analysis["imports"] = dict(sorted(imports.items(), key=lambda x: x[1], reverse=True)[:10])
        analysis["frameworks"] = frameworks
        
    except Exception as e:
        logger.warning("Python analysis failed: %s", e)


def _detect_technologies(repo_dir: Path, analysis: Dict[str, Any]) -> None:
    """Detect technologies and deployment methods"""
    content = ""
    for file_path in repo_dir.rglob("*"):
        try:
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.yaml', '.yml', '.json', '.md']:
                content += file_path.read_text().lower()
        except Exception:
            continue
    
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
            if db not in analysis["database_tech"]:
                analysis["database_tech"].append(db)
    
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
            if deploy not in analysis["deployment_tech"]:
                analysis["deployment_tech"].append(deploy)


def analyze_components(repo_dir: Path) -> Dict[str, Any]:
    """Analyze system components based on actual codebase structure"""
    components: Dict[str, Any] = {
        "detected": [],
        "services": [],
        "utilities": [],
        "models": [],
        "handlers": []
    }
    
    try:
        src_dir = repo_dir / "src"
        app_dir = repo_dir / "app"
        search_dirs = [src_dir, app_dir] if app_dir.exists() else [src_dir] if src_dir.exists() else [repo_dir]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
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
        
        main_patterns = {
            "api": ["fastapi", "flask", "app.py", "main.py"],
            "database": ["database", "db", "postgres", "sqlite", "model"],
            "frontend": ["static", "templates", "public", "web", "ui"],
            "core": ["core", "engine", "manager", "processor"]
        }
        
        for component_type, patterns in main_patterns.items():
            if any(pattern in str(f) for f in repo_dir.rglob("*") if f.is_file()):
                if component_type not in components["detected"]:
                    components["detected"].append(component_type)
        
        if not components["detected"]:
            components["detected"] = ["core", "api", "database"]
        
        return components
        
    except Exception as e:
        logger.warning("Component analysis failed: %s", e)
        return {"detected": ["core", "api", "database"], "services": [], "utilities": [], "models": [], "handlers": []}


def detect_design_patterns(repo_dir: Path) -> List[str]:
    """Detect actual design patterns in the codebase"""
    patterns: List[str] = []
    
    try:
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
        }
        
        for py_file in repo_dir.rglob("*.py"):
            try:
                content = py_file.read_text().lower()
                
                for pattern_name, indicators in pattern_indicators.items():
                    if any(indicator in content for indicator in indicators):
                        if pattern_name.lower() in content or any(f"class.*{ind}" in content for ind in indicators):
                            if pattern_name not in patterns:
                                patterns.append(pattern_name)
            except Exception:
                continue
        
        if not patterns:
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


def analyze_architecture(repo_dir: Path) -> Dict[str, Any]:
    """Analyze system architecture"""
    return {
        "components": analyze_components(repo_dir),
        "structure": analyze_full_codebase(repo_dir),
        "patterns": detect_design_patterns(repo_dir)
    }


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
    
    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary.append("\n## Recent Changes")
            for change_file in change_files[:10]:
                title = change_file.stem.split("-", 1)[-1].replace("-", " ").title()
                summary.append(f"* [{title}](changes/{change_file.name})")
    
    (docs_dir / "SUMMARY.md").write_text("\n".join(summary))
    print(f"✅ Updated SUMMARY.md (showing only recent versions)")


def determine_docs_to_update(repo_dir: str, changed_files: List[str], analysis: Dict[str, Any]) -> Dict[str, bool]:
    """
    FIX: Added missing function to determine which docs need updating
    """
    docs_to_update = {
        "summary": False,
        "architecture": False,
        "workflow": False,
        "api": False
    }
    
    # Check if major files changed
    major_files = ["README.md", "setup.py", "requirements.txt", "package.json", "Dockerfile"]
    if any(f in str(changed_files) for f in major_files):
        docs_to_update["summary"] = True
    
    # Check for architecture changes
    arch_indicators = ["refactor", "migrate", "schema", "model", "service"]
    if any(indicator in str(changed_files).lower() for indicator in arch_indicators):
        docs_to_update["architecture"] = True
    
    # Check for workflow changes
    workflow_indicators = [".github", ".gitlab", "jenkins", "ci", "cd", "deploy"]
    if any(indicator in str(changed_files).lower() for indicator in workflow_indicators):
        docs_to_update["workflow"] = True
    
    # Check for API changes
    api_indicators = ["api", "endpoint", "route", "handler", "controller"]
    if any(indicator in str(changed_files).lower() for indicator in api_indicators):
        docs_to_update["api"] = True
    
    # If significance is high, update everything
    if analysis.get("significance", 0) >= 8:
        docs_to_update = {k: True for k in docs_to_update.keys()}
    
    return docs_to_update


def analyze_architectural_impact(repo_dir: Path, changed_files: List[str], analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine if changes warrant a new architecture/workflow version
    Uses semantic versioning (v1.0, v1.1, v2.0) instead of incremental numbers
    """
    versioning_decision: Dict[str, Any] = {
        "needs_new_architecture_version": False,
        "needs_new_workflow_version": False,
        "architecture_change_reason": "",
        "workflow_change_reason": ""
    }

    # STRICT criteria for architectural changes (only truly major changes)
    major_arch_indicators = [
        len(changed_files) > 50,
        any("migrate" in f.lower() for f in changed_files),
        any("refactor" in f.lower() for f in changed_files),
        any("restructure" in f.lower() for f in changed_files),
        analysis.get("type") == "breaking_change" and analysis.get("significance", 0) >= 9,
        any("schema" in f.lower() and "migration" not in f.lower() for f in changed_files),
        any("docker" in f.lower() and "compose" in f.lower() for f in changed_files),
        any("kubernetes" in f.lower() for f in changed_files),
        any("terraform" in f.lower() for f in changed_files),
    ]

    # STRICT criteria for workflow changes (only major process changes)
    major_workflow_indicators = [
        any("github" in f.lower() and "workflow" in f.lower() for f in changed_files),
        any("gitlab" in f.lower() and "ci" in f.lower() for f in changed_files),
        any("jenkins" in f.lower() for f in changed_files),
        any("deploy" in f.lower() and ("script" in f.lower() or "config" in f.lower()) for f in changed_files),
        analysis.get("type") == "breaking_change" and "deployment" in analysis.get("impact_scope", []),
        len(changed_files) > 40,
    ]

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


async def generate_comprehensive_documentation(
    repo_dir: Path,
    analysis: Dict[str, Any],
    changed_files: List[str],
    doc_persona: str = "internal",
    docs_to_update: Optional[Dict[str, bool]] = None
) -> Dict[str, str]:
    """
    Orchestrates the generation of comprehensive documentation by using the ComprehensiveDocBuilder.
    """
    if docs_to_update is None:
        docs_to_update = determine_docs_to_update(str(repo_dir), changed_files, analysis)

    if not any(docs_to_update.values()):
        print("✅ No documentation updates needed based on file changes.")
        return {}

    builder = ComprehensiveDocBuilder(
        repo_dir=repo_dir,
        doc_persona=doc_persona
    )
    
    generated_docs = await builder.build(analysis, docs_to_update)
    
    print("✅ Comprehensive documentation generation complete!")
    return generated_docs


def analyze_workflows(repo_dir: Path) -> Dict[str, Any]:
    """Analyze development workflows"""
    workflows: Dict[str, Any] = {
        "has_ci_cd": False,
        "ci_files": [],
        "scripts": []
    }
    
    ci_files = [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci"]
    for ci_file in ci_files:
        if (repo_dir / ci_file).exists():
            workflows["has_ci_cd"] = True
            workflows["ci_files"].append(ci_file)
    
    scripts_dir = repo_dir / "scripts"
    if scripts_dir.exists():
        workflows["scripts"] = [f.name for f in scripts_dir.iterdir() if f.is_file()]
    
    return workflows


def analyze_api_structure(repo_dir: Path) -> Dict[str, Any]:
    """Analyze API structure"""
    api_info: Dict[str, Any] = {
        "has_api": False,
        "api_files": [],
        "framework": None
    }
    
    frameworks = {
        "FastAPI": ["from fastapi", "FastAPI()"],
        "Flask": ["from flask", "Flask(__name__)"],
        "Express": ["express()", "require('express')"]
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


def get_changed_files_from_analysis(analysis: Dict[str, Any]) -> List[str]:
    """Extract changed files list from analysis"""
    return analysis.get("affected_components", [])


async def generate_smart_documentation(
    repo_dir: Path,
    analysis: Dict[str, Any],
    commit_sha: str,
    ref: str,
    doc_persona: str = "internal",
    docs_to_update: Optional[Dict[str, bool]] = None
) -> None:
    """
    Generate comprehensive documentation based on analysis
    This is the main entry point that orchestrates everything
    """
    from app.services.documentation.change_docs import (
        create_change_documentation,
        update_main_readme,
        update_changelog,
        create_migration_guide,
        update_summary_md,
    )
    
    docs_dir = repo_dir / "docs"
    changes_dir = docs_dir / "changes"
    docs_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔍 Checking documentation quality...")
    changed_files = get_changed_files_from_analysis(analysis)
    await generate_comprehensive_documentation(repo_dir, analysis, changed_files, doc_persona, docs_to_update=docs_to_update)
    
    # 1. Create detailed change documentation
    create_change_documentation(changes_dir, analysis, commit_sha, ref)
    
    # 2. Update main README if needed
    if analysis.get("documentation_needs", {}).get("update_readme", False):
        update_main_readme(repo_dir, analysis)
    
    # 3. Update changelog
    if analysis.get("documentation_needs", {}).get("create_changelog", False):
        update_changelog(repo_dir, analysis, commit_sha)
    
    # 4. Create migration guide for breaking changes
    if analysis.get("documentation_needs", {}).get("create_migration_guide", False):
        create_migration_guide(docs_dir, analysis)
    
    # 5. Update SUMMARY.md for GitBook navigation
    await update_summary_md(docs_dir, analysis, commit_sha)