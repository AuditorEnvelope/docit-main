"""
Discovery Scanner - First-Principles Repository Analysis

This module treats every codebase as a unique biological organism.
It performs a deep-tissue scan to identify Natural Primitives:
- INGRESS: Where data/energy enters (entry points)
- EGRESS: Where the system affects the world (side effects)  
- STATE: How the system remembers (data models)
- ORCHESTRATORS: High-centrality files (system hearts)

NO TEMPLATES. NO ASSUMPTIONS. PURE DISCOVERY.
"""

import ast
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class PrimitiveType(str, Enum):
    """Natural primitives discovered in any codebase."""
    INGRESS = "ingress"      # Entry points
    EGRESS = "egress"        # Side effects
    STATE = "state"          # Data models
    ORCHESTRATOR = "orchestrator"  # High-centrality files
    TRANSFORMER = "transformer"    # Data transformation logic
    CONNECTOR = "connector"  # External integrations


@dataclass
class DiscoveredPrimitive:
    """A discovered system primitive."""
    primitive_type: PrimitiveType
    file_path: str
    name: str
    description: str
    connections: List[str] = field(default_factory=list)  # What it connects to
    imports_in: List[str] = field(default_factory=list)   # Who imports this
    imports_out: List[str] = field(default_factory=list)  # What this imports
    evidence: List[str] = field(default_factory=list)     # Code evidence
    centrality_score: float = 0.0  # Higher = more central to system


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

    # The Four Natural Primitives
    ingress_points: List[DiscoveredPrimitive]
    egress_points: List[DiscoveredPrimitive]
    state_models: List[DiscoveredPrimitive]
    orchestrators: List[DiscoveredPrimitive]

    # Derived insights
    data_journeys: List[DataJourney]

    # Centrality analysis
    file_centrality: Dict[str, float]  # file -> centrality score
    import_graph: Dict[str, List[str]]  # file -> [imported files]

    # Tech stack detected
    tech_stack: Dict[str, List[str]]

    # Constraints & "Warts" discovered
    constraints: List[str]
    brittle_points: List[str]

    def get_all_primitives(self) -> List[DiscoveredPrimitive]:
        """Get all discovered primitives."""
        return (
            self.ingress_points +
            self.egress_points +
            self.state_models +
            self.orchestrators
        )


def discover_repository(repo_dir: Path, analysis: Dict[str, Any] = None) -> DiscoveryReport:
    """
    Perform a deep-tissue scan of the repository.

    This is the main entry point for discovery. It:
    1. Scans all source files
    2. Builds import graph
    3. Identifies primitives
    4. Traces data journeys
    5. Finds constraints & brittle points
    """
    print("=" * 80)
    print("🔭 DISCOVERY SCANNER: Beginning deep-tissue scan")
    print("=" * 80)

    # Step 1: Build import graph
    print("\n📊 Phase 1: Building import graph...")
    import_graph = _build_import_graph(repo_dir)
    file_centrality = _calculate_centrality(import_graph)

    # Step 2: Identify primitives
    print("\n🔍 Phase 2: Identifying Natural Primitives...")
    ingress_points = _discover_ingress(repo_dir, analysis)
    egress_points = _discover_egress(repo_dir, analysis)
    state_models = _discover_state(repo_dir, analysis)
    orchestrators = _discover_orchestrators(
        repo_dir, file_centrality, analysis)

    # Step 3: Trace data journeys
    print("\n🛤️ Phase 3: Tracing data journeys...")
    data_journeys = _trace_data_journeys(
        repo_dir, ingress_points, egress_points, state_models
    )

    # Step 4: Find constraints & brittle points
    print("\n⚠️ Phase 4: Finding constraints & brittle points...")
    constraints = _find_constraints(repo_dir)
    brittle_points = _find_brittle_points(repo_dir)

    # Step 5: Extract tech stack
    tech_stack = _extract_tech_stack(repo_dir, analysis)

    # Determine project name
    project_name = _determine_project_name(repo_dir, analysis)

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
    )

    # Log summary
    print("\n" + "=" * 80)
    print("📋 DISCOVERY COMPLETE")
    print("=" * 80)
    print(f"  🚪 Ingress Points: {len(ingress_points)}")
    print(f"  📤 Egress Points: {len(egress_points)}")
    print(f"  💾 State Models: {len(state_models)}")
    print(f"  ❤️ Orchestrators: {len(orchestrators)}")
    print(f"  🛤️ Data Journeys: {len(data_journeys)}")
    print(f"  ⚠️ Constraints: {len(constraints)}")
    print(f"  💔 Brittle Points: {len(brittle_points)}")
    print("=" * 80)

    return report


def _build_import_graph(repo_dir: Path) -> Dict[str, List[str]]:
    """Build a graph of what each file imports."""
    import_graph = defaultdict(list)

    source_files = _get_source_files(repo_dir)

    for file_path in source_files:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            imports = _extract_imports(content, file_path, repo_dir)
            rel_path = str(file_path.relative_to(repo_dir))
            import_graph[rel_path] = imports
        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")

    return dict(import_graph)


def _calculate_centrality(import_graph: Dict[str, List[str]]) -> Dict[str, float]:
    """
    Calculate centrality score for each file.
    Higher score = more central to the system.

    Uses simple in-degree + out-degree heuristic.
    """
    centrality = defaultdict(float)

    # Count how many times each file is imported (in-degree)
    in_degree = defaultdict(int)
    for file_path, imports in import_graph.items():
        for imp in imports:
            in_degree[imp] += 1

    # Calculate centrality as combination of in-degree and out-degree
    for file_path in import_graph:
        out_degree = len(import_graph[file_path])
        centrality[file_path] = in_degree.get(file_path, 0) * 2 + out_degree

    # Normalize to 0-1 range
    if centrality:
        max_centrality = max(centrality.values())
        if max_centrality > 0:
            centrality = {k: v / max_centrality for k, v in centrality.items()}

    return dict(centrality)


def _discover_ingress(repo_dir: Path, analysis: Dict[str, Any] = None) -> List[DiscoveredPrimitive]:
    """
    Discover INGRESS points - where data/energy enters the system.

    Looks for:
    - API routes (FastAPI, Express, etc.)
    - Main functions
    - Event handlers
    - CLI commands
    - UI pages/routes
    - Webhook handlers
    """
    ingress_points = []
    source_files = _get_source_files(repo_dir)

    # Patterns that indicate entry points
    ingress_patterns = {
        # FastAPI/Python
        '@app.get': 'HTTP GET endpoint',
        '@app.post': 'HTTP POST endpoint',
        '@app.put': 'HTTP PUT endpoint',
        '@app.delete': 'HTTP DELETE endpoint',
        '@router.get': 'HTTP GET endpoint',
        '@router.post': 'HTTP POST endpoint',
        '@router.put': 'HTTP PUT endpoint',
        '@router.delete': 'HTTP DELETE endpoint',
        'def main(': 'Main entry point',
        'if __name__': 'Script entry point',

        # Express/Node
        'app.get(': 'HTTP GET endpoint',
        'app.post(': 'HTTP POST endpoint',
        'app.put(': 'HTTP PUT endpoint',
        'app.delete(': 'HTTP DELETE endpoint',
        'router.get(': 'HTTP GET endpoint',
        'router.post(': 'HTTP POST endpoint',
        'router.use(': 'Middleware entry',

        # React/Next.js
        'export default function': 'React component entry',
        'getServerSideProps': 'Next.js server entry',
        'getStaticProps': 'Next.js static entry',
        'useLoaderData': 'React Router loader',
        'useActionData': 'React Router action',

        # Event handlers
        'on_event': 'Event handler',
        'addEventListener': 'Event listener',
        '.on(': 'Event listener',
        '@EventHandler': 'Event handler',
        'def handle_': 'Handler function',
        'async def handle_': 'Async handler',

        # CLI
        '@click.command': 'CLI command',
        '@click.option': 'CLI option',
        'argparse': 'CLI argument parser',
    }

    for file_path in source_files:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(repo_dir))

            for pattern, description in ingress_patterns.items():
                if pattern in content:
                    # Extract function/route names
                    matches = _extract_ingress_names(content, pattern)
                    for match_name in matches[:3]:  # Limit to top 3
                        ingress_points.append(DiscoveredPrimitive(
                            primitive_type=PrimitiveType.INGRESS,
                            file_path=rel_path,
                            name=match_name,
                            description=description,
                            evidence=[f"Pattern: {pattern}"],
                            centrality_score=0.5,  # Entry points are moderately central
                        ))
        except Exception as e:
            logger.debug(f"Could not scan {file_path}: {e}")

    return ingress_points


def _discover_egress(repo_dir: Path, analysis: Dict[str, Any] = None) -> List[DiscoveredPrimitive]:
    """
    Discover EGRESS points - where the system affects the world.

    Looks for:
    - Database operations
    - HTTP client calls
    - File writes
    - External API calls
    - Logging/telemetry
    - Hardware I/O
    """
    egress_points = []
    source_files = _get_source_files(repo_dir)

    egress_patterns = {
        # Database
        'db.execute': 'Database write',
        'session.commit': 'Database transaction commit',
        'session.add': 'Database insert',
        'collection.insert': 'MongoDB insert',
        'collection.update': 'MongoDB update',
        '.save(': 'Model save',
        '.create(': 'Model create',
        '.delete(': 'Model delete',
        'prisma.': 'Prisma database operation',

        # HTTP Client
        'fetch(': 'HTTP client request',
        'axios.': 'Axios HTTP request',
        'httpx.': 'HTTPX request',
        'requests.': 'Requests HTTP call',
        'curl': 'HTTP request',

        # File I/O
        'writeFile': 'File write',
        'fs.write': 'File system write',
        'open(': 'File open',
        '.write(': 'Write operation',

        # External APIs
        'sendGrid': 'SendGrid email',
        'twilio': 'Twilio SMS',
        'stripe': 'Stripe payment',
        'openai': 'OpenAI API',
        'anthropic': 'Anthropic API',
        'moralis': 'Moralis Web3',

        # Logging
        'logger.': 'Logging',
        'console.log': 'Console output',
        'winston': 'Winston logging',
        'sentry': 'Sentry telemetry',

        # Blockchain
        'eth_call': 'Ethereum call',
        'sendTransaction': 'Blockchain transaction',
        'contract.': 'Smart contract call',
    }

    for file_path in source_files:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(repo_dir))

            for pattern, description in egress_patterns.items():
                if pattern.lower() in content.lower():
                    egress_points.append(DiscoveredPrimitive(
                        primitive_type=PrimitiveType.EGRESS,
                        file_path=rel_path,
                        name=pattern,
                        description=description,
                        evidence=[f"Found: {pattern}"],
                        centrality_score=0.3,
                    ))
        except Exception as e:
            logger.debug(f"Could not scan {file_path}: {e}")

    return egress_points


def _discover_state(repo_dir: Path, analysis: Dict[str, Any] = None) -> List[DiscoveredPrimitive]:
    """
    Discover STATE - how the system remembers things.

    Looks for:
    - Database schemas/models
    - TypeScript interfaces
    - React context/state
    - Global stores (Redux, Zustand)
    - Config files
    """
    state_models = []
    source_files = _get_source_files(repo_dir)

    # Look for model/schema files specifically
    model_patterns = [
        'models/', 'model/', 'schemas/', 'schema/',
        'entities/', 'types/', 'interfaces/',
    ]

    for file_path in source_files:
        try:
            rel_path = str(file_path.relative_to(repo_dir))
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Check if this is a model/schema file
            is_model_file = any(p in rel_path.lower() for p in model_patterns)

            state_indicators = [
                'class ', 'interface ', 'type ', 'schema',
                'Model', 'Entity', 'Document', 'Collection',
                'useState', 'useContext', 'createContext',
                'defineStore', 'createSlice', 'reducer',
            ]

            if is_model_file or any(ind in content for ind in state_indicators):
                # Extract class/interface/type names
                names = _extract_state_names(content, file_path.suffix)

                for name in names[:5]:  # Limit
                    state_models.append(DiscoveredPrimitive(
                        primitive_type=PrimitiveType.STATE,
                        file_path=rel_path,
                        name=name,
                        description='Data model/schema',
                        evidence=[f"Defined in {file_path.name}"],
                        centrality_score=0.7,  # State is highly central
                    ))
        except Exception as e:
            logger.debug(f"Could not scan {file_path}: {e}")

    return state_models


def _discover_orchestrators(
    repo_dir: Path,
    centrality: Dict[str, float],
    analysis: Dict[str, Any] = None
) -> List[DiscoveredPrimitive]:
    """
    Discover ORCHESTRATORS - files with high centrality.
    These are the "system hearts" that coordinate multiple components.
    """
    orchestrators = []

    # Files with centrality > 0.5 are orchestrators
    threshold = 0.5

    for file_path, score in sorted(centrality.items(), key=lambda x: -x[1]):
        if score > threshold:
            full_path = repo_dir / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(
                        encoding='utf-8', errors='ignore')
                    name = full_path.stem

                    # Determine what this orchestrates
                    description = _infer_orchestrator_role(content, file_path)

                    orchestrators.append(DiscoveredPrimitive(
                        primitive_type=PrimitiveType.ORCHESTRATOR,
                        file_path=file_path,
                        name=name,
                        description=description,
                        centrality_score=score,
                    ))
                except Exception as e:
                    logger.debug(f"Could not read {full_path}: {e}")

    return orchestrators[:10]  # Top 10 orchestrators


def _trace_data_journeys(
    repo_dir: Path,
    ingress: List[DiscoveredPrimitive],
    egress: List[DiscoveredPrimitive],
    state: List[DiscoveredPrimitive],
) -> List[DataJourney]:
    """
    Trace the most important data objects through the codebase.
    From raw input → transformation → final persistence/egress.
    """
    journeys = []

    # Pick the most important data types from state
    key_data_types = [s.name for s in state[:5]] if state else ['Unknown']

    # For each key data type, try to trace its journey
    for data_type in key_data_types[:3]:
        # Find where it enters
        entry = ingress[0].file_path if ingress else "Unknown"

        # Find where it's transformed (look for processing files)
        transformation_points = _find_transformation_points(
            repo_dir, data_type)

        # Find where it persists
        persistence = state[0].file_path if state else None

        # Find where it exits
        exit_points = [e.file_path for e in egress[:3]]

        journeys.append(DataJourney(
            data_type=data_type,
            ingress_point=entry,
            transformation_points=transformation_points,
            persistence_point=persistence,
            egress_points=exit_points,
            journey_description=f"{data_type} flows from {entry} through processing to persistence/egress",
        ))

    return journeys


def _find_constraints(repo_dir: Path) -> List[str]:
    """Find system constraints - limitations, assumptions, requirements."""
    constraints = []
    source_files = _get_source_files(repo_dir)

    constraint_patterns = [
        r'TODO:.*',
        r'FIXME:.*',
        r'HACK:.*',
        r'WARNING:.*',
        r'LIMITATION:.*',
        r'NOTE:.*',
        r'MUST:.*',
        r'SHALL:.*',
        r'constraint',
        r'limitation',
        r'maximum',
        r'minimum',
        r'rate limit',
        r'timeout',
        r'deprecated',
    ]

    for file_path in source_files[:50]:  # Limit for performance
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(repo_dir))

            for pattern in constraint_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:2]:  # Limit per file
                    constraint = f"{rel_path}: {match[:100]}"
                    if constraint not in constraints:
                        constraints.append(constraint)
        except Exception:
            pass

    return constraints[:20]  # Top 20 constraints


def _find_brittle_points(repo_dir: Path) -> List[str]:
    """Find brittle code - complex regex, timing dependencies, recursive logic."""
    brittle_points = []
    source_files = _get_source_files(repo_dir)

    brittle_patterns = [
        (r're\.(compile|match|search)', 'Complex regex'),
        (r'setTimeout|setInterval', 'Timing dependency'),
        (r'recursive|recurse', 'Recursive logic'),
        (r'sleep|wait|delay', 'Timing dependency'),
        (r'while True', 'Infinite loop risk'),
        (r'except.*pass', 'Silent exception swallowing'),
        (r'catch.*{}', 'Silent error handling'),
        (r'any\)', 'Loose typing'),
        (r'// @ts-ignore', 'TypeScript ignore'),
        (r'# type: ignore', 'Python type ignore'),
    ]

    for file_path in source_files[:50]:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(repo_dir))

            for pattern, description in brittle_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    brittle_points.append(f"{rel_path}: {description}")
        except Exception:
            pass

    return brittle_points[:15]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_source_files(repo_dir: Path) -> List[Path]:
    """Get all source files in the repository."""
    extensions = {'.py', '.js', '.ts', '.tsx',
                  '.jsx', '.go', '.java', '.rs', '.rb'}
    exclude_dirs = {'node_modules', '.git', '__pycache__',
                    'dist', 'build', 'venv', '.venv', 'env'}

    source_files = []
    for ext in extensions:
        for file_path in repo_dir.rglob(f'*{ext}'):
            if not any(d in file_path.parts for d in exclude_dirs):
                source_files.append(file_path)

    return source_files


def _extract_imports(content: str, file_path: Path, repo_dir: Path) -> List[str]:
    """Extract import statements from file content."""
    imports = []

    # Python imports
    py_imports = re.findall(
        r'^(?:from|import)\s+([^\s#]+)', content, re.MULTILINE)
    imports.extend(py_imports)

    # JS/TS imports
    js_imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
    imports.extend(js_imports)

    # Also handle require
    requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
    imports.extend(requires)

    return list(set(imports))


def _extract_ingress_names(content: str, pattern: str) -> List[str]:
    """Extract function/route names for ingress points."""
    names = []

    # Try to extract function name after pattern
    # Handle decorators like @app.get("/path")
    if '@' in pattern:
        matches = re.findall(
            rf'{re.escape(pattern)}[^)]*\)\s*(?:async\s+)?def\s+(\w+)', content)
        names.extend(matches)

    # Handle function definitions
    func_matches = re.findall(r'def\s+(\w+)\s*\(', content)
    names.extend(func_matches[:2])

    return list(set(names)) if names else ['entry_point']


def _extract_state_names(content: str, suffix: str) -> List[str]:
    """Extract class/interface/type names for state models."""
    names = []

    if suffix in {'.py'}:
        # Python classes
        names = re.findall(r'class\s+(\w+)', content)
    elif suffix in {'.ts', '.tsx'}:
        # TypeScript interfaces and types
        names = re.findall(r'(?:interface|type|class)\s+(\w+)', content)
    elif suffix in {'.js', '.jsx'}:
        # JavaScript classes
        names = re.findall(r'class\s+(\w+)', content)

    return names


def _find_transformation_points(repo_dir: Path, data_type: str) -> List[str]:
    """Find files that transform the given data type."""
    # Simple heuristic: find files that mention the data type
    transformation_points = []
    source_files = _get_source_files(repo_dir)

    for file_path in source_files[:30]:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if data_type.lower() in content.lower():
                rel_path = str(file_path.relative_to(repo_dir))
                transformation_points.append(rel_path)
        except Exception:
            pass

    return transformation_points[:5]


def _infer_orchestrator_role(content: str, file_path: str) -> str:
    """Infer the role of an orchestrator file."""
    content_lower = content.lower()

    if 'router' in content_lower or 'route' in content_lower:
        return 'Request routing & endpoint coordination'
    elif 'service' in file_path.lower():
        return 'Business logic coordination'
    elif 'controller' in file_path.lower():
        return 'Request handling & response coordination'
    elif 'loader' in file_path.lower():
        return 'Application initialization & dependency wiring'
    elif 'index' in file_path.lower():
        return 'Module export & public API surface'
    elif 'util' in file_path.lower() or 'helper' in file_path.lower():
        return 'Shared utility coordination'
    else:
        return 'Cross-cutting coordination'


def _extract_tech_stack(repo_dir: Path, analysis: Dict[str, Any] = None) -> Dict[str, List[str]]:
    """Extract tech stack from analysis or files."""
    if analysis and 'frameworks' in analysis:
        return {
            'frameworks': analysis.get('frameworks', []),
            'languages': analysis.get('languages', []),
            'databases': analysis.get('database_tech', []),
        }

    # Fallback: detect from files
    tech_stack = {'frameworks': [], 'languages': [], 'databases': []}

    # Check package.json
    pkg_json = repo_dir / 'package.json'
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            deps = {**data.get('dependencies', {}), **
                    data.get('devDependencies', {})}

            if 'react' in deps:
                tech_stack['frameworks'].append('React')
            if 'express' in deps:
                tech_stack['frameworks'].append('Express')
            if 'next' in deps:
                tech_stack['frameworks'].append('Next.js')
            if 'fastapi' in deps:
                tech_stack['frameworks'].append('FastAPI')
        except Exception:
            pass

    # Detect languages from file extensions
    source_files = _get_source_files(repo_dir)
    extensions = set(f.suffix for f in source_files)

    if '.py' in extensions:
        tech_stack['languages'].append('Python')
    if '.ts' in extensions or '.tsx' in extensions:
        tech_stack['languages'].append('TypeScript')
    if '.js' in extensions or '.jsx' in extensions:
        tech_stack['languages'].append('JavaScript')
    if '.go' in extensions:
        tech_stack['languages'].append('Go')

    return tech_stack


def _determine_project_name(repo_dir: Path, analysis: Dict[str, Any] = None) -> str:
    """Determine the project name from analysis or files."""
    # Check analysis first
    if analysis:
        if analysis.get('package_name'):
            return analysis['package_name']
        if analysis.get('project_name') and not analysis['project_name'].startswith('docai'):
            return analysis['project_name']

    # Check package.json
    pkg_json = repo_dir / 'package.json'
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            if data.get('name') and not data['name'].startswith('docai'):
                return data['name']
        except Exception:
            pass

    # Fall back to directory name
    return repo_dir.name
