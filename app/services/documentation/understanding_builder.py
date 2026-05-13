"""
Understanding Builder – Produces a structured, token-efficient system
understanding from raw DiscoveryReport signals.

This is a PURE PYTHON pass (no LLM calls). It transforms verbose raw
discovery data into a compact semantic model the LLM can reason about
efficiently, replacing raw code dumps in prompts.

The output dict is designed to be:
  - Short enough to fit in every per-section prompt
  - Rich enough that the LLM understands the whole system
  - Structured so the LLM can reference real components by name
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.documentation.discovery_scanner import (
    DiscoveryReport,
    DiscoveredPrimitive,
    DataJourney,
)


def build_repo_understanding(
    discovery: Optional[DiscoveryReport],
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a structured, compressed understanding of the repository.

    Uses ONLY the DiscoveryReport (and optionally the codebase analysis)
    — no LLM call is made here.

    Returns a dict with keys:
        system_summary, components, data_flows, api_surface,
        storage, external_integrations, key_behaviors
    """
    if not discovery:
        return _empty_understanding()

    analysis = analysis or {}

    return {
        "system_summary": _build_system_summary(discovery, analysis),
        "components": _build_components(discovery),
        "data_flows": _build_data_flows(discovery),
        "api_surface": _build_api_surface(discovery),
        "storage": _build_storage(discovery, analysis),
        "external_integrations": _build_external_integrations(discovery),
        "key_behaviors": _build_key_behaviors(discovery),
    }


# ── System summary ──────────────────────────────────────────────────────

def _build_system_summary(discovery: DiscoveryReport, analysis: Dict) -> str:
    """One-paragraph system summary distilled from signals."""
    parts: List[str] = []

    # Project identity
    parts.append(f"{discovery.project_name}")

    # Tech stack
    langs = discovery.language_profile
    if langs:
        top_langs = sorted(langs.items(), key=lambda x: -x[1])[:3]
        lang_str = ", ".join(f"{ext}({n})" for ext, n in top_langs)
        parts.append(f"written in {lang_str}")

    ts = discovery.tech_stack
    frameworks = ts.get("frameworks", []) or ts.get("runtime", [])
    if frameworks:
        parts.append(f"using {', '.join(frameworks[:4])}")

    # Scale
    n_ingress = len(discovery.ingress_points)
    n_egress = len(discovery.egress_points)
    n_state = len(discovery.state_models)
    parts.append(
        f"with {n_ingress} entry points, {n_egress} side-effect sites, "
        f"and {n_state} state models"
    )

    # Data journeys
    if discovery.data_journeys:
        journey_types = [j.data_type for j in discovery.data_journeys[:3]]
        parts.append(f"tracing data through: {', '.join(journey_types)}")

    return ". ".join(parts) + "."


# ── Components ──────────────────────────────────────────────────────────

def _build_components(discovery: DiscoveryReport) -> List[Dict[str, Any]]:
    """Extract logical components from orchestrators and high-centrality files."""
    components: List[Dict[str, Any]] = []
    seen_files: set = set()

    # Orchestrators are the system's nervous system
    for p in sorted(discovery.orchestrators, key=lambda x: -x.centrality_score)[:10]:
        if p.file_path in seen_files:
            continue
        seen_files.add(p.file_path)

        depends_on = [
            imp for imp in p.imports_out[:5]
            if imp not in seen_files
        ]

        components.append({
            "name": p.name,
            "file": p.file_path,
            "responsibility": p.description or _infer_responsibility(p),
            "centrality": round(p.centrality_score, 2),
            "depends_on": depends_on,
        })

    # Add high-centrality files not already captured
    for fpath, score in sorted(
        discovery.file_centrality.items(), key=lambda x: -x[1]
    )[:15]:
        if fpath in seen_files:
            continue
        seen_files.add(fpath)

        # Find the matching primitive for a description
        desc = ""
        for prim in discovery.get_all_primitives():
            if prim.file_path == fpath:
                desc = prim.description
                break

        if not desc:
            desc = f"high-centrality file (score {round(score, 2)})"

        components.append({
            "name": _filename_to_name(fpath),
            "file": fpath,
            "responsibility": desc,
            "centrality": round(score, 2),
            "depends_on": [],
        })

        if len(components) >= 15:
            break

    return components


# ── Data flows ──────────────────────────────────────────────────────────

def _build_data_flows(discovery: DiscoveryReport) -> List[str]:
    """Compact descriptions of data journeys."""
    flows: List[str] = []
    for j in discovery.data_journeys[:5]:
        through = " → ".join(
            j.transformation_points[:3]) if j.transformation_points else "direct"
        egress = ", ".join(j.egress_points[:2]) if j.egress_points else "?"
        flows.append(
            f"{j.data_type}: {j.ingress_point} → [{through}] → {egress}"
        )

    # Synthesize from primitives if no journeys traced
    if not flows and discovery.ingress_points and discovery.egress_points:
        for ing in discovery.ingress_points[:3]:
            for eg in discovery.egress_points[:2]:
                flows.append(f"{ing.name} → ... → {eg.name}")
                if len(flows) >= 3:
                    break
            if len(flows) >= 3:
                break

    return flows


# ── API surface ─────────────────────────────────────────────────────────

def _build_api_surface(discovery: DiscoveryReport) -> List[Dict[str, str]]:
    """List of exposed endpoints / entry points."""
    surface: List[Dict[str, str]] = []
    for p in discovery.ingress_points[:12]:
        surface.append({
            "name": p.name,
            "file": p.file_path,
            "type": _classify_ingress(p),
            "signals": p.description[:100] if p.description else "",
        })
    return surface


# ── Storage ─────────────────────────────────────────────────────────────

def _build_storage(
    discovery: DiscoveryReport, analysis: Dict
) -> List[Dict[str, str]]:
    """State models + detected databases."""
    storage: List[Dict[str, str]] = []

    for p in discovery.state_models[:8]:
        storage.append({
            "name": p.name,
            "file": p.file_path,
            "type": "model",
            "signals": p.description[:80] if p.description else "",
        })

    # Add database tech from analysis
    for db in analysis.get("database_tech", []):
        storage.append(
            {"name": db, "file": "", "type": "database", "signals": ""})

    return storage


# ── External integrations ───────────────────────────────────────────────

def _build_external_integrations(discovery: DiscoveryReport) -> List[Dict[str, str]]:
    """Egress points that reach outside the system."""
    integrations: List[Dict[str, str]] = []
    for p in discovery.egress_points[:10]:
        if "network" in (p.description or "").lower() or "http" in (p.description or "").lower():
            integrations.append({
                "name": p.name,
                "file": p.file_path,
                "signals": p.description[:80] if p.description else "",
            })

    # Even if no explicit network egress, list all egress as potential integrations
    if not integrations:
        for p in discovery.egress_points[:6]:
            integrations.append({
                "name": p.name,
                "file": p.file_path,
                "signals": p.description[:80] if p.description else "",
            })

    return integrations


# ── Key behaviors ───────────────────────────────────────────────────────

def _build_key_behaviors(discovery: DiscoveryReport) -> List[str]:
    """Notable patterns, constraints, and brittle points."""
    behaviors: List[str] = []

    # Constraints
    for c in discovery.constraints[:5]:
        behaviors.append(f"constraint: {c}")

    # Brittle points
    for b in discovery.brittle_points[:3]:
        behaviors.append(f"brittle: {b}")

    # Tech stack specials
    ts = discovery.tech_stack
    for category, items in ts.items():
        if items and category not in ("languages", "runtime"):
            behaviors.append(f"{category}: {', '.join(items[:3])}")

    return behaviors[:10]


# ── Utilities ───────────────────────────────────────────────────────────

def _empty_understanding() -> Dict[str, Any]:
    return {
        "system_summary": "No discovery data available.",
        "components": [],
        "data_flows": [],
        "api_surface": [],
        "storage": [],
        "external_integrations": [],
        "key_behaviors": [],
    }


def _infer_responsibility(p: DiscoveredPrimitive) -> str:
    """Infer a one-line responsibility from primitive signals."""
    if p.evidence:
        return "; ".join(p.evidence[:2])
    if p.connections:
        return f"coordinates {len(p.connections)} modules"
    return "orchestration"


def _filename_to_name(fpath: str) -> str:
    """Extract a readable name from a file path."""
    parts = fpath.replace("\\", "/").split("/")
    fname = parts[-1] if parts else fpath
    # Remove extension
    if "." in fname:
        fname = fname.rsplit(".", 1)[0]
    return fname


def _classify_ingress(p: DiscoveredPrimitive) -> str:
    """Classify an ingress point by its signals."""
    desc = (p.description or "").lower()
    if "route" in desc or "get" in desc or "post" in desc:
        return "http"
    if "cli" in desc or "command" in desc:
        return "cli"
    if "event" in desc or "listener" in desc:
        return "event"
    if "page" in desc or "ui" in desc:
        return "ui_page"
    return "entry"
