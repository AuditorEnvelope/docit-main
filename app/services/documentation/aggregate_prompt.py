"""
Staff Engineer Documentation – Voice-Locked Per-Section Fan-Out

Architecture:
  1. Discovery scanner → raw signals (imports, ingress, egress, state, files)
  2. LLM STEP 1 → decides what sections THIS repo needs (planning call)
  3. LLM STEP 2 → writes EACH section in a dedicated call with TARGETED evidence
     (async fan-out across key pool, same model for voice uniformity)
  4. Validator → structural checks on each section
  5. Assemble → combine all sections into the final docs dict

Key design decisions:
  - Each section gets its own LLM call with FULL evidence for its anchors
  - No prompt compaction ever – prompts are small enough per-section
  - Same model (same provider) for all sections → uniform voice
  - Parallel calls gated by asyncio.Semaphore(pool_size)
  - Per-section retry budget; partial failures don't kill the whole doc
"""

from dataclasses import dataclass, field
import asyncio
import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any

from app.services.llm.rotator import get_rotator, LLMResult
from app.services.documentation.parsing import extract_section
from app.services.documentation.planner import DocumentationPlan
from app.services.documentation.discovery_scanner import (
    DiscoveryReport,
    discover_repository,
)
from app.services.documentation.understanding_builder import build_repo_understanding
from app.services.documentation.section_semantic_validator import (
    is_section_semantically_strong,
    get_semantic_issues,
    build_retry_hint,
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
    Generate Staff Engineer quality documentation via per-section fan-out.

    Pipeline:
      Step 1 – Discovery scanner → raw signals.
      Step 2 – Understanding builder → structured system model (no LLM).
      Step 3 – Evidence bundle.
      Step 4 – Planning call (LLM) → sections + information_needs.
      Step 5…N – Per-section fan-out (LLM) → generation + semantic validation
               + selective retry.
    """
    repo_path = Path(repo_dir) if isinstance(repo_dir, str) else repo_dir
    project_name = _clean_project_name(repo_name, repo_path, analysis)

    print(f"\n{'='*80}")
    print(f"📖 Starting LLM-first documentation for: {project_name}")
    print(f"{'='*80}")

    # ── Step 1: Run discovery scanner ────────────────────────────────────
    print("\n🔭 Running discovery scanner …")
    try:
        discovery_report = discover_repository(repo_path, analysis)
    except Exception as exc:
        logger.warning("Discovery scanner failed: %s", exc)
        discovery_report = None

    # ── Step 2: Build repo understanding (no LLM call) ───────────────────
    print("\n🧩 Building structured system understanding …")
    repo_understanding = build_repo_understanding(discovery_report, analysis)
    print(f"   Components: {len(repo_understanding.get('components', []))}")
    print(f"   Data flows: {len(repo_understanding.get('data_flows', []))}")
    print(f"   API surface: {len(repo_understanding.get('api_surface', []))}")

    # ── Step 3: Build FULL evidence bundle ────────────────────────────────
    evidence = _build_evidence_bundle(repo_path, analysis, discovery_report)
    # Embed understanding into the evidence bundle so planning + generation see it
    evidence["repo_understanding"] = repo_understanding

    # ── Step 4: PLANNING CALL (sync, single call) ────────────────────────
    print("\n🧠 Planning call: asking LLM what sections THIS repo needs …")
    planned_sections = await _planning_call(project_name, persona, evidence)
    print(f"   → Planned {len(planned_sections)} sections:")
    for s in planned_sections:
        print(f"      • [{s['id']}] {s['title']}")

    # ── Step 5: PER-SECTION FAN-OUT (async, parallel) ────────────────────
    print(f"\n✍️  Generating {len(planned_sections)} sections via fan-out …")
    docs, token_data = await _fanout_generation(
        project_name, persona, evidence, planned_sections,
        discovery_report, repo_understanding,
    )

    # ── Step 6: Store plan for downstream writers ────────────────────────
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
# PLANNING CALL (unchanged logic, sync)
# ---------------------------------------------------------------------------

async def _planning_call(
    project_name: str,
    persona: str,
    evidence: Dict,
) -> List[Dict]:
    """Ask the LLM what sections this repo's documentation should have."""

    persona_block = _get_planning_persona_block(persona)

    # Persona-specific title guidance
    if persona not in ("internal", "dev"):
        # Developer persona: user-facing, short titles
        title_guidance = """Title rules for DEVELOPER (user-facing) documentation:
- Titles must be SHORT and CLEAR (2-5 words)
- Write from the USER's perspective — what feature or task is this about?
- Use plain language a non-technical user would understand
- DO NOT use engineering jargon, action verbs like "Orchestrating", or system terms

Examples of GOOD developer doc titles:
  "Wallet Connection & Access"
  "Classroom Setup"
  "Course Content & Materials"
  "Assignments & Grading"
  "Messaging & Communication"
  "User Profile & Settings"
  "Getting Started"

Examples of BAD developer doc titles (FORBIDDEN):
  "Connecting Your Wallet to Access DappClassroom" (too verbose)
  "Orchestrating Request-Response Cycles" (engineering jargon)
  "Enforcing JWT Expiry & Refresh Token Rotation" (internal detail)
  "Propagating Component State Across the Render Tree" (internal detail)"""
    else:
        # Internal persona: intent-based engineering titles
        title_guidance = """Title formula: [Action Verb] + [Specific Domain] + [System Impact / Constraint]
Examples of GOOD titles (use your own, these are just the formula demo):
  "Enforcing JWT Expiry & Refresh Token Rotation"
  "Propagating Component State Across the Render Tree"
  "Serializing Domain Events to the Persistence Layer"

Examples of BAD titles (FORBIDDEN):
  "Overview", "Architecture", "API", "Workflow", "Components", "Database" """

    prompt = f"""You are a Staff Software Engineer (equivalent to Meta L6).
Your job: READ the evidence about a real codebase and decide what documentation
sections it actually needs.

IMPORTANT: This scanner is FULLY ADAPTIVE. It does not know or assume the tech
stack in advance. The evidence below was discovered by structural analysis of
the actual codebase. Your job is to INTERPRET these signals and plan sections
that are specific to what THIS codebase actually does.

DO NOT use generic section names like "Overview", "Architecture", "Workflow".
EVERY title must be specific to THIS codebase, describing what the code does.

{title_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT: {project_name}
PERSONA:
{persona_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADAPTIVE CODEBASE EVIDENCE (discovered, not assumed):
{json.dumps(_slim_evidence_for_planning(evidence), indent=1, default=str)[:14000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO READ THE EVIDENCE:
- "discovery.ingress_samples": Where data enters (routes, CLI, event handlers)
- "discovery.egress_samples": Side effects (DB writes, HTTP calls, file I/O)
- "discovery.state_models": Data structures / entities the system remembers
- "discovery.orchestrators": High-centrality files that coordinate flow
- "discovery.directory_roles": What each directory does (ingress/state/egress)
- "discovery.language_profile": Which languages and how many files each
- "discovery.file_role_summary": Files grouped by role
- "tech_stack": Dependencies and frameworks from actual manifest files
- "file_snippets": Content of key files for reference
- "existing_documentation": EXISTING human-written docs (READMEs, ADRs, changelogs)
- "api_specifications": OpenAPI/Swagger specs – real API contracts
- "ci_cd_pipelines": CI/CD workflow configs – document deployment pipeline
- "schema_definitions": Proto/GraphQL/Prisma schemas – data contracts
- "infrastructure": Terraform/Helm/K8s configs – production topology

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: Return ONLY a JSON array (no markdown, no explanation) of 5–9 sections.
Each section object must have exactly these keys:
  "id"              – slug, e.g. "jwt-refresh-rotation"
  "title"           – intent-based title (see formula above)
  "description"     – 1 sentence: what an engineer will learn from this section
  "subsections"     – list of 4–7 specific sub-headings
  "evidence_anchors"– list of 3–8 file paths from the evidence that are MOST
                      relevant for writing THIS section (enables targeted evidence)
  "information_needs"– list of 2–4 specific questions this section must answer
                      (e.g. "How does token refresh work?", "What DB tables are involved?")
  "complexity"      – one of: "low", "medium", "high" (how much evidence is needed)

Base sections ENTIRELY on the evidence. If you don't see evidence for something,
don't invent a section for it.

STRICT NO-HALLUCINATION CHECK before returning your plan:
- For each section, verify its topic appears in the evidence. If it doesn't,
  DROP that section. Do not pad the plan with generic infra/deployment/
  orchestration sections when no such evidence exists.
- Specifically: NO Kubernetes, AWS, Docker, Terraform, Helm, Redis, Kafka,
  gRPC, service-mesh, or microservices sections unless those tools are
  visible in tech_stack / dependencies / infrastructure / file_snippets.
- Each section's "evidence_anchors" must list REAL file paths from the
  evidence above. Fabricated paths = plan rejected.

Return ONLY valid JSON. No prose before or after.
"""

    rotator = get_rotator()
    result = rotator.generate_with_rotation(prompt)

    if not result:
        return _fallback_sections(evidence)

    raw = result.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        sections = json.loads(raw)
        if isinstance(sections, list) and sections:
            return [_normalise_section(s) for s in sections if isinstance(s, dict)]
    except json.JSONDecodeError as exc:
        logger.warning(
            "Planning call JSON parse failed: %s\nRaw: %s", exc, raw[:500])

    return _fallback_sections(evidence)


# ---------------------------------------------------------------------------
# PER-SECTION FAN-OUT (the core change)
# ---------------------------------------------------------------------------

async def _fanout_generation(
    project_name: str,
    persona: str,
    evidence: Dict,
    planned_sections: List[Dict],
    discovery: Optional[DiscoveryReport],
    repo_understanding: Optional[Dict] = None,
) -> Tuple[Dict[str, str], Dict]:
    """
    Generate each section in its own LLM call, fanning out across the
    preferred provider's key pool.

    NEW: Includes semantic validation + selective retry + cross-section context.

    Returns (docs_dict, aggregated_token_data).
    """
    rotator = get_rotator()
    provider = rotator.get_preferred_provider()
    if not provider:
        logger.error("No healthy provider for generation")
        return _make_fallback_docs(planned_sections), _empty_token_data()

    pool_size = max(1, len(provider.healthy_slots()))
    concurrency = int(os.getenv("DOC_GENERATION_CONCURRENCY", str(pool_size)))
    sem = asyncio.Semaphore(concurrency)

    print(
        f"🔀 Using {provider.name} ({pool_size} key slots, concurrency={concurrency})")

    persona_block = _get_generation_persona_block(persona)
    quality_rules = _get_quality_rules(persona)

    # Build per-section targeted evidence + prompt
    section_prompts: Dict[str, str] = {}
    for section in planned_sections:
        targeted_evidence = _build_targeted_evidence(
            section, evidence, discovery, repo_understanding, persona
        )
        section_prompts[section["id"]] = _build_section_prompt(
            project_name, persona_block, quality_rules,
            section, targeted_evidence, repo_understanding,
        )

    # Cross-section summaries: populated as sections complete
    completed_summaries: Dict[str, str] = {}
    completed_lock = asyncio.Lock()

    # Fan-out with semantic validation + selective retry
    async def _gen_one(section: Dict) -> Tuple[str, Optional[LLMResult]]:
        async with sem:
            sid = section["id"]
            print(f"   📝 [{sid}] generating …")

            # Add cross-section context if available
            prompt = section_prompts[sid]
            async with completed_lock:
                if completed_summaries:
                    cross_ctx = _build_cross_section_context(
                        completed_summaries)
                    prompt = prompt + cross_ctx

            result = await rotator.generate_with_pool(
                prompt, provider=provider, max_retries=3,
            )

            if not result:
                print(f"   ❌ [{sid}] FAILED after retries")
                return sid, None

            # Extract content
            tag = sid.upper().replace("-", "_")
            content = extract_section(result.content, tag)
            if not content:
                raw = result.content.strip()
                raw = re.sub(r'<[A-Z_]+_START>\s*', '', raw)
                raw = re.sub(r'\s*<[A-Z_]+_END>', '', raw)
                content = raw.strip()

            # Semantic validation + selective retry
            if content and not is_section_semantically_strong(content, repo_understanding):
                issues = get_semantic_issues(content, repo_understanding)
                retry_hint = build_retry_hint(issues)
                print(
                    f"   ⚠️  [{sid}] semantically weak ({', '.join(i.split(':')[0] for i in issues)}), retrying …")

                # Build stronger retry prompt
                retry_prompt = prompt + retry_hint
                retry_result = await rotator.generate_with_pool(
                    retry_prompt, provider=provider, max_retries=2,
                )
                if retry_result:
                    retry_content = extract_section(retry_result.content, tag)
                    if not retry_content:
                        raw = retry_result.content.strip()
                        raw = re.sub(r'<[A-Z_]+_START>\s*', '', raw)
                        raw = re.sub(r'\s*<[A-Z_]+_END>', '', raw)
                        retry_content = raw.strip()

                    # Use retry only if it's actually better
                    if retry_content and len(retry_content) >= len(content) * 0.8:
                        content = retry_content
                        # Add retry tokens to the original result
                        result = LLMResult(
                            content=retry_result.content,
                            model_name=retry_result.model_name,
                            input_tokens=result.input_tokens + retry_result.input_tokens,
                            output_tokens=result.output_tokens + retry_result.output_tokens,
                            total_tokens=result.total_tokens + retry_result.total_tokens,
                        )
                        print(f"   ✅ [{sid}] retry improved quality")
                    else:
                        print(
                            f"   ℹ️  [{sid}] keeping original (retry not better)")

            if content:
                print(f"   ✅ [{sid}] done ({len(content)} chars)")
                # Build a short summary for cross-section context
                summary = _summarize_section(
                    content, section.get("title", sid))
                async with completed_lock:
                    completed_summaries[sid] = summary

                # Overwrite result content with extracted content
                result = LLMResult(
                    content=content,
                    model_name=result.model_name,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    total_tokens=result.total_tokens,
                )
            else:
                print(f"   ❌ [{sid}] empty content after extraction")
                result = None

            return sid, result

    results = await asyncio.gather(
        *[_gen_one(s) for s in planned_sections],
        return_exceptions=True,
    )

    # Assemble docs + aggregate tokens
    docs: Dict[str, str] = {}
    total_in = 0
    total_out = 0
    model_name = provider.name

    for item in results:
        if isinstance(item, Exception):
            logger.error("Section generation raised: %s", item)
            continue
        sid, result = item
        if result:
            docs[sid] = result.content
            total_in += result.input_tokens
            total_out += result.output_tokens
            model_name = result.model_name

    # Post-process mermaid
    docs = _sanitize_mermaid(docs)

    # Log missing sections
    for s in planned_sections:
        if s["id"] not in docs:
            print(f"   ⚠️  [{s['id']}] NOT generated – will show as missing")

    token_data = {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "model_name": model_name,
    }
    return docs, token_data


# ---------------------------------------------------------------------------
# Per-section prompt builder
# ---------------------------------------------------------------------------

def _build_section_prompt(
    project_name: str,
    persona_block: str,
    quality_rules: str,
    section: Dict,
    targeted_evidence: Dict,
    repo_understanding: Optional[Dict] = None,
) -> str:
    """Build a focused prompt for writing ONE section.

    Uses structured understanding as primary context, with raw snippets
    only as supplementary evidence. This produces more system-aware output.
    """

    sub_text = "\n".join(f"## {sub}" for sub in section.get("subsections", []))
    tag = section["id"].upper().replace("-", "_")

    # Information needs from the planner (if available)
    info_needs = section.get("information_needs", [])
    info_needs_block = ""
    if info_needs:
        info_needs_block = (
            "\n\nKEY QUESTIONS THIS SECTION MUST ANSWER:\n"
            + "\n".join(f"- {q}" for q in info_needs)
        )

    return f"""You are generating high-quality technical documentation for a real codebase.

PROJECT: {project_name}

{persona_block}

{quality_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WRITING PROCESS (follow this order):
Step 1: Understand the system using the SYSTEM CONTEXT below.
        Identify all components, their roles, and how they connect.
Step 2: For THIS section, identify the key flows, responsibilities, and
        integration points from the SECTION-SPECIFIC EVIDENCE.
Step 3: Write a clear, structured section that explains HOW the system
        works — not just WHAT it does. Reference real components by name.

STRICT RULES:
- DO NOT write generic statements. Every sentence must be specific to THIS codebase.
- ALWAYS reference real components, files, flows, and APIs from the evidence.
- Explain HOW the system works: data flow, control flow, error paths.
- If something is unclear from the evidence, say: "Not enough evidence found."
- Every paragraph must add concrete, actionable information.

EVIDENCE-ONLY RULE (CRITICAL — NO HALLUCINATION):
- Every technology, tool, file path, class name, env var, table, and config
  value you mention MUST be visible somewhere in the SYSTEM CONTEXT,
  SECTION-SPECIFIC EVIDENCE, or SUPPLEMENTARY CODE SNIPPETS below.
- DO NOT introduce Kubernetes, Docker, AWS, Terraform, Redis, Kafka, gRPC,
  service mesh, or any tool/platform unless it appears in the evidence.
- DO NOT write speculative content like "typically deployed on...",
  "usually scaled via...", "can be orchestrated with...". If the evidence
  doesn't show it, it doesn't exist for this codebase.
- If a required sub-heading has no supporting evidence, write one honest
  sentence: "Not enough evidence found in this codebase." Do not fabricate.

BANNED PHRASES (instant quality failure):
- "This module handles..."
- "This component is responsible for..."
- "This system is designed to..."
- "It provides scalability and flexibility"
- "Robust and efficient"
- "Overview", "In summary...", "This section covers..."
- Any single-sentence paragraph (every paragraph needs substance)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM CONTEXT (structured understanding of the full codebase):
{json.dumps(targeted_evidence.get('system_context', {}), indent=1, default=str)[:4000]}

SECTION-SPECIFIC EVIDENCE:
{json.dumps(targeted_evidence.get('section_context', {}), indent=1, default=str)[:5000]}

SUPPLEMENTARY CODE SNIPPETS (use only to cite specifics):
{json.dumps(targeted_evidence.get('raw_evidence', {}), indent=1, default=str)[:3000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK: Write ONE section of documentation.

Section ID: {section['id']}
Section Title: {section['title']}
Description: {section['description']}
Required Sub-headings:
{sub_text}
{info_needs_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MERMAID DIAGRAM RULES:
- No parentheses anywhere in node labels or edge labels
- No slashes in labels (use "and" instead of "/")
- Only: graph TD, A[Label] --> B[Label], A --> |edge label| B
- NO classDef, NO style, NO fill

OUTPUT FORMAT (use EXACT tags):
<{tag}_START>
# {section['title']}

{sub_text}

[Write detailed technical content here]
<{tag}_END>

Write ONLY the tagged section. No preamble. No summary after.
MINIMUM 700 words of dense, specific, actionable content.
"""


def _build_targeted_evidence(
    section: Dict,
    full_evidence: Dict,
    discovery: Optional[DiscoveryReport],
    repo_understanding: Optional[Dict] = None,
    persona: str = "internal",
) -> Dict:
    """Build a structured evidence pack with 3 tiers:

    1. system_context  – from repo_understanding (always included, compact)
    2. section_context – relevant components, flows, behaviors for THIS section
    3. raw_evidence    – minimal file snippets (max 3 files from evidence_anchors)

    This replaces the old approach of dumping all snippets into the prompt.
    """
    targeted: Dict[str, Any] = {}

    # ── Tier 1: System context (from understanding builder) ───────────
    understanding = repo_understanding or full_evidence.get(
        "repo_understanding", {})
    is_developer = persona not in ("internal", "dev")

    if is_developer:
        # Developer persona: strip internal details, keep high-level summary only
        targeted["system_context"] = {
            "system_summary": understanding.get("system_summary", ""),
            "tech_stack": full_evidence.get("tech_stack", {}),
        }
    else:
        targeted["system_context"] = {
            "system_summary": understanding.get("system_summary", ""),
            "components": understanding.get("components", [])[:10],
            "tech_stack": full_evidence.get("tech_stack", {}),
            "dependencies": full_evidence.get("dependencies", {}),
        }

    # ── Tier 2: Section-specific context ────────────────────────────
    section_ctx: Dict[str, Any] = {}

    # Find relevant components for this section
    section_title_lower = section.get("title", "").lower()
    section_desc_lower = section.get("description", "").lower()
    section_text = section_title_lower + " " + section_desc_lower

    if understanding.get("components") and not is_developer:
        # Internal: include relevant components with full detail
        relevant_components = [
            c for c in understanding["components"]
            if _is_relevant_to_section(c, section_text)
        ]
        # If no specific match, include top 5 by centrality
        if not relevant_components:
            relevant_components = understanding["components"][:5]
        section_ctx["relevant_components"] = relevant_components[:8]

    # Relevant data flows
    if understanding.get("data_flows"):
        section_ctx["relevant_flows"] = [
            f for f in understanding["data_flows"]
            if any(kw in f.lower() for kw in section_text.split()[:6])
        ] or understanding["data_flows"][:3]

    # Key behaviors
    if understanding.get("key_behaviors"):
        if is_developer:
            # Developer: translate behaviors to user-facing descriptions
            section_ctx["key_behaviors"] = [
                b for b in understanding["key_behaviors"][:5]
                if not any(kw in b.lower() for kw in ["internal", "private", "cron", "worker", "migration"])
            ]
        else:
            section_ctx["key_behaviors"] = understanding["key_behaviors"][:5]

    # API surface (if section is about API/routes/endpoints)
    if understanding.get("api_surface") and any(
        kw in section_text for kw in ["api", "route", "endpoint", "request", "entry"]
    ):
        section_ctx["api_surface"] = understanding["api_surface"][:8]

    # Storage — INTERNAL ONLY (never expose DB details to developer persona)
    if not is_developer and understanding.get("storage") and any(
        kw in section_text for kw in ["data", "state", "persist", "storage", "model", "schema"]
    ):
        section_ctx["storage"] = understanding["storage"][:6]

    # Integrations (if section is about external services)
    if understanding.get("external_integrations") and any(
        kw in section_text for kw in ["integrat", "external", "third", "service", "protocol"]
    ):
        section_ctx["external_integrations"] = understanding["external_integrations"][:5]

    # Include discovery signals (compact, very useful)
    if "discovery" in full_evidence:
        section_ctx["discovery_signals"] = full_evidence["discovery"]

    # Include existing docs (rich context — especially critical for developer persona
    # since SDK/API info must come from explicitly documented sources)
    if "existing_documentation" in full_evidence:
        section_ctx["existing_documentation"] = full_evidence["existing_documentation"]

    # Information needs from planner
    if section.get("information_needs"):
        section_ctx["information_needs"] = section["information_needs"]

    targeted["section_context"] = section_ctx

    # ── Tier 3: Raw evidence (minimal, max 3 anchor files) ───────────
    anchors = section.get("evidence_anchors", [])
    all_snippets = full_evidence.get("file_snippets", {})
    raw_snippets: Dict[str, str] = {}
    max_raw_files = 3  # Aggressive limit — understanding carries the context

    for anchor in anchors:
        if len(raw_snippets) >= max_raw_files:
            break
        if anchor in all_snippets:
            raw_snippets[anchor] = all_snippets[anchor][:2000]
        else:
            for path, content in all_snippets.items():
                if path.endswith(anchor) or anchor.endswith(path):
                    raw_snippets[anchor] = content[:2000]
                    break

    # Fallback: if no anchors matched, include top 3 global snippets
    if not raw_snippets:
        for k, v in list(all_snippets.items())[:3]:
            raw_snippets[k] = v[:2000]

    targeted["raw_evidence"] = raw_snippets

    # CI/CD, schemas, infra – include if present and relevant
    # Developer persona: skip internal infra details
    extra_keys = ["ci_cd_pipelines", "schema_definitions",
                  "infrastructure", "api_specifications"]
    if is_developer:
        # Only public API specs for developer persona
        extra_keys = ["api_specifications"]
    for key in extra_keys:
        if key in full_evidence:
            targeted["raw_evidence"][key] = full_evidence[key]

    return targeted


# ---------------------------------------------------------------------------
# Persona blocks & quality rules (extracted for reuse)
# ---------------------------------------------------------------------------

def _get_planning_persona_block(persona: str) -> str:
    if persona in ("internal", "dev"):
        return """INTERNAL DOCUMENTATION – THE SURGEON'S MANUAL

Audience: A new backend/fullstack engineer joining the team on Day 1.
Goal: After reading this, they can debug a production incident at 2 AM WITHOUT
asking anyone for help.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE COVERAGE REQUIREMENT (for internal docs):
The plan MUST include sections that expose HOW the codebase is wired, so a new
engineer understands the system's shape. At minimum, include sections that cover
(when the evidence supports them — skip what doesn't apply):
  • File & module structure — how the repo is organized, what each directory owns
  • Request/data flow — how a request/event travels from entry point to response
  • API surface — routes, handlers, request/response contracts (only if API exists)
  • Data model & persistence — schemas, tables, state models (only if DB/state exists)
  • Core orchestrators — the high-centrality files that coordinate business logic
  • External integrations — third-party services, webhooks, outbound calls
  • Background/async work — jobs, queues, schedulers (only if they exist)
Prefer SPECIFIC titles that name the actual subsystem (e.g. "Section Fan-Out
& Semantic Validation Pipeline" instead of generic "Architecture").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ANTI-HALLUCINATION RULE (CRITICAL):
- Only plan sections for technologies, patterns, and concepts that are PRESENT
  in the evidence (tech_stack, file_snippets, dependencies, discovery signals,
  ci_cd_pipelines, infrastructure).
- DO NOT invent sections about Kubernetes, AWS, Docker, Terraform, Redis, Kafka,
  gRPC, microservices, or any tool/pattern that is NOT visible in the evidence.
- If no CI/CD pipeline is in evidence, DO NOT plan a deployment-pipeline section.
- If no infrastructure-as-code is in evidence, DO NOT plan an infra/orchestration
  section.
- Ground every planned section in a concrete evidence anchor (file, route,
  dependency, or discovery signal). If you cannot cite one, drop the section.

WHAT TO DOCUMENT (go DEEP on every one that is supported by evidence):
- Complete system onboarding: how to set up, run, test, and deploy locally
- Every service, module, and package – what it does, who calls it, what it mutates
- Database schema: every table, every column, every index, every migration pattern
- Authentication & authorization internals: token lifecycle, refresh logic, session storage
- Transaction boundaries: where do writes happen? What's atomic? What can partially fail?
- Error handling chains: what exceptions propagate where, retry policies
- Environment variables & config: every env var, what it controls, what breaks if missing
- Inter-service communication: protocols, serialization, timeout values
- Background jobs, cron tasks, workers: what runs, when, what happens if it fails
- Deployment pipeline: ONLY if CI/CD evidence exists — build steps, staging gates, rollback

EVERY section must have:
- Actual file paths and function/class names from the evidence
- Code snippets showing real patterns (not pseudo-code)
- Data flow diagrams (Mermaid) showing how data moves through the system
- Specific numbers: timeout values, retry counts, connection pool sizes

MINIMUM 600 words per section."""
    else:
        return """DEVELOPER DOCUMENTATION – THE USER'S GUIDE

Audience: An external developer or end-user who wants to USE this product/platform.
They do NOT care about internal code, implementation details, or how you built it.

CRITICAL RULE: ZERO INTERNAL CODE EXPOSURE
- NEVER mention internal function names, private methods, internal file paths
- NEVER show internal code snippets or implementation logic
- NEVER discuss database schemas, internal service architecture
- NEVER explain HOW something was built — only explain HOW TO USE it

SDK / API DOCUMENTATION RULE:
- ONLY document an SDK, API, or library if it is EXPLICITLY mentioned in the
  project's existing README, documentation files, code comments, or public exports.
- If no SDK/API is explicitly documented or exported, DO NOT invent or assume one.
- For SDK/API that IS explicitly documented: show method signatures, parameters,
  return types, and working code examples.

UI / FRONTEND PROJECT RULE:
- If this is a UI/frontend project with no public SDK, document FEATURES from the
  user's perspective: what the user sees, what they can do, step-by-step workflows.
- Describe screens, buttons, forms, and user journeys — NOT components or code.

WHAT TO DOCUMENT:
- Complete user journey: from first visit/signup to achieving their goal
- Every feature the user can access: describe it as the user EXPERIENCES it
- SDK/API reference ONLY if explicitly present in existing docs/README/exports
- UI walkthrough: every screen, every button, every workflow
- Integration guides: how to connect this product to other tools/services
- Troubleshooting from the USER's perspective

MINIMUM 600 words per section."""


def _get_generation_persona_block(persona: str) -> str:
    if persona in ("internal", "dev"):
        return """INTERNAL DOCUMENTATION – THE SURGEON'S MANUAL

You are writing for a new engineer who just joined the team. After reading your
documentation, they must be able to:
1. Set up the entire project locally from scratch
2. Understand how every request flows through the system end-to-end
3. Debug any production incident at 2 AM without waking anyone up
4. Understand every database table, migration pattern, and query hotspot
5. Know where every environment variable is used and what breaks without it

WRITING RULES:
- EXHAUSTIVE DETAIL: If you mention a service, list every method it exposes
- REAL CODE: Show actual code snippets from the evidence. No pseudo-code.
- FAILURE MODES: Every section MUST have a "What breaks and how to fix it" subsection
- FILE PATHS: Reference actual files from the evidence
- NUMBERS: Connection pool sizes, timeout values, retry counts – be specific
- FLOW DIAGRAMS: Include Mermaid diagrams showing data flow

ANTI-HALLUCINATION RULE (ZERO TOLERANCE):
- Document ONLY what is present in the evidence. If the evidence does not show
  Kubernetes, AWS, Docker, Terraform, Redis, Kafka, gRPC, service mesh, or any
  other technology, DO NOT mention it. DO NOT add "Orchestration Considerations
  with Kubernetes" or "AWS Infrastructure" sections if those tools aren't in
  the tech_stack, dependencies, or infrastructure evidence.
- If the section title implies a topic that has NO evidence, say "Not enough
  evidence found in this codebase" for that subsection — do NOT fabricate
  content to fill space.
- Every technology, file path, class name, env var, and config value you mention
  MUST appear verbatim somewhere in the evidence provided to you.
- Speculation is forbidden. If you find yourself writing "typically", "usually",
  "often deployed on", "can be scaled via" — STOP. That is hallucination.

BANNED:
- "This module handles..." – instead, say exactly WHAT it does and HOW
- Vague one-liners – every paragraph must add concrete, actionable information
- Inventing deployment/infra content when no infra evidence exists"""
    else:
        return """DEVELOPER DOCUMENTATION – THE USER'S GUIDE

You are writing for an external developer or end-user who wants to USE this product.
They don't know or care about your internal code.

ABSOLUTE RULE: ZERO INTERNAL CODE EXPOSURE
- NEVER mention internal function names, private methods, or class names
- NEVER show internal code snippets, file paths, or implementation logic
- NEVER discuss database schemas, internal services, or infrastructure
- NEVER explain HOW the system is built — only HOW the user interacts with it
- If the evidence shows internal code, TRANSLATE it into user-facing language

SDK / API VISIBILITY RULE:
- ONLY document SDKs, APIs, or libraries that are EXPLICITLY mentioned in the
  project's existing README, docs, code comments, or public exports.
- If the codebase has no explicitly documented public SDK/API, do NOT invent one.
- For SDKs/APIs that ARE explicitly documented: provide method signatures,
  parameters, return types, and working code examples.

UI / FRONTEND PROJECT RULE:
- If this is a UI or frontend project with no public SDK:
  → Document every FEATURE from the user's point of view
  → Describe what the user sees, what buttons they click, what forms they fill
  → Walk through every user workflow step-by-step
  → NEVER describe React components, state management, or internal architecture

WHAT TO DOCUMENT:
- COMPLETE USER JOURNEY: Walk through every step from signup to success
- EVERY USER-FACING FEATURE: Describe what the user sees and can do
- SDK/API REFERENCE: ONLY if explicitly documented in existing docs/README/exports
- UI WALKTHROUGH: Describe every screen, every button, every workflow
- INTEGRATION GUIDES: Step-by-step instructions for connecting external services

WRITING STYLE:
- Write like Stripe, Vercel, or Notion docs: warm, clear, action-oriented
- Use "you" language: "You can...", "To get started..."
- Include numbered step-by-step instructions for EVERY workflow"""


def _get_quality_rules(persona: str) -> str:
    if persona in ("internal", "dev"):
        return """QUALITY REQUIREMENTS (NON-NEGOTIABLE):
- MINIMUM 700 words per section. If under 700 words, you haven't gone deep enough.
- Every section MUST include at least one Mermaid diagram OR detailed code snippet
- Every section MUST reference at least 3 specific files from the evidence
- Every section MUST have a "Failure Modes" subsection
- Include exact file paths, function signatures, config keys, and error messages
- The "So What?" test: Would this help an on-call engineer right now? If NO, rewrite."""
    else:
        return """QUALITY REQUIREMENTS (NON-NEGOTIABLE):
- MINIMUM 700 words per section. Be EXHAUSTIVELY descriptive.
- Every section MUST include step-by-step instructions or working examples
- Every section MUST be written from the USER's perspective, not the builder's
- A user should NEVER have to guess how something works after reading your docs
- Include user-flow diagrams for every major feature
- NEVER expose ANY internal implementation detail, file path, or class name. Period.
- SDK/API sections are ONLY allowed if the project explicitly documents a public SDK/API.
  If no SDK exists, write about features and user workflows instead.
- The "User Test": Would an end-user understand this without reading source code? If NO, rewrite."""


# ---------------------------------------------------------------------------
# Evidence builder – compacts repo signals into a dense JSON object
# ---------------------------------------------------------------------------

def _build_evidence_bundle(
    repo_path: Path,
    analysis: Dict,
    discovery: Optional[DiscoveryReport],
) -> Dict:
    """Build a dense evidence bundle for the LLM."""
    bundle: Dict[str, Any] = {}

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

    bundle["key_files"] = {
        "source": analysis.get("source_files", [])[:40],
        "pages": analysis.get("page_files", [])[:15],
        "components": analysis.get("component_files", [])[:15],
        "api": analysis.get("api_files", [])[:15],
        "config": analysis.get("config_files", [])[:10],
    }

    bundle["dependencies"] = _top_dependencies(analysis)
    bundle["file_snippets"] = _read_critical_files(repo_path, analysis)

    # ── Adaptive discovery signals ────────────────────────────────────
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
                {"file": p.file_path, "name": p.name, "signals": p.description}
                for p in discovery.ingress_points[:12]
            ],
            "egress_samples": [
                {"file": p.file_path, "name": p.name, "signals": p.description}
                for p in discovery.egress_points[:12]
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

        if discovery.language_profile:
            bundle["discovery"]["language_profile"] = discovery.language_profile
        if discovery.directory_roles:
            bundle["discovery"]["directory_roles"] = dict(
                list(discovery.directory_roles.items())[:20]
            )
        if discovery.file_role_summary:
            bundle["discovery"]["file_role_summary"] = {
                role: files[:8]
                for role, files in discovery.file_role_summary.items()
            }
        if discovery.manifest_data:
            bundle["discovery"]["manifests_found"] = list(
                discovery.manifest_data.keys())

        if discovery.key_file_snippets:
            for k, v in discovery.key_file_snippets.items():
                if k not in bundle["file_snippets"]:
                    bundle["file_snippets"][k] = v

        if discovery.existing_docs:
            bundle["existing_documentation"] = {
                rel: content[:2000]
                for rel, content in list(discovery.existing_docs.items())[:10]
            }
        if discovery.api_specs:
            bundle["api_specifications"] = {
                rel: content[:2000]
                for rel, content in list(discovery.api_specs.items())[:3]
            }
        if discovery.ci_cd_configs:
            bundle["ci_cd_pipelines"] = {
                rel: content[:1500]
                for rel, content in list(discovery.ci_cd_configs.items())[:5]
            }
        if discovery.schema_files:
            bundle["schema_definitions"] = {
                rel: content[:2000]
                for rel, content in list(discovery.schema_files.items())[:5]
            }
        if discovery.infra_configs:
            bundle["infrastructure"] = {
                rel: content[:1500]
                for rel, content in list(discovery.infra_configs.items())[:4]
            }

    return bundle


def _read_critical_files(repo_path: Path, analysis: Dict) -> Dict[str, str]:
    """Read the most important files and return content snippets."""
    snippets: Dict[str, str] = {}
    SKIP_DIRS = {"node_modules", ".git", "__pycache__",
                 "dist", "build", "venv", ".venv"}
    READ_LIMIT = 4000  # chars per file — generous since per-section prompts are small
    MAX_FILES = 20

    priority_patterns = [
        "package.json", "pyproject.toml", "requirements.txt",
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "README.md", ".env.example",
        "src/index.ts", "src/main.ts", "src/app.ts", "src/index.js",
        "app/main.py", "main.py", "app.py", "server.py", "server.ts", "server.js",
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

    source_files = analysis.get("source_files", [])
    api_files = analysis.get("api_files", [])
    interesting = list(set(source_files[:12] + api_files[:6]))

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
    raw_deps = analysis.get("dependencies", {})
    if isinstance(raw_deps, dict):
        skip_prefixes = ("@types/", "eslint", "prettier",
                         "typescript", "ts-node", "@testing-library")
        filtered = [k for k in raw_deps if not any(
            k.startswith(p) for p in skip_prefixes)]
        return {"production": filtered[:30]}
    return {"raw": str(raw_deps)[:500]}


# ---------------------------------------------------------------------------
# Cross-section context & helpers
# ---------------------------------------------------------------------------

def _build_cross_section_context(completed_summaries: Dict[str, str]) -> str:
    """Build a compact cross-section context block to append to prompts.

    This helps sections avoid repeating what earlier sections covered and
    maintain consistency across the document.
    """
    if not completed_summaries:
        return ""

    lines = [
        "\n\n━━━ ALREADY-WRITTEN SECTIONS (avoid repetition, maintain consistency) ━━━"]
    # max 5 summaries
    for sid, summary in list(completed_summaries.items())[:5]:
        lines.append(f"• [{sid}]: {summary}")
    lines.append("━━━ END OF CROSS-SECTION CONTEXT ━━━")
    return "\n".join(lines)


def _summarize_section(content: str, title: str) -> str:
    """Build a 1-2 sentence summary of a completed section for cross-section context.

    This is purely heuristic — no LLM call.
    """
    # Take first non-heading, non-empty paragraph
    lines = content.split("\n")
    for line in lines:
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith("```")
            and not stripped.startswith("---")
            and not stripped.startswith("━")
            and len(stripped) > 40
        ):
            # Truncate to ~150 chars
            return stripped[:150] + ("…" if len(stripped) > 150 else "")

    return f"Covers: {title}"


def _slim_evidence_for_planning(evidence: Dict) -> Dict:
    """Create a lighter evidence bundle for the planning call.

    The planning call only needs to understand WHAT the repo contains,
    not the full file content. This reduces planning token usage.
    """
    slim: Dict[str, Any] = {}

    # Keep structured understanding (compact, high-value)
    if "repo_understanding" in evidence:
        slim["repo_understanding"] = evidence["repo_understanding"]

    # Keep metadata
    for key in ["tech_stack", "package_info", "repo_structure",
                "file_counts", "key_files", "dependencies"]:
        if key in evidence:
            slim[key] = evidence[key]

    # Keep discovery signals (already compact)
    if "discovery" in evidence:
        slim["discovery"] = evidence["discovery"]

    # Keep existing docs, API specs, CI/CD (but NOT full file snippets)
    for key in ["existing_documentation", "api_specifications",
                "ci_cd_pipelines", "schema_definitions", "infrastructure"]:
        if key in evidence:
            slim[key] = evidence[key]

    # Include file snippet KEYS only (not content) — planner needs to know
    # which files exist so it can assign evidence_anchors
    if "file_snippets" in evidence:
        slim["available_file_snippets"] = list(
            evidence["file_snippets"].keys())

    return slim


def _is_relevant_to_section(component: Dict, section_text: str) -> bool:
    """Check if a component is likely relevant to a section based on keywords."""
    comp_text = (
        component.get("name", "") + " " +
        component.get("responsibility", "") + " " +
        component.get("file", "")
    ).lower()

    # Check for any word overlap (simple but effective)
    section_words = set(section_text.split())
    # Remove common stop words
    stop_words = {"the", "and", "for", "with", "from",
                  "into", "via", "a", "an", "of", "to", "in"}
    section_words -= stop_words

    for word in section_words:
        if len(word) > 3 and word in comp_text:
            return True
    return False


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
        "evidence_anchors": s.get("evidence_anchors", []),
        "information_needs": s.get("information_needs", []),
        "complexity": s.get("complexity", "medium"),
    }


def _fallback_sections(evidence: Dict) -> List[Dict]:
    frameworks = evidence.get("tech_stack", {}).get("frameworks", [])
    fw_str = ", ".join(frameworks[:3]) if frameworks else "the application"
    return [
        {
            "id": "request-lifecycle",
            "title": f"Tracing Request Lifecycle Through {fw_str}",
            "description": "How a request enters, is processed, and returns a response.",
            "subsections": ["Entry Points", "Middleware Chain", "Response Shaping", "Error Paths"],
            "evidence_anchors": [],
        },
        {
            "id": "data-persistence",
            "title": "Persisting & Querying Application State",
            "description": "Database schema, query patterns, and transaction boundaries.",
            "subsections": ["Schema Design", "Read Paths", "Write Paths", "Migrations"],
            "evidence_anchors": [],
        },
        {
            "id": "auth-identity",
            "title": "Enforcing Identity & Access Control",
            "description": "Authentication flow, token handling, and authorization checks.",
            "subsections": ["Token Lifecycle", "Auth Middleware", "Permission Model", "Failure Modes"],
            "evidence_anchors": [],
        },
    ]


def _make_fallback_docs(planned_sections: List[Dict]) -> Dict[str, str]:
    return {
        s["id"]: f"# {s['title']}\n\nDocumentation unavailable – LLM generation failed. Retry."
        for s in planned_sections
    }


def _empty_token_data() -> Dict:
    return {"input_tokens": 0, "output_tokens": 0, "model_name": "unknown"}


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
    return ""
