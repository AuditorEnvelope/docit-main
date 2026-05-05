"""
Discovery Scanner - Adaptive First-Principles Repository Analysis

ZERO hardcoded technology patterns. ZERO hardcoded framework names.
This module treats every codebase as an unknown organism and discovers
its structure purely from evidence:

  1. Manifest scanning   → reads ACTUAL dependency files for tech stack
  2. Existing docs scan   → reads READMEs, ADRs, changelogs, CONTRIBUTING, API specs
  3. CI/CD & infra scan   → reads workflows, IaC, proto/schema, linting configs
  4. Structural profiling → file extensions, directory roles, file sizes
  5. Import graph         → who-imports-whom (language-agnostic regex)
  6. Content signals      → decorators, class density, IO patterns, exports
  7. Centrality analysis  → identifies system hearts via graph metrics

The scanner produces a DiscoveryReport with raw signals. The downstream
LLM planning call (aggregate_prompt.py) interprets these signals and
decides what documentation sections THIS specific codebase deserves.

NO TEMPLATES. NO ASSUMPTIONS. PURE DISCOVERY.
"""

import ast
import json
import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Public data structures (backward-compatible with the rest of the pipeline)
# ────────────────────────────────────────────────────────────────────────────

class PrimitiveType(str, Enum):
    """Natural primitives discovered in any codebase."""
    INGRESS = "ingress"
    EGRESS = "egress"
    STATE = "state"
    ORCHESTRATOR = "orchestrator"
    TRANSFORMER = "transformer"
    CONNECTOR = "connector"


@dataclass
class DiscoveredPrimitive:
    """A discovered system primitive."""
    primitive_type: PrimitiveType
    file_path: str
    name: str
    description: str
    connections: List[str] = field(default_factory=list)
    imports_in: List[str] = field(default_factory=list)
    imports_out: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    centrality_score: float = 0.0


@dataclass
class DataJourney:
    """Traces a data object through the codebase."""
    data_type: str
    ingress_point: str
    transformation_points: List[str]
    persistence_point: Optional[str]
    egress_points: List[str]
    journey_description: str


@dataclass
class DiscoveryReport:
    """Complete discovery scan results."""
    project_name: str

    # Natural primitives
    ingress_points: List[DiscoveredPrimitive]
    egress_points: List[DiscoveredPrimitive]
    state_models: List[DiscoveredPrimitive]
    orchestrators: List[DiscoveredPrimitive]

    # Derived insights
    data_journeys: List[DataJourney]

    # Graph metrics
    file_centrality: Dict[str, float]
    import_graph: Dict[str, List[str]]

    # Adaptively-detected tech stack (from manifests, not hardcoded lists)
    tech_stack: Dict[str, List[str]]

    # Constraints & brittle points
    constraints: List[str]
    brittle_points: List[str]

    # ── NEW: richer adaptive signals ───────────────────────────────────
    manifest_data: Dict[str, Any] = field(default_factory=dict)
    directory_roles: Dict[str, str] = field(default_factory=dict)
    language_profile: Dict[str, int] = field(default_factory=dict)
    file_role_summary: Dict[str, List[str]] = field(default_factory=dict)
    key_file_snippets: Dict[str, str] = field(default_factory=dict)

    # ── Enterprise evidence: existing docs, CI/CD, infra ──────────────
    existing_docs: Dict[str, str] = field(default_factory=dict)
    ci_cd_configs: Dict[str, str] = field(default_factory=dict)
    api_specs: Dict[str, str] = field(default_factory=dict)
    schema_files: Dict[str, str] = field(default_factory=dict)
    infra_configs: Dict[str, str] = field(default_factory=dict)

    def get_all_primitives(self) -> List[DiscoveredPrimitive]:
        return (
            self.ingress_points
            + self.egress_points
            + self.state_models
            + self.orchestrators
        )


# ────────────────────────────────────────────────────────────────────────────
# Constants – purely structural, never technology-specific
# ────────────────────────────────────────────────────────────────────────────

# Directories to always skip during traversal
_SKIP_DIRS: Set[str] = {
    "node_modules", ".git", "__pycache__", "dist", "build", "venv",
    ".venv", "env", ".env", ".tox", ".mypy_cache", ".pytest_cache",
    "target", "out", "bin", "obj", ".next", ".nuxt", ".output",
    "coverage", ".cache", "vendor", "Pods",
}

# Extensions we consider as "source code" – but we ALSO auto-detect
# from the repo so we never miss a language we didn't anticipate.
_SEED_SOURCE_EXTS: Set[str] = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rs", ".rb",
    ".cs", ".cpp", ".c", ".h", ".hpp", ".swift", ".kt", ".kts",
    ".scala", ".clj", ".ex", ".exs", ".lua", ".php", ".dart", ".r",
    ".jl", ".zig", ".nim", ".sol", ".vy", ".move", ".cairo",
    ".sh", ".bash", ".zsh", ".ps1", ".bat",
    # Schema / proto / config-as-code
    ".proto", ".graphql", ".gql", ".prisma", ".thrift", ".avsc",
    ".tf", ".hcl", ".bicep",
}

# Well-known manifest filenames (we read them; we do NOT hardcode what's inside)
_MANIFEST_FILENAMES: Set[str] = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "requirements.txt", "Pipfile", "Cargo.toml", "go.mod", "go.sum",
    "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
    "composer.json", "pubspec.yaml", "Package.swift",
    "mix.exs", "project.clj", "deno.json", "bun.lockb",
    "CMakeLists.txt", "Makefile", "Dockerfile", "docker-compose.yml",
    "docker-compose.yaml", ".env.example", "turbo.json", "lerna.json",
    "pnpm-workspace.yaml", "nx.json",
}

# ── Documentation files to read for enterprise-level evidence ──────────
# These are GOLD for understanding existing architecture decisions,
# conventions, and domain knowledge that the LLM should build upon.
_DOC_FILENAMES: Set[str] = {
    # READMEs (any casing)
    "readme.md", "readme.rst", "readme.txt", "readme",
    # Architecture Decision Records
    "adr.md", "decisions.md",
    # Changelogs & release notes
    "changelog.md", "changelog.rst", "changelog.txt", "changelog",
    "changes.md", "history.md", "release_notes.md", "releases.md",
    # Contributing & governance
    "contributing.md", "contributing.rst", "code_of_conduct.md",
    "governance.md", "security.md", "security.txt",
    # API specs (read as text – we parse the raw content)
    "openapi.yaml", "openapi.yml", "openapi.json",
    "swagger.yaml", "swagger.yml", "swagger.json",
    "api.yaml", "api.yml", "api.json", "api.md",
    # Architecture & design docs
    "architecture.md", "design.md", "design.rst",
    "tech_spec.md", "rfc.md",
    # Deployment & ops
    "deployment.md", "runbook.md", "playbook.md",
    "infrastructure.md", "operations.md",
    # License
    "license", "license.md", "license.txt",
}
# Patterns (globs) for doc directories to scan recursively
_DOC_DIR_PATTERNS: List[str] = [
    "docs", "doc", "documentation", "wiki",
    "adr", "adrs", "decisions",
    ".github",
]

# ── CI/CD & infrastructure config filenames ────────────────────────────
_CICD_FILENAMES: Set[str] = {
    # GitHub Actions
    ".github/workflows",  # directory, handled specially
    # GitLab
    ".gitlab-ci.yml",
    # Jenkins
    "Jenkinsfile",
    # CircleCI
    ".circleci/config.yml",
    # Travis
    ".travis.yml",
    # Azure Pipelines
    "azure-pipelines.yml",
    # Bitbucket
    "bitbucket-pipelines.yml",
    # AWS
    "buildspec.yml", "appspec.yml", "samconfig.toml",
    "template.yaml", "template.yml",  # SAM / CloudFormation
    "serverless.yml", "serverless.ts",
    # Terraform
    "main.tf", "variables.tf", "outputs.tf", "providers.tf",
    "terraform.tfvars",
    # Kubernetes / Helm
    "Chart.yaml", "values.yaml",
    # Docker
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".dockerignore",
    # Linting / formatting
    ".eslintrc.json", ".eslintrc.js", ".eslintrc.yml", ".eslintrc",
    ".prettierrc", ".prettierrc.json", ".prettierrc.yml",
    ".editorconfig",
    "biome.json",
    ".flake8", ".pylintrc", "mypy.ini", ".mypy.ini",
    "ruff.toml", ".ruff.toml",
    ".rubocop.yml",
    "rustfmt.toml", ".rustfmt.toml", "clippy.toml",
    ".golangci.yml", ".golangci.yaml",
    # Test config
    "jest.config.js", "jest.config.ts", "vitest.config.ts",
    "pytest.ini", "conftest.py", "tox.ini",
    ".nycrc", ".nycrc.json",
    # Schema / proto registry
    "buf.yaml", "buf.gen.yaml",
    "prisma/schema.prisma",
}

# Schema / API spec extensions to sweep for inside subdirs
_SCHEMA_EXTS: Set[str] = {
    ".proto", ".graphql", ".gql", ".prisma", ".thrift",
    ".avsc", ".avdl",  # Avro
    ".fbs",  # FlatBuffers
    ".capnp",  # Cap'n Proto
}

# Infra-as-code extensions
_INFRA_EXTS: Set[str] = {
    ".tf", ".hcl", ".bicep",
}

# Maximum chars to read per file for content analysis
_READ_LIMIT = 4000
_DOC_READ_LIMIT = 6000  # docs get a bigger budget – they're high-value
_MAX_SOURCE_FILES = 500
_MAX_DOC_FILES = 30  # cap on how many doc files we ingest


# ────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ────────────────────────────────────────────────────────────────────────────

def discover_repository(
    repo_dir: Path, analysis: Dict[str, Any] = None
) -> DiscoveryReport:
    """
    Perform an adaptive deep-tissue scan of the repository.

    Pipeline:
      1. Enumerate files & auto-detect languages
      2. Read manifest files → extract real tech stack
      2b. Read existing documentation (READMEs, ADRs, changelogs, API specs)
      2c. Read CI/CD, infra, schema, linting configs
      3. Build import graph → compute centrality
      4. Classify file roles via content signals
      5. Identify primitives (ingress, egress, state, orchestrators)
      6. Trace data journeys
      7. Find constraints & brittle code
    """
    print("=" * 80)
    print("🔭 ADAPTIVE DISCOVERY SCANNER: Beginning deep-tissue scan")
    print("=" * 80)

    analysis = analysis or {}

    # ── 1. Enumerate source files & build language profile ────────────
    print("\n📂 Phase 1: Enumerating source files …")
    source_files = _get_source_files(repo_dir)
    language_profile = _build_language_profile(source_files, repo_dir)
    print(f"   Found {len(source_files)} source files across "
          f"{len(language_profile)} language(s): "
          f"{', '.join(f'{ext}({n})' for ext, n in language_profile.most_common(5))}")

    # ── 2. Read manifest files → adaptive tech stack ─────────────────
    print("\n📦 Phase 2: Reading manifest files …")
    manifest_data = _read_all_manifests(repo_dir)
    tech_stack = _extract_tech_stack_from_manifests(manifest_data, analysis)
    print(f"   Manifests found: {list(manifest_data.keys())}")

    # ── 2b. Read existing documentation ───────────────────────────────
    print("\n📚 Phase 2b: Reading existing documentation …")
    existing_docs, api_specs = _read_existing_docs(repo_dir)
    print(f"   Docs found: {len(existing_docs)} files, "
          f"API specs: {len(api_specs)} files")
    if existing_docs:
        print(f"   Doc files: {list(existing_docs.keys())[:10]}")

    # ── 2c. Read CI/CD, infra, schema, linting configs ────────────
    print("\n⚙️  Phase 2c: Reading CI/CD, infra & schema configs …")
    ci_cd_configs, schema_files, infra_configs = _read_ci_and_infra(repo_dir)
    print(f"   CI/CD: {len(ci_cd_configs)}, Schemas: {len(schema_files)}, "
          f"Infra: {len(infra_configs)}")

    # ── 3. Build import graph & centrality ───────────────────────────
    print("\n📊 Phase 3: Building import graph …")
    import_graph = _build_import_graph(repo_dir, source_files)
    file_centrality = _calculate_centrality(import_graph)

    # ── 4. Classify file roles through content analysis ──────────────
    print("\n🔍 Phase 4: Classifying file roles via content signals …")
    file_roles, directory_roles = _classify_files_and_dirs(
        repo_dir, source_files
    )

    # ── 5. Identify primitives from roles & centrality ───────────────
    print("\n🧬 Phase 5: Identifying Natural Primitives …")
    ingress_points = _extract_primitives(
        file_roles, PrimitiveType.INGRESS, file_centrality
    )
    egress_points = _extract_primitives(
        file_roles, PrimitiveType.EGRESS, file_centrality
    )
    state_models = _extract_primitives(
        file_roles, PrimitiveType.STATE, file_centrality
    )
    orchestrators = _identify_orchestrators(
        repo_dir, file_centrality, file_roles
    )

    # ── 6. Trace data journeys ───────────────────────────────────────
    print("\n🛤️  Phase 6: Tracing data journeys …")
    data_journeys = _trace_data_journeys(
        repo_dir, source_files, ingress_points, egress_points, state_models
    )

    # ── 7. Find constraints & brittle code ───────────────────────────
    print("\n⚠️  Phase 7: Scanning for constraints & brittle code …")
    constraints = _find_constraints(repo_dir, source_files)
    brittle_points = _find_brittle_points(repo_dir, source_files)

    # ── 8. Read key file snippets for evidence ───────────────────────
    key_snippets = _read_key_file_snippets(
        repo_dir, file_centrality, manifest_data)

    # ── Build file role summary for LLM ──────────────────────────────
    file_role_summary = _build_role_summary(file_roles)

    # ── Determine project name ───────────────────────────────────────
    project_name = _determine_project_name(repo_dir, analysis, manifest_data)

    report = DiscoveryReport(
        project_name=project_name,
        ingress_points=ingress_points,
        egress_points=egress_points,
        state_models=state_models,
        orchestrators=orchestrators,
        data_journeys=data_journeys,
        file_centrality=file_centrality,
        import_graph=import_graph,
        tech_stack=tech_stack,
        constraints=constraints,
        brittle_points=brittle_points,
        manifest_data=manifest_data,
        directory_roles=directory_roles,
        language_profile=dict(language_profile),
        file_role_summary=file_role_summary,
        key_file_snippets=key_snippets,
        existing_docs=existing_docs,
        ci_cd_configs=ci_cd_configs,
        api_specs=api_specs,
        schema_files=schema_files,
        infra_configs=infra_configs,
    )

    _print_summary(report)
    return report


# ────────────────────────────────────────────────────────────────────────────
# Phase 1: File enumeration & language profiling
# ────────────────────────────────────────────────────────────────────────────

def _get_source_files(repo_dir: Path) -> List[Path]:
    """Enumerate source files, auto-detecting languages from what exists."""
    source_files: List[Path] = []

    for root, dirs, files in os.walk(repo_dir):
        # Prune skip dirs in-place
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        root_path = Path(root)
        for fname in files:
            fpath = root_path / fname
            if fpath.suffix in _SEED_SOURCE_EXTS:
                source_files.append(fpath)
            elif fpath.suffix and len(fpath.suffix) <= 6 and fpath.suffix not in {
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff",
                ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".webp", ".avif",
                ".lock", ".map", ".min", ".zip", ".tar", ".gz",
            }:
                # Heuristic: include unknown small-suffix files if they look
                # like text (we'll let content analysis figure the rest out).
                # This means we never miss a language we didn't seed.
                if fpath.stat().st_size < 500_000:  # skip huge binary
                    source_files.append(fpath)

            if len(source_files) >= _MAX_SOURCE_FILES:
                return source_files

    return source_files


def _build_language_profile(
    source_files: List[Path], repo_dir: Path
) -> Counter:
    """Count files per extension to build a language profile."""
    counter: Counter = Counter()
    for f in source_files:
        counter[f.suffix] += 1
    return counter


# ────────────────────────────────────────────────────────────────────────────
# Phase 2: Manifest reading → adaptive tech stack
# ────────────────────────────────────────────────────────────────────────────

def _read_all_manifests(repo_dir: Path) -> Dict[str, Any]:
    """Read every manifest file found anywhere in the repo."""
    manifests: Dict[str, Any] = {}

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname.lower() in {m.lower() for m in _MANIFEST_FILENAMES}:
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(repo_dir))
                try:
                    raw = fpath.read_text(encoding="utf-8", errors="ignore")[
                        :_READ_LIMIT * 2
                    ]
                    if fname.endswith(".json"):
                        manifests[rel] = json.loads(raw)
                    else:
                        manifests[rel] = raw
                except Exception:
                    manifests[rel] = "(unreadable)"
    return manifests


def _extract_tech_stack_from_manifests(
    manifests: Dict[str, Any], analysis: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Derive tech stack purely from manifest contents.

    We read what the developer declared – we never guess or hardcode
    "if X then Y framework". The raw dependency names ARE the tech stack.
    """
    stack: Dict[str, List[str]] = {
        "languages": [],
        "frameworks": [],
        "databases": [],
        "dependencies": [],
        "dev_dependencies": [],
        "build_tools": [],
    }

    # Use analysis if it already has data (from comprehensive.py)
    if analysis:
        stack["languages"] = list(analysis.get("languages", []))
        stack["frameworks"] = list(analysis.get("frameworks", []))
        stack["databases"] = list(analysis.get("database_tech", []))

    all_dep_names: Set[str] = set()
    all_dev_dep_names: Set[str] = set()

    for rel_path, content in manifests.items():
        fname = Path(rel_path).name.lower()

        if fname == "package.json" and isinstance(content, dict):
            deps = content.get("dependencies", {})
            dev_deps = content.get("devDependencies", {})
            if isinstance(deps, dict):
                all_dep_names.update(deps.keys())
            if isinstance(dev_deps, dict):
                all_dev_dep_names.update(dev_deps.keys())
            # Scripts tell us about build tooling
            scripts = content.get("scripts", {})
            if isinstance(scripts, dict):
                stack["build_tools"].extend(
                    [f"npm:{k}" for k in scripts.keys()]
                )

        elif fname == "requirements.txt" and isinstance(content, str):
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg = re.split(r"[>=<!\[;]", line)[0].strip()
                    if pkg:
                        all_dep_names.add(pkg)

        elif fname in ("pyproject.toml", "setup.cfg") and isinstance(content, str):
            # Extract dependency names from pyproject.toml (simple regex)
            dep_matches = re.findall(
                r'"([a-zA-Z0-9_-]+)(?:[>=<]|")', content
            )
            all_dep_names.update(dep_matches)

        elif fname == "cargo.toml" and isinstance(content, str):
            dep_matches = re.findall(
                r'^\s*([a-zA-Z0-9_-]+)\s*=', content, re.MULTILINE
            )
            all_dep_names.update(dep_matches)

        elif fname == "go.mod" and isinstance(content, str):
            dep_matches = re.findall(
                r'^\s+([\w./\-]+)\s', content, re.MULTILINE)
            all_dep_names.update(dep_matches)

        elif fname == "gemfile" and isinstance(content, str):
            dep_matches = re.findall(r"gem\s+['\"]([^'\"]+)['\"]", content)
            all_dep_names.update(dep_matches)

        elif fname == "composer.json" and isinstance(content, dict):
            require = content.get("require", {})
            if isinstance(require, dict):
                all_dep_names.update(require.keys())

    # Store top dependencies as the real tech signal
    stack["dependencies"] = sorted(all_dep_names)[:60]
    stack["dev_dependencies"] = sorted(all_dev_dep_names)[:30]

    return stack


# ────────────────────────────────────────────────────────────────────────────
# Phase 2b: Read existing documentation – enterprise evidence
# ────────────────────────────────────────────────────────────────────────────

def _read_existing_docs(
    repo_dir: Path,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Harvest every piece of human-written documentation in the repo.

    Returns:
        existing_docs: {relative_path: content} – READMEs, ADRs, changelogs, etc.
        api_specs:     {relative_path: content} – OpenAPI / Swagger / API Markdown
    """
    existing_docs: Dict[str, str] = {}
    api_specs: Dict[str, str] = {}
    doc_count = 0

    api_keywords = {"openapi", "swagger", "api.yaml", "api.yml", "api.json"}

    def _ingest(fpath: Path) -> None:
        nonlocal doc_count
        if doc_count >= _MAX_DOC_FILES:
            return
        rel = str(fpath.relative_to(repo_dir))
        if rel in existing_docs or rel in api_specs:
            return
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")[
                :_DOC_READ_LIMIT
            ]
            if not content.strip():
                return
            fname_lower = fpath.name.lower()
            if fname_lower in api_keywords or fname_lower.startswith(("openapi", "swagger")):
                api_specs[rel] = content
            else:
                existing_docs[rel] = content
            doc_count += 1
        except Exception:
            pass

    # 1. Root-level doc files (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.)
    for fname in repo_dir.iterdir():
        if not fname.is_file():
            continue
        if fname.name.lower() in _DOC_FILENAMES:
            _ingest(fname)

    # 2. Known doc directories – scan recursively for .md / .rst / .txt / .yaml / .json
    doc_exts = {".md", ".rst", ".txt", ".yaml", ".yml", ".json", ".adoc"}
    for dname in _DOC_DIR_PATTERNS:
        dpath = repo_dir / dname
        if not dpath.is_dir():
            continue
        for root, dirs, files in os.walk(dpath):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in doc_exts:
                    _ingest(fpath)
                if doc_count >= _MAX_DOC_FILES:
                    break
            if doc_count >= _MAX_DOC_FILES:
                break

    # 3. Sweep for any README / CHANGELOG / CONTRIBUTING in subdirectories
    #    (enterprise monorepos often have per-package READMEs)
    readme_names = {"readme.md", "readme.rst", "readme.txt",
                    "changelog.md", "contributing.md"}
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname.lower() in readme_names:
                _ingest(Path(root) / fname)
        if doc_count >= _MAX_DOC_FILES:
            break

    return existing_docs, api_specs


# ────────────────────────────────────────────────────────────────────────────
# Phase 2c: Read CI/CD, infra, schema & linting configs
# ────────────────────────────────────────────────────────────────────────────

def _read_ci_and_infra(
    repo_dir: Path,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Read CI/CD pipeline configs, schema/proto files, and infra-as-code.

    Returns:
        ci_cd_configs:  {relative_path: content}
        schema_files:   {relative_path: content}  (proto, graphql, prisma, etc.)
        infra_configs:  {relative_path: content}  (terraform, helm, k8s, etc.)
    """
    ci_cd: Dict[str, str] = {}
    schemas: Dict[str, str] = {}
    infra: Dict[str, str] = {}

    def _safe_read(fpath: Path, limit: int = _READ_LIMIT) -> Optional[str]:
        try:
            return fpath.read_text(encoding="utf-8", errors="ignore")[:limit]
        except Exception:
            return None

    # 1. Known CI/CD files at root or well-known paths
    for ci_name in _CICD_FILENAMES:
        ci_path = repo_dir / ci_name
        if ci_path.is_file():
            content = _safe_read(ci_path)
            if content:
                ci_cd[ci_name] = content
        elif ci_path.is_dir():
            # e.g. .github/workflows/ – read all YAML inside
            for wf in ci_path.rglob("*.yml"):
                rel = str(wf.relative_to(repo_dir))
                content = _safe_read(wf)
                if content:
                    ci_cd[rel] = content
            for wf in ci_path.rglob("*.yaml"):
                rel = str(wf.relative_to(repo_dir))
                content = _safe_read(wf)
                if content:
                    ci_cd[rel] = content

    # 2. Schema / proto files anywhere in the repo
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in _SCHEMA_EXTS:
                rel = str(fpath.relative_to(repo_dir))
                content = _safe_read(fpath)
                if content:
                    schemas[rel] = content

    # 3. Infra-as-code files & directories
    #    Look for terraform/, k8s/, kubernetes/, helm/, infra/, deploy/ dirs
    infra_dirs = ["terraform", "k8s", "kubernetes", "helm", "infra",
                  "deploy", "deployment", "cdk", "pulumi", "cloudformation"]
    for idir_name in infra_dirs:
        idir = repo_dir / idir_name
        if not idir.is_dir():
            continue
        for root, dirs, files in os.walk(idir):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fname in files:
                fpath = Path(root) / fname
                # Read tf, hcl, yaml, json, toml inside infra dirs
                if fpath.suffix.lower() in (
                    _INFRA_EXTS | {".yaml", ".yml", ".json", ".toml"}
                ):
                    rel = str(fpath.relative_to(repo_dir))
                    content = _safe_read(fpath)
                    if content:
                        infra[rel] = content

    # Also pick up standalone .tf files at root
    for fpath in repo_dir.glob("*.tf"):
        rel = str(fpath.relative_to(repo_dir))
        if rel not in infra:
            content = _safe_read(fpath)
            if content:
                infra[rel] = content

    return ci_cd, schemas, infra


# ────────────────────────────────────────────────────────────────────────────
# Phase 3: Import graph & centrality
# ────────────────────────────────────────────────────────────────────────────

def _build_import_graph(
    repo_dir: Path, source_files: List[Path]
) -> Dict[str, List[str]]:
    """Language-agnostic import graph built from regex patterns."""
    graph: Dict[str, List[str]] = defaultdict(list)

    for fpath in source_files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")[
                :_READ_LIMIT
            ]
            rel = str(fpath.relative_to(repo_dir))
            imports = _extract_imports_generic(content)
            graph[rel] = imports
        except Exception:
            pass

    return dict(graph)


def _extract_imports_generic(content: str) -> List[str]:
    """Extract imports with language-agnostic regexes."""
    imports: Set[str] = set()

    # Python: from X import Y | import X
    for m in re.finditer(r'^(?:from|import)\s+([^\s#;]+)', content, re.MULTILINE):
        imports.add(m.group(1).split(".")[0])

    # JS/TS: import ... from "X" | require("X")
    for m in re.finditer(r'''(?:from|require)\s*\(?\s*['"]([^'"]+)['"]''', content):
        imports.add(m.group(1).split("/")[0])

    # Go: import "X" or import ( "X" )
    for m in re.finditer(r'"([\w./\-]+)"', content):
        imports.add(m.group(1).split("/")[0])

    # Rust: use X::Y
    for m in re.finditer(r'^use\s+([\w:]+)', content, re.MULTILINE):
        imports.add(m.group(1).split("::")[0])

    # Java/Kotlin: import X.Y.Z
    for m in re.finditer(r'^import\s+(?:static\s+)?([a-zA-Z][\w.]+)', content, re.MULTILINE):
        imports.add(m.group(1).split(".")[0])

    return list(imports)


def _calculate_centrality(import_graph: Dict[str, List[str]]) -> Dict[str, float]:
    """
    Compute normalized centrality.
    Score = 2 * in_degree + out_degree, then normalize to [0, 1].
    """
    centrality: Dict[str, float] = defaultdict(float)
    in_degree: Dict[str, int] = defaultdict(int)

    for src, imports in import_graph.items():
        for imp in imports:
            in_degree[imp] += 1

    for src in import_graph:
        out = len(import_graph[src])
        centrality[src] = in_degree.get(src, 0) * 2 + out

    if centrality:
        mx = max(centrality.values()) or 1
        centrality = {k: v / mx for k, v in centrality.items()}

    return dict(centrality)


# ────────────────────────────────────────────────────────────────────────────
# Phase 4: Adaptive file & directory role classification
# ────────────────────────────────────────────────────────────────────────────

def _classify_files_and_dirs(
    repo_dir: Path, source_files: List[Path]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """
    Classify every source file's ROLE by reading its content and applying
    purely structural heuristics (NOT technology-specific ones).

    Returns:
        file_roles: {rel_path: {roles: [...], signals: [...], names: [...]}}
        directory_roles: {dir_path: inferred_role}
    """
    file_roles: Dict[str, Dict[str, Any]] = {}
    dir_role_votes: Dict[str, Counter] = defaultdict(Counter)

    for fpath in source_files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")[
                :_READ_LIMIT
            ]
            rel = str(fpath.relative_to(repo_dir))
            dir_rel = str(fpath.parent.relative_to(repo_dir))

            roles, signals, names = _analyze_file_content(
                content, fpath.name, fpath.suffix, rel
            )

            file_roles[rel] = {
                "roles": roles,
                "signals": signals,
                "names": names,
            }

            # Vote for directory role
            for role in roles:
                dir_role_votes[dir_rel][role] += 1

        except Exception:
            pass

    # Resolve directory roles from votes
    directory_roles: Dict[str, str] = {}
    for d, votes in dir_role_votes.items():
        if votes:
            directory_roles[d] = votes.most_common(1)[0][0]

    return file_roles, directory_roles


def _analyze_file_content(
    content: str, filename: str, suffix: str, rel_path: str
) -> Tuple[List[str], List[str], List[str]]:
    """
    Assign roles and extract signals from a single file using STRUCTURAL
    heuristics only. We look for patterns like:

    INGRESS signals (entry points):
      - Route/endpoint decorators or registrations
      - Main/entry-point functions
      - Event handler registrations
      - Exported page/component default functions

    EGRESS signals (side effects):
      - Network client calls (any fetch/request/http verb)
      - File write operations
      - Database write operations (insert/update/delete/commit/save)
      - Logging/telemetry sinks

    STATE signals (data definitions):
      - Class/interface/type/struct definitions in model-like paths
      - Schema definitions, migration files
      - ORM model classes

    ORCHESTRATOR signals:
      - Many imports (high fan-out)
      - Router/middleware registration
      - Initialization/bootstrap code

    None of these check for SPECIFIC framework names.
    """
    roles: List[str] = []
    signals: List[str] = []
    names: List[str] = []

    lines = content.splitlines()
    num_lines = len(lines)
    content_lower = content.lower()
    path_lower = rel_path.lower()

    # ── Count structural features ────────────────────────────────────
    import_count = len(re.findall(
        r'^(?:import|from|require|use )', content, re.MULTILINE
    ))
    class_defs = re.findall(
        r'(?:^|\s)(?:class|interface|type|struct|enum|model)\s+(\w+)',
        content, re.MULTILINE
    )
    func_defs = re.findall(
        r'(?:^|\s)(?:def|func|function|fn|fun|sub)\s+(\w+)',
        content, re.MULTILINE
    )
    decorator_lines = re.findall(r'^[ \t]*@[\w.]+', content, re.MULTILINE)
    export_defaults = re.findall(
        r'export\s+default\s+(?:function|class|const)\s+(\w+)',
        content, re.MULTILINE
    )

    # ── INGRESS detection (entry points) ─────────────────────────────
    # Route/endpoint decorators: @X.verb(...) or @verb(...)
    route_decorators = re.findall(
        r'@\w+\.(get|post|put|delete|patch|head|options|route|api_route)\s*\(',
        content_lower,
    )
    # Route registrations: app.verb( or router.verb(
    route_registrations = re.findall(
        r'\w+\.(get|post|put|delete|patch|use|route|all|head|options)\s*\(',
        content_lower,
    )
    # Main / entry point
    has_main = bool(re.search(
        r'(?:def\s+main\s*\(|if\s+__name__\s*==|func\s+main\s*\(|'
        r'fn\s+main\s*\(|public\s+static\s+void\s+main)',
        content,
    ))
    # CLI decorators/patterns
    cli_signals = bool(re.search(
        r'@\w*\.(?:command|option|argument)\s*\(|argparse|OptionParser|clap::',
        content,
    ))
    # Event listener patterns
    event_signals = bool(re.search(
        r'\.on\s*\(|addEventListener|@EventHandler|on_event|handle_event|'
        r'\.subscribe\s*\(|\.listen\s*\(',
        content_lower,
    ))

    if route_decorators or route_registrations:
        roles.append("ingress")
        verb_list = list(set(route_decorators + route_registrations))[:5]
        signals.append(f"route_verbs: {verb_list}")
        # Extract route handler names
        handler_names = re.findall(
            r'(?:async\s+)?(?:def|function)\s+(\w+)',
            content,
        )
        names.extend(handler_names[:5])

    if has_main:
        roles.append("ingress")
        signals.append("main_entry_point")

    if cli_signals:
        roles.append("ingress")
        signals.append("cli_entry")

    if event_signals and "ingress" not in roles:
        roles.append("ingress")
        signals.append("event_listener")

    if export_defaults:
        # Could be a page / UI entry
        page_indicators = any(
            kw in path_lower
            for kw in ["page", "screen", "view", "route", "app/"]
        )
        if page_indicators:
            roles.append("ingress")
            signals.append("ui_page_entry")
            names.extend(export_defaults[:3])

    # ── EGRESS detection (side effects) ──────────────────────────────
    # Network calls (generic patterns, NOT framework-specific names)
    network_calls = bool(re.search(
        r'\.(?:fetch|request|send|post|get|put|delete|patch)\s*\(|'
        r'(?:http|https)://|'
        r'new\s+\w*(?:Client|Request|Connection)\s*\(',
        content,
    ))
    # DB write patterns (generic)
    db_writes = bool(re.search(
        r'\.(?:execute|commit|save|insert|update|delete|create|destroy|'
        r'upsert|bulkCreate|bulkWrite|add_all|flush)\s*\(',
        content_lower,
    ))
    # File write patterns
    file_writes = bool(re.search(
        r'\.(?:write|writeFile|writeFileSync|write_text|write_bytes)\s*\(',
        content_lower,
    ))
    # Logging sinks
    log_sinks = bool(re.search(
        r'(?:logger|log|console)\.\w+\s*\(', content_lower
    ))

    if network_calls:
        roles.append("egress")
        signals.append("network_calls")
    if db_writes:
        roles.append("egress")
        signals.append("db_writes")
    if file_writes:
        roles.append("egress")
        signals.append("file_writes")
    if log_sinks and "egress" not in roles:
        # Only mark as egress if it's PRIMARILY a logging file
        if "log" in filename.lower():
            roles.append("egress")
            signals.append("logging_sink")

    # ── STATE detection (data definitions) ───────────────────────────
    model_path = any(
        kw in path_lower
        for kw in [
            "model", "schema", "entity", "type", "interface",
            "migration", "table", "dto", "struct", "proto",
        ]
    )
    high_class_density = len(class_defs) >= 2
    schema_markers = bool(re.search(
        r'(?:Column|Field|Schema|Table|Model|Entity|Serializer|'
        r'validator|@Entity|@Table|@Column|#\[derive)',
        content,
    ))

    if model_path or (high_class_density and schema_markers):
        roles.append("state")
        signals.append(f"class_defs: {class_defs[:5]}")
        names.extend(class_defs[:8])
    elif high_class_density and not roles:
        # File with many class defs might be state
        roles.append("state")
        signals.append(f"class_defs: {class_defs[:5]}")
        names.extend(class_defs[:5])

    # ── ORCHESTRATOR detection ───────────────────────────────────────
    high_fan_out = import_count >= 8
    is_init_or_index = filename.lower() in {
        "__init__.py", "index.ts", "index.js", "mod.rs", "main.go",
        "app.py", "app.ts", "app.js", "server.py", "server.ts",
        "server.js",
    }

    if high_fan_out:
        roles.append("orchestrator")
        signals.append(f"import_count: {import_count}")

    if is_init_or_index and import_count >= 3:
        if "orchestrator" not in roles:
            roles.append("orchestrator")
        signals.append("init_or_index_file")

    # ── Config detection ─────────────────────────────────────────────
    config_indicators = any(
        kw in path_lower
        for kw in ["config", "setting", "env", "const"]
    )
    if config_indicators and not roles:
        roles.append("config")
        signals.append("config_file")

    # ── Test detection ───────────────────────────────────────────────
    test_indicators = any(
        kw in path_lower for kw in ["test", "spec", "__tests__"]
    )
    if test_indicators:
        roles.append("test")
        signals.append("test_file")

    # Default: transformer (does processing but doesn't fit above)
    if not roles:
        roles.append("transformer")
        signals.append("general_logic")

    if not names:
        names = func_defs[:5] or class_defs[:3] or [fpath_stem(filename)]

    return roles, signals, names


def fpath_stem(filename: str) -> str:
    return Path(filename).stem


# ────────────────────────────────────────────────────────────────────────────
# Phase 5: Primitive extraction from file roles
# ────────────────────────────────────────────────────────────────────────────

def _extract_primitives(
    file_roles: Dict[str, Dict[str, Any]],
    target_type: PrimitiveType,
    centrality: Dict[str, float],
) -> List[DiscoveredPrimitive]:
    """Extract primitives of a given type from classified files."""
    primitives: List[DiscoveredPrimitive] = []
    role_key = target_type.value  # "ingress", "egress", "state"

    for rel_path, info in file_roles.items():
        if role_key in info["roles"]:
            for name in info["names"][:3]:
                primitives.append(DiscoveredPrimitive(
                    primitive_type=target_type,
                    file_path=rel_path,
                    name=name,
                    description="; ".join(info["signals"][:3]),
                    evidence=info["signals"][:5],
                    centrality_score=centrality.get(rel_path, 0.0),
                ))

    # Sort by centrality descending, keep top 15
    primitives.sort(key=lambda p: -p.centrality_score)
    return primitives[:15]


def _identify_orchestrators(
    repo_dir: Path,
    centrality: Dict[str, float],
    file_roles: Dict[str, Dict[str, Any]],
) -> List[DiscoveredPrimitive]:
    """Identify orchestrators: high-centrality files or those tagged as orchestrator."""
    candidates: Dict[str, float] = {}

    # Files with centrality > 0.4
    for fp, score in centrality.items():
        if score > 0.4:
            candidates[fp] = score

    # Also add files explicitly tagged as orchestrator
    for fp, info in file_roles.items():
        if "orchestrator" in info["roles"]:
            candidates[fp] = max(
                candidates.get(fp, 0), centrality.get(fp, 0.3)
            )

    orchestrators: List[DiscoveredPrimitive] = []
    for fp, score in sorted(candidates.items(), key=lambda x: -x[1]):
        info = file_roles.get(fp, {"signals": [], "names": []})
        desc = "; ".join(info.get("signals", [])[:3]) or "high-centrality file"
        name = info.get("names", [Path(fp).stem])[
            0] if info.get("names") else Path(fp).stem
        orchestrators.append(DiscoveredPrimitive(
            primitive_type=PrimitiveType.ORCHESTRATOR,
            file_path=fp,
            name=name,
            description=desc,
            centrality_score=score,
        ))
        if len(orchestrators) >= 10:
            break

    return orchestrators


# ────────────────────────────────────────────────────────────────────────────
# Phase 6: Data journey tracing
# ────────────────────────────────────────────────────────────────────────────

def _trace_data_journeys(
    repo_dir: Path,
    source_files: List[Path],
    ingress: List[DiscoveredPrimitive],
    egress: List[DiscoveredPrimitive],
    state: List[DiscoveredPrimitive],
) -> List[DataJourney]:
    """Trace data objects from ingress → transformation → egress."""
    journeys: List[DataJourney] = []

    key_types = [s.name for s in state[:5]] if state else []
    if not key_types:
        return journeys

    for dtype in key_types[:3]:
        entry = ingress[0].file_path if ingress else "unknown"
        transforms = _find_mentions(repo_dir, source_files, dtype, limit=5)
        persist = state[0].file_path if state else None
        exits = [e.file_path for e in egress[:3]]

        journeys.append(DataJourney(
            data_type=dtype,
            ingress_point=entry,
            transformation_points=transforms,
            persistence_point=persist,
            egress_points=exits,
            journey_description=(
                f"{dtype} enters at {entry}, transformed in "
                f"{len(transforms)} files, persists, then exits"
            ),
        ))

    return journeys


def _find_mentions(
    repo_dir: Path, source_files: List[Path], term: str, limit: int = 5
) -> List[str]:
    """Find files that mention a given term."""
    found: List[str] = []
    term_lower = term.lower()
    for fpath in source_files[:80]:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")[
                :_READ_LIMIT
            ]
            if term_lower in content.lower():
                found.append(str(fpath.relative_to(repo_dir)))
        except Exception:
            pass
        if len(found) >= limit:
            break
    return found


# ────────────────────────────────────────────────────────────────────────────
# Phase 7: Constraints & brittle code
# ────────────────────────────────────────────────────────────────────────────

def _find_constraints(repo_dir: Path, source_files: List[Path]) -> List[str]:
    """Find developer-annotated constraints: TODO, FIXME, HACK, etc."""
    constraints: List[str] = []
    pattern = re.compile(
        r'(TODO|FIXME|HACK|WARNING|LIMITATION|DEPRECATED|BUG|XXX|SAFETY)\s*:?\s*(.*)',
        re.IGNORECASE,
    )

    for fpath in source_files[:60]:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            rel = str(fpath.relative_to(repo_dir))
            for m in pattern.finditer(content):
                msg = m.group(0).strip()[:120]
                entry = f"{rel}: {msg}"
                if entry not in constraints:
                    constraints.append(entry)
                if len(constraints) >= 25:
                    return constraints
        except Exception:
            pass

    return constraints


def _find_brittle_points(repo_dir: Path, source_files: List[Path]) -> List[str]:
    """Detect structurally brittle code patterns."""
    brittle: List[str] = []
    checks = [
        (re.compile(r'except\s*:\s*pass|except\s+\w+\s*:\s*pass', re.IGNORECASE),
         "silent exception swallow"),
        (re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}'),
         "empty catch block"),
        (re.compile(r'while\s+[Tt]rue|loop\s*\{'),
         "potential infinite loop"),
        (re.compile(r'#\s*type:\s*ignore|//\s*@ts-ignore|//\s*@ts-expect-error'),
         "type system override"),
        (re.compile(r'(?:sleep|time\.sleep|Thread\.sleep|setTimeout)\s*\(\s*\d'),
         "hardcoded timing dependency"),
        (re.compile(r'(?:eval|exec)\s*\('),
         "dynamic code execution"),
    ]

    for fpath in source_files[:60]:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            rel = str(fpath.relative_to(repo_dir))
            for pat, label in checks:
                if pat.search(content):
                    entry = f"{rel}: {label}"
                    if entry not in brittle:
                        brittle.append(entry)
        except Exception:
            pass

    return brittle[:20]


# ────────────────────────────────────────────────────────────────────────────
# Key file snippets for evidence
# ────────────────────────────────────────────────────────────────────────────

def _read_key_file_snippets(
    repo_dir: Path,
    centrality: Dict[str, float],
    manifests: Dict[str, Any],
) -> Dict[str, str]:
    """Read the most important files for the LLM to reference."""
    snippets: Dict[str, str] = {}
    count = 0
    max_files = 15

    # 1. All manifest files (already loaded)
    for rel, content in manifests.items():
        if count >= max_files:
            break
        if isinstance(content, dict):
            snippets[rel] = json.dumps(content, indent=2)[:_READ_LIMIT]
        elif isinstance(content, str):
            snippets[rel] = content[:_READ_LIMIT]
        count += 1

    # 2. Top centrality files
    top_central = sorted(centrality.items(), key=lambda x: -x[1])[:10]
    for rel, _ in top_central:
        if count >= max_files:
            break
        if rel in snippets:
            continue
        fpath = repo_dir / rel
        if fpath.exists() and fpath.is_file():
            try:
                snippets[rel] = fpath.read_text(
                    encoding="utf-8", errors="ignore"
                )[:_READ_LIMIT]
                count += 1
            except Exception:
                pass

    return snippets


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _build_role_summary(
    file_roles: Dict[str, Dict[str, Any]]
) -> Dict[str, List[str]]:
    """Group files by role for a compact summary."""
    summary: Dict[str, List[str]] = defaultdict(list)
    for fp, info in file_roles.items():
        for role in info["roles"]:
            summary[role].append(fp)
    return dict(summary)


def _determine_project_name(
    repo_dir: Path,
    analysis: Dict[str, Any],
    manifests: Dict[str, Any],
) -> str:
    """Determine project name from manifests or analysis."""
    # From analysis
    if analysis:
        pkg = analysis.get("package_name", "")
        if pkg and not pkg.startswith("docai"):
            return pkg
        proj = analysis.get("project_name", "")
        if proj and not proj.startswith("docai"):
            return proj

    # From package.json
    for rel, content in manifests.items():
        if Path(rel).name.lower() == "package.json" and isinstance(content, dict):
            name = content.get("name", "")
            if name and not name.startswith("docai"):
                return name

    return repo_dir.name


def _print_summary(report: DiscoveryReport) -> None:
    print("\n" + "=" * 80)
    print("📋 ADAPTIVE DISCOVERY COMPLETE")
    print("=" * 80)
    print(f"  📁 Project: {report.project_name}")
    print(f"  🗣️  Languages: {report.language_profile}")
    print(f"  🚪 Ingress Points: {len(report.ingress_points)}")
    print(f"  📤 Egress Points: {len(report.egress_points)}")
    print(f"  💾 State Models: {len(report.state_models)}")
    print(f"  ❤️  Orchestrators: {len(report.orchestrators)}")
    print(f"  🛤️  Data Journeys: {len(report.data_journeys)}")
    print(f"  📦 Manifests: {len(report.manifest_data)}")
    print(f"  📚 Existing Docs: {len(report.existing_docs)}")
    print(f"  📑 API Specs: {len(report.api_specs)}")
    print(f"  ⚙️  CI/CD Configs: {len(report.ci_cd_configs)}")
    print(f"  📀 Schema Files: {len(report.schema_files)}")
    print(f"  🏧 Infra Configs: {len(report.infra_configs)}")
    print(
        f"  📂 Directory Roles: {dict(list(report.directory_roles.items())[:8])}")
    print(f"  ⚠️  Constraints: {len(report.constraints)}")
    print(f"  💔 Brittle Points: {len(report.brittle_points)}")
    print("=" * 80)
