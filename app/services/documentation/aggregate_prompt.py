"""
Staff Engineer Documentation - LLM-First Approach

The LLM decides what sections a repo needs. No templates. No fixed section lists.
The discovery scanner provides raw signals; the LLM interprets them and invents
section titles that are specific to THIS codebase.

Pipeline:
  1. Discovery scanner → raw signals (imports, ingress, egress, state, files)
  2. LLM STEP 1 → decides what sections THIS repo needs (planning call)
  3. LLM STEP 2 → writes each section with full depth (generation call)
"""

from dataclasses import dataclass, field
import json
import re
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any

from app.services.llm.rotator import get_rotator
from app.services.documentation.parsing import extract_section
from app.services.documentation.planner import DocumentationPlan
from app.services.documentation.discovery_scanner import (
    DiscoveryReport,
    discover_repository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class mirrors DynamicSection so the rest of the pipeline doesn't break
# ---------------------------------------------------------------------------


@dataclass
class DynamicSection:
    id: str
    title: str
    description: str
    primitives: List[str] = field(default_factory=list)
    subsections: List[str] = field(default_factory=list)
    priority: int = 50
    persona: str = "internal"


# ---------------------------------------------------------------------------
# Main entry point (called from comprehensive.py)
# ---------------------------------------------------------------------------

async def generate_all_docs_in_single_call(
    repo_dir,
    analysis: Dict,
    recent_changes: Dict,
    persona: str,
    plan: Optional[DocumentationPlan] = None,
    repo_name: str = None,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    Generate Staff Engineer quality documentation.

    Two-call strategy:
      Call 1 – Planning: LLM reads the raw signals and decides what sections
                         this specific repo deserves (≤ 900 tokens out).
      Call 2 – Writing:  LLM writes every planned section in full.
    """
    repo_path = Path(repo_dir) if isinstance(repo_dir, str) else repo_dir
    project_name = _clean_project_name(repo_name, repo_path, analysis)

    print(f"\n{'='*80}")
    print(f"📖 Starting LLM-first documentation for: {project_name}")
    print(f"{'='*80}")

    # ── Step 1: Run discovery scanner ────────────────────────────────────────
    print("\n🔭 Running discovery scanner …")
    try:
        discovery_report = discover_repository(repo_path, analysis)
    except Exception as exc:
        logger.warning("Discovery scanner failed: %s", exc)
        discovery_report = None

    # ── Step 2: Compact evidence bundle ──────────────────────────────────────
    evidence = _build_evidence_bundle(repo_path, analysis, discovery_report)

    # ── Step 3: PLANNING CALL ────────────────────────────────────────────────
    print("\n🧠 Planning call: asking LLM what sections THIS repo needs …")
    planned_sections = await _planning_call(
        project_name, persona, evidence
    )
    print(f"   → Planned {len(planned_sections)} sections:")
    for s in planned_sections:
        print(f"      • [{s['id']}] {s['title']}")

    # ── Step 4: GENERATION CALL ──────────────────────────────────────────────
    print("\n✍️  Generation call: writing every section …")
    docs, token_data = await _generation_call(
        project_name, persona, evidence, planned_sections
    )

    # ── Step 5: Store plan for downstream writers ────────────────────────────
    docs["plan"] = {
        "sections": [
            {"id": s["id"], "title": s["title"], "type": "llm-planned"}
            for s in planned_sections
        ],
        "repo_type": _infer_repo_type(discovery_report, analysis),
        "complexity": _infer_complexity(analysis),
        "complexity_score": _infer_complexity(analysis),
    }

    return docs, token_data


# ---------------------------------------------------------------------------
# PLANNING CALL
# ---------------------------------------------------------------------------

async def _planning_call(
    project_name: str,
    persona: str,
    evidence: Dict,
) -> List[Dict]:
    """
    Ask the LLM: 'Given this specific codebase, what sections should the
    documentation have?'

    Returns a list of dicts: [{id, title, description, subsections}, …]
    """
    persona_guidance = (
        "INTERNAL (Surgeon's Manual) – document the guts: private methods, "
        "transactions, failure modes, race conditions, gotchas."
        if persona in ("internal", "dev")
        else
        "PUBLIC (Owner's Manual) – document the surface: entry points, "
        "API contracts, quickstarts, integration examples."
    )

    prompt = f"""You are a Staff Software Engineer (equivalent to Meta L6).
Your job: READ the evidence about a real codebase and decide what documentation
sections it actually needs.

DO NOT use generic section names like "Overview", "Architecture", "Workflow".
EVERY title must be specific to THIS codebase, describing what the code actually does.

Title formula: [Action Verb] + [Specific Domain] + [System Impact / Constraint]
Examples of GOOD titles:
  "Enforcing JWT Expiry & Refresh Token Rotation"
  "Propagating Wallet Connect State Across Component Tree"
  "Serializing Solidity Events to PostgreSQL via Ethers.js Listeners"
  "Circuit-Breaking External Price-Feed Calls with Exponential Back-off"

Examples of BAD titles (FORBIDDEN):
  "Overview", "Architecture", "API", "Workflow", "Components", "Database"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT: {project_name}
PERSONA: {persona_guidance}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CODEBASE EVIDENCE:
{json.dumps(evidence, indent=2, default=str)[:12000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: Return ONLY a JSON array (no markdown, no explanation) of 5–9 sections.
Each section object must have exactly these keys:
  "id"          – slug, e.g. "jwt-refresh-rotation"
  "title"       – intent-based title (see formula above)
  "description" – 1 sentence: what an engineer will learn from this section
  "subsections" – list of 3–5 specific sub-headings

Base sections ENTIRELY on the evidence. If you don't see evidence for something,
don't invent a section for it.

Return ONLY valid JSON. No prose before or after.
"""

    rotator = get_rotator()
    result = rotator.generate_with_rotation(prompt)

    if not result:
        return _fallback_sections(evidence)

    raw = result.content.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        sections = json.loads(raw)
        if isinstance(sections, list) and sections:
            # Validate & normalise
            return [_normalise_section(s) for s in sections if isinstance(s, dict)]
    except json.JSONDecodeError as exc:
        logger.warning(
            "Planning call JSON parse failed: %s\nRaw: %s", exc, raw[:500])

    return _fallback_sections(evidence)


# ---------------------------------------------------------------------------
# GENERATION CALL
# ---------------------------------------------------------------------------

async def _generation_call(
    project_name: str,
    persona: str,
    evidence: Dict,
    planned_sections: List[Dict],
) -> Tuple[Dict[str, str], Dict]:
    """
    Write every planned section with full depth.
    """
    persona_guidance = (
        "INTERNAL (Surgeon's Manual): document private implementation details, "
        "failure modes, race conditions, transaction boundaries, gotchas. "
        "Every sentence must help an on-call engineer debug at 2 AM."
        if persona in ("internal", "dev")
        else
        "PUBLIC (Owner's Manual): focus on developer experience, clear examples, "
        "integration patterns, and time-to-value."
    )

    # Build the section output format
    section_format_lines = []
    for s in planned_sections:
        tag = s["id"].upper().replace("-", "_")
        sub_text = "\n".join(f"## {sub}" for sub in s.get("subsections", []))
        section_format_lines.append(
            f"<{tag}_START>\n# {s['title']}\n\n{sub_text}\n\n"
            f"[Write detailed technical content here]\n<{tag}_END>"
        )
    section_format = "\n\n".join(section_format_lines)

    # Build what-to-cover brief
    section_briefs = "\n".join(
        f"• [{s['id']}] {s['title']}\n  → {s['description']}\n"
        f"  Subsections: {', '.join(s.get('subsections', []))}"
        for s in planned_sections
    )

    prompt = f"""You are a Staff Software Engineer (Meta L6) writing production documentation.

PROJECT: {project_name}
PERSONA: {persona_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE "SO WHAT?" TEST (apply to every sentence you write):
Would this sentence help an on-call engineer debug a production incident right now?
If NO → delete it and write specifics.

BANNED phrases: "This module handles …", "This component is responsible for …",
"Overview", "This section covers …", "In summary …"

REQUIRED: file paths, function names, exact config keys, error codes, data shapes,
timing constraints, failure modes, and concrete code snippets.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CODEBASE EVIDENCE:
{json.dumps(evidence, indent=2, default=str)[:16000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTIONS TO WRITE:
{section_briefs}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MERMAID DIAGRAM RULES:
- No parentheses anywhere in node labels or edge labels
- No slashes in labels (use "and" instead of "/")
- Only: graph TD, A[Label] --> B[Label], A --> |edge label| B
- NO classDef, NO style, NO fill

OUTPUT FORMAT (use EXACT tags):
{section_format}

Write ONLY the tagged sections. No preamble. No summary after.
Every section must have at minimum 400 words of specific, useful content.
Include code snippets showing real patterns from the evidence where possible.
"""

    rotator = get_rotator()
    result = rotator.generate_with_rotation(prompt)

    empty_token_data = {"input_tokens": 0,
                        "output_tokens": 0, "model_name": "unknown"}

    if not result:
        logger.error("Generation call returned no result")
        return _make_fallback_docs(planned_sections), empty_token_data

    token_data = {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "model_name": result.model_name,
    }

    raw = result.content

    # Extract each section
    docs: Dict[str, str] = {}
    for s in planned_sections:
        tag = s["id"].upper().replace("-", "_")
        content = extract_section(raw, tag)
        if content:
            docs[s["id"]] = content
            print(f"   ✅ [{s['id']}] extracted ({len(content)} chars)")
        else:
            # Fallback: look for the markdown h1 title
            escaped = re.escape(s["title"])
            m = re.search(
                rf"#\s+{escaped}\s*\n(.*?)(?=\n#\s|\Z)", raw, re.DOTALL | re.IGNORECASE
            )
            if m:
                docs[s["id"]] = f"# {s['title']}\n\n{m.group(1).strip()}"
                print(f"   ✅ [{s['id']}] extracted via title fallback")
            else:
                print(f"   ⚠️  [{s['id']}] NOT found in output")

    # Post-process Mermaid
    docs = _sanitize_mermaid(docs)

    return docs, token_data


# ---------------------------------------------------------------------------
# Evidence builder – compacts repo signals into a dense JSON object
# ---------------------------------------------------------------------------

def _build_evidence_bundle(
    repo_path: Path,
    analysis: Dict,
    discovery: Optional[DiscoveryReport],
) -> Dict:
    """
    Build a dense evidence bundle for the LLM.
    Includes: file tree, key files' content snippets, tech stack, discovery signals.
    """
    bundle: Dict[str, Any] = {}

    # Basic analysis data
    bundle["tech_stack"] = {
        "languages": analysis.get("languages", []),
        "frameworks": analysis.get("frameworks", []),
        "databases": analysis.get("database_tech", []),
        "deployment": analysis.get("deployment_tech", []),
        "state_management": analysis.get("state_management", []),
    }
    bundle["package_info"] = {
        "name": analysis.get("package_name", ""),
        "description": analysis.get("package_description", ""),
        "version": analysis.get("package_version", ""),
        "scripts": analysis.get("scripts", {}),
    }
    bundle["repo_structure"] = {
        "type": analysis.get("repo_structure", "unknown"),
        "root_directories": analysis.get("root_directories", []),
        "subprojects": list(analysis.get("subprojects", {}).keys()),
    }
    bundle["file_counts"] = {
        "total": analysis.get("file_count", 0),
        "source_files": analysis.get("total_source_files", 0),
        "components": analysis.get("total_components", 0),
        "pages": analysis.get("total_pages", 0),
    }

    # Key file listings
    bundle["key_files"] = {
        "source": analysis.get("source_files", [])[:40],
        "pages": analysis.get("page_files", [])[:15],
        "components": analysis.get("component_files", [])[:15],
        "api": analysis.get("api_files", [])[:15],
        "config": analysis.get("config_files", [])[:10],
    }

    bundle["dependencies"] = _top_dependencies(analysis)

    # Read critical files for content snippets
    bundle["file_snippets"] = _read_critical_files(repo_path, analysis)

    # Discovery signals
    if discovery:
        bundle["discovery"] = {
            "ingress_count": len(discovery.ingress_points),
            "egress_count": len(discovery.egress_points),
            "state_models": [p.name for p in discovery.state_models[:10]],
            "orchestrators": [
                {"file": p.file_path, "role": p.description,
                    "centrality": round(p.centrality_score, 2)}
                for p in sorted(discovery.orchestrators, key=lambda x: -x.centrality_score)[:8]
            ],
            "ingress_samples": [
                {"file": p.file_path, "name": p.name, "type": p.description}
                for p in discovery.ingress_points[:10]
            ],
            "egress_samples": [
                {"file": p.file_path, "type": p.description}
                for p in discovery.egress_points[:10]
            ],
            "constraints": discovery.constraints[:10],
            "brittle_points": discovery.brittle_points[:10],
            "tech_stack": discovery.tech_stack,
            "data_journeys": [
                {
                    "data_type": j.data_type,
                    "from": j.ingress_point,
                    "through": j.transformation_points[:3],
                    "to": j.egress_points[:3],
                }
                for j in discovery.data_journeys[:3]
            ],
        }

    return bundle


def _read_critical_files(repo_path: Path, analysis: Dict) -> Dict[str, str]:
    """Read the most important files and return content snippets."""
    snippets: Dict[str, str] = {}

    SKIP_DIRS = {"node_modules", ".git", "__pycache__",
                 "dist", "build", "venv", ".venv"}
    READ_LIMIT = 3000  # chars per file
    MAX_FILES = 12

    # Priority files to always try to read
    priority_patterns = [
        "package.json", "pyproject.toml", "requirements.txt",
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "README.md", ".env.example",
        # Entry points
        "src/index.ts", "src/main.ts", "src/app.ts", "src/index.js",
        "app/main.py", "main.py", "app.py", "server.py", "server.ts", "server.js",
        # Config
        "tsconfig.json", "next.config.js", "next.config.ts",
        "tailwind.config.js", "vite.config.ts",
    ]

    count = 0
    for pattern in priority_patterns:
        if count >= MAX_FILES:
            break
        target = repo_path / pattern
        if target.exists() and target.is_file():
            try:
                content = target.read_text(
                    encoding="utf-8", errors="ignore")[:READ_LIMIT]
                snippets[pattern] = content
                count += 1
            except Exception:
                pass

    # Also read orchestrators (high-centrality files)
    source_files = analysis.get("source_files", [])
    api_files = analysis.get("api_files", [])
    interesting = list(set(source_files[:8] + api_files[:4]))

    for rel_path in interesting:
        if count >= MAX_FILES:
            break
        if rel_path in snippets:
            continue
        full = repo_path / rel_path
        if full.exists() and full.is_file():
            if any(skip in full.parts for skip in SKIP_DIRS):
                continue
            try:
                content = full.read_text(
                    encoding="utf-8", errors="ignore")[:READ_LIMIT]
                snippets[rel_path] = content
                count += 1
            except Exception:
                pass

    return snippets


def _top_dependencies(analysis: Dict) -> Dict[str, List[str]]:
    """Return the most relevant dependencies."""
    raw_deps = analysis.get("dependencies", {})
    if isinstance(raw_deps, dict):
        # Filter out dev tooling noise
        skip_prefixes = ("@types/", "eslint", "prettier",
                         "typescript", "ts-node", "@testing-library")
        filtered = [k for k in raw_deps if not any(
            k.startswith(p) for p in skip_prefixes)]
        return {"production": filtered[:30]}
    return {"raw": str(raw_deps)[:500]}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _clean_project_name(repo_name: Optional[str], repo_path: Path, analysis: Dict) -> str:
    pkg = analysis.get("package_name", "")
    if pkg and not pkg.startswith("docai"):
        return pkg
    if repo_name and not repo_name.startswith("docai"):
        return repo_name.split("/")[-1] if "/" in repo_name else repo_name
    name = analysis.get("project_name", "")
    if name and not name.startswith("docai"):
        return name
    return repo_path.name


def _infer_repo_type(discovery: Optional[DiscoveryReport], analysis: Dict) -> str:
    rt = analysis.get("repo_structure", "")
    if rt == "monorepo":
        langs = analysis.get("languages", [])
        if "typescript" in [l.lower() for l in langs] or "javascript" in [l.lower() for l in langs]:
            return "fullstack-monorepo"
        return "monorepo"
    fws = [f.lower() for f in analysis.get("frameworks", [])]
    if any(f in fws for f in ["react", "vue", "next.js", "svelte"]):
        if any(f in fws for f in ["fastapi", "express", "django", "flask"]):
            return "fullstack"
        return "frontend"
    if any(f in fws for f in ["fastapi", "express", "django", "flask", "nestjs"]):
        return "backend-api"
    return "unknown"


def _infer_complexity(analysis: Dict) -> int:
    fc = analysis.get("file_count", 0)
    if fc > 500:
        return 9
    if fc > 200:
        return 7
    if fc > 50:
        return 5
    return 3


def _normalise_section(s: Dict) -> Dict:
    return {
        "id": re.sub(r"[^a-z0-9-]", "-", s.get("id", "section").lower()).strip("-"),
        "title": s.get("title", "Untitled Section"),
        "description": s.get("description", ""),
        "subsections": s.get("subsections", []),
    }


def _fallback_sections(evidence: Dict) -> List[Dict]:
    """
    Very basic fallback when the planning call fails.
    Still more specific than the old template – uses detected frameworks.
    """
    frameworks = evidence.get("tech_stack", {}).get("frameworks", [])
    fw_str = ", ".join(frameworks[:3]) if frameworks else "the application"
    return [
        {
            "id": "request-lifecycle",
            "title": f"Tracing Request Lifecycle Through {fw_str}",
            "description": "How a request enters, is processed, and returns a response.",
            "subsections": ["Entry Points", "Middleware Chain", "Response Shaping", "Error Paths"],
        },
        {
            "id": "data-persistence",
            "title": "Persisting & Querying Application State",
            "description": "Database schema, query patterns, and transaction boundaries.",
            "subsections": ["Schema Design", "Read Paths", "Write Paths", "Migrations"],
        },
        {
            "id": "auth-identity",
            "title": "Enforcing Identity & Access Control",
            "description": "Authentication flow, token handling, and authorization checks.",
            "subsections": ["Token Lifecycle", "Auth Middleware", "Permission Model", "Failure Modes"],
        },
    ]


def _make_fallback_docs(planned_sections: List[Dict]) -> Dict[str, str]:
    return {
        s["id"]: f"# {s['title']}\n\nDocumentation unavailable – LLM generation failed. Retry."
        for s in planned_sections
    }


def _sanitize_mermaid(docs: Dict[str, str]) -> Dict[str, str]:
    """Fix common Mermaid syntax errors produced by LLMs."""
    def fix_block(m):
        c = m.group(1)
        c = re.sub(r'\[([^\[\]()]+)\s*\(([^)]+)\)\]',
                   lambda x: f'[{x.group(1).strip()} - {x.group(2).replace("/", " ").strip()}]', c)
        c = re.sub(r'\|([^|()]+)\s*\(([^)]+)\)\|',
                   lambda x: f'|{x.group(1).strip()} via {x.group(2).replace("/", " and ").strip()}|', c)
        c = re.sub(r'\|([^|]*)/([^|]*)\|',
                   lambda x: f'|{x.group(1).strip()} and {x.group(2).strip()}|', c)
        return f'```mermaid\n{c}\n```'

    sanitized = {}
    for k, v in docs.items():
        if isinstance(v, str) and "```mermaid" in v:
            v = re.sub(r'```mermaid\n(.*?)\n```',
                       fix_block, v, flags=re.DOTALL)
        sanitized[k] = v
    return sanitized


# ---------------------------------------------------------------------------
# Backward-compat shim: discovery_integration.py calls these
# ---------------------------------------------------------------------------

def run_discovery_and_generate_sections(repo_path, analysis, persona):
    """
    Shim so discovery_integration.py doesn't break.
    Returns (report, [], archetype_placeholder).
    """
    try:
        report = discover_repository(repo_path, analysis)
    except Exception as exc:
        logger.warning("Discovery shim failed: %s", exc)
        report = None

    from app.services.documentation.archetype_detector import detect_archetype, Archetype
    try:
        archetype = detect_archetype(analysis)
    except Exception:
        archetype = None

    return report, [], archetype


def build_discovery_prompt(*args, **kwargs) -> str:
    """Shim – the new pipeline doesn't use a pre-built discovery prompt."""
    return ""
